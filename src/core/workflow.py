from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from src.agents.copywriter import CopywriterAgent
from src.agents.matchmaker import MatchmakerAgent
from src.agents.profile_extract import ProfileExtractionAgent
from src.agents.reviewer import ReviewerAgent
from src.core.models import CompanyProfile, SenderContext, TargetProfile


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
    print("▸ [Extractor] Parsing profiles...")
    t_prof = extractor.extract_target_profile(state["raw_profile_text"])

    c_prof = None
    if state.get("raw_company_text"):
        c_prof = extractor.extract_company_profile(state["raw_company_text"])

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


def matchmaker_node(state: GraphState) -> dict:
    print("▸ [Matchmaker] Generating angles...")
    result = matchmaker.generate_angles(
        target_profile=state["target_profile"],
        sender_context=state["sender_context"],
        analyst_insights=state["analyst_insights"],
        company_profile=state.get("company_profile"),
    )
    angles = [a.model_dump() for a in result.selected_angles]
    return {
        "outreach_angles": angles,
        "selected_angle": angles[0] if angles else None,
    }


def copywriter_node(state: GraphState) -> dict:
    revision = state.get("revision_count", 0)
    print(f"▸ [Copywriter] Drafting messages (revision #{revision})...")

    result = copywriter.draft_messages(
        target_profile=state["target_profile"],
        sender_context=state["sender_context"],
        selected_angle=state["selected_angle"],
        platform=state["platform"],
    )

    return {
        "connection_note": result.connection_note,
        "dm_message": result.dm_message,
        "drafted_messages": result.model_dump(),
        "revision_count": revision + 1,
    }


def reviewer_node(state: GraphState) -> dict:
    print("▸ [Reviewer] Quality check...")
    result = reviewer.review(
        drafted_messages=state["drafted_messages"],
        target_context=state["target_profile"].model_dump(),
        angle_used=state["selected_angle"],
    )

    if result.passes_criteria:
        print("  ✓ Approved")
        return {"final_passed": True}

    print(f"  ✗ Rejected: {result.critique}")

    updates: dict[str, Any] = {"review_feedback": result.critique}
    if result.suggested_connection_note:
        updates["connection_note"] = result.suggested_connection_note
    if result.suggested_dm_message:
        updates["dm_message"] = result.suggested_dm_message
    return updates


def should_continue(state: GraphState) -> str:
    max_revisions = 3
    if state.get("final_passed"):
        return "end"
    if state.get("revision_count", 0) >= max_revisions:
        print("  ⚠ Max revisions reached. Forcing approval.")
        return "end"
    return "retry"


def build_workflow() -> StateGraph:
    workflow = StateGraph(GraphState)

    workflow.add_node("Extractor", extract_node)
    workflow.add_node("Matchmaker", matchmaker_node)
    workflow.add_node("Copywriter", copywriter_node)
    workflow.add_node("Reviewer", reviewer_node)

    workflow.set_entry_point("Extractor")
    workflow.add_edge("Extractor", "Matchmaker")
    workflow.add_edge("Matchmaker", "Copywriter")
    workflow.add_edge("Copywriter", "Reviewer")

    workflow.add_conditional_edges(
        "Reviewer",
        should_continue,
        {"end": END, "retry": "Copywriter"},
    )

    return workflow


app = build_workflow().compile()