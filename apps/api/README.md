# AkademX10 XAI API Skeleton

This is the Phase 2C FastAPI backend skeleton for AkademX10 XAI. It mirrors the Phase 2B frontend contracts with mock in-memory data only.

## Not Implemented Yet

- No real Supabase connection
- No database credentials
- No real auth provider
- No OpenAI, Claude, LiveAvatar, STT, or TTS integration
- No payment or SSO
- No frontend API connection yet

## Setup

```powershell
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Example Curl

```powershell
curl http://127.0.0.1:8000/health
curl -H "x-mock-role: platform" http://127.0.0.1:8000/api/platform/templates
curl -H "x-mock-role: company" http://127.0.0.1:8000/api/company/trainings
curl -H "x-mock-role: learner" http://127.0.0.1:8000/api/learner/sessions/demo-session-1
```

## Mock Roles

- `platform`: AkademX10 operator
- `company`: customer company manager
- `learner`: employee learner

The mock role is read from the `x-mock-role` header.
