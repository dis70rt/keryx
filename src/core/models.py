from pydantic import BaseModel, Field


class ExperienceItem(BaseModel):
    title: str = Field(description="Job title or role")
    company: str = Field(description="Company name")
    duration: str | None = Field(None, description="Time spent in the role")
    key_responsibilities: list[str] = Field(
        description="Main achievements and duties"
    )


class PostSummary(BaseModel):
    topic: str = Field(description="Core topic of the post")
    key_takeaway: str = Field(description="Main point the author was making")
    tone: str = Field(description="Tone: professional, enthusiastic, vulnerable, etc.")


class TargetProfile(BaseModel):
    first_name: str
    last_name: str
    current_title: str
    location: str | None = None
    professional_summary: str = Field(
        description="2-3 sentence synthesized summary of their profile"
    )
    past_experience: list[ExperienceItem]
    skills_and_endorsements: list[str]
    services_offered: list[str] = Field(default_factory=list)
    recent_activity_themes: list[PostSummary] = Field(
        description="Top themes from recent posts"
    )
    inferred_interests: list[str] = Field(
        description="What this person cares about based on profile data"
    )
    communication_style: str = Field(
        description="E.g., Casual, academic, direct, promotional"
    )


class CompanyProfile(BaseModel):
    company_name: str
    industry_and_domain: str
    mission_statement: str | None = None
    recent_company_news_or_launches: list[str]
    core_tech_stack: list[str]
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