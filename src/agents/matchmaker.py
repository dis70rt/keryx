import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate

from src.core.llm_client import create_llm
from src.core.models import CompanyProfile, SenderContext, TargetProfile


class OutreachAngle(BaseModel):
    angle_name: str = Field(description="Short name for this strategic angle")
    psychological_reasoning: str = Field(
        description="WHY this angle will work on this specific person"
    )
    hook_sentence: str = Field(
        description="1-2 sentence opening hook expressing this angle"
    )


class MatchmakerResult(BaseModel):
    selected_angles: list[OutreachAngle] = Field(
        description="2-3 highly tailored outreach angles"
    )


class MatchmakerAgent:
    def __init__(self) -> None:
        self.llm = create_llm()
        prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "matchmaker_system.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Missing prompt file at: {prompt_path}")
        self.system_prompt = prompt_path.read_text(encoding="utf-8")

    def generate_angles(
        self,
        target_profile: TargetProfile,
        sender_context: SenderContext,
        analyst_insights: Any,
        company_profile: CompanyProfile | None = None,
        past_hooks: str | None = None,
    ) -> MatchmakerResult:
        structured_llm = self.llm.with_structured_output(MatchmakerResult)

        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "TARGET PROFILE:\n{target_json}\n\nTARGET INSIGHTS:\n{insights_json}\n\nSENDER CONTEXT:\n{sender_json}\n\nCOMPANY PROFILE:\n{company_json}\n\n{past_hooks_section}"),
        ])

        chain = prompt | structured_llm
        print("  → Generating outreach angles...")

        if hasattr(analyst_insights, "model_dump_json"):
            insights_formatted = analyst_insights.model_dump_json(indent=2)
        else:
            insights_formatted = json.dumps(analyst_insights, indent=2)

        return chain.invoke({
            "target_json": target_profile.model_dump_json(indent=2),
            "insights_json": insights_formatted,
            "sender_json": sender_context.model_dump_json(indent=2),
            "company_json": (
                company_profile.model_dump_json(indent=2)
                if company_profile
                else "No company data available."
            ),
            "past_hooks_section": past_hooks or "No past hook data available yet.",
        })