import { PlusCircle } from "lucide-react";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getPlatformTemplates } from "@/lib/adapters/platformAdapter";

export const dynamic = "force-dynamic";

export default async function PlatformTemplatesPage() {
  const templates = await getPlatformTemplates();

  return (
    <AppShell>
      <ProtectedRoute allowedRoles={["platform"]}>
        <div className="space-y-6">
          <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Platform templates</p>
                <h1 className="mt-2 text-3xl font-semibold">Training template library</h1>
                <p className="mt-2 max-w-3xl text-slate-600">Platform creates and configures reusable training products before assigning them to customer companies.</p>
              </div>
              <Button type="button" className="bg-slate-950 text-white hover:bg-slate-800">
                <PlusCircle className="h-4 w-4" />
                Create Template
              </Button>
            </div>
          </section>

          <div className="grid gap-4 md:grid-cols-2">
            {templates.map((template) => (
              <Card key={template.id} className="rounded-lg border-slate-200">
                <CardHeader>
                  <div className="flex items-start justify-between gap-3">
                    <CardTitle>{template.title}</CardTitle>
                    <Badge variant="secondary">{template.category}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm leading-6 text-slate-600">{template.description}</p>
                  <div className="flex flex-wrap gap-2">
                    {["Videos", "21-state flow", "LiveAvatar instructions", "Prompts", "Rubrics", "Skill tags"].map((item) => (
                      <Badge key={item} variant="outline">{item}</Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </ProtectedRoute>
    </AppShell>
  );
}
