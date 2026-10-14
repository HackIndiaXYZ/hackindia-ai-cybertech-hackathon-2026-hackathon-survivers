import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL", "gemini-2.5-flash"
)
APP_ENV = os.getenv("APP_ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

DATA_DIR = BASE_DIR / "data"
RAG_DATA_DIR = DATA_DIR / "civic_knowledge"
CHROMA_DIR = DATA_DIR / "chroma_db"

RAG_DATA_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)


def validate_config():
    if not GEMINI_API_KEY.strip():
        raise RuntimeError(
            "GEMINI_API_KEY is missing from .env"
        )
