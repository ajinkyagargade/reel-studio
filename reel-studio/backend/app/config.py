"""Central configuration. Values come from environment variables or backend/.env"""
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

DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data")).resolve()
UPLOAD_DIR = DATA_DIR / "uploads"
WORK_DIR = DATA_DIR / "work"
OUTPUT_DIR = DATA_DIR / "outputs"
DB_PATH = DATA_DIR / "reelstudio.sqlite3"
FONTS_DIR = BASE_DIR / "assets" / "fonts"
USER_FONT_DIR = DATA_DIR / "fonts"
LOGO_DIR = DATA_DIR / "logos"
FRONTEND_BUILD = Path(os.getenv("FRONTEND_BUILD", BASE_DIR.parent / "frontend" / "build"))

for _d in (DATA_DIR, UPLOAD_DIR, WORK_DIR, OUTPUT_DIR, USER_FONT_DIR, LOGO_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --- Speech to text (faster-whisper, runs locally, free) ---
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")  # tiny/base/small/medium/large-v3
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "auto")  # auto/cpu/cuda
WHISPER_COMPUTE = os.getenv("WHISPER_COMPUTE", "int8")  # int8 for CPU, float16 for GPU

# --- LLM for summaries / key points / narration (optional) ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

# --- Server ---
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()]
MAX_UPLOAD_GB = float(os.getenv("MAX_UPLOAD_GB", "8"))
JOB_WORKERS = int(os.getenv("JOB_WORKERS", "2"))
