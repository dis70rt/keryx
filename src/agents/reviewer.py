import sys
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional, Any

# Add the 'src' directory to the path so we can import 'core'
sys.path.append(str(Path(__file__).resolve().parent.parent))

from langchain_core.prompts import ChatPromptTemplate
from core.llm_client import create_llm

# --- Reviewer Output Model ---
class ReviewResult(BaseModel):
    passes_criteria: bool = Field(description="True ONLY if the message is flawless, human-sounding, and ready to send. False if it needs revision.")
    critique: str = Field(description="Detailed explanation of what is wrong (e.g., 'Too long', 'Sounds like AI', 'CTA is too demanding') or why it passed.")
    suggested_revision: Optional[str] = Field(description="If it failed, provide a heavily revised, polished version that fixes the issues.")

class ReviewerAgent:
    def __init__(self):
        # We might want a lower temperature for the reviewer so it's strictly analytical
        self.llm = create_llm()
        # Optionally override temperature if your llm_client supports it:
        # self.llm.temperature = 0.2
        
        prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "reviewer_system.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Missing prompt file at: {prompt_path}")
            
        self.system_prompt = prompt_path.read_text(encoding="utf-8")

    def review(
        self, 
        drafted_message: Any, # Accepts dict or DraftedMessage object
        target_context: Any,
        angle_used: Any
    ) -> ReviewResult:
        """
        Critiques a drafted message and decides if it is ready to send.
        """
        structured_llm = self.llm.with_structured_output(ReviewResult)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", """
            Please review the following draft.
            
            TARGET CONTEXT:
            {target_json}
            
            ANGLE SUPPOSED TO BE USED:
            {angle_json}
            
            DRAFTED MESSAGE TO REVIEW:
            {draft_json}
            """)
        ])
        
        chain = prompt | structured_llm
        print("Running Quality Assurance Check...")
        
        # Format inputs safely
        def safe_format(obj):
            if hasattr(obj, "model_dump_json"):
                return obj.model_dump_json(indent=2)
            return str(obj)
            
        return chain.invoke({
            "target_json": safe_format(target_context),
            "angle_json": safe_format(angle_used),
            "draft_json": safe_format(drafted_message)
        })

# --- Example Usage for Testing ---
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # 1. Provide a BAD draft to see if the Critic catches it
    bad_draft = {
        "subject_line": "Synergizing our core competencies",
        "message_body": "I hope this email finds you well. I was deeply impressed by your tapestry of experience on LinkedIn. As you transition into entrepreneurship, I believe our AI services can unlock transformative growth for your endeavors. Would you be open to a 45-minute discovery call next Tuesday to delve into how we can align our synergies?",
        "word_count": 55
    }
    
    mock_angle = "Entrepreneurship Leap: Acknowledge the fear of his recent transition to self-employment."
    mock_target = {"name": "Edward", "communication_style": "Casual"}
    
    reviewer = ReviewerAgent()
    result = reviewer.review(
        drafted_message=bad_draft,
        target_context=mock_target,
        angle_used=mock_angle
    )
    
    print("\n--- REVIEW RESULTS ---")
    print(f"PASSED: {result.passes_criteria}")
    print(f"CRITIQUE: {result.critique}")
    if result.suggested_revision:
        print(f"\nSUGGESTED REVISION:\n{result.suggested_revision}")