import { redirect } from "next/navigation";

export default async function LegacySessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  redirect(`/learner/session/${sessionId}`);
}
