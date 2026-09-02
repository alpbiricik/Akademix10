---
name: akademx10-lead
description: >-
  Behavioral protocol for Lead and Implementation agents working on AkademX10.
  Use to structure engineering blocks, manage dependencies, orchestrate subagents,
  and enforce quality gates before task handoff.
---

# AkademX10 Lead & Implementation Behavior

This guide instructs Lead and Implementation agents on how to execute features, structure work, delegate tasks, and maintain architectural integrity.

---

## 1. Core Operating Principles

1. **Repository Reality as Truth:** Always inspect the actual codebase first (`git status`, tests, code) rather than relying blindly on older handoff text.
2. **Authoritative Guardrails:** Product and security guardrails in the master handoff documents are strict constraints that must never be broken.
3. **Structured Packaging (3–6 Blocks):** Do not fragment work into dozens of microscopic tasks. Organize work into 3–6 cohesive engineering blocks (e.g. Contract -> Provider -> UI/Integration -> Quality Gate).
4. **Zero Out-of-Scope Bloat:** Do not introduce Hume.ai, SSO, Stripe, Kubernetes, Pinecone, or unrelated refactors unless explicitly instructed.

---

## 2. Planning & Execution Workflow

When starting an implementation block:

1. **Pre-Flight Check:**
   - Verify `git status --short` (ensure clean or expected working state).
   - Read relevant domain models in `apps/api/app/schemas/dtos.py` and `apps/web/src/lib/state-machine/types.ts`.
2. **Execution:**
   - Write or update server-side providers and routers first.
   - Maintain strict separation between conversation generation and rubric scoring.
   - Ensure all provider API keys remain server-side only.
   - Update frontend adapters and components with proper error handling and fallback states.
3. **Quality Gate Execution:**
   - Execute the verification workflow (`akademx10-verification`).
   - Ensure both backend unittests and frontend build pass before requesting review.

---

## 3. Subagent Delegation Guidelines

- **Independent Parallel Tasks:** Delegate to parallel subagents ONLY when work affects completely disjoint files/subsystems (e.g. backend provider service vs frontend UI component).
- **No Shared File Conflicts:** Never assign two concurrent subagents to modify the same file (e.g. `session-runner.tsx` or `learner.py`).
- **Clear Scopes:** Provide subagents with explicit file paths, expected signatures, and boundary constraints.
- **Reviewer Handoff:** Always invoke or prompt the Reviewer Agent (`akademx10-reviewer`) after substantial modifications.
