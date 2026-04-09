from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Look for .env in backend/ first, then the project root
_ENV_FILE = (
    Path(__file__).parent.parent / ".env"
    if (Path(__file__).parent.parent / ".env").exists()
    else Path(__file__).parent.parent.parent / ".env"
)

# Absolute path to backend/ so relative chroma_path is always resolved correctly
# regardless of the working directory uvicorn is launched from.
_BACKEND_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,   # shell empty vars don't override .env values
    )

    # Required — app refuses to start without this
    anthropic_api_key: str

    # Optional — blank means offline mode; /ingest returns 503
    sciencedirect_api_key: str = ""

    # Optional — Springer Nature API key
    springer_nature_api_key: str = ""

    # App behaviour
    use_mock_data: bool = True
    chroma_path: str = "./chroma_store"
    embedding_model: str = "all-MiniLM-L6-v2"
    use_reranker: bool = True
    claude_model: str = "claude-sonnet-4-6"
    claude_max_tokens: int = 4096  # detailed clinical answers need headroom
    # Comma-separated list of allowed CORS origins
    # e.g. "http://localhost:4000,https://vetchat-ai.vercel.app"
    frontend_origin: str = "http://localhost:4000"

    # Database + auth
    database_url: str = ""
    jwt_secret: str = ""
    jwt_expire_minutes: int = 10080  # 7 days

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origin.split(",") if o.strip()]

    @model_validator(mode="after")
    def _resolve_chroma_path(self) -> "Settings":
        """Resolve a relative chroma_path to an absolute path anchored at backend/."""
        p = Path(self.chroma_path)
        if not p.is_absolute():
            self.chroma_path = str(_BACKEND_DIR / p)
        # Rewrite postgresql:// → postgresql+asyncpg:// for SQLAlchemy async driver
        if self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self

    def validate_required(self) -> None:
        if not self.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required but not set. "
                "Copy .env.example to .env and add your key."
            )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.validate_required()
    return _settings
