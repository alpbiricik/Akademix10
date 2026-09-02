---
name: akademx10-verification
description: >-
  Standard reusable verification quality gate workflow for AkademX10.
  Use whenever code changes have been made in backend, frontend, database, or contracts,
  or before declaring an engineering block complete.
---

# AkademX10 Verification Workflow

This workflow defines the standard verification steps and commands that must be executed to ensure high quality, zero regressions, and strict guardrail compliance.

---

## 1. Backend Verification

Run the Python compilation check and unit test suite:

```powershell
# 1. Verify Python syntax and bytecode compilation across app
.\apps\api\.venv\Scripts\python.exe -m compileall apps/api/app

# 2. Run full backend test suite (115+ tests)
$env:PYTHONPATH="apps/api"
.\apps\api\.venv\Scripts\python.exe -m unittest discover -s apps/api/tests -t apps/api
```

### Verification Criteria:
- `compileall` must exit with code 0 and list all modules cleanly.
- All unit tests must pass with `OK` (0 errors, 0 failures).
- If modifying a specific service (e.g. `conversation_service`), run focused tests first:
  ```powershell
  $env:PYTHONPATH="apps/api"
  .\apps\api\.venv\Scripts\python.exe -m unittest apps/api/tests/test_conversation_service.py
  ```

---

## 2. Frontend Verification

Run ESLint and Next.js production build:

```powershell
# 1. Run ESLint across apps/web
npm --prefix apps/web run lint

# 2. Run clean Next.js production build
npm --prefix apps/web run build
```

### Verification Criteria:
- `npm run lint` must pass with 0 errors.
- `npm run build` must compile successfully with all static and dynamic routes correctly typed.
- Canonical routes must remain valid:
  - `/learner/sessions/[sessionId]/report`
  - `/platform/*`
  - `/company/*`

---

## 3. Repository & Hygiene Verification

```powershell
# 1. Check for formatting and whitespace errors
git diff --check

# 2. Check working tree status
git status --short
```

### Security & Privacy Checklist:
- [ ] No API keys, passwords, or secrets in frontend `.env*`, code files, or Git history.
- [ ] No `NEXT_PUBLIC_*` containing server-side credentials.
- [ ] No `console.log` or logging statements dumping raw audio, transcripts, or provider tokens.
- [ ] No permanent DB tables added for ephemeral voice turns.
- [ ] No regressions in tenant isolation or role boundaries (`platform`, `company`, `learner`).
