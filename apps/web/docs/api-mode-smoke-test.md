# API Mode Smoke Test

Phase 2 defaults to mock mode. Use API mode only when testing the FastAPI adapter contract.

## 1. Run The Backend

```powershell
cd C:\Users\ASUS\Akademix10\apps\api
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Backend checks:

- `http://localhost:8000/health`
- `http://localhost:8000/docs`

## 2. Run The Frontend In API Mode

Create or update:

```text
C:\Users\ASUS\Akademix10\apps\web\.env.local
```

Use:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_DATA_SOURCE_MODE=api
```

Restart the frontend dev server after changing env values.

## 3. Open The Smoke Page

```text
http://localhost:3000/dev/api-smoke
```

Click `Run Smoke Test`.

Expected checks:

- platform templates
- platform companies
- platform usage
- platform assignment POST
- company trainings
- company employees
- company reports
- learner trainings
- demo session
- session state patch
- answer submit
- usage event and cost-log endpoints

## 4. Switch Back To Mock Mode

Update `.env.local`:

```env
NEXT_PUBLIC_DATA_SOURCE_MODE=mock
```

Restart the frontend dev server again.
