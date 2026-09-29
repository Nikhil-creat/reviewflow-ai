from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model_fast: str = "llama-3.1-8b-instant"
    groq_model_smart: str = "llama-3.3-70b-versatile"

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    database_url: str = "postgresql://reviewflow:reviewflow_dev@localhost:5433/reviewflow"
    redis_url: str = "redis://localhost:6379/0"
    vision_service_url: str = "http://localhost:8100"

    autopilot_interval_seconds: int = 60
    auto_reply_min_confidence: float = 0.85
    cors_origins: str = "http://localhost:3000"
    run_autopilot_in_process: bool = False
    seed_demo: bool = True
    supabase_jwt_secret: str = ""
    google_places_api_key: str = ""

    @property
    def llm_enabled(self) -> bool:
        return bool(self.groq_api_key) and not self.groq_api_key.startswith("gsk_your")


settings = Settings()
