"""
DevMind — Developer Debugging Memory Agent
Shared configuration loaded from .env
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from devmind root directory
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

HINDSIGHT_API_KEY  = os.getenv("HINDSIGHT_API_KEY", "").strip()
HINDSIGHT_BASE_URL = os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io").strip()
GROQ_API_KEY       = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL         = os.getenv("GROQ_MODEL", "qwen/qwen3-32b").strip()
MEMORY_BANK_ID     = os.getenv("MEMORY_BANK_ID", "devmind-debug-bank").strip()
APP_PORT           = int(os.getenv("APP_PORT", 8000))


def is_hindsight_demo() -> bool:
    """Check if Hindsight is running in demo mode."""
    return (
        not HINDSIGHT_API_KEY
        or HINDSIGHT_API_KEY.upper() == "DEMO"
        or HINDSIGHT_API_KEY.startswith("your_")
    )


def is_groq_demo() -> bool:
    """Check if Groq LLM is running in demo mode."""
    return (
        not GROQ_API_KEY
        or GROQ_API_KEY.upper() == "DEMO"
        or GROQ_API_KEY.startswith("your_")
    )


def get_app_mode() -> str:
    """Return 'real' if both Hindsight and Groq have real keys configured, else 'demo'."""
    return "demo" if (is_hindsight_demo() or is_groq_demo()) else "real"
