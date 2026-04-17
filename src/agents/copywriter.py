import sys
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional, Any

# Add the 'src' directory to the path so we can import 'core'
sys.path.append(str(Path(__file__).resolve().parent.parent))

from langchain_core.prompts import ChatPromptTemplate
from core.models import TargetProfile, SenderContext
from core.llm_client import create_llm

# --- Copywriter Output Model ---
class DraftedMessage(BaseModel):
    subject_line: Optional[str] = Field(description="A short, catchy subject line (leave blank if the platform is LinkedIn DM).")
    message_body: str = Field(description="The complete, finalized outreach message, strictly under 100 words.")
    word_count: int = Field(description="The exact word count of the message body (to verify adherence to the limit).")

class CopywriterAgent:
    def __init__(self):
        self.llm = create_llm()
        
        # Load the external markdown prompt
        prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "copywriter_system.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Missing prompt file at: {prompt_path}")
            
        self.system_prompt = prompt_path.read_text(encoding="utf-8")

    def draft_message(
        self, 
        target_profile: TargetProfile, 
        sender_context: SenderContext,
        selected_angle: Any,  # Using Any to accept the OutreachAngle dict or Pydantic model
        platform: str = "LinkedIn"
    ) -> DraftedMessage:
        """
        Drafts the final outreach message based on the selected angle.
        """
        structured_llm = self.llm.with_structured_output(DraftedMessage)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", """
            PLATFORM: {platform}
            
            TARGET CONTEXT:
            Name: {target_name}
            Title: {target_title}
            Communication Style: {target_style}
            
            SENDER CONTEXT (Ask Type): {sender_ask}
            
            SELECTED ANGLE & HOOK:
            {angle_json}
            """)
        ])
        
        chain = prompt | structured_llm
        print(f"Drafting final {platform} message...")
        
        # Extract angle data whether it's a dict or a Pydantic object
        if hasattr(selected_angle, "model_dump_json"):
            angle_formatted = selected_angle.model_dump_json(indent=2)
        else:
            angle_formatted = str(selected_angle)
            
        return chain.invoke({
            "platform": platform,
            "target_name": f"{target_profile.first_name} {target_profile.last_name}",
            "target_title": target_profile.current_title,
            "target_style": target_profile.communication_style,
            "sender_ask": sender_context.ask_type,
            "angle_json": angle_formatted
        })

# --- Example Usage for Testing ---
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Mocking data to test the Copywriter directly
    # (In Production, these come from your previous agents)
    mock_target = TargetProfile(
        first_name="Edward",
        last_name="Sun",
        current_title="Brand & Web Designer / Content Creator",
        professional_summary="Christian-led brand designer who recently went independent.",
        past_experience=[],
        skills_and_endorsements=[],
        recent_activity_themes=[],
        inferred_interests=[],
        communication_style="Casual, authentic, and highly relatable. Uses emojis."
    )
    
    mock_sender = SenderContext(
        sender_name="Dis70rt",
        sender_current_status="Founder of AI Growth Agency",
        sender_core_competencies=[],
        sender_highlight_projects=[],
        ask_type="Collaboration/Networking"
    )
    
    mock_angle = {
        "angle_name": "Entrepreneurship Leap",
        "psychological_reasoning": "He recently quit his job to go solo and posted about the fears associated with it. Validating that courage builds instant rapport.",
        "hook_sentence": "Edward, massive respect for taking the leap into full-time self-employment—I know exactly how terrifying that first month is."
    }
    
    copywriter = CopywriterAgent()
    draft = copywriter.draft_message(
        target_profile=mock_target,
        sender_context=mock_sender,
        selected_angle=mock_angle,
        platform="LinkedIn DM"
    )
    
    print("\n--- FINAL MESSAGE ---")
    if draft.subject_line:
        print(f"Subject: {draft.subject_line}\n")
    print(draft.message_body)
    print(f"\n(Word Count: {draft.word_count})")