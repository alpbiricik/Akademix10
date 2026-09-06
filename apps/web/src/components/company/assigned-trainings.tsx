"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ClipboardList, PlayCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getCompanyTrainings } from "@/lib/adapters/companyAdapter";
import { BROWSER_ASSIGNMENTS_STORAGE_KEY } from "@/lib/adapters/platformAdapter";
import type { TrainingTemplateDTO } from "@/lib/contracts/dtos";
import type { TrainingTemplate } from "@/lib/state-machine/types";

interface AssignedTraining {
  id: string;
  templateId: string;
  title: string;
  companyId: string;
  companyName: string;
  assignedAt: string;
  status: "sent_to_company";
}

export function AssignedTrainings() {
  const [assignments, setAssignments] = useState<AssignedTraining[]>([]);
  const [templates, setTemplates] = useState<Array<TrainingTemplate | TrainingTemplateDTO>>([]);

  useEffect(() => {
    queueMicrotask(() => {
      setAssignments(readAssignments());
    });
    getCompanyTrainings().then(setTemplates);
  }, []);

  const displayItems = useMemo(() => {
    if (assignments.length) return assignments;

    return templates.slice(0, 3).map((template) => ({
      id: `default-${template.id}`,
      templateId: template.id,
      title: template.title,
      companyId: "company-demo",
      companyName: "Northwind Sales Academy",
      assignedAt: "Current assignment",
      status: "sent_to_company" as const,
    }));
  }, [assignments, templates]);

  return (
    <Card className="rounded-lg border-slate-200">
      <CardHeader>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>Assigned trainings from AkademX10</CardTitle>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              Trainings sent by the AkademX10 admin team appear here for company rollout.
            </p>
          </div>
          <Badge className="bg-teal-50 text-teal-800">{displayItems.length} available</Badge>
        </div>
      </CardHeader>
      <CardContent className="grid gap-3">
        {displayItems.map((assignment) => {
          const template = templates.find((item) => item.id === assignment.templateId);

          return (
            <AssignedTrainingCard key={assignment.id} assignment={assignment} template={template} />
          );
        })}
      </CardContent>
    </Card>
  );
}

function AssignedTrainingCard({
  assignment,
  template,
}: {
  assignment: AssignedTraining;
  template?: TrainingTemplate | TrainingTemplateDTO;
}) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-4">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-semibold">{assignment.title}</p>
            {template ? <Badge variant="secondary">{template.category}</Badge> : null}
          </div>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            {template?.description ?? "Custom training sent by AkademX10 admin."}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge variant="outline">{template?.estimatedDurationMin ?? 40} min</Badge>
            <Badge variant="outline">{template?.defaultStateCount ?? 21} states</Badge>
            <Badge variant="outline">{template?.avatarPolicy.activeTargetMin ?? 7} avatar min</Badge>
            <Badge variant="outline">Sent to {assignment.companyName}</Badge>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/company/trainings" className="inline-flex h-9 shrink-0 items-center justify-center gap-1.5 rounded-md border border-slate-200 bg-white px-2.5 text-sm font-medium text-slate-900 shadow-xs transition hover:bg-slate-100">
            <ClipboardList className="h-4 w-4" />
            Review
          </Link>
          <Link href="/company/trainings" className="inline-flex h-9 shrink-0 items-center justify-center gap-1.5 rounded-md bg-slate-950 px-2.5 text-sm font-medium text-white transition hover:bg-slate-800">
            <PlayCircle className="h-4 w-4" />
            Rollout
          </Link>
        </div>
      </div>
    </div>
  );
}

function readAssignments(): AssignedTraining[] {
  try {
    const value = window.localStorage.getItem(BROWSER_ASSIGNMENTS_STORAGE_KEY);
    if (!value) return [];
    const parsed = JSON.parse(value);
    if (!Array.isArray(parsed)) return [];

    return parsed.filter((item): item is AssignedTraining => {
      return (
        typeof item.id === "string" &&
        typeof item.templateId === "string" &&
        typeof item.title === "string" &&
        typeof item.companyId === "string" &&
        typeof item.companyName === "string" &&
        typeof item.assignedAt === "string" &&
        item.status === "sent_to_company"
      );
    });
  } catch {
    return [];
  }
}
