import sys
from pathlib import Path
from typing import TypedDict, Optional, Dict, Any, List

# Add the 'src' directory to the path 
sys.path.append(str(Path(__file__).resolve().parent.parent))

from langgraph.graph import StateGraph, END
from core.models import TargetProfile, CompanyProfile, SenderContext
from agents.profile_extract import ProfileExtractionAgent
from agents.analyst import AnalystAgent
from agents.matchmaker import MatchmakerAgent
from agents.copywriter import CopywriterAgent
from agents.reviewer import ReviewerAgent

# --- 1. Define the State ---
# This dictionary gets passed from node to node.
class GraphState(TypedDict):
    raw_profile_text: str
    raw_company_text: Optional[str]
    platform: str
    
    sender_context: SenderContext
    
    target_profile: Optional[TargetProfile]
    company_profile: Optional[CompanyProfile]
    
    analyst_insights: Optional[Dict[str, Any]]
    outreach_angles: Optional[List[Dict[str, str]]]
    selected_angle: Optional[Dict[str, str]]
    
    drafted_message: Optional[Dict[str, Any]]
    review_feedback: Optional[str]
    revision_count: int
    final_passed_message: Optional[Dict[str, Any]]


# --- 2. Initialize Agents ---
# We initialize them once outside the nodes to save overhead
extractor = ProfileExtractionAgent()
analyst = AnalystAgent()
matchmaker = MatchmakerAgent()
copywriter = CopywriterAgent()
reviewer = ReviewerAgent()


# --- 3. Define the Nodes ---

def extract_node(state: GraphState) -> GraphState:
    print("Graph: [Extracting Profiles]")
    t_prof = extractor.extract_target_profile(state["raw_profile_text"])
    
    c_prof = None
    if state.get("raw_company_text"):
        c_prof = extractor.extract_company_profile(state["raw_company_text"])
        
    return {
        "target_profile": t_prof, 
        "company_profile": c_prof
    }

def analyst_node(state: GraphState) -> GraphState:
    print("Graph: [Analyzing Psychology]")
    insights = analyst.analyze(state["target_profile"], state.get("company_profile"))
    return {"analyst_insights": insights.model_dump()}

def matchmaker_node(state: GraphState) -> GraphState:
    print("Graph: [Generating Angles]")
    result = matchmaker.generate_angles(
        target_profile=state["target_profile"],
        sender_context=state["sender_context"],
        analyst_insights=state["analyst_insights"],
        company_profile=state.get("company_profile")
    )
    # For now, we auto-select the first angle generated.
    angles = [a.model_dump() for a in result.selected_angles]
    return {
        "outreach_angles": angles,
        "selected_angle": angles[0] if angles else None
    }

def copywriter_node(state: GraphState) -> GraphState:
    print(f"Graph: [Drafting Message] (Revision count: {state.get('revision_count', 0)})")
    
    # If the critic failed the last iteration, we should technically inject the feedback 
    # into the copywriter. For simplicity, the critic provides a suggested_revision 
    # which we can handle in the critic node, but the copywriter will try again here.
    
    draft = copywriter.draft_message(
        target_profile=state["target_profile"],
        sender_context=state["sender_context"],
        selected_angle=state["selected_angle"],
        platform=state["platform"]
    )
    
    return {
        "drafted_message": draft.model_dump(),
        "revision_count": state.get('revision_count', 0) + 1
    }

def reviewer_node(state: GraphState) -> GraphState:
    print("Graph: [Reviewing Draft]")
    result = reviewer.review(
        drafted_message=state["drafted_message"],
        target_context=state["target_profile"].model_dump(),
        angle_used=state["selected_angle"]
    )
    
    if result.passes_criteria:
        print("-> Critic PASSED the message.")
        return {"final_passed_message": state["drafted_message"]}
    else:
        print("-> Critic FAILED the message:")
        print(f"   Feedback: {result.critique}")
        return {"review_feedback": result.critique}

# --- 4. Define the Edge Logic (Routing) ---
def should_continue(state: GraphState) -> str:
    """Decides if we are done or if we need to draft again."""
    maximum_revisions = 3
    
    if state.get("final_passed_message"):
        return "end" # Passed! Output it.
    elif state.get("revision_count", 0) >= maximum_revisions:
        print("-> Reached max revisions. Forcing approval.")
        return "end"
    else:
        return "retry" # Failed, go back to copywriter

# --- 5. Build the Graph ---
workflow = StateGraph(GraphState)

workflow.add_node("Extractor", extract_node)
workflow.add_node("Analyst", analyst_node)
workflow.add_node("Matchmaker", matchmaker_node)
workflow.add_node("Copywriter", copywriter_node)
workflow.add_node("Reviewer", reviewer_node)

# Linear flow up until the copywriter
workflow.set_entry_point("Extractor")
workflow.add_edge("Extractor", "Analyst")
workflow.add_edge("Analyst", "Matchmaker")
workflow.add_edge("Matchmaker", "Copywriter")
workflow.add_edge("Copywriter", "Reviewer")

# Conditional loop from reviewer back to copywriter
workflow.add_conditional_edges(
    "Reviewer",
    should_continue,
    {
        "end": END,
        "retry": "Copywriter"
    }
)

app = workflow.compile()