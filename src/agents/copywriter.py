from pathlib import Path
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from src.core.llm_client import create_llm
from src.core.models import GeneratedMessages, SenderContext, TargetProfile


class CopywriterAgent:
    def __init__(self) -> None:
        self.llm = create_llm()
        prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "copywriter_system.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Missing prompt file at: {prompt_path}")
        self.system_prompt = prompt_path.read_text(encoding="utf-8")

    def draft_messages(
        self,
        target_profile: TargetProfile,
        sender_context: SenderContext,
        selected_angle: Any,
        platform: str = "LinkedIn",
        relevant_context: str | None = None,
        review_feedback: str | None = None,
    ) -> GeneratedMessages:
        """Draft both a connection note and a DM message in a single LLM call."""
        structured_llm = self.llm.with_structured_output(GeneratedMessages)

        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", """PLATFORM: {platform}

TARGET CONTEXT:
Name: {target_name}
Title: {target_title}
Communication Style: {target_style}

SENDER CONTEXT:
Name: {sender_name}
Status: {sender_status}
Ask Type: {sender_ask}

MOST RELEVANT SENDER BACKGROUND:
{relevant_context}

SELECTED ANGLE & HOOK:
{angle_json}

{revision_block}

Generate EXACTLY two outputs:
1. connection_note: A short, punchy LinkedIn connection request note. STRICT MAX 300 characters. Make it personal and compelling.
2. dm_message: A longer, highly personalized direct message requesting a backend engineering internship. ~150 words. Reference specific things from the target's profile and your own projects."""),
        ])

        chain = prompt | structured_llm
        print("  → Drafting connection note + DM message...")

        if hasattr(selected_angle, "model_dump_json"):
            angle_formatted = selected_angle.model_dump_json(indent=2)
        else:
            angle_formatted = str(selected_angle)

        # Build the context: use RAG-retrieved context if available, otherwise fall back
        if relevant_context:
            context_block = relevant_context
        else:
            resume = sender_context.resume_text or "No resume provided."
            projects = sender_context.projects_context or "No project context provided."
            context_block = f"RESUME:\n{resume}\n\nPROJECTS:\n{projects}"

        # Build revision context if the Reviewer sent feedback
        if review_feedback:
            revision_block = (
                "IMPORTANT — REVISION REQUIRED:\n"
                f"The reviewer rejected your previous draft because: {review_feedback}\n"
                "Fix ONLY the issues mentioned above. Keep everything else the same."
            )
        else:
            revision_block = ""

        return chain.invoke({
            "platform": platform,
            "target_name": f"{target_profile.first_name} {target_profile.last_name}",
            "target_title": target_profile.current_title,
            "target_style": target_profile.communication_style,
            "sender_name": sender_context.sender_name,
            "sender_status": sender_context.sender_current_status,
            "sender_ask": sender_context.ask_type,
            "relevant_context": context_block,
            "angle_json": angle_formatted,
            "revision_block": revision_block,
        })