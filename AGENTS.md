# AkademX10 Development Operating System (AGENTS.md)

This file defines the authoritative, non-negotiable rules, guardrails, and operating standards for all AI agents working on the AkademX10 XAI codebase.

---

## 1. Project Overview & Identity
- **Product:** AkademX10 is a multi-training, multi-tenant B2B AI roleplay, competency scoring, and corporate reporting platform.
- **Avatar Role:** LiveAvatar/visual avatar is an interactive **experience layer** in specific roleplay states, **not** the core product. The core value is rubric-based AI scoring, skill development tracking, structured feedback, and enterprise reporting.
- **Active Roles:** ONLY `platform`, `company`, and `learner`.
  - Never reintroduce `admin`, `trainer`, `platform_admin`, or `company_admin` as active product roles. Legacy redirects must remain client-side UX redirects only.

---

## 2. Architecture & Route Guardrails
- **Stack:** Next.js (App Router, TypeScript, Tailwind) + FastAPI (Python 3.13) + Supabase (Postgres, Auth, RLS).
- **Tenant Isolation:** Maintained via `company_members`, `company_id`, and Postgres RLS. Never bypass or weaken backend authorization and RLS policies.
- **Contract Stability:** Preserve existing frontend adapters and backend DTO schemas (`apps/web/src/lib/adapters/`, `apps/api/app/schemas/dtos.py`).
- **Canonical Routes:**
  - Platform: `/platform/dashboard`, `/platform/templates`, `/platform/companies`, `/platform/assignments`, `/platform/usage`, `/platform/reports`
  - Company: `/company/dashboard`, `/company/trainings`, `/company/employees`, `/company/reports`, `/company/usage`
  - Learner: `/learner/dashboard`, `/learner/trainings`, `/learner/session/[sessionId]`, `/learner/sessions/[sessionId]/report`
  - Canonical Learner Report Route: `/learner/sessions/[sessionId]/report` (always plural `sessions`).

---

## 3. AI Contract & Evaluation Separation
- **Strict Separation:** Real-time conversation generation (LLM roleplay) and rubric scoring/evaluation are separate systems.
- **No Per-Turn Scoring:** Live voice/text turns invoke the conversation LLM to sustain dialogue; they do **NOT** invoke comprehensive rubric scoring.
- **Final Session Evaluation (Evaluation Contract v2):**
  - Text answers are not scored state-by-state.
  - Final evaluation executes **once** as an idempotent batch job at session finalize (`POST /api/learner/sessions/{id}/finalize`).
  - Do not rewrite or replace the existing scoring/report engine without explicit requirement.

---

## 4. Privacy, Security & Data Minimization
- **Secrets Boundary:** Provider API keys (`GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `DEEPGRAM_API_KEY`, `SUPABASE_SECRET_KEY`) must exist **only** on the backend/server. Never expose keys in `NEXT_PUBLIC_*`, browser bundles, API responses, or client exceptions.
- **Client Auth:** Normal product requests use the learner/company/platform user JWT. The Supabase `service_role` key must **never** be used in normal frontend/product request paths.
- **Zero Raw Media Retention:** Raw audio/video streams must **never** be saved to permanent storage (no disk, S3, or Supabase storage persistence).
- **Ephemeral Conversation Context:**
  - Live conversation context exists only in short-lived TTL cache (`InMemoryConversationCache`, `live-avatar:{sessionId}:{stateId}`).
  - Do not create permanent per-turn database tables (e.g. `conversation_turns`).
  - Text drafts remain in browser `sessionStorage` until finalized, then cleared.
- **Log Sanitization:** Full conversation transcripts, raw audio payloads, tokens, passwords, and provider API payloads must **never** be logged to application logs or console.

---

## 5. Scope Boundaries (Out of Scope for MVP/Faz 4)
Do NOT add or introduce unless explicitly requested by the user:
- Hume.ai / emotion or facial analysis
- SSO / SAML integration
- Stripe / billing / payment gateways
- Kubernetes infrastructure
- Pinecone / external vector databases (pgvector in Supabase is used if RAG needed)
- Phase 5 dashboard/authoring expansions
- Unrelated large UI refactors or role/route redesigns

---

## 6. Git & Change Control
- **Branch Protection:** Never work directly on `main`. Never perform automatic merges.
- **Push Policy:** Do not push to remote unless explicitly requested by the user.
- **Inspection First:** Always run `git status --short` before starting work.
- **Scoped Edits:** Keep changes focused on the assigned task block.
- **Concurrency:** Avoid concurrent edits by multiple agents to the same file.

---

## 7. Agent Roles & Work Style
- **Work Packaging:** Do not fragment features into dozens of micro-tasks. Structure implementation into 3–6 meaningful engineering blocks.
- **Source of Truth:**
  - For **product & architectural guardrails**: Handoff documents (`AkademX10_XAI_Master_Roadmap_ve_Handoff.pdf`, etc.) are authoritative.
  - For **current implementation state**: The **repository code and tests** are the source of truth (overriding stale documentation claims).
- **Lead Agent:** Owns execution planning, task delegation, dependency ordering, and running quality gates.
- **Reviewer / QA Agent:** Inspects diffs, verifies test execution, checks regressions against guardrails, and classifies findings as `BLOCKER`, `IMPORTANT`, or `MINOR`.
