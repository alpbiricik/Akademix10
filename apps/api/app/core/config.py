import os

from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "AkademX10 XAI API")
APP_ENV = os.getenv("APP_ENV", "local")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
API_VERSION = os.getenv("API_VERSION", "0.1.0")
