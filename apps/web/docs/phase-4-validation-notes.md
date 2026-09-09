# Phase 4 implementation and acceptance record

Date: 2026-09-07. Branch: `voice-avatar-poc`.

This change keeps Gemini, ElevenLabs and LiveAvatar Lite, including the confirmed
PCM16 / 24 kHz audio framing, paced delivery and WebSocket receive pump. It adds
the missing evaluation connection and failure recovery around that path.

## Implemented blocks

1. **Final evaluation:** omitted live-state answers are collected from the
   session's backend TTL context. Every accepted learner turn is included; avatar
   replies are excluded. Up to three 2000-character turns fit the final-only 8000
   character bound; the existing standalone scoring limit remains 5000. Text
   drafts remain in sessionStorage. No raw answer is inserted into Supabase.
   Confirmed persistence clears conversation context. Missing/expired evidence
   fails explicitly rather than generating an empty report.
   The unused legacy `/answers` HTTP route now returns `final_evaluation_required`
   instead of bypassing Evaluation Contract v2 with per-state scoring. The current
   session runner uses local drafts and finalize; its active flow is unchanged.
2. **Retry and cache:** one process-local claim per session, owner-safe renewal,
   structured-result reuse on persistence retry, DB completion recheck before
   scoring, bounded thread-safe caches with active expiry. A completed request
   reads the persisted report without calling the scorer again. Activity extends
   earlier states' TTL for final evaluation, without feeding those states to the
   conversation model. Restart clears the session's temporary conversation data.
3. **Avatar lifecycle:** create/start is idempotent; a start must match a
   server-issued token. Stop affects only the owned socket. Stale stops cannot
   remove replacements. Timed cleanup and whole-utterance send serialization are
   covered by local tests.
4. **Recovery:** written conversation uses `textOnly` and bypasses TTS. TTS
   failures preserve the generated text. Failed background avatar delivery makes
   the same PCM available as an in-memory WAV for browser playback, for at most
   120 seconds. Delivery reads use normal learner JWT/session authorization.
   STT idle waits are bounded; blocking conversation work leaves the asyncio
   event loop. `VOICE_ENABLED=false` and `LIVE_AVATAR_ENABLED=false` provide
   independent server-side kill switches; both default to true.
5. **Measurements:** authenticated
   `GET /api/learner/sessions/{id}/voice/metrics` returns numeric-only counts,
   p50/p95 observations, usage and optional configured cost estimates. Unknown
   prices return null, never a claimed zero actual cost. Data is process-local
   with TTL. `apps/api/scripts/voice_poc_report.py` exports this report using a
   dedicated learner JWT from `AKADEMX10_TEST_ACCESS_TOKEN`; do not paste a JWT
   into chat, command history or a committed file.

## Verification

- Backend compileall: PASS.
- Backend unittest discovery: 163 total; 136 passed, 27 skipped. Skips are
  pre-existing legacy mock authorization/report endpoint tests, not live-provider
  or hosted JWT evidence.
- Frontend adapter tests: 5 passed (`node --test apps/web/tests/session-adapter.test.mjs`).
- Frontend ESLint: PASS, no errors or warnings.
- Next.js production build: PASS; canonical learner/company/platform report
  routes remain present.
- Browser bundle scan: 34 JavaScript files; no configured server provider or
  privileged Supabase key found. Values were not printed.
- `git diff --check`: PASS (line-ending notices only).
- Ten local deterministic lifecycle cycles, concurrent finalization, persistence
  retry, cache expiry/owner replacement, cross-session delivery isolation and
  actual loopback WebSocket queue/ping regression tests pass.

The obsolete migration test filename was corrected from
`0006_restrict_finalize_rpc_grants.sql` to the existing
`0009_restrict_finalize_rpc_grants.sql`; the assertions still verify revoked
anonymous access. No migration or hosted database mutation was executed here.

## Historical acceptance evidence and limits (superseded by September 8 update)

**Phase 4 status: NEEDS LIVE ACCEPTANCE; not GO and not production-ready.**

- The ten automated cycles use fake providers and a loopback WebSocket. They are
  not ten paid LiveAvatar sessions, Turkish quality approval or seven measured
  minutes of avatar use. A dedicated test learner must complete that live run,
  including a final report and a retry, before closing 4F.
- Measure provider billing/credits and inspect microphone denial, real provider
  disconnect, browser close and reconnect behavior in that run. Export the
  numeric report before its TTL expires or the API restarts. Configure the
  `VOICE_POC_*_USD_*` rates documented in `voice_poc_metrics.py` from the account's
  actual plan; compare estimates with billing independently.
- Current TTS is downloaded completely before the existing paced avatar send.
  This working path was deliberately preserved. Full-response latency is not
  LLM time-to-first-token; provider first-audio time is not browser playback
  latency; transport completion is not avatar first-frame timing. Progressive
  streaming and browser first-frame measurement remain separate 4B/4F work.
- The cache protocol supports a future Redis-compatible implementation, but
  this POC still uses one API process. It does not provide distributed scoring
  leases or restart-resumable raw conversation context. Multi-worker rollout
  requires an actual shared cache/claim implementation and validation.
- Next-state AI memory is unchanged: each state follows its own scenario. The
  final evaluator collects all retained learner answers.
- Existing generic rubrics are still used; material upload, rubric authoring
  and publishing are Phase 5 content operations, not delivered by this change.
- No real hosted JWT/RLS/browser acceptance run or provider price verification
  was performed in this change. The separate reviewer turn was attempted but
  could not finish because of the agent usage limit; the lead inspected the
  changes and ran the recorded gates. Independent review remains pending.

Use a fresh test session after restarting the backend to exercise the new
collection path. Conversations whose old in-memory context already expired
cannot be recovered or retroactively scored from missing evidence.


## September 8 implementation update

Status: CODE IMPLEMENTED / LIVE AND HOSTED ACCEPTANCE PENDING. This is not Phase 4 GO.

### Delivered

- Initial text/voice selection before mounting an avatar. Written mode calls the
  existing `textOnly` conversation endpoint and includes accepted answers in final
  evaluation without STT, TTS or avatar startup. Switching modes cancels delivery.
- Missing final answers return `missing_session_answers` and `missingStateIds`.
  Recovery navigates to a missing step and removes its completion marker; existing
  live evidence and completed reports cannot be overwritten through recovery.
- `VOICE_STREAMING_ENABLED=false` and `CONVERSATION_STREAMING_ENABLED=false` are
  default-off server flags. The new TTS pull stream feeds paced PCM24k frames to
  the existing avatar transport with bounded concurrent deliveries. Gemini SSE
  measures first-token latency but validates the complete JSON before speaking.
- Quota/rate-limit failures have sanitized error codes and nonretryable LLM
  failures do not repeat provider requests. Text is preserved on TTS failure.
  Partially delivered audio is not automatically replayed. Cancellation is checked
  before synthesis and each send; blocking provider reads retain a 30-second timeout.
- Frontend release while token/connect/start is pending now prevents orphan avatar
  sessions. Existing receive pump and default buffered audio route are retained.
- Authenticated numeric browser measurements and first-token/retry/cancel metrics.
  `browser_end_to_end` measures response arrival; browser media `playing` measures
  playback readiness, not proven audible avatar speech onset. Continuous WebRTC
  audio may not fire another playing event for every reply. These limitations must
  be considered during real latency acceptance; no lip-sync claim is made.
- Additive migration `0010_voice_usage_summary.sql` adds a numeric-only summary
  and narrowly authorized owner/active learner/membership RPC. Existing RLS is
  unchanged. Summary persistence is bounded and asynchronous at finalize/stop.
  Unknown actual provider billing remains null, separate from estimates.

### Verification at implementation handoff

- Backend: 187 discovered, 160 passed, 27 legacy tests skipped; compileall PASS.
- Frontend: 11 Node tests PASS, lint PASS, production build PASS.
- 34 browser JavaScript bundles scanned against configured backend secret values:
  no matches; values were not printed.
- New route tests use actual Bearer/profile/role dependencies with fake external
  transport. They cover missing token, wrong role, cross-company reads, numeric
  metric validation and evidence recovery. They are not hosted JWT/RLS evidence.
- New avatar manager tests exercise release during token/connect/start and
  StrictMode reacquisition. New provider tests exercise SSE, bounded PCM,
  cancellation, partial-delivery handling and safe error classification.
- Hosted acceptance script `apps/api/scripts/phase4_hosted_acceptance.py --help`
  checked. No provider, paid, or hosted acceptance run was performed.

### Rollout and remaining gates

1. Restart backend and frontend to load the code. Select **Yazili devam et** on
   the first avatar step. Complete real answers in every required step and click
   **Egitimi Bitir**, then open the canonical session report. Keep the same tab;
   backend live evidence expires after the configured inactivity TTL or restart.
2. Migration 0010 is prepared but NOT applied. Apply through the existing database
   migration process in the test environment and verify the RPC with owner,
   cross-tenant, inactive and anonymous users. Until then optional summary writes
   fail safely and metrics remain temporary. No existing training data is reset.
3. Configure dedicated local test environment variables (never paste tokens into
   chat): AKADEMX10_TEST_ACCESS_TOKEN, AKADEMX10_TEST_OTHER_ACCESS_TOKEN and
   AKADEMX10_TEST_SESSION_ID. The latter must be an already completed test session.
   Run the hosted acceptance script with `--run`. Exact same-key finalize replay
   additionally needs the exact original body via AKADEMX10_TEST_FINALIZE_BODY_JSON;
   otherwise the script only verifies new-key rejection and reports replay pending.
   The script does not perform the initial browser training or direct Postgres RLS
   test and cannot prove provider invocation counts from HTTP report equality alone.
4. Credits permitting: compare buffered and streaming modes using ten controlled
   avatar cycles and approximately seven active minutes; verify Turkish quality,
   final reply audio, interruption/reconnect and microphone denial. Compare numeric
   exports with actual provider billing before GO/CONDITIONAL GO/NO-GO.
5. Single API process only. No Redis deployment or restart-resumable raw evidence.
   Numeric summary snapshots reject older smaller counts; after process restart,
   partial new measurements may not replace a larger previously persisted summary.

Existing training contents, step order, scoring engine and user home-page edits
were preserved. No commit, push or merge was performed. Phase 5 starts with a
versioned step editor, followed by content-to-draft generation and corporate
assignment/enrollment; these features were not mixed into the Phase 4 change.


### Review follow-up

An independent reviewer inspected the root/frontend/provider changes (excluding
its own metrics implementation, reviewed by the lead). It identified buffered
TTS read-error normalization and a missing cancellation counter. Both were fixed
with regression tests: connection reset/broken pipe/incomplete HTTP reads now
preserve typed text fallback, and cancellation counts actual active delivery jobs
once, not every repeated stop request. Recovery UI text corruption was corrected.

Independent follow-up verdict: PASS for reviewed local code; no open BLOCKER or IMPORTANT findings. Reviewer independently ran 11 streaming tests. The added nonretryable quota test also confirms one conversation provider call and preserved learner evidence. Hosted migration/RLS, real browser and paid voice acceptance remain pending.


## Pre-training briefing and written opening correction

The learner now chooses written/voice mode in a briefing before training content
is shown, then explicitly starts. Repeated in-step mode switching is removed.
The existing authenticated opening endpoint accepts textOnly=true and generates
an actual opening question with no TTS/orchestrator invocation, even when voice is
disabled. This fixes the previous written mode displaying scenario instructions
without an AI question. The backend test verifies both text opening and voice-off
rejection of normal audio opening. Session mode is scoped to the training run;
written answers still feed the unchanged final evaluation path.


## September 9: prepare opening before avatar startup

Voice-mode opening order is now prepare text/PCM -> mount/connect avatar -> send
prepared speech. Preparation never creates an avatar session; a TTS/quota failure
returns the generated text with no prepared ID, so the UI cannot open a billed
avatar for that failed opening. The default subsequent-turn voice pipeline and
PCM24k pacing remain unchanged. This removes LLM/TTS preparation from the period
where the avatar is already open; real provider connection/playback delay remains.

The new authenticated POST /sessions/{id}/voice/opening/prepare accepts stateId.
The existing opening endpoint accepts optional preparedOpeningId and textOnly.
Preparation is single-flight and held only in bounded RAM (120-second TTL,
16 entries, 2MB per entry, 8MB stored PCM). Duplicate consumption does not start
another delivery or repeat synthesis. Cancellation and current/completed-state
checks prevent replay into a stale step. No migration is needed for this fix.

Backend verification: 197 tests discovered, 170 passed, 27 legacy skips. Eight
new preparation regressions cover concurrent duplicate preparation, consume,
expiry, quota, cancellation, capacity and completed-state refusal. Real paid
provider startup latency and billing reduction are not measured by these tests.

Frontend verification after this correction: 19 tests passed, including the
pre-training briefing, locked written mode, prepare-before-avatar ordering and
the 30-second first-frame watchdog. ESLint and the Next.js production build pass.

Avatar startup now has a 30-second first-frame watchdog; failure unmounts the avatar and cancels prepared delivery. Prepared failures retain the question for written fallback; explicit retry clears the failed cached preparation before trying again. Provider/network teardown is best effort and remains backed by the server session timeout.

## September 9: PCM pacing correction

Buffered and streaming LiveAvatar audio now share monotonic deadline pacing.
WebSocket send time is deducted from the next wait instead of accumulating on top
of every 100ms PCM frame. A long network stall resets the deadline so recovery
does not emit an uncontrolled catch-up burst. Arbitrary TTS chunks are reframed
with at most one 4800-byte frame buffered; an odd final PCM16 byte is rejected.
The 24kHz mono PCM format and existing agent.speak/end contract are unchanged.
