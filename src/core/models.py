from pydantic import BaseModel, Field, model_validator


class ExperienceItem(BaseModel):
    title: str = Field(default="", description="Job title or role")
    company: str = Field(default="", description="Company name")
    duration: str | None = Field(None, description="Time spent in the role")
    key_responsibilities: list[str] = Field(
        default_factory=list, description="Main achievements and duties"
    )


class PostSummary(BaseModel):
    topic: str = Field(default="", description="Core topic of the post")
    key_takeaway: str = Field(default="", description="Main point the author was making")
    tone: str = Field(default="", description="Tone: professional, enthusiastic, vulnerable, etc.")


class TargetProfile(BaseModel):
    first_name: str = Field(default="")
    last_name: str = Field(default="")
    current_title: str = Field(default="")
    location: str | None = None
    professional_summary: str = Field(
        default="", description="2-3 sentence synthesized summary of their profile"
    )
    past_experience: list[ExperienceItem] = Field(default_factory=list)
    skills_and_endorsements: list[str] = Field(default_factory=list)
    services_offered: list[str] = Field(default_factory=list)
    recent_activity_themes: list[PostSummary] = Field(
        default_factory=list, description="Top themes from recent posts"
    )
    inferred_interests: list[str] = Field(
        default_factory=list, description="What this person cares about based on profile data"
    )
    communication_style: str = Field(
        default="", description="E.g., Casual, academic, direct, promotional"
    )

    @model_validator(mode="before")
    @classmethod
    def sanitize_lists(cls, data: dict) -> dict:
        """Strip invalid entries from lists to survive LLM hallucinations.

        The local model sometimes stuffs a garbage string into the
        past_experience list instead of a proper ExperienceItem dict.
        This validator silently drops those entries.
        """
        if isinstance(data, dict):
            # Drop non-dict entries from past_experience
            raw_exp = data.get("past_experience", [])
            if isinstance(raw_exp, list):
                data["past_experience"] = [
                    item for item in raw_exp if isinstance(item, dict)
                ][:5]  # hard cap at 5 most recent

            # Cap skills list
            raw_skills = data.get("skills_and_endorsements", [])
            if isinstance(raw_skills, list):
                data["skills_and_endorsements"] = [
                    s for s in raw_skills if isinstance(s, str) and len(s) < 100
                ][:10]

            # Cap activity themes
            raw_themes = data.get("recent_activity_themes", [])
            if isinstance(raw_themes, list):
                data["recent_activity_themes"] = raw_themes[:5]

        return data


class CompanyProfile(BaseModel):
    company_name: str = Field(default="")
    industry_and_domain: str = Field(default="")
    mission_statement: str | None = None
    recent_company_news_or_launches: list[str] = Field(default_factory=list)
    core_tech_stack: list[str] = Field(default_factory=list)
    target_audience: str | None = None


class SenderContext(BaseModel):
    sender_name: str
    sender_current_status: str
    sender_core_competencies: list[str]
    sender_highlight_projects: list[str]
    ask_type: str = Field(
        description="E.g., 'Networking', 'Sales Pitch', 'Internship Request'"
    )
    resume_text: str = Field(default="", description="Parsed .tex resume content")
    projects_context: str = Field(
        default="", description="Serialized projects.json data"
    )


class GeneratedMessages(BaseModel):
    """Constrained LLM output for the two-part messaging system."""

    connection_note: str = Field(
        description="Short, punchy LinkedIn connection request note. STRICT MAX 300 characters.",
        max_length=300,
    )
    dm_message: str = Field(
        description="Highly personalized direct message requesting a backend engineering internship (~150 words)."
    )