import os
import shutil
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env.local", override=False)
DATA = Path(os.getenv("DATA_DIR", str(ROOT / "data")))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
PYTHON = sys.executable
NODE = os.getenv("NODE_EXECUTABLE") or shutil.which("node")
if not NODE and os.name == "nt":
    bundled = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
    if bundled.exists():
        NODE = str(bundled)

def provider_status():
    return {name: bool(os.getenv(name)) for name in (
        "NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET", "KRX_API_KEY",
        "DART_API_KEY", "OPENAI_API_KEY",
    )}
