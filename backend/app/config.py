"""Runtime configuration, read from environment variables (or a .env file)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'erp.db'}")
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production-please")
ACCESS_TOKEN_MINUTES = int(os.environ.get("ACCESS_TOKEN_MINUTES", "720"))
# Public URL of the frontend; used inside the invoice QR code (…/verify/<token>).
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:5173").rstrip("/")
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
# Business day boundaries (dashboard "today") use this timezone.
BUSINESS_TZ = os.environ.get("BUSINESS_TZ", "Asia/Dhaka")
