"use client";

import { useEffect, useMemo, useState } from "react";
import { Bot, Building2, CheckCircle2, Send, Video } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { BROWSER_ASSIGNMENTS_STORAGE_KEY, assignTemplateToCompany, getPlatformCompanies, getPlatformTemplates } from "@/lib/adapters/platformAdapter";
import type { CompanyDTO, TrainingTemplateDTO } from "@/lib/contracts/dtos";
import type { Company, TrainingTemplate } from "@/lib/state-machine/types";

interface AssignedTraining {
  id: string;
  templateId: string;
  title: string;
  companyId: string;
  companyName: string;
  assignedAt: string;
  status: "sent_to_company";
}

export function TrainingAdminWorkspace() {
  const [templates, setTemplates] = useState<Array<TrainingTemplate | TrainingTemplateDTO>>([]);
  const [companies, setCompanies] = useState<Array<Company | CompanyDTO>>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [selectedCompanyId, setSelectedCompanyId] = useState("");
  const [customTitle, setCustomTitle] = useState("");
  const [videoNotes, setVideoNotes] = useState("Mock plan: context video, scenario video, recap video.");
  const [avatarCommands, setAvatarCommands] = useState("LiveAvatar Lite is concise, warm, and active only in critical coaching blocks.");
  const [sentAssignments, setSentAssignments] = useState<AssignedTraining[]>([]);

  useEffect(() => {
    let active = true;
    Promise.all([getPlatformTemplates(), getPlatformCompanies()]).then(([loadedTemplates, loadedCompanies]) => {
      if (!active) return;
      setTemplates(loadedTemplates);
      setCompanies(loadedCompanies);
      setSelectedTemplateId((current) => current || loadedTemplates[0]?.id || "");
      setSelectedCompanyId((current) => current || loadedCompanies[0]?.id || "");
      setCustomTitle((current) => current || loadedTemplates[0]?.title || "");
    });
    return () => {
      active = false;
    };
  }, []);

  const selectedTemplate = useMemo(
    () => templates.find((template) => template.id === selectedTemplateId) ?? templates[0],
    [selectedTemplateId, templates]
  );

  const selectedCompany = useMemo(
    () => companies.find((company) => company.id === selectedCompanyId) ?? companies[0],
    [selectedCompanyId, companies]
  );

  async function sendToCompany() {
    if (!selectedTemplate || !selectedCompany) return;

    const assignment: AssignedTraining = {
      id: `${selectedTemplate.id}-${selectedCompany.id}-${Date.now()}`,
      templateId: selectedTemplate.id,
      title: customTitle.trim() || selectedTemplate.title,
      companyId: selectedCompany.id,
      companyName: selectedCompany.name,
      assignedAt: new Date().toISOString(),
      status: "sent_to_company",
    };

    await assignTemplateToCompany({ templateId: selectedTemplate.id, companyId: selectedCompany.id });
    const current = readAssignments();
    const next = [assignment, ...current.filter((item) => item.templateId !== assignment.templateId || item.companyId !== assignment.companyId)];
    window.localStorage.setItem(BROWSER_ASSIGNMENTS_STORAGE_KEY, JSON.stringify(next));
    setSentAssignments((items) => [assignment, ...items]);
  }

  if (!selectedTemplate || !selectedCompany) {
    return <Card className="rounded-lg border-slate-200"><CardContent className="p-6 text-sm text-slate-600">Loading training factory...</CardContent></Card>;
  }

  return (
    <Card className="rounded-lg border-slate-200">
      <CardHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle>Training factory</CardTitle>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              Select a reusable template, define mock video/avatar notes, and send the training direction to a customer company.
            </p>
          </div>
          <Badge className="bg-teal-50 text-teal-800">Platform mock</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="template">Training template</Label>
              <select
                id="template"
                value={selectedTemplateId}
                onChange={(event) => {
                  setSelectedTemplateId(event.target.value);
                  const next = templates.find((template) => template.id === event.target.value);
                  setCustomTitle(next?.title ?? "");
                }}
                className="h-9 w-full rounded-md border border-slate-200 bg-white px-2.5 text-sm shadow-xs outline-none focus-visible:border-teal-600 focus-visible:ring-3 focus-visible:ring-teal-600/20"
              >
                {templates.map((template) => (
                  <option key={template.id} value={template.id}>{template.title}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="company">Send to company</Label>
              <select
                id="company"
                value={selectedCompanyId}
                onChange={(event) => setSelectedCompanyId(event.target.value)}
                className="h-9 w-full rounded-md border border-slate-200 bg-white px-2.5 text-sm shadow-xs outline-none focus-visible:border-teal-600 focus-visible:ring-3 focus-visible:ring-teal-600/20"
              >
                {companies.map((company) => (
                  <option key={company.id} value={company.id}>{company.name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="custom-title">Training title</Label>
              <Input id="custom-title" value={customTitle} onChange={(event) => setCustomTitle(event.target.value)} placeholder={selectedTemplate.title} />
            </div>
            <Button type="button" onClick={sendToCompany} className="w-full bg-slate-950 text-white hover:bg-slate-800">
              <Send className="h-4 w-4" />
              Send Training to Company
            </Button>
          </div>
          <TemplatePreview template={selectedTemplate} company={selectedCompany} />
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="rounded-lg border-slate-200">
            <CardHeader><CardTitle className="flex items-center gap-2 text-base"><Video className="h-5 w-5 text-teal-700" />Video inputs</CardTitle></CardHeader>
            <CardContent><Textarea value={videoNotes} onChange={(event) => setVideoNotes(event.target.value)} /></CardContent>
          </Card>
          <Card className="rounded-lg border-slate-200">
            <CardHeader><CardTitle className="flex items-center gap-2 text-base"><Bot className="h-5 w-5 text-teal-700" />LiveAvatar Lite instructions</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Textarea value={avatarCommands} onChange={(event) => setAvatarCommands(event.target.value)} />
              <p className="text-xs leading-5 text-slate-500">No real LiveAvatar calls are made in Phase 2A.</p>
            </CardContent>
          </Card>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="font-medium">Recently sent in this browser</p>
          <div className="mt-3 grid gap-2">
            {sentAssignments.length ? sentAssignments.map((assignment) => (
              <div key={assignment.id} className="flex flex-col gap-2 rounded-md bg-white p-3 text-sm sm:flex-row sm:items-center sm:justify-between">
                <span>{assignment.title} to {assignment.companyName}</span>
                <Badge className="bg-emerald-50 text-emerald-800"><CheckCircle2 className="h-3 w-3" />Sent</Badge>
              </div>
            )) : <p className="text-sm text-slate-600">No training has been sent yet in this browser session.</p>}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function TemplatePreview({ template, company }: { template: TrainingTemplate | TrainingTemplateDTO; company: Company | CompanyDTO }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">{template.category}</p>
          <h2 className="mt-1 text-xl font-semibold">{template.title}</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">{template.description}</p>
        </div>
        <Badge variant="secondary">v{template.version}</Badge>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-4">
        <SmallMetric label="Duration" value={`${template.estimatedDurationMin} min`} />
        <SmallMetric label="States" value={`${template.defaultStateCount}`} />
        <SmallMetric label="Avatar" value={`${template.avatarPolicy.activeTargetMin} min`} />
        <SmallMetric label="Budget" value={`$${template.avatarPolicy.safeBudgetUsd.toFixed(2)}`} />
      </div>
      <div className="mt-4 rounded-md bg-white p-3 text-sm">
        <div className="flex items-center gap-2 font-medium"><Building2 className="h-4 w-4 text-teal-700" />Customer target</div>
        <p className="mt-1 text-slate-600">{company.name} - {company.industry} - {company.learnerCount} learners</p>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {template.skillTags.map((item) => <Badge key={item} variant="outline">{item}</Badge>)}
      </div>
    </div>
  );
}

function SmallMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-white p-3 text-sm">
      <p className="text-slate-500">{label}</p>
      <p className="mt-1 font-semibold text-slate-950">{value}</p>
    </div>
  );
}

function readAssignments(): AssignedTraining[] {
  try {
    const value = window.localStorage.getItem(BROWSER_ASSIGNMENTS_STORAGE_KEY);
    if (!value) return [];
    const parsed = JSON.parse(value);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is AssignedTraining => (
      typeof item.id === "string" &&
      typeof item.templateId === "string" &&
      typeof item.title === "string" &&
      typeof item.companyId === "string" &&
      typeof item.companyName === "string" &&
      typeof item.assignedAt === "string" &&
      item.status === "sent_to_company"
    ));
  } catch {
    return [];
  }
}
