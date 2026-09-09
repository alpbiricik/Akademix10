import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")
load_dotenv()


APP_NAME = os.getenv("APP_NAME", "AkademX10 XAI API")
APP_ENV = os.getenv("APP_ENV", "local")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
API_VERSION = os.getenv("API_VERSION", "0.1.0")
VOICE_ENABLED = os.getenv("VOICE_ENABLED", "true").lower() == "true"
LIVE_AVATAR_ENABLED = os.getenv("LIVE_AVATAR_ENABLED", "true").lower() == "true"
VOICE_STREAMING_ENABLED = os.getenv("VOICE_STREAMING_ENABLED", "false").lower() == "true"
CONVERSATION_STREAMING_ENABLED = os.getenv("CONVERSATION_STREAMING_ENABLED", "false").lower() == "true"

CONVERSATION_PROVIDER = os.getenv("CONVERSATION_PROVIDER", "gemini").strip().lower()
CONVERSATION_LANGUAGE = os.getenv("CONVERSATION_LANGUAGE", "tr").strip().lower() or "tr"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_CONVERSATION_MODEL = os.getenv("GEMINI_CONVERSATION_MODEL", "gemini-3.6-flash")
GEMINI_CONVERSATION_THINKING_LEVEL = os.getenv("GEMINI_CONVERSATION_THINKING_LEVEL", "").strip().lower() or None
def _conversation_context_ttl() -> int:
    value = os.getenv("CONVERSATION_CONTEXT_TTL_SECONDS")
    if value is None:
        if APP_ENV.strip().lower() in {"production", "prod"}:
            raise ValueError("CONVERSATION_CONTEXT_TTL_SECONDS is required in production")
        return 1800
    try:
        ttl = int(value)
    except ValueError:
        raise ValueError("CONVERSATION_CONTEXT_TTL_SECONDS must be a positive integer") from None
    if ttl <= 0:
        raise ValueError("CONVERSATION_CONTEXT_TTL_SECONDS must be a positive integer")
    return ttl


CONVERSATION_CONTEXT_TTL_SECONDS = _conversation_context_ttl()

STT_PROVIDER = os.getenv("STT_PROVIDER", "elevenlabs").strip().lower()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_STT_MODEL = os.getenv("ELEVENLABS_STT_MODEL", "scribe_v2_realtime")
ELEVENLABS_STT_LANGUAGE = os.getenv("ELEVENLABS_STT_LANGUAGE", "tr")
ELEVENLABS_STT_COMMIT_STRATEGY = os.getenv("ELEVENLABS_STT_COMMIT_STRATEGY", "vad").strip().lower()
ELEVENLABS_STT_VAD_SILENCE_THRESHOLD_SECS = float(os.getenv("ELEVENLABS_STT_VAD_SILENCE_THRESHOLD_SECS", "0.8"))
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "elevenlabs").strip().lower()
TTS_LANGUAGE = os.getenv("TTS_LANGUAGE", "tr")
ELEVENLABS_TTS_MODEL = os.getenv("ELEVENLABS_TTS_MODEL", "eleven_flash_v2_5")
ELEVENLABS_TTS_LANGUAGE = os.getenv("ELEVENLABS_TTS_LANGUAGE", "tr")
ELEVENLABS_TTS_VOICE_ID = os.getenv("ELEVENLABS_TTS_VOICE_ID", "")

LIVE_AVATAR_PROVIDER = os.getenv("LIVE_AVATAR_PROVIDER", "heygen").strip().lower()
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY", "")
HEYGEN_AVATAR_ID = os.getenv("HEYGEN_AVATAR_ID", "9650a758-1085-4d49-8bf3-f347565ec229")
HEYGEN_VOICE_ID = os.getenv("HEYGEN_VOICE_ID", "")
HEYGEN_QUALITY = os.getenv("HEYGEN_QUALITY", "medium").strip().lower()
LIVE_AVATAR_MAX_SESSION_SECONDS = int(os.getenv("LIVE_AVATAR_MAX_SESSION_SECONDS", "600"))
LIVE_AVATAR_SANDBOX = os.getenv("LIVE_AVATAR_SANDBOX", "true").lower() == "true"
LIVE_AVATAR_SANDBOX_AVATAR_ID = os.getenv("LIVE_AVATAR_SANDBOX_AVATAR_ID", "dd73ea75-1218-4ef3-92ce-606d5f7fbc0a")
