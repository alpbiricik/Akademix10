import type { TrainingModule, TrainingState } from "@/lib/state-machine/types";

export const communicationSalesStateIds = Array.from({ length: 21 }, (_, index) => `communication-sales-state-${String(index + 1).padStart(2, "0")}`);

export const communicationSalesStates: TrainingState[] = [
  ["intro", "Welcome and session goals", "Welcome to your AI customer communication roleplay. You will practice discovery, empathy, objection handling, and next-step closing.", "Understands the journey, expected participation, and scoring model.", ["Communication", "Confidence"], false, 0, "viewed"],
  ["video", "Customer context brief", "Short video: a renewal customer is unsure whether the platform is still worth the cost.", "Identifies customer context, pressure, and conversation objective.", ["Product Knowledge", "Communication"], false, 0, "viewed"],
  ["avatar", "Avatar coach welcome", "LiveAvatar Lite coach frames the practice standard: listen first, clarify value, handle objections, and close with a useful next step.", "Receives concise coaching and understands the success criteria.", ["Confidence", "Communication"], true, 45, "viewed"],
  ["question", "First response", "Customer says: We are not sure the platform is worth renewing. What is your first response?", "Acknowledges concern, avoids defensiveness, and asks a useful discovery question.", ["Empathy", "Communication"], false, 0, "answered"],
  ["video", "Value framing lesson", "Short video: connect product value to customer outcomes instead of feature lists.", "Can distinguish outcome language from feature language.", ["Product Knowledge", "Closing"], false, 0, "viewed"],
  ["roleplay", "Competitor objection", "Customer: Your competitor is cheaper and promises faster onboarding. Respond without dismissing the concern.", "Shows empathy, clarifies priorities, differentiates value, and asks for a next step.", ["Objection Handling", "Product Knowledge", "Confidence"], true, 60, "answered"],
  ["feedback", "Roleplay checkpoint", "Feedback checkpoint summarizes where your response created trust and where it could be sharper.", "Feedback is behavior-specific and connected to the rubric.", ["Communication", "Objection Handling"], false, 0, "manual"],
  ["reflection", "Discovery reflection", "Write two discovery questions that uncover the customer's real renewal concern.", "Questions are open-ended, specific, and tied to business outcomes.", ["Communication", "Empathy"], false, 0, "answered"],
  ["video", "Proof point lesson", "Short video: use adoption, retention, and time-to-value signals as proof points.", "Connects proof points to customer outcomes.", ["Product Knowledge", "Closing"], false, 0, "viewed"],
  ["question", "ROI objection drill", "How would you respond if the customer says: I do not see measurable ROI from last quarter?", "Acknowledges concern, proposes evidence review, and avoids unsupported claims.", ["Objection Handling", "Product Knowledge"], false, 0, "answered"],
  ["avatar", "Coach micro-model", "LiveAvatar Lite coach demonstrates an empathy-to-value response pattern.", "Learner notices the reusable response structure.", ["Empathy", "Structure"], true, 45, "viewed"],
  ["roleplay", "Executive stakeholder", "Customer: My CFO only cares about cost. Help the customer prepare a business case.", "Clarifies stakeholder criteria and maps value to business evidence.", ["Communication", "Product Knowledge", "Closing"], true, 60, "answered"],
  ["feedback", "Stakeholder feedback", "Feedback compares your executive-stakeholder answer against clarity, evidence, and next action.", "Scores are transparent and tied to observable behavior.", ["Communication", "Closing"], false, 0, "manual"],
  ["video", "Closing lesson", "Short video: closing means securing a useful next commitment, not forcing a yes.", "Understands close as a next-step agreement.", ["Closing", "Confidence"], false, 0, "viewed"],
  ["question", "Closing question", "What question would you ask before proposing the next meeting?", "Clarifies decision process before pushing a recommendation.", ["Closing", "Communication"], false, 0, "answered"],
  ["roleplay", "Pricing follow-up", "Customer: Send me the pricing and I will think about it. Guide the conversation toward a clear next step.", "Clarifies process, confirms value criteria, and proposes a dated follow-up.", ["Closing", "Confidence", "Communication"], true, 60, "answered"],
  ["reflection", "Personal phrase", "Write one sentence you will use in your next renewal or objection-handling conversation.", "Action is specific, realistic, and immediately usable.", ["Communication", "Confidence"], false, 0, "answered"],
  ["avatar", "Final coaching cue", "LiveAvatar Lite coach gives one final cue before the personal action plan.", "Coaching is concise, practical, and linked to the session objective.", ["Confidence", "Closing"], true, 45, "viewed"],
  ["feedback", "Final scoring checkpoint", "Final feedback summarizes skill progress and one focus area for the next conversation.", "Feedback connects strengths, growth areas, and next action.", ["Communication", "Empathy", "Closing"], false, 0, "manual"],
  ["reflection", "Final action plan", "Write your final action plan for the next customer conversation.", "Action plan is concrete, time-bound, and linked to a real scenario.", ["Action Planning", "Confidence"], false, 0, "answered"],
  ["final", "Final summary", "Session complete. Open your report to review scores, strengths, improvement areas, and next actions.", "Learner understands completion and report handoff.", ["Communication", "Confidence"], true, 105, "viewed"],
].map(([type, title, prompt, rubric, skillTags, avatarEnabled, avatarBudgetSec, completionRule], index) => ({
  id: communicationSalesStateIds[index],
  moduleId: "communication-sales-101",
  order: index + 1,
  title: String(title),
  type: type as TrainingState["type"],
  estimatedMin: index === 0 ? 2 : index === 20 ? 2 : 1 + (index % 3),
  avatarEnabled: Boolean(avatarEnabled),
  avatarBudgetSec: Number(avatarBudgetSec),
  prompt: String(prompt),
  rubric: String(rubric),
  skillTags: skillTags as string[],
  completionRule: completionRule as TrainingState["completionRule"],
}));

export const communicationSalesTraining: TrainingModule = {
  id: "communication-sales-101",
  templateId: "template-sales-communication",
  title: "AI Roleplay: Customer Communication",
  description: "A 40-minute AI-powered roleplay session for customer empathy, objection handling, and next-step closing.",
  durationMin: 40,
  stateIds: communicationSalesStateIds,
  skillTags: ["Communication", "Empathy", "Objection Handling", "Product Knowledge", "Closing", "Confidence"],
  status: "active",
};

export const trainingModules: TrainingModule[] = [communicationSalesTraining];
export const stressManagementTraining = communicationSalesTraining;
export const stressManagementStates = communicationSalesStates;
