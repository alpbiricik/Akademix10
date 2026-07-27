import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MockLoginForm } from "@/app/login/mock-login-form";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#25214d] px-4 py-10">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(24,197,181,0.26),transparent_28rem),radial-gradient(circle_at_bottom_right,rgba(230,42,117,0.22),transparent_24rem)]" />
      <Card className="relative w-full max-w-md rounded-lg border-white/10 bg-white shadow-2xl shadow-black/20">
        <CardHeader>
          <Link href="/" className="text-sm font-semibold text-teal-700">
            AkademX10 XAI
          </Link>
          <CardTitle>Choose your workspace</CardTitle>
          <p className="text-sm leading-6 text-slate-600">
            Select your account type to continue into the right AkademX10 workspace.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <MockLoginForm />
        </CardContent>
      </Card>
    </main>
  );
}
