import json
import sys
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Any

# Add the 'src' directory to the path so we can import 'core'
sys.path.append(str(Path(__file__).resolve().parent.parent))

from langchain_core.prompts import ChatPromptTemplate
from core.models import TargetProfile, CompanyProfile, SenderContext
from core.llm_client import create_llm

# --- Matchmaker Output Models ---
class OutreachAngle(BaseModel):
    angle_name: str = Field(description="A short name for this strategic angle, e.g., 'Alumni Connection' or 'Burnout Solution'")
    psychological_reasoning: str = Field(description="WHY this specific angle will work on this specific person, based on CRO and psychological alignment.")
    hook_sentence: str = Field(description="A 1-2 sentence opening hook expressing this angle, ready to be used in an email or DM.")

class MatchmakerResult(BaseModel):
    selected_angles: List[OutreachAngle] = Field(description="2 to 3 highly tailored angles for outreach.")

class MatchmakerAgent:
    def __init__(self):
        self.llm = create_llm()
        
        # Load the external markdown prompt
        prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "matchmaker_system.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Missing prompt file at: {prompt_path}")
            
        self.system_prompt = prompt_path.read_text(encoding="utf-8")

    def generate_angles(
        self, 
        target_profile: TargetProfile, 
        sender_context: SenderContext,
        analyst_insights: Any,  # Using Any to easily accept dict or AnalystInsights object
        company_profile: Optional[CompanyProfile] = None
    ) -> MatchmakerResult:
        """
        Synthesizes all context to generate high-converting outreach angles.
        """
        structured_llm = self.llm.with_structured_output(MatchmakerResult)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "TARGET PROFILE:\n{target_json}\n\nTARGET INSIGHTS:\n{insights_json}\n\nSENDER CONTEXT:\n{sender_json}\n\nCOMPANY PROFILE:\n{company_json}")
        ])
        
        chain = prompt | structured_llm
        print("Generating Matchmaker Angles...")
        
        # Handle analyst_insights depending on whether it's a Pydantic model or a dictionary
        if hasattr(analyst_insights, "model_dump_json"):
            insights_formatted = analyst_insights.model_dump_json(indent=2)
        else:
            insights_formatted = json.dumps(analyst_insights, indent=2)
            
        return chain.invoke({
            "target_json": target_profile.model_dump_json(indent=2),
            "insights_json": insights_formatted,
            "sender_json": sender_context.model_dump_json(indent=2),
            "company_json": company_profile.model_dump_json(indent=2) if company_profile else "No company data available."
        })

# --- Example Usage for Testing ---
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Mocking Sender Context for testing
    mock_sender = SenderContext(
        sender_name="Dis70rt",
        sender_current_status="Founder of an AI growth agency",
        sender_core_competencies=["AI Automation", "LangChain", "CRO", "Cold Outreach"],
        sender_highlight_projects=["Built an AI matchmaker agent that increased response rates by 200%"],
        ask_type="Networking/Collaboration"
    )
    
    # (In a real flow, you would pass your actual scraped profiles and analyst results here)
    # mock_target = ...
    # mock_company = ...
    # mock_insights = ...
    
    print("Matchmaker script is ready to go! Ensure you pass the outputs from the Extractor and Analyst to use it.")