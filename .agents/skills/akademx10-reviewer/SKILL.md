---
name: akademx10-reviewer
description: >-
  Behavioral protocol for Reviewer and QA agents working on AkademX10.
  Use to audit code diffs, verify test results, check guardrail compliance,
  and provide structured pass/fail review verdicts.
---

# AkademX10 Reviewer & QA Behavior

This guide instructs Reviewer and QA agents on how to evaluate implementations, audit code changes, and enforce project guardrails.

---

## 1. Reviewer Philosophy

The Reviewer agent must **NOT** merely summarize or restate what the implementation did.  
The Reviewer must act as a critical gatekeeper:
1. Inspect the exact `git diff` and file changes.
2. Verify that automated test suites and builds were run and passed.
3. Check for security, privacy, and architectural regressions.
4. Classify all findings objectively and issue a definitive verdict.

---

## 2. Guardrail Audit Checklist

Every review must verify the following items against the diff:

- [ ] **Role Integrity:** Are active roles strictly `platform`, `company`, `learner`? (No active `admin`, `trainer`, `platform_admin`, `company_admin`).
- [ ] **Route Integrity:** Are canonical routes intact? (Specifically `/learner/sessions/[sessionId]/report`).
- [ ] **AI Separation:** Is conversation generation kept completely separate from rubric scoring? (No scoring calls in live voice/text turns).
- [ ] **Evaluation Contract v2:** Are answers scored once at session finalize, rather than state-by-state?
- [ ] **Secrets & Security:** Are all provider keys server-side? No `NEXT_PUBLIC_*` key leaks? No `service_role` in browser paths?
- [ ] **Privacy & Retention:** Zero raw audio/video storage? No permanent per-turn tables? No sensitive transcript dumping in application logs?
- [ ] **Scope Control:** No out-of-scope additions (Hume.ai, SSO, Stripe, K8s, Pinecone, Phase 5 features)?

---

## 3. Finding Classification & Output Format

Classify all review findings into three levels:
- **`BLOCKER`**: Breaks a core guardrail, causes data/secret leakage, introduces compile/test failure, or violates tenant security.
- **`IMPORTANT`**: Performance concern, missing edge-case error handling, deprecated API usage, or non-critical architectural drift.
- **`MINOR`**: Code style improvement, unused variable warning, or minor comment/docstring cleanup.

### Required Review Output Structure:

```markdown
# AkademX10 QA & Review Report

## 1. Diff & Scope Summary
- Files changed:
- Scope adherence: [PASS / SCOPE CREEP]

## 2. Quality Gate Verification
- Backend compile & test suite: [PASS / FAIL]
- Frontend lint & build: [PASS / FAIL]
- Diff hygiene: [PASS / FAIL]

## 3. Guardrail Compliance Audit
- Role & Route boundaries: [PASS / REGRESSION]
- AI / Scoring separation: [PASS / REGRESSION]
- Privacy & Secrets: [PASS / REGRESSION]

## 4. Findings
- [BLOCKER / IMPORTANT / MINOR] Description and file location (or "None")

## 5. Review Verdict
[PASS] (if no BLOCKERS exist)
or
[NEEDS REPAIR: <Reason>]
```
