from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated environment configuration loaded at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = "ollama"
    llm_model: str = "gemma4:e2b"
    llm_temperature: float = 0.7
    ollama_base_url: str = "http://localhost:11434"

    admin_email: str = "example@example.com"
    google_sheets_cred_path: Path = Field(default=Path("data/google_credentials.json"))
    target_sheet_name: str = "Keryx Outreach"
    sheet_tab_targets: str = "Targets"
    sheet_tab_notes: str = "Connection Notes"
    sheet_tab_dms: str = "DM Messages"

    # Sender data
    sender_linkedin_url: str
    sender_profile_cache_path: Path = Field(default=Path("data/sender_profile.json"))

    resume_path: Path = Field(default=Path("data/resume.tex"))
    projects_path: Path = Field(default=Path("data/projects.json"))

    auth_state_path: Path = Field(default=Path("data/auth_state.json"))
    headless: bool = False

    cache_db_path: Path = Field(default=Path("data/cache.db"))
    snapshot_dir: Path = Field(default=Path("data/snapshots"))


def load_settings() -> Settings:
    """Instantiate and return validated settings. Fails fast on missing vars."""
    return Settings()
