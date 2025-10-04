from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, computed_field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    LLM_MODEL: str = Field("llama3.2")
    SOTERIA_API_KEY: str | None = None
    BASE_DIR: Path = Path(__file__).parent.resolve()

    CHROMA_PATH: Path = "chroma"
    COLLECTION_NAME: str = "local-rag"
    TEXT_EMBEDDING_MODEL: str = "nomic-embed-text"

    @property
    @computed_field
    def TEMP_FOLDER(self) -> Path:
        return self.BASE_DIR / ".temp"


settings = Settings()  # type: ignore
