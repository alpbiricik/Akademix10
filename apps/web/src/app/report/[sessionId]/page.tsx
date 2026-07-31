import { redirect } from "next/navigation";

export default async function LegacyReportPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  redirect(`/learner/report/${sessionId}`);
}
