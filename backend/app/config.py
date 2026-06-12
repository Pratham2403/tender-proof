from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongodb_url: str = "mongodb://localhost:27017/tenderproof"
    redis_url: str = "redis://localhost:6379/0"
    google_api_key: str = ""
    openrouter_api_key: str = ""
    upload_dir: str = "./uploads"
    confidence_threshold: float = 0.70
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
