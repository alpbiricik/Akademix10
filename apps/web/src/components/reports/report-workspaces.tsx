"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { AlertTriangle, BarChart3, Calendar, RefreshCw, ShieldCheck } from "lucide-react";
import { ApiError } from "@/lib/api/errors";
import { getCompanyAggregateReport, getCompanyTrainings } from "@/lib/adapters/companyAdapter";
import { getLearnerSessionScoringResults, getLearnerStructuredReport } from "@/lib/adapters/learnerAdapter";
import { getPlatformAggregateReport, getPlatformCompanies, getPlatformTemplates } from "@/lib/adapters/platformAdapter";
import type {
  CompanyAggregateReportDTO,
  LearnerSessionReportDTO,
  PlatformAggregateReportDTO,
  ReportCoverageDTO,
  StructuredScoringResultDTO,
} from "@/lib/contracts/dtos";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";

type LoadState<T> =
  | { status: "loading"; data: T | null; message?: string }
  | { status: "success"; data: T; message?: string }
  | { status: "error"; data: T | null; message: string };

interface AggregateFilters {
  templateId?: string;
  companyId?: string;
  dateFrom?: string;
  dateTo?: string;
}

interface TemplateOption {
  id: string;
  title: string;
}

interface CompanyOption {
  id: string;
  name: string;
}

export function LearnerReportWorkspace({ sessionId }: { sessionId: string }) {
  const requestIdRef = useRef(0);
  const [state, setState] = useState<LoadState<{ report: LearnerSessionReportDTO | null; scoringResults: StructuredScoringResultDTO[] }>>({
    status: "loading",
    data: null,
  });

  const load = useCallback(async () => {
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setState((current) => ({ status: "loading", data: current.data }));
    try {
      const [report, scoringResults] = await Promise.all([
        getLearnerStructuredReport(sessionId),
        getLearnerSessionScoringResults(sessionId),
      ]);
      if (requestId !== requestIdRef.current) return;
      setState({ status: "success", data: { report, scoringResults } });
    } catch (error) {
      if (requestId !== requestIdRef.current) return;
      setState((current) => ({ status: "error", data: current.data, message: getFriendlyErrorMessage(error) }));
    }
  }, [sessionId]);

  useEffect(() => {
    void load();
    return () => {
      requestIdRef.current += 1;
    };
  }, [load]);

  return (
    <ReportSurface
      eyebrow="Learner report"
      title="Session scoring report"
      description="Your scored practice states, skill impact, and next actions from the current report snapshot."
      state={state}
      onRetry={load}
    >
      {state.status === "success" ? <LearnerReportContent report={state.data.report} scoringResults={state.data.scoringResults} /> : null}
    </ReportSurface>
  );
}

export function CompanyReportsWorkspace() {
  const requestIdRef = useRef(0);
  const [filters, setFilters] = useState<AggregateFilters>({});
  const [draftFilters, setDraftFilters] = useState<AggregateFilters>({});
  const [templates, setTemplates] = useState<TemplateOption[]>([]);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [state, setState] = useState<LoadState<CompanyAggregateReportDTO | null>>({ status: "loading", data: null });

  const load = useCallback(async (nextFilters: AggregateFilters) => {
    const validation = validateDateRange(nextFilters);
    if (validation) {
      setValidationMessage(validation);
      return;
    }
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setValidationMessage(null);
    setState((current) => ({ status: "loading", data: current.data }));
    try {
      const [report, trainingTemplates] = await Promise.all([getCompanyAggregateReport(cleanFilters(nextFilters)), getCompanyTrainings()]);
      if (requestId !== requestIdRef.current) return;
      setTemplates(trainingTemplates.map(toTemplateOption));
      setState({ status: "success", data: report });
    } catch (error) {
      if (requestId !== requestIdRef.current) return;
      setState((current) => ({ status: "error", data: current.data, message: getFriendlyErrorMessage(error) }));
    }
  }, []);

  useEffect(() => {
    void load({});
    return () => {
      requestIdRef.current += 1;
    };
  }, [load]);

  function applyFilters() {
    const next = cleanFilters(draftFilters);
    setFilters(next);
    void load(next);
  }

  return (
    <ReportSurface
      eyebrow="Company reports"
      title="Company aggregate training performance"
      description="Company-scoped scoring coverage, aggregate scores, and development priorities."
      state={state}
      onRetry={() => load(filters)}
      controls={<AggregateFiltersPanel filters={draftFilters} templates={templates} validationMessage={validationMessage} onChange={setDraftFilters} onApply={applyFilters} />}
    >
      {state.status === "success" ? <CompanyReportContent report={state.data} /> : null}
    </ReportSurface>
  );
}

export function PlatformReportsWorkspace() {
  const requestIdRef = useRef(0);
  const [filters, setFilters] = useState<AggregateFilters>({});
  const [draftFilters, setDraftFilters] = useState<AggregateFilters>({});
  const [templates, setTemplates] = useState<TemplateOption[]>([]);
  const [companies, setCompanies] = useState<CompanyOption[]>([]);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [state, setState] = useState<LoadState<PlatformAggregateReportDTO | null>>({ status: "loading", data: null });

  const load = useCallback(async (nextFilters: AggregateFilters) => {
    const validation = validateDateRange(nextFilters);
    if (validation) {
      setValidationMessage(validation);
      return;
    }
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setValidationMessage(null);
    setState((current) => ({ status: "loading", data: current.data }));
    try {
      const [report, trainingTemplates, companyOptions] = await Promise.all([
        getPlatformAggregateReport(cleanFilters(nextFilters)),
        getPlatformTemplates(),
        getPlatformCompanies(),
      ]);
      if (requestId !== requestIdRef.current) return;
      setTemplates(trainingTemplates.map(toTemplateOption));
      setCompanies(companyOptions.map(toCompanyOption));
      setState({ status: "success", data: report });
    } catch (error) {
      if (requestId !== requestIdRef.current) return;
      setState((current) => ({ status: "error", data: current.data, message: getFriendlyErrorMessage(error) }));
    }
  }, []);

  useEffect(() => {
    void load({});
    return () => {
      requestIdRef.current += 1;
    };
  }, [load]);

  function applyFilters() {
    const next = cleanFilters(draftFilters);
    setFilters(next);
    void load(next);
  }

  return (
    <ReportSurface
      eyebrow="Platform reports"
      title="Platform aggregate performance"
      description="Platform-wide scoring coverage, sample health, and skill trends across available report snapshots."
      state={state}
      onRetry={() => load(filters)}
      controls={<AggregateFiltersPanel filters={draftFilters} templates={templates} companies={companies} validationMessage={validationMessage} onChange={setDraftFilters} onApply={applyFilters} />}
    >
      {state.status === "success" ? <PlatformReportContent report={state.data} /> : null}
    </ReportSurface>
  );
}

function LearnerReportContent({ report, scoringResults }: { report: LearnerSessionReportDTO | null; scoringResults: StructuredScoringResultDTO[] }) {
  if (!report) return <EmptyState title="No structured report yet" description="Complete and submit a scored practice state to create a session report." />;

  return (
    <div className="space-y-6">
      <StatusNotices coverage={report.coverage} />
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Overall score" value={formatScore(report.overallScore)} />
        <MetricCard label="Scoring coverage" value={formatPercent(report.coverage.scoringCoverage)} />
        <MetricCard label="Evaluated states" value={`${report.evaluatedStateCount}/${report.coverage.expectedStateCount}`} />
        <MetricCard label="Generated" value={formatDate(report.generatedAt)} />
      </div>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-6">
          <BarListCard title="Dimension summary" items={report.dimensionSummaries} getLabel={(item) => item.name} getValue={(item) => item.averageScore} />
          <BarListCard title="Skill impact" items={report.skillSummaries} getLabel={(item) => item.skill} getValue={(item) => item.averageScore} getDetail={(item) => `Avg impact +${item.averageDelta}`} />
          <ScoringDetailCard scoringResults={scoringResults} />
        </div>
        <div className="space-y-6">
          <ListCard title="Strengths" items={report.strengths} />
          <ListCard title="Improvement areas" items={report.improvementAreas} />
          <ListCard title="Recommended next actions" items={report.recommendedNextActions.map(formatAction)} />
          <GuardrailCard total={report.guardrailSummary.totalFlags} codes={report.guardrailSummary.codes} />
          <VersionCard schemaVersion={report.schemaVersion} sourceVersions={report.sourceScoringSchemaVersions} generatedAt={report.generatedAt} />
        </div>
      </div>
    </div>
  );
}

function CompanyReportContent({ report }: { report: CompanyAggregateReportDTO | null }) {
  if (!report || report.scoredSessionCount === 0) return <EmptyState title="No scored company sessions yet" description="Aggregate reports appear after learners submit scored practice responses." />;
  return (
    <div className="space-y-6">
      <StatusNotices coverage={report.coverage} />
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Average score" value={formatScore(report.averageOverallScore)} />
        <MetricCard label="Scored sessions" value={`${report.scoredSessionCount}/${report.coverage.totalSessionCount}`} />
        <MetricCard label="Coverage" value={formatPercent(report.coverage.scoringCoverage)} />
        <MetricCard label="Generated" value={formatDate(report.generatedAt)} />
      </div>
      <div className="grid gap-6 xl:grid-cols-2">
        <BarListCard title="Dimension averages" items={report.dimensionAverages} getLabel={(item) => item.name} getValue={(item) => item.averageScore} />
        <BarListCard title="Skill averages" items={report.skillAverages} getLabel={(item) => item.skill} getValue={(item) => item.averageScore} getDetail={(item) => `Avg impact +${item.averageDelta}`} />
        <BarListCard title="Strongest dimensions" items={report.strongestDimensions} getLabel={(item) => item.name} getValue={(item) => item.averageScore} />
        <BarListCard title="Development priorities" items={report.developmentPriorityDimensions} getLabel={(item) => item.name} getValue={(item) => item.averageScore} />
      </div>
      <GuardrailCard total={report.guardrailSummary.totalFlags} codes={report.guardrailSummary.codes} />
    </div>
  );
}

function PlatformReportContent({ report }: { report: PlatformAggregateReportDTO | null }) {
  if (!report || report.reportCoverage.scoredSessionCount === 0) return <EmptyState title="No platform score samples yet" description="Platform aggregate reporting will populate as scored sessions arrive." />;
  return (
    <div className="space-y-6">
      <StatusNotices coverage={report.reportCoverage} />
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Average score" value={formatScore(report.aggregateScoreSummary.averageOverallScore)} />
        <MetricCard label="Companies" value={`${report.companyCount}`} />
        <MetricCard label="Templates" value={`${report.trainingTemplateCount}`} />
        <MetricCard label="Scored sessions" value={`${report.reportCoverage.scoredSessionCount}/${report.reportCoverage.totalSessionCount}`} />
      </div>
      <div className="grid gap-6 xl:grid-cols-2">
        <BarListCard title="Dimension trends" items={report.dimensionTrends} getLabel={(item) => item.name} getValue={(item) => item.averageScore} />
        <BarListCard title="Skill trends" items={report.skillTrends} getLabel={(item) => item.skill} getValue={(item) => item.averageScore} getDetail={(item) => `Avg impact +${item.averageDelta}`} />
      </div>
      <GuardrailCard total={0} codes={[]} />
    </div>
  );
}

function ReportSurface<T>({ eyebrow, title, description, state, controls, children, onRetry }: { eyebrow: string; title: string; description: string; state: LoadState<T>; controls?: ReactNode; children: ReactNode; onRetry: () => void }) {
  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">{eyebrow}</p>
            <h1 className="mt-2 text-3xl font-semibold">{title}</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{description}</p>
          </div>
          <Button type="button" variant="outline" onClick={onRetry} aria-label="Retry report request">
            <RefreshCw className="h-4 w-4" />
            Retry
          </Button>
        </div>
      </section>
      {controls}
      {state.status === "loading" ? <LoadingState hasData={Boolean(state.data)} /> : null}
      {state.status === "error" ? <ErrorState message={state.message} onRetry={onRetry} /> : null}
      {children}
    </div>
  );
}

function AggregateFiltersPanel({ filters, templates, companies, validationMessage, onChange, onApply }: { filters: AggregateFilters; templates: TemplateOption[]; companies?: CompanyOption[]; validationMessage: string | null; onChange: (filters: AggregateFilters) => void; onApply: () => void }) {
  return (
    <Card className="rounded-lg border-slate-200">
      <CardHeader><CardTitle className="flex items-center gap-2"><Calendar className="h-5 w-5 text-teal-700" />Filters</CardTitle></CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-4">
        <Field label="Training">
          <select className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm" value={filters.templateId ?? ""} onChange={(event) => onChange({ ...filters, templateId: event.target.value || undefined })}>
            <option value="">All trainings</option>
            {templates.map((template) => <option key={template.id} value={template.id}>{template.title}</option>)}
          </select>
        </Field>
        {companies ? (
          <Field label="Company">
            <select className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm" value={filters.companyId ?? ""} onChange={(event) => onChange({ ...filters, companyId: event.target.value || undefined })}>
              <option value="">All companies</option>
              {companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}
            </select>
          </Field>
        ) : null}
        <Field label="From">
          <Input type="date" value={filters.dateFrom ?? ""} onChange={(event) => onChange({ ...filters, dateFrom: event.target.value || undefined })} />
        </Field>
        <Field label="To">
          <Input type="date" value={filters.dateTo ?? ""} onChange={(event) => onChange({ ...filters, dateTo: event.target.value || undefined })} />
        </Field>
        <div className="flex items-end">
          <Button type="button" onClick={onApply}>Apply filters</Button>
        </div>
        {validationMessage ? <p className="md:col-span-4 text-sm text-red-700">{validationMessage}</p> : null}
      </CardContent>
    </Card>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return <div className="grid gap-2"><Label>{label}</Label>{children}</div>;
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <Card className="rounded-lg border-slate-200">
      <CardContent className="p-5">
        <p className="text-sm text-slate-500">{label}</p>
        <p className="mt-1 text-2xl font-semibold text-slate-950">{value}</p>
      </CardContent>
    </Card>
  );
}

function BarListCard<T>({ title, items, getLabel, getValue, getDetail }: { title: string; items: T[]; getLabel: (item: T) => string; getValue: (item: T) => number | null; getDetail?: (item: T) => string }) {
  return (
    <Card className="rounded-lg border-slate-200">
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        {items.length ? items.map((item) => {
          const value = getValue(item);
          return (
            <div key={getLabel(item)} className="space-y-2">
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="font-medium text-slate-700">{getLabel(item)}</span>
                <span className="text-slate-500">{value === null ? "Not scored" : `${value}/100`}</span>
              </div>
              <Progress value={value ?? 0} />
              {getDetail ? <p className="text-xs text-slate-500">{getDetail(item)}</p> : null}
            </div>
          );
        }) : <p className="text-sm text-slate-500">No score samples yet.</p>}
      </CardContent>
    </Card>
  );
}

function ScoringDetailCard({ scoringResults }: { scoringResults: StructuredScoringResultDTO[] }) {
  return (
    <Card className="rounded-lg border-slate-200">
      <CardHeader><CardTitle>Scored state details</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        {scoringResults.length ? scoringResults.map((result) => (
          <div key={`${result.sessionId}-${result.stateId}`} className="rounded-md border border-slate-200 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-medium text-slate-950">{result.stateId}</p>
              <Badge className="bg-teal-50 text-teal-800">Overall {result.overallScore}/100</Badge>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-600">{result.conciseLearnerFeedback}</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {result.dimensionScores.map((dimension) => (
                <div key={dimension.dimensionId} className="rounded-md bg-slate-50 p-3 text-sm">
                  <div className="flex justify-between gap-3">
                    <span className="text-slate-600">{dimension.name}</span>
                    <span className="font-semibold text-slate-950">{dimension.score}/100</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )) : <p className="text-sm text-slate-500">No scored states are available for this session yet.</p>}
      </CardContent>
    </Card>
  );
}

function ListCard({ title, items }: { title: string; items: string[] }) {
  return (
    <Card className="rounded-lg border-slate-200">
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent className="space-y-2">
        {items.length ? items.map((item) => <p key={item} className="rounded-md bg-slate-50 p-3 text-sm text-slate-700">{item}</p>) : <p className="text-sm text-slate-500">No items yet.</p>}
      </CardContent>
    </Card>
  );
}

function StatusNotices({ coverage }: { coverage: ReportCoverageDTO }) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {coverage.isPartial ? <Notice tone="amber" text={`Partial report: ${coverage.missingStateIds.length} states do not have scores yet.`} /> : <Notice tone="green" text="Report coverage is complete for the available scored snapshot." />}
      {coverage.insufficientSample ? <Notice tone="amber" text="Insufficient sample: use this report as directional until more sessions are scored." /> : <Notice tone="green" text="Sample size is sufficient for this report contract." />}
    </div>
  );
}

function Notice({ text, tone }: { text: string; tone: "amber" | "green" }) {
  const className = tone === "amber" ? "border-amber-200 bg-amber-50 text-amber-950" : "border-emerald-200 bg-emerald-50 text-emerald-950";
  return <div className={`rounded-lg border p-4 text-sm ${className}`}><AlertTriangle className="mr-2 inline h-4 w-4" />{text}</div>;
}

function GuardrailCard({ total, codes }: { total: number; codes: string[] }) {
  return (
    <Card className="rounded-lg border-slate-200">
      <CardHeader><CardTitle className="flex items-center gap-2"><ShieldCheck className="h-5 w-5 text-teal-700" />Guardrail summary</CardTitle></CardHeader>
      <CardContent className="text-sm text-slate-600">
        {total === 0 ? "No guardrail flags in this report snapshot." : `${total} flags: ${codes.join(", ")}`}
      </CardContent>
    </Card>
  );
}

function VersionCard({ schemaVersion, sourceVersions, generatedAt }: { schemaVersion: string; sourceVersions: string[]; generatedAt: string }) {
  return (
    <Card className="rounded-lg border-slate-200">
      <CardHeader><CardTitle className="flex items-center gap-2"><BarChart3 className="h-5 w-5 text-teal-700" />Report metadata</CardTitle></CardHeader>
      <CardContent className="space-y-2 text-sm text-slate-600">
        <p>Report schema {schemaVersion}</p>
        <p>Scoring schema {sourceVersions.join(", ") || "none yet"}</p>
        <p>Generated {formatDate(generatedAt)}</p>
      </CardContent>
    </Card>
  );
}

function LoadingState({ hasData }: { hasData: boolean }) {
  return <div aria-live="polite" className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600">{hasData ? "Refreshing report..." : "Loading report..."}</div>;
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p>{message}</p>
        <Button type="button" variant="outline" onClick={onRetry}>Retry</Button>
      </div>
    </div>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <Card className="rounded-lg border-slate-200">
      <CardContent className="p-6">
        <p className="font-semibold text-slate-950">{title}</p>
        <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
      </CardContent>
    </Card>
  );
}

function getFriendlyErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    const code = extractErrorCode(error.payload);
    if (error.status === 403) return "You do not have access to this report area.";
    if (error.status === 404 || code === "report_not_found") return "This report is not available for your account.";
    if (error.status === 422 || code === "invalid_report_filter") return "Check the report filters and try again.";
    if (error.status === 0) return "The report service could not be reached.";
  }
  return "The report could not be loaded. Try again in a moment.";
}

function extractErrorCode(payload: unknown) {
  if (!isRecord(payload)) return null;
  const detail = payload.detail;
  if (!isRecord(detail)) return null;
  const code = detail.code;
  return typeof code === "string" ? code : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object");
}

function toTemplateOption(value: { id: string; title: string }): TemplateOption {
  return { id: value.id, title: value.title };
}

function toCompanyOption(value: { id: string; name: string }): CompanyOption {
  return { id: value.id, name: value.name };
}

function validateDateRange(filters: AggregateFilters) {
  if (!filters.dateFrom || !filters.dateTo) return null;
  return filters.dateFrom > filters.dateTo ? "From date must be before or equal to To date." : null;
}

function cleanFilters(filters: AggregateFilters): AggregateFilters {
  return {
    templateId: filters.templateId || undefined,
    companyId: filters.companyId || undefined,
    dateFrom: filters.dateFrom || undefined,
    dateTo: filters.dateTo || undefined,
  };
}

function formatScore(value: number | null | undefined) {
  return value === null || value === undefined ? "Not scored" : `${value}/100`;
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return "0%";
  return `${Math.round(value * 100)}%`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
}

function formatAction(value: string) {
  return value.replaceAll("_", " ");
}
