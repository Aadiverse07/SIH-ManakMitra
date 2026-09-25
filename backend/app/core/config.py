"""Central application configuration loaded from environment variables."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

def _int(name: str, default: int, minimum: int = 0) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except ValueError:
        return default

def _float(name: str, default: float, minimum: float = 0.0) -> float:
    try:
        return max(minimum, float(os.getenv(name, str(default))))
    except ValueError:
        return default

class Settings:
    APP_NAME = os.getenv("APP_NAME", "ManakMitra API")
    APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    LLM_API_KEYS = [k for k in (
        os.getenv("LLM_API_KEY"), os.getenv("LLM_API_KEY_2"),
        os.getenv("LLM_API_KEY_3"), os.getenv("LLM_API_KEY_4")
    ) if k]
    LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.6-flash")
    AI2_API_KEYS = [k for k in (
        os.getenv("AI2_API_KEY"), os.getenv("AI2_API_KEY_2"),
        os.getenv("AI2_API_KEY_3"), os.getenv("AI2_API_KEY_4")
    ) if k]
    AI2_MODEL = os.getenv("AI2_MODEL", LLM_MODEL)

    CORS_ORIGINS = [o.strip() for o in os.getenv(
        "CORS_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500"
    ).split(",") if o.strip()]
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    OPS_ADMIN_TOKEN = os.getenv("OPS_ADMIN_TOKEN", "")

    # Certification application email delivery (optional).
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = _int("SMTP_PORT", 587, 1)
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "")

    # Phase 8: request and AI budgets. Values are deliberately configurable.
    MAX_MESSAGE_LENGTH = _int("MAX_MESSAGE_LENGTH", 10000, 1)
    MAX_REQUEST_SIZE_BYTES = _int("MAX_REQUEST_SIZE_BYTES", 32768, 1024)
    MAX_CONTEXT_SIZE_CHARS = _int("MAX_CONTEXT_SIZE_CHARS", 24000, 1000)
    MAX_OUTPUT_TOKENS = _int("MAX_OUTPUT_TOKENS", 1024, 1)
    # Provider networking: a response that takes several seconds is normal for
    # a grounded BIS request. Keep the SDK timeout above the observed 4–8s
    # failure window while remaining bounded.
    LLM_REQUEST_TIMEOUT_MS = _int("LLM_REQUEST_TIMEOUT_MS", 30000, 1000)
    LLM_TRANSIENT_RETRIES = _int("LLM_TRANSIENT_RETRIES", 1, 0)
    # Hard cap on provider calls inside ONE generate() call (all keys and retries
    # combined). Previously 4 keys x 2 attempts = 8 calls for AI #1 plus 8 more
    # for AI #2 = 16 calls per chat message whenever the provider was failing.
    LLM_MAX_CALLS_PER_GENERATE = _int("LLM_MAX_CALLS_PER_GENERATE", 2, 1)
    MAX_AI1_CALLS_PER_REQUEST = _int("MAX_AI1_CALLS_PER_REQUEST", 1, 0)
    MAX_AI2_CALLS_PER_REQUEST = _int("MAX_AI2_CALLS_PER_REQUEST", 1, 0)

    # Content moderation: flagged (sexual/harm) queries never reach AI #1/#2 --
    # 1st offense is a warning, 2nd offense blocks the user for this many
    # seconds. Disable with MODERATION_ENABLED=false if ever needed.
    MODERATION_ENABLED = os.getenv("MODERATION_ENABLED", "true").lower() == "true"
    MODERATION_BLOCK_SECONDS = _int("MODERATION_BLOCK_SECONDS", 3600, 1)

    RATE_LIMIT_WINDOW_SECONDS = _int("RATE_LIMIT_WINDOW_SECONDS", 60, 1)
    RATE_LIMIT_REQUESTS_PER_IP = _int("RATE_LIMIT_REQUESTS_PER_IP", 60, 1)
    RATE_LIMIT_CHAT_PER_IP = _int("RATE_LIMIT_CHAT_PER_IP", 10, 1)
    RATE_LIMIT_SEARCH_PER_IP = _int("RATE_LIMIT_SEARCH_PER_IP", 30, 1)

    # Phase 9: scheduler. Disabled by default unless explicitly enabled.
    SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "false").lower() == "true"
    BIS_SYNC_ENABLED = os.getenv("BIS_SYNC_ENABLED", "false").lower() == "true"
    BIS_SYNC_INTERVAL = _int("BIS_SYNC_INTERVAL", 86400, 60)
    CACHE_CLEANUP_INTERVAL = _int("CACHE_CLEANUP_INTERVAL", 3600, 60)
    USAGE_STATS_INTERVAL = _int("USAGE_STATS_INTERVAL", 3600, 60)
    TEMPORARY_DATA_CLEANUP_INTERVAL = _int("TEMPORARY_DATA_CLEANUP_INTERVAL", 3600, 60)
    BIS_SYNC_RETRIES = _int("BIS_SYNC_RETRIES", 1, 0)

    # Phase 10: semantic retrieval. Gemini Embedding 2 supports flexible output
    # dimensions; 768 is the stored pgvector contract for this migration.
    EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "gemini").lower()
    EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", os.getenv("LLM_API_KEY", ""))
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-2")
    EMBEDDING_DIMENSIONS = _int("EMBEDDING_DIMENSIONS", 768, 1)
    EMBEDDING_MAX_INPUT_CHARS = _int("EMBEDDING_MAX_INPUT_CHARS", 12000, 100)
    EMBEDDING_BATCH_SIZE = _int("EMBEDDING_BATCH_SIZE", 32, 1)
    EMBEDDING_RETRIES = _int("EMBEDDING_RETRIES", 2, 0)

    HYBRID_LEXICAL_WEIGHT = _float("HYBRID_LEXICAL_WEIGHT", 0.55, 0.0)
    HYBRID_VECTOR_WEIGHT = _float("HYBRID_VECTOR_WEIGHT", 0.35, 0.0)
    HYBRID_METADATA_WEIGHT = _float("HYBRID_METADATA_WEIGHT", 0.10, 0.0)
    VECTOR_MIN_SIMILARITY = _float("VECTOR_MIN_SIMILARITY", 0.0, 0.0)
    DOCUMENT_STORAGE_ROOT = os.getenv("DOCUMENT_STORAGE_ROOT", "backend/storage/documents")
    DOCUMENT_MAX_SIZE_BYTES = _int("DOCUMENT_MAX_SIZE_BYTES", 25 * 1024 * 1024, 1024)
    DOCUMENT_OCR_ENABLED = os.getenv("DOCUMENT_OCR_ENABLED", "true").lower() == "true"

settings = Settings()

def validate_required_settings():
    missing = []
    if not settings.SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if missing:
        raise RuntimeError(
            f"Missing required backend environment variables: {', '.join(missing)}. "
            "See backend/.env.example."
        )
    if settings.ENVIRONMENT.lower() == "production" and "*" in settings.CORS_ORIGINS:
        raise RuntimeError("CORS_ORIGINS must not contain '*' in production.")
    if settings.EMBEDDING_DIMENSIONS != 768:
        raise RuntimeError(
            "EMBEDDING_DIMENSIONS must remain 768 for the Phase 10 pgvector schema. "
            "Create a new migration before changing the embedding dimension."
        )
    if (
        settings.HYBRID_LEXICAL_WEIGHT
        + settings.HYBRID_VECTOR_WEIGHT
        + settings.HYBRID_METADATA_WEIGHT
    ) <= 0:
        raise RuntimeError("At least one hybrid retrieval weight must be positive.")
