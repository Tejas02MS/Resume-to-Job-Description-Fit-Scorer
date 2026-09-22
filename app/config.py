from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    max_file_size_mb: int = 5
    extraction_timeout_seconds: float = 20.0
    weights: dict[str, float] = {
        "skills": 0.40,
        "experience": 0.25,
        "education": 0.10,
        "responsibilities": 0.15,
        "domain": 0.10,
    }
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def normalized_weights(self) -> dict[str, float]:
        total = sum(self.weights.values())
        if total <= 0:
            raise ValueError("At least one scoring weight must be positive.")
        return {k: v / total for k, v in self.weights.items()}

@lru_cache
def get_settings() -> Settings:
    return Settings()
