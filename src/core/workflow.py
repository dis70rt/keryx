from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from src.agents.copywriter import CopywriterAgent
from src.agents.matchmaker import MatchmakerAgent
from src.agents.profile_extract import ProfileExtractionAgent
from src.agents.reviewer import ReviewerAgent
from src.core.models import CompanyProfile, SenderContext, TargetProfile
from src.tools.sender_rag import SenderRAG
from src.tools.memory import EpisodicMemory
from src.core.logger import logger


class GraphState(TypedDict):
    raw_profile_text: str
    raw_company_text: str | None
    platform: str

    sender_context: SenderContext

    target_profile: TargetProfile | None
    company_profile: CompanyProfile | None

    analyst_insights: dict[str, Any] | None
    outreach_angles: list[dict[str, str]] | None
    selected_angle: dict[str, str] | None

    # RAG: dynamically retrieved sender context
    relevant_sender_context: str | None
    sender_rag: Any  # SenderRAG instance (not serializable, passed by ref)

    # Episodic Memory
    past_successful_hooks: str | None
    episodic_memory: Any  # EpisodicMemory instance

    connection_note: str | None
    dm_message: str | None
    drafted_messages: dict[str, str] | None

    review_feedback: str | None
    revision_count: int
    final_passed: bool


extractor = ProfileExtractionAgent()
matchmaker = MatchmakerAgent()
copywriter = CopywriterAgent()
reviewer = ReviewerAgent()


def extract_node(state: GraphState) -> dict:
    logger.step("[Extractor] Parsing profiles")

    try:
        t_prof = extractor.extract_target_profile(state["raw_profile_text"])
    except Exception as e:
        logger.warn(f"Target extraction failed: {e}")
        # Build a minimal skeleton so the pipeline can still attempt outreach
        from src.core.models import TargetProfile
        t_prof = TargetProfile(
            first_name="Unknown",
            last_name="",
            current_title="Professional",
            professional_summary="Could not extract profile details.",
        )

    c_prof = None
    if state.get("raw_company_text"):
        try:
            c_prof = extractor.extract_company_profile(state["raw_company_text"])
        except Exception as e:
            logger.warn(f"Company extraction failed: {e}")

    insights = {
        "professional_summary": t_prof.professional_summary,
        "communication_style": t_prof.communication_style,
        "inferred_interests": t_prof.inferred_interests,
        "recent_themes": [t.model_dump() for t in t_prof.recent_activity_themes],
    }

    return {
        "target_profile": t_prof,
        "company_profile": c_prof,
        "analyst_insights": insights,
    }


def retriever_node(state: GraphState) -> dict:
    """RAG node: retrieve only the most relevant sender context for this target."""
    logger.step("[Retriever] Finding relevant sender context")
    sender_rag: SenderRAG | None = state.get("sender_rag")

    if not sender_rag:
        logger.warn("No RAG index available, using full sender context.")
        return {"relevant_sender_context": None}

    # Build a query from the target's extracted data
    target = state.get("target_profile")
    company = state.get("company_profile")

    query_parts: list[str] = []
    if target:
        query_parts.extend(target.skills_and_endorsements[:5])
        if target.current_title:
            query_parts.append(target.current_title)
    if company:
        query_parts.extend(company.core_tech_stack[:5])
        if company.industry_and_domain:
            query_parts.append(company.industry_and_domain)

    query = ", ".join(query_parts) if query_parts else "software engineering"

    with logger.status("Querying vector store..."):
        retrieved = sender_rag.retrieve(query, k=3)
        
    logger.success(f"Retrieved {len(retrieved.splitlines())} relevant context chunks")
    return {"relevant_sender_context": retrieved}


def memory_recall_node(state: GraphState) -> dict:
    """Episodic Memory recall: fetch past successful hooks for this target type."""
    logger.step("[Memory] Recalling past successful hooks")
    memory: EpisodicMemory | None = state.get("episodic_memory")

    if not memory:
        logger.warn("No episodic memory available.")
        return {"past_successful_hooks": None}

    target = state.get("target_profile")
    company = state.get("company_profile")

    industry = ""
    title = ""
    if company and company.industry_and_domain:
        industry = company.industry_and_domain
    if target and target.current_title:
        title = target.current_title

    with logger.status("Querying cache.db..."):
        hooks = memory.recall(target_industry=industry, target_title=title, limit=3)
        formatted = memory.format_for_prompt(hooks)

    if hooks:
        logger.success(f"Found {len(hooks)} relevant past hooks")
    else:
        logger.sub_step("No past hooks yet (cold start)")

    return {"past_successful_hooks": formatted if formatted else None}


def matchmaker_node(state: GraphState) -> dict:
    logger.step("[Matchmaker] Generating angles")
    result = matchmaker.generate_angles(
        target_profile=state["target_profile"],
        sender_context=state["sender_context"],
        analyst_insights=state["analyst_insights"],
        company_profile=state.get("company_profile"),
        past_hooks=state.get("past_successful_hooks"),
    )
    angles = [a.model_dump() for a in result.selected_angles]
    return {
        "outreach_angles": angles,
        "selected_angle": angles[0] if angles else None,
    }


def copywriter_node(state: GraphState) -> dict:
    revision = state.get("revision_count", 0)
    logger.step(f"[Copywriter] Drafting messages (revision #{revision})")

    # On retries, pass the Reviewer's feedback so the Copywriter knows WHY
    # the previous draft was rejected, instead of blindly regenerating.
    feedback = state.get("review_feedback") if revision > 0 else None

    try:
        result = copywriter.draft_messages(
            target_profile=state["target_profile"],
            sender_context=state["sender_context"],
            selected_angle=state["selected_angle"],
            platform=state["platform"],
            relevant_context=state.get("relevant_sender_context"),
            review_feedback=feedback,
        )

        return {
            "connection_note": result.connection_note,
            "dm_message": result.dm_message,
            "drafted_messages": result.model_dump(),
            "revision_count": revision + 1,
        }
    except Exception as e:
        # If the LLM produces garbage tokens on a retry, don't crash the
        # whole pipeline.  Fall back to whatever draft is already in state
        # (the Reviewer may have written suggested rewrites).
        logger.warn(f"Copywriter LLM error: {e}")
        logger.sub_step("Falling back to previous draft in state.")
        return {
            "revision_count": revision + 1,
            "review_feedback": None,  # clear feedback to stop retry loop
        }


def reviewer_node(state: GraphState) -> dict:
    logger.step("[Reviewer] Quality check")

    try:
        result = reviewer.review(
            drafted_messages=state["drafted_messages"],
            target_context=state["target_profile"].model_dump(),
            angle_used=state["selected_angle"],
        )
    except Exception as e:
        # If the Reviewer LLM produces garbage, auto-approve.
        # The draft already passed the Copywriter and is usable.
        logger.warn(f"Reviewer LLM error: {e}")
        logger.sub_step("Auto-approving current draft.")
        return {"final_passed": True}

    if result.passes_criteria:
        logger.success("Approved")
        return {"final_passed": True}

    logger.error(f"Rejected: {result.critique}")

    updates: dict[str, Any] = {"review_feedback": result.critique}
    if result.suggested_connection_note:
        updates["connection_note"] = result.suggested_connection_note
    if result.suggested_dm_message:
        updates["dm_message"] = result.suggested_dm_message
    return updates


def memory_store_node(state: GraphState) -> dict:
    """Store the approved hook into episodic memory for future recall."""
    memory: EpisodicMemory | None = state.get("episodic_memory")
    if not memory or not state.get("final_passed"):
        return {}

    target = state.get("target_profile")
    company = state.get("company_profile")
    angle = state.get("selected_angle", {})

    industry = company.industry_and_domain if company else "Unknown"
    title = target.current_title if target else "Unknown"
    name = f"{target.first_name} {target.last_name}" if target else "Unknown"

    memory.record_success(
        target_industry=industry,
        target_title=title,
        target_name=name,
        hook_name=angle.get("angle_name", ""),
        hook_reasoning=angle.get("psychological_reasoning", ""),
        hook_sentence=angle.get("hook_sentence", ""),
    )
    logger.success("Hook stored in episodic memory")
    return {}

def should_continue(state: GraphState) -> str:
    max_revisions = 2
    if state.get("final_passed"):
        return "store_memory"
    if state.get("revision_count", 0) >= max_revisions:
        logger.warn("Max revisions reached. Forcing approval.")
        return "store_memory"
    return "retry"


def build_workflow() -> StateGraph:
    workflow = StateGraph(GraphState)

    workflow.add_node("Extractor", extract_node)
    workflow.add_node("Retriever", retriever_node)
    workflow.add_node("MemoryRecall", memory_recall_node)
    workflow.add_node("Matchmaker", matchmaker_node)
    workflow.add_node("Copywriter", copywriter_node)
    workflow.add_node("Reviewer", reviewer_node)
    workflow.add_node("MemoryStore", memory_store_node)

    # Linear flow: Extract → Retrieve → Recall → Match → Copy → Review
    workflow.set_entry_point("Extractor")
    workflow.add_edge("Extractor", "Retriever")
    workflow.add_edge("Retriever", "MemoryRecall")
    workflow.add_edge("MemoryRecall", "Matchmaker")
    workflow.add_edge("Matchmaker", "Copywriter")
    workflow.add_edge("Copywriter", "Reviewer")

    # Conditional: Reviewer → MemoryStore (approved/max) or → Copywriter (retry)
    workflow.add_conditional_edges(
        "Reviewer",
        should_continue,
        {"store_memory": "MemoryStore", "retry": "Copywriter"},
    )
    workflow.add_edge("MemoryStore", END)

    return workflow


app = build_workflow().compile()