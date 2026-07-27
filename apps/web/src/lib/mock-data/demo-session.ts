export type DemoSessionStateType =
  | "intro"
  | "video"
  | "avatar"
  | "question"
  | "roleplay"
  | "reflection"
  | "feedback"
  | "final";

export interface DemoSessionState {
  id: string;
  order: number;
  title: string;
  type: DemoSessionStateType;
  estimatedMin: number;
  avatarEnabled: boolean;
  avatarBudgetSec: number;
  prompt: string;
  rubric: string;
  skillTags: string[];
}

export interface DemoSession {
  sessionId: string;
  title: string;
  description: string;
  totalDurationMin: 40;
  avatarTargetMin: 7;
  avatarToggleTarget: 10;
  bufferedAvatarMin: 8.05;
  safeBudgetUsd: 1.25;
  states: DemoSessionState[];
}

export const demoSession: DemoSession = {
  sessionId: "demo-session-1",
  title: "Sales Communication Roleplay Sprint",
  description:
    "A 40-minute training session for workplace communication, consultative selling, objection handling, and confident customer follow-up.",
  totalDurationMin: 40,
  avatarTargetMin: 7,
  avatarToggleTarget: 10,
  bufferedAvatarMin: 8.05,
  safeBudgetUsd: 1.25,
  states: [
    {
      id: "demo-state-01",
      order: 1,
      title: "Session orientation",
      type: "intro",
      estimatedMin: 2,
      avatarEnabled: false,
      avatarBudgetSec: 0,
      prompt:
        "Welcome to AkademX10 XAI. You will practice a realistic sales conversation and receive coaching feedback.",
      rubric: "Understands the session goal, structure, and expected participation.",
      skillTags: ["Communication", "Confidence"],
    },
    {
      id: "demo-state-02",
      order: 2,
      title: "Customer context brief",
      type: "video",
      estimatedMin: 3,
      avatarEnabled: false,
      avatarBudgetSec: 0,
      prompt:
        "Training content introduces a customer success manager preparing for a renewal conversation with a skeptical account owner.",
      rubric: "Identifies customer context, business pressure, and conversation objective.",
      skillTags: ["Product Knowledge", "Communication"],
    },
    {
      id: "demo-state-03",
      order: 3,
      title: "Coach sets the standard",
      type: "avatar",
      estimatedMin: 1,
      avatarEnabled: true,
      avatarBudgetSec: 45,
      prompt:
        "LiveAvatar Lite coach frames the standard: listen first, clarify value, handle objections, and close with a next step.",
      rubric: "Receives concise coaching and understands the success criteria.",
      skillTags: ["Confidence", "Communication"],
    },
    {
      id: "demo-state-04",
      order: 4,
      title: "First response question",
      type: "question",
      estimatedMin: 2,
      avatarEnabled: false,
      avatarBudgetSec: 0,
      prompt:
        "A customer says: We are not sure the platform is worth renewing. What is your first response?",
      rubric: "Acknowledges concern, avoids defensiveness, and asks a useful discovery question.",
      skillTags: ["Empathy", "Communication", "Objection Handling"],
    },
    {
      id: "demo-state-05",
      order: 5,
      title: "Discovery question practice",
      type: "reflection",
      estimatedMin: 2,
      avatarEnabled: false,
      avatarBudgetSec: 0,
      prompt:
        "Write two discovery questions that help uncover the customer's real concern before pitching a solution.",
      rubric: "Questions are open-ended, specific, and tied to business outcomes.",
      skillTags: ["Communication", "Empathy"],
    },
    {
      id: "demo-state-06",
      order: 6,
      title: "Value framing lesson",
      type: "video",
      estimatedMin: 3,
      avatarEnabled: false,
      avatarBudgetSec: 0,
      prompt:
        "Short content block: connect product value to customer outcomes, not feature lists.",
      rubric: "Can distinguish feature language from outcome language.",
      skillTags: ["Product Knowledge", "Closing"],
    },
    {
      id: "demo-state-07",
      order: 7,
      title: "Coach micro-model",
      type: "avatar",
      estimatedMin: 1,
      avatarEnabled: true,
      avatarBudgetSec: 45,
      prompt:
        "LiveAvatar Lite coach demonstrates a short empathy-to-value response pattern.",
      rubric: "Notices the response structure and can reuse the pattern.",
      skillTags: ["Empathy", "Structure"],
    },
    {
      id: "demo-state-08",
      order: 8,
      title: "Roleplay setup",
      type: "roleplay",
      estimatedMin: 3,
      avatarEnabled: true,
      avatarBudgetSec: 60,
      prompt:
        "Customer: Your competitor is cheaper and promises faster onboarding. Respond in a way that protects value without dismissing the concern.",
      rubric: "Shows empathy, clarifies priorities, differentiates value, and asks for a concrete next step.",
      skillTags: ["Objection Handling", "Product Knowledge", "Confidence"],
    },
    {
      id: "demo-state-09",
      order: 9,
      title: "Roleplay checkpoint",
      type: "feedback",
      estimatedMin: 2,
      avatarEnabled: true,
      avatarBudgetSec: 30,
      prompt:
        "The checkpoint summarizes the roleplay response and highlights where the answer created or lost trust.",
      rubric: "Feedback is behavior-specific, balanced, and connected to the rubric.",
      skillTags: ["Communication", "Objection Handling"],
    },
    {
      id: "demo-state-10",
      order: 10,
      title: "Confidence reset",
      type: "avatar",
      estimatedMin: 1,
      avatarEnabled: true,
      avatarBudgetSec: 45,
      prompt:
        "LiveAvatar Lite coach reinforces calm pace, confident tone, and one sentence to recover from pressure.",
      rubric: "Learner receives a memorable confidence cue.",
      skillTags: ["Confidence", "Communication"],
    },
    {
      id: "demo-state-11",
      order: 11,
      title: "Objection handling drill",
      type: "question",
      estimatedMin: 2,
      avatarEnabled: false,
      avatarBudgetSec: 0,
      prompt:
        "How would you respond if the customer says: I do not see measurable ROI from the last quarter?",
      rubric: "Acknowledges the concern, proposes evidence review, and avoids unsupported claims.",
      skillTags: ["Objection Handling", "Product Knowledge"],
    },
    {
      id: "demo-state-12",
      order: 12,
      title: "Proof point lesson",
      type: "video",
      estimatedMin: 2,
      avatarEnabled: false,
      avatarBudgetSec: 0,
      prompt:
        "Content block: use adoption, retention, and time-to-value signals as proof points in renewal conversations.",
      rubric: "Connects proof points to customer outcomes.",
      skillTags: ["Product Knowledge", "Closing"],
    },
    {
      id: "demo-state-13",
      order: 13,
      title: "Stakeholder empathy",
      type: "reflection",
      estimatedMin: 2,
      avatarEnabled: false,
      avatarBudgetSec: 0,
      prompt:
        "What pressure might the customer be under internally, and how should that change your tone?",
      rubric: "Infers stakeholder pressure and adjusts communication with empathy.",
      skillTags: ["Empathy", "Communication"],
    },
    {
      id: "demo-state-14",
      order: 14,
      title: "Coach reframes the close",
      type: "avatar",
      estimatedMin: 1,
      avatarEnabled: true,
      avatarBudgetSec: 45,
      prompt:
        "LiveAvatar Lite coach explains that closing means securing a useful next commitment, not forcing a yes.",
      rubric: "Understands close as a next-step agreement.",
      skillTags: ["Closing", "Confidence"],
    },
    {
      id: "demo-state-15",
      order: 15,
      title: "Closing roleplay",
      type: "roleplay",
      estimatedMin: 3,
      avatarEnabled: true,
      avatarBudgetSec: 60,
      prompt:
        "Customer: Send me the pricing and I will think about it. Guide the conversation toward a clear next step.",
      rubric: "Clarifies decision process, confirms value criteria, and proposes a dated follow-up.",
      skillTags: ["Closing", "Confidence", "Communication"],
    },
    {
      id: "demo-state-16",
      order: 16,
      title: "Scoring checkpoint",
      type: "feedback",
      estimatedMin: 2,
      avatarEnabled: false,
      avatarBudgetSec: 0,
      prompt:
        "Scoring compares the learner response against clarity, empathy, structure, objection handling, and confidence.",
      rubric: "Scores are transparent and tied to observable behavior.",
      skillTags: ["Communication", "Closing", "Confidence"],
    },
    {
      id: "demo-state-17",
      order: 17,
      title: "Final coaching cue",
      type: "avatar",
      estimatedMin: 1,
      avatarEnabled: true,
      avatarBudgetSec: 45,
      prompt:
        "LiveAvatar Lite coach gives one final cue before the learner writes a personal action plan.",
      rubric: "Coaching is concise, practical, and linked to the session objective.",
      skillTags: ["Confidence", "Closing"],
    },
    {
      id: "demo-state-18",
      order: 18,
      title: "Personal action plan",
      type: "reflection",
      estimatedMin: 2,
      avatarEnabled: false,
      avatarBudgetSec: 0,
      prompt:
        "Write one sentence you will use in your next renewal or objection-handling conversation.",
      rubric: "Action is specific, usable, and connected to a realistic conversation.",
      skillTags: ["Communication", "Confidence", "Closing"],
    },
    {
      id: "demo-state-19",
      order: 19,
      title: "Summary video",
      type: "video",
      estimatedMin: 2,
      avatarEnabled: false,
      avatarBudgetSec: 0,
      prompt:
        "Content recap: discovery, empathy, value proof, objection handling, and next-step closing.",
      rubric: "Can recall the core communication model.",
      skillTags: ["Communication", "Product Knowledge"],
    },
    {
      id: "demo-state-20",
      order: 20,
      title: "Avatar handoff to report",
      type: "avatar",
      estimatedMin: 1,
      avatarEnabled: true,
      avatarBudgetSec: 153,
      prompt:
        "LiveAvatar Lite coach closes the experience and explains that the report will summarize skills and next actions.",
      rubric: "Learner understands completion and report handoff.",
      skillTags: ["Confidence", "Communication"],
    },
    {
      id: "demo-state-21",
      order: 21,
      title: "Final summary",
      type: "final",
      estimatedMin: 2,
      avatarEnabled: true,
      avatarBudgetSec: 0,
      prompt:
        "Final summary: review strengths, growth areas, and the next action before opening the report.",
      rubric: "Summarizes performance and points learner toward continued skill development.",
      skillTags: ["Communication", "Empathy", "Closing", "Confidence"],
    },
  ],
};

export const demoSessions: DemoSession[] = [demoSession];
