export type TrainingCategory =
  | "Sales"
  | "Leadership"
  | "Project Management"
  | "Workplace Ethics";

export interface TrainingTemplate {
  id: string;
  title: string;
  category: TrainingCategory;
  audience: string;
  description: string;
  defaultDurationMin: number;
  stateCount: number;
  avatarTargetMin: number;
  avatarToggleTarget: number;
  videoSlots: string[];
  avatarCommandSlots: string[];
  rubricFocus: string[];
}

export interface MockCustomerCompany {
  id: string;
  name: string;
  segment: string;
  learners: number;
}

export const trainingTemplates: TrainingTemplate[] = [
  {
    id: "sales-communication-roleplay",
    title: "Sales Communication Roleplay",
    category: "Sales",
    audience: "Sales and customer success teams",
    description:
      "Consultative selling, objection handling, customer empathy, and next-step closing practice.",
    defaultDurationMin: 40,
    stateCount: 21,
    avatarTargetMin: 7,
    avatarToggleTarget: 10,
    videoSlots: ["Customer context brief", "Value framing lesson", "Proof point lesson", "Summary recap"],
    avatarCommandSlots: ["Coach greeting", "Objection model", "Confidence reset", "Report handoff"],
    rubricFocus: ["Clarity", "Empathy", "Objection Handling", "Closing", "Confidence"],
  },
  {
    id: "leadership-feedback-coaching",
    title: "Leadership Feedback and Coaching",
    category: "Leadership",
    audience: "Team leads and first-time managers",
    description:
      "Practice giving clear feedback, coaching without blame, and aligning expectations after difficult moments.",
    defaultDurationMin: 35,
    stateCount: 18,
    avatarTargetMin: 6,
    avatarToggleTarget: 8,
    videoSlots: ["Feedback model", "Difficult conversation example", "Coaching close"],
    avatarCommandSlots: ["Manager coach intro", "Tone calibration", "Roleplay debrief"],
    rubricFocus: ["Clarity", "Empathy", "Accountability", "Coaching", "Confidence"],
  },
  {
    id: "project-management-alignment",
    title: "Project Management Alignment",
    category: "Project Management",
    audience: "Project managers and cross-functional leads",
    description:
      "Scope alignment, stakeholder communication, risk escalation, and deadline negotiation practice.",
    defaultDurationMin: 45,
    stateCount: 22,
    avatarTargetMin: 7,
    avatarToggleTarget: 10,
    videoSlots: ["Project brief", "Risk escalation pattern", "Stakeholder update example"],
    avatarCommandSlots: ["PM coach intro", "Escalation rehearsal", "Decision recap"],
    rubricFocus: ["Structure", "Risk Framing", "Stakeholder Alignment", "Decision Quality"],
  },
  {
    id: "workplace-ethics-scenarios",
    title: "Workplace Ethics Scenarios",
    category: "Workplace Ethics",
    audience: "All employees",
    description:
      "Recognize ethical risks, speak up safely, and choose appropriate escalation paths.",
    defaultDurationMin: 30,
    stateCount: 16,
    avatarTargetMin: 5,
    avatarToggleTarget: 7,
    videoSlots: ["Ethics principles", "Speak-up scenario", "Escalation path recap"],
    avatarCommandSlots: ["Ethics coach intro", "Scenario reflection", "Commitment close"],
    rubricFocus: ["Judgment", "Clarity", "Courage", "Policy Awareness"],
  },
];

export const customerCompanies: MockCustomerCompany[] = [
  { id: "northwind-sales", name: "Northwind Sales Academy", segment: "B2B sales", learners: 312 },
  { id: "contoso-cs", name: "Contoso Customer Success", segment: "SaaS customer success", learners: 188 },
  { id: "fabrikam-retail", name: "Fabrikam Retail Enablement", segment: "Retail operations", learners: 420 },
];

export const ASSIGNED_TRAININGS_STORAGE_KEY = "akademx10.assignedTrainings";
