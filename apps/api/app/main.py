from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import API_VERSION, APP_NAME, FRONTEND_ORIGIN
from app.routers import company, health, learner, platform, usage

app = FastAPI(title=APP_NAME, version=API_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(platform.router)
app.include_router(company.router)
app.include_router(learner.router)
app.include_router(usage.router)
