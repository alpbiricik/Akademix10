# AkademX10 Copilot Instructions

You are helping build AkademX10, an AI-powered competency development and roleplay training SaaS.

Current phase: Phase 1 clickable prototype.

Do not implement real AI, real LiveAvatar, real STT/TTS, payment, SSO, or production backend unless explicitly asked.

Prioritize:
- clean TypeScript
- Next.js App Router
- reusable components
- mock data first
- state-machine driven training flow
- simple and readable architecture
- no over-engineering

Product concept:
- 40-minute training session
- 21-step state-machine
- avatar is active only in selected interactive blocks
- video blocks are pre-rendered or placeholder
- AI responses are mocked in Phase 1
- final report contains skill scores, feedback, and action plan

Use these entities:
- User
- TrainingModule
- TrainingState
- TrainingSession
- UserAnswer
- SkillScore
- FinalReport

Coding style:
- Use TypeScript types/interfaces.
- Keep business logic outside UI components when possible.
- Put mock data under src/lib/mock-data.
- Put state-machine helpers under src/lib/state-machine.
- Put reusable UI components under src/components.
- Use Tailwind and shadcn/ui.
- Keep components small and readable.

Never add unnecessary dependencies.
Never use real API keys in code.
Never store secrets in frontend.