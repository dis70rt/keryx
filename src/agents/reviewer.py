from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate

from src.core.llm_client import create_llm


class ReviewResult(BaseModel):
    passes_criteria: bool = Field(
        description="True ONLY if both messages are flawless and ready to send"
    )
    critique: str = Field(
        description="What's wrong or why it passed"
    )
    suggested_connection_note: str | None = Field(
        None, description="Revised connection note if failed"
    )
    suggested_dm_message: str | None = Field(
        None, description="Revised DM message if failed"
    )


class ReviewerAgent:
    def __init__(self) -> None:
        self.llm = create_llm()
        prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "reviewer_system.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Missing prompt file at: {prompt_path}")
        self.system_prompt = prompt_path.read_text(encoding="utf-8")

    def review(
        self,
        drafted_messages: Any,
        target_context: Any,
        angle_used: Any,
    ) -> ReviewResult:
        """Review both the connection note and DM message for quality."""
        structured_llm = self.llm.with_structured_output(ReviewResult)

        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", """Review the following drafts:

TARGET CONTEXT:
{target_json}

ANGLE USED:
{angle_json}

CONNECTION NOTE:
{connection_note}

DM MESSAGE:
{dm_message}

Verify:
1. Connection note is under 300 characters and punchy
2. DM message is ~150 words, personalized, and human-sounding
3. No AI clichés or corporate jargon
4. CTA is low-friction"""),
        ])

        chain = prompt | structured_llm
        print("  → Running quality review...")

        def safe_format(obj: Any) -> str:
            if hasattr(obj, "model_dump_json"):
                return obj.model_dump_json(indent=2)
            return str(obj)

        if isinstance(drafted_messages, dict):
            conn_note = drafted_messages.get("connection_note", "")
            dm_msg = drafted_messages.get("dm_message", "")
        else:
            conn_note = getattr(drafted_messages, "connection_note", "")
            dm_msg = getattr(drafted_messages, "dm_message", "")

        return chain.invoke({
            "target_json": safe_format(target_context),
            "angle_json": safe_format(angle_used),
            "connection_note": conn_note,
            "dm_message": dm_msg,
        })