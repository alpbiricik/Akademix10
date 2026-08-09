import os

from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "AkademX10 XAI API")
APP_ENV = os.getenv("APP_ENV", "local")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
API_VERSION = os.getenv("API_VERSION", "0.1.0")

CONVERSATION_PROVIDER = os.getenv("CONVERSATION_PROVIDER", "mock").strip().lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_CONVERSATION_MODEL = os.getenv("GEMINI_CONVERSATION_MODEL", "gemini-3.6-flash")
GEMINI_CONVERSATION_THINKING_LEVEL = os.getenv("GEMINI_CONVERSATION_THINKING_LEVEL", "").strip().lower() or None
CONVERSATION_CONTEXT_TTL_SECONDS = int(os.getenv("CONVERSATION_CONTEXT_TTL_SECONDS", "1800"))
