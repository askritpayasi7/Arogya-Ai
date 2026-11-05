from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    """Application configuration settings."""
    model_config = SettingsConfigDict(
        env_file=[".env", "Prescription/.env", "prescription/.env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for Ollama service"
    )
    ollama_embed_model: str = Field(
        default="nomic-embed-text",
        description="Ollama embedding model name"
    )
    chroma_persist_dir: Path = Field(
        default=Path("./data/vector_db"),
        description="Directory for local persistent ChromaDB"
    )
    research_papers_dir: Path = Field(
        default=Path("./data/research_papers"),
        description="Directory containing research papers"
    )
    fssai_regulations_dir: Path = Field(
        default=Path("./data/fssai_regulations"),
        description="Directory containing FSSAI regulation documents"
    )
    gemini_api_key: str | None = Field(
        default=None,
        description="API key for Gemini relationship extraction"
    )
    gemini_model: str = Field(
        default="gemini-flash-lite-latest",
        description="Gemini model name for relationship extraction"
    )
    ollama_nli_model: str = Field(
        default="llama3.2:1b",
        description="Lightweight Ollama model for laptop-friendly NLI verification"
    )
    google_client_secret_file: str | None = Field(
        default=None,
        description="Path to Google OAuth client secret JSON file"
    )
    dashboard_port: int = Field(
        default=8001,
        description="Port for dashboard web server (matching Google Cloud redirect URI)"
    )
    dashboard_host: str = Field(
        default="127.0.0.1",
        description="Host interface for dashboard server"
    )
    admin_password: str = Field(
        default="admin123",
        description="Password for Admin Dashboard access"
    )
    secret_key: str = Field(
        default="clinical-health-app-secret-session-key-2026",
        description="Secret key for encrypting dashboard user session cookies"
    )

    def find_client_secret_file(self) -> Path | None:
        """Locate Google OAuth client secret JSON in root directory or configured path."""
        if self.google_client_secret_file:
            p = Path(self.google_client_secret_file)
            if p.exists():
                return p

        # Search for any client_secret*.json in current directory or parent
        for search_dir in [Path("."), Path("..")]:
            matches = list(search_dir.glob("client_secret*.json"))
            if matches:
                return matches[0].resolve()

        return None


# Global settings singleton
settings = Settings()
