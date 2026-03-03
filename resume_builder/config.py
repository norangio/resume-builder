from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
    )

    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    model: str = Field("claude-opus-4-6", alias="CLAUDE_MODEL")

    candidate_name: str = Field(..., alias="CANDIDATE_NAME")
    candidate_email: str = Field(..., alias="CANDIDATE_EMAIL")
    candidate_phone: str = Field(..., alias="CANDIDATE_PHONE")
    candidate_location: str = Field(..., alias="CANDIDATE_LOCATION")
    candidate_linkedin: str | None = Field(None, alias="CANDIDATE_LINKEDIN")

    career_docs_dir: Path = BASE_DIR / "career_docs"
    prompts_dir: Path = BASE_DIR / "resume_builder" / "prompts"
    templates_dir: Path = BASE_DIR / "templates"
    output_dir: Path = BASE_DIR / "output"
    drafts_dir: Path = BASE_DIR / "drafts"


settings = Settings()
