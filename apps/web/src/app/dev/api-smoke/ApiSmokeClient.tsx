"use client";

import { useState } from "react";
import { CheckCircle2, Loader2, PlayCircle, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { smokeTestAllApi, type SmokeSuiteResult } from "@/lib/api/smokeTest";

interface SmokeState {
  ok: boolean;
  mode: string;
  suites: SmokeSuiteResult[];
}

export function ApiSmokeClient() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SmokeState | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runSmokeTest() {
    setLoading(true);
    setError(null);
    try {
      setResult(await smokeTestAllApi());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown smoke test error.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 p-6 text-slate-950">
      <div className="mx-auto max-w-5xl space-y-6">
        <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Developer tools</p>
          <div className="mt-2 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="text-3xl font-semibold">Developer API Smoke Test</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                Runs frontend adapter calls against the FastAPI backend and Supabase-backed runtime.
              </p>
            </div>
            <Button type="button" onClick={runSmokeTest} disabled={loading} className="bg-slate-950 text-white hover:bg-slate-800">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <PlayCircle className="h-4 w-4" />}
              Run Smoke Test
            </Button>
          </div>
        </section>

        {error ? <StatusCard ok={false} title="Smoke test error" detail={error} /> : null}
        {result ? <StatusCard ok={result.ok} title={`Mode: ${result.mode}`} detail={result.ok ? "All API smoke suites passed." : "One or more suites need attention."} /> : null}

        <div className="grid gap-4">
          {result?.suites.map((suite) => (
            <Card key={suite.name} className="rounded-lg border-slate-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  {suite.ok ? <CheckCircle2 className="h-5 w-5 text-emerald-700" /> : <XCircle className="h-5 w-5 text-red-700" />}
                  {suite.name}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {suite.message ? <p className="text-sm text-slate-600">{suite.message}</p> : null}
                {suite.checks.map((check) => (
                  <div key={check.name} className="flex flex-col gap-1 rounded-md bg-slate-50 p-3 text-sm sm:flex-row sm:items-center sm:justify-between">
                    <span className="font-medium">{check.name}</span>
                    <span className={check.ok ? "text-emerald-700" : "text-red-700"}>{check.detail}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </main>
  );
}

function StatusCard({ ok, title, detail }: { ok: boolean; title: string; detail: string }) {
  return (
    <Card className="rounded-lg border-slate-200">
      <CardContent className="flex items-start gap-3 p-4">
        {ok ? <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald-700" /> : <XCircle className="mt-0.5 h-5 w-5 text-red-700" />}
        <div>
          <p className="font-semibold">{title}</p>
          <p className="mt-1 text-sm text-slate-600">{detail}</p>
        </div>
      </CardContent>
    </Card>
  );
}
