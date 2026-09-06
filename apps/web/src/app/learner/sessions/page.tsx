import { redirect } from "next/navigation";

export default function LearnerSessionsRootPage() {
  redirect("/learner/sessions/active/report");
}
