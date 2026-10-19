"use client";

import { useMemo, useRef, useState } from "react";
import {
  assessScenario,
  emptyDestination,
  emptyResource,
  formatNumber,
  validateScenario,
  type AssessmentResult,
  type Finding,
  type ValidationIssue,
} from "@/lib/assessment";
import {
  createExport,
  destinationFormFrom,
  emptyScenarioForm,
  formToScenario,
  parseImport,
  resourceFormFrom,
  scenarioToForm,
  type DestinationForm,
  type ResourceForm,
  type ScenarioForm,
} from "@/lib/labForm";
import { findStarterScenario, STARTER_SCENARIOS } from "@/lib/scenarios";

const SEVERITY_BADGE: Record<Finding["severity"], string> = {
  error: "badge badge-danger",
  warning: "badge badge-warn",
  info: "badge badge-info",
};

export default function ImpactAssessmentLabPage() {
  const [form, setScenarioForm] = useState<ScenarioForm>(() => emptyScenarioForm());
  const [result, setResult] = useState<AssessmentResult | null>(null);
  const [issues, setIssues] = useState<ValidationIssue[]>([]);
  const [dirty, setDirty] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const invalidPaths = useMemo(() => new Set(issues.map((i) => i.path)), [issues]);

  function patch(update: Partial<ScenarioForm>) {
    setScenarioForm((prev) => ({ ...prev, ...update }));
    setDirty(true);
    setNotice(null);
  }

  function updateResource(id: string, update: Partial<ResourceForm>) {
    setScenarioForm((prev) => ({
      ...prev,
      resources: prev.resources.map((r) => (r.id === id ? { ...r, ...update } : r)),
    }));
    setDirty(true);
  }

  function updateDestination(id: string, update: Partial<DestinationForm>) {
    setScenarioForm((prev) => ({
      ...prev,
      destinations: prev.destinations.map((d) =>
        d.id === id ? { ...d, ...update } : d,
      ),
    }));
    setDirty(true);
  }

  function addResource() {
    setScenarioForm((prev) => ({
      ...prev,
      resources: [...prev.resources, resourceFormFrom(emptyResource())],
    }));
    setDirty(true);
  }

  function removeResource(id: string) {
    setScenarioForm((prev) => ({
      ...prev,
      resources:
        prev.resources.length > 1
          ? prev.resources.filter((r) => r.id !== id)
          : prev.resources,
    }));
    setDirty(true);
  }

  function addDestination() {
    setScenarioForm((prev) => ({
      ...prev,
      destinations: [...prev.destinations, destinationFormFrom(emptyDestination())],
    }));
    setDirty(true);
  }

  function removeDestination(id: string) {
    setScenarioForm((prev) => ({
      ...prev,
      destinations:
        prev.destinations.length > 1
          ? prev.destinations.filter((d) => d.id !== id)
          : prev.destinations,
    }));
    setDirty(true);
  }

  function loadScenario(id: string) {
    if (id === "") {
      reset();
      return;
    }
    const starter = findStarterScenario(id);
    if (!starter) return;
    setScenarioForm(scenarioToForm(starter.input));
    setResult(null);
    setIssues([]);
    setDirty(true);
    setImportError(null);
    setNotice(`Loaded illustrative scenario: ${starter.name}`);
  }

  function reset() {
    setScenarioForm(emptyScenarioForm());
    setResult(null);
    setIssues([]);
    setDirty(false);
    setImportError(null);
    setNotice(null);
  }

  function run() {
    const scenario = formToScenario(form);
    const found = validateScenario(scenario);
    setIssues(found);
    if (found.length > 0) {
      setResult(null);
      return;
    }
    setResult(assessScenario(scenario));
    setDirty(false);
    setNotice(null);
  }

  function exportJson() {
    const data = createExport(formToScenario(form));
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "impactledger-lab-scenario.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function importJson(file: File) {
    setImportError(null);
    setNotice(null);
    const text = await file.text();
    const parsed = parseImport(text);
    if (!parsed.ok) {
      setImportError(parsed.error);
      return;
    }
    setScenarioForm(scenarioToForm(parsed.input));
    setResult(null);
    setIssues([]);
    setDirty(true);
    setNotice("Imported scenario. Run the assessment to see its results.");
  }

  const resourceNames = form.resources.map((r) => r.name).filter((n) => n.trim() !== "");

  return (
    <main className="container-x py-10">
      <header className="max-w-3xl">
        <p className="kpi-label">Interactive sandbox</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight">
          Impact Assessment Lab
        </h1>
        <p className="mt-3" style={{ color: "var(--text-muted)" }}>
          Enter a hypothetical relief-operation scenario and see whether its
          reported financial and physical records reconcile. Everything runs in
          your browser against the deterministic rules explained below.
        </p>
      </header>

      <div className="alert alert-info mt-5" role="note">
        <span aria-hidden="true">ⓘ</span>
        <p>
          This is a sandbox. The figures you enter are <strong>not</strong> read
          from or written to ImpactLedger&apos;s database, are not anchored on a
          blockchain, and never leave your browser. Starter scenarios are
          clearly marked <em>illustrative examples</em> — they are not real
          programme data.
        </p>
      </div>

      <div className="mt-8 grid gap-8 lg:grid-cols-2">
        {/* ------------------------------------------------------------ INPUTS */}
        <section aria-labelledby="inputs-heading" className="flex flex-col gap-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 id="inputs-heading" className="text-lg font-semibold">
              Your scenario
            </h2>
            <div className="flex flex-wrap gap-2">
              <button type="button" className="btn btn-secondary btn-sm" onClick={exportJson}>
                Export JSON
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => fileRef.current?.click()}
              >
                Import JSON
              </button>
              <button type="button" className="btn btn-ghost btn-sm" onClick={reset}>
                Reset
              </button>
            </div>
          </div>

          <div className="field">
            <label className="label" htmlFor="scenario-preset">
              Start from a scenario
            </label>
            <select
              id="scenario-preset"
              className="select"
              defaultValue=""
              onChange={(e) => loadScenario(e.target.value)}
            >
              <option value="">Blank scenario</option>
              {STARTER_SCENARIOS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} (illustrative)
                </option>
              ))}
            </select>
            <p className="help">
              Starter scenarios are hand-written illustrative examples, not
              production records.
            </p>
          </div>

          {notice && (
            <p className="help" role="status">
              {notice}
            </p>
          )}
          {importError && (
            <p className="alert alert-danger" role="alert">
              <span aria-hidden="true">⚠</span>
              {importError}
            </p>
          )}

          <div className="card card-pad grid gap-4 sm:grid-cols-2">
            <TextField
              id="scenario-name"
              label="Scenario / initiative name"
              value={form.scenarioName}
              onChange={(v) => patch({ scenarioName: v })}
              placeholder="e.g. Flood relief — phase 1"
              className="sm:col-span-2"
            />
            <TextField
              id="currency"
              label="Currency"
              value={form.currency}
              onChange={(v) => patch({ currency: v })}
              placeholder="INR"
              help="A single currency is assumed; no conversion is applied."
            />
          </div>

          <fieldset className="card card-pad">
            <legend className="label px-1">Financial records</legend>
            <p className="help mb-3">
              Leave a field blank if the figure is unknown — blank means
              &ldquo;not provided&rdquo;, not zero.
            </p>
            <div className="grid gap-4 sm:grid-cols-3">
              <NumberField
                id="contributions"
                label="Contributions received"
                value={form.contributionsReceived}
                onChange={(v) => patch({ contributionsReceived: v })}
                invalid={invalidPaths.has("contributionsReceived")}
              />
              <NumberField
                id="allocated"
                label="Amount allocated"
                value={form.amountAllocated}
                onChange={(v) => patch({ amountAllocated: v })}
                invalid={invalidPaths.has("amountAllocated")}
              />
              <NumberField
                id="expenditure"
                label="Expenditure recorded"
                value={form.expenditureRecorded}
                onChange={(v) => patch({ expenditureRecorded: v })}
                invalid={invalidPaths.has("expenditureRecorded")}
              />
            </div>
          </fieldset>

          <div className="card card-pad">
            <div className="flex items-center justify-between gap-3">
              <h3 className="font-semibold">Resource batches</h3>
              <button type="button" className="btn btn-ghost btn-sm" onClick={addResource}>
                + Add batch
              </button>
            </div>
            <p className="help mb-4">
              Each batch tracks one resource. Expected remaining = opening
              quantity + receipts + transfers in − distributions − transfers out
              − losses − disposals, using only the fields you fill in.
            </p>
            <div className="flex flex-col gap-4">
              {form.resources.map((r, i) => (
                <ResourceRow
                  key={r.id}
                  index={i}
                  row={r}
                  invalidPaths={invalidPaths}
                  canRemove={form.resources.length > 1}
                  onChange={(update) => updateResource(r.id, update)}
                  onRemove={() => removeResource(r.id)}
                />
              ))}
            </div>
          </div>

          <div className="card card-pad">
            <div className="flex items-center justify-between gap-3">
              <h3 className="font-semibold">Distribution destinations</h3>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={addDestination}
              >
                + Add destination
              </button>
            </div>
            <p className="help mb-4">
              Where distributed units went. Type the resource name exactly as
              entered above so the breakdown can be matched.
            </p>
            <datalist id="resource-name-options">
              {resourceNames.map((name) => (
                <option key={name} value={name} />
              ))}
            </datalist>
            <div className="flex flex-col gap-4">
              {form.destinations.map((d, i) => (
                <DestinationRow
                  key={d.id}
                  index={i}
                  row={d}
                  invalidPaths={invalidPaths}
                  canRemove={form.destinations.length > 1}
                  onChange={(update) => updateDestination(d.id, update)}
                  onRemove={() => removeDestination(d.id)}
                />
              ))}
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn btn-primary" onClick={run}>
              Run assessment
            </button>
            <button type="button" className="btn btn-secondary" onClick={reset}>
              Reset sandbox
            </button>
          </div>
        </section>

        {/* ----------------------------------------------------------- RESULTS */}
        <section aria-labelledby="results-heading" className="flex flex-col gap-5">
          <h2 id="results-heading" className="text-lg font-semibold">
            Assessment
          </h2>

          <div aria-live="polite" className="flex flex-col gap-5">
            {issues.length > 0 && (
              <div className="alert alert-danger" role="alert">
                <span aria-hidden="true">⚠</span>
                <div>
                  <p className="font-medium">Fix these inputs before running.</p>
                  <ul className="mt-2 list-disc pl-5 text-sm">
                    {issues.map((issue, idx) => (
                      <li key={`${issue.path}-${idx}`}>
                        <span className="mono text-xs">{issue.path}</span>{" "}
                        {issue.message}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {!result && issues.length === 0 && (
              <div className="card card-pad">
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                  Enter your figures and choose <strong>Run assessment</strong>.
                  The result appears here, with the inputs behind every finding.
                </p>
              </div>
            )}

            {result && dirty && (
              <div className="alert alert-warn" role="status">
                <span aria-hidden="true">✎</span>
                <p>Inputs have changed since this assessment was run.</p>
              </div>
            )}

            {result && <ResultsView result={result} currency={form.currency} />}
          </div>
        </section>
      </div>

      <input
        ref={fileRef}
        type="file"
        accept="application/json,.json"
        className="sr-only"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void importJson(file);
          e.target.value = "";
        }}
      />
    </main>
  );
}

// ---------------------------------------------------------------------------
// Field primitives
// ---------------------------------------------------------------------------

function TextField({
  id,
  label,
  value,
  onChange,
  placeholder,
  help,
  className,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  help?: string;
  className?: string;
}) {
  return (
    <div className={`field ${className ?? ""}`}>
      <label className="label" htmlFor={id}>
        {label}
      </label>
      <input
        id={id}
        className="input"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
      {help && <span className="help">{help}</span>}
    </div>
  );
}

function NumberField({
  id,
  label,
  value,
  onChange,
  invalid,
  help,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  invalid?: boolean;
  help?: string;
}) {
  return (
    <div className="field">
      <label className="label" htmlFor={id}>
        {label}
      </label>
      <input
        id={id}
        className="input"
        type="text"
        inputMode="decimal"
        autoComplete="off"
        value={value}
        aria-invalid={invalid ? "true" : undefined}
        onChange={(e) => onChange(e.target.value)}
      />
      {help && <span className="help">{help}</span>}
    </div>
  );
}

function ResourceRow({
  index,
  row,
  invalidPaths,
  canRemove,
  onChange,
  onRemove,
}: {
  index: number;
  row: ResourceForm;
  invalidPaths: Set<string>;
  canRemove: boolean;
  onChange: (update: Partial<ResourceForm>) => void;
  onRemove: () => void;
}) {
  const base = `resources.${index}`;
  const quantityFields: { key: keyof ResourceForm; label: string }[] = [
    { key: "openingQuantity", label: "Opening quantity" },
    { key: "received", label: "Received" },
    { key: "transfersIn", label: "Transfers in" },
    { key: "distributed", label: "Distributed" },
    { key: "transfersOut", label: "Transfers out" },
    { key: "losses", label: "Losses" },
    { key: "disposed", label: "Disposed" },
    { key: "observedRemaining", label: "Physical count" },
  ];

  return (
    <fieldset className="panel">
      <legend className="label px-1">Batch {index + 1}</legend>
      <div className="grid gap-3 sm:grid-cols-2">
        <TextField
          id={`${base}-name`}
          label="Resource name"
          value={row.name}
          onChange={(v) => onChange({ name: v })}
          placeholder="e.g. Blankets"
        />
        <TextField
          id={`${base}-unit`}
          label="Unit"
          value={row.unit}
          onChange={(v) => onChange({ unit: v })}
          placeholder="unit / kit / litre"
        />
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {quantityFields.map((f) => (
          <NumberField
            key={String(f.key)}
            id={`${base}-${String(f.key)}`}
            label={f.label}
            value={row[f.key] as string}
            invalid={invalidPaths.has(`${base}.${String(f.key)}`)}
            onChange={(v) => onChange({ [f.key]: v } as Partial<ResourceForm>)}
          />
        ))}
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <TextField
          id={`${base}-funding`}
          label="Funding reference"
          value={row.fundingReference}
          onChange={(v) => onChange({ fundingReference: v })}
          placeholder="e.g. PO-2026-014"
          help="The purchase, commitment or allocation that funded this batch."
        />
        <TextField
          id={`${base}-evidence`}
          label="Evidence reference"
          value={row.evidenceReference}
          onChange={(v) => onChange({ evidenceReference: v })}
          placeholder="e.g. DN-1145"
          help="A document or receipt reference, if one exists."
        />
      </div>

      {canRemove && (
        <div className="mt-3 flex justify-end">
          <button type="button" className="btn btn-danger btn-sm" onClick={onRemove}>
            Remove batch
          </button>
        </div>
      )}
    </fieldset>
  );
}

function DestinationRow({
  index,
  row,
  invalidPaths,
  canRemove,
  onChange,
  onRemove,
}: {
  index: number;
  row: DestinationForm;
  invalidPaths: Set<string>;
  canRemove: boolean;
  onChange: (update: Partial<DestinationForm>) => void;
  onRemove: () => void;
}) {
  const base = `destinations.${index}`;
  return (
    <fieldset className="panel">
      <legend className="label px-1">Destination {index + 1}</legend>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="field">
          <label className="label" htmlFor={`${base}-resource`}>
            Resource name
          </label>
          <input
            id={`${base}-resource`}
            className="input"
            list="resource-name-options"
            value={row.resourceName}
            onChange={(e) => onChange({ resourceName: e.target.value })}
            placeholder="Matches a batch above"
          />
        </div>
        <TextField
          id={`${base}-destination`}
          label="Destination"
          value={row.destination}
          onChange={(v) => onChange({ destination: v })}
          placeholder="e.g. Khairatabad relief camp"
        />
        <NumberField
          id={`${base}-quantity`}
          label="Quantity"
          value={row.quantity}
          invalid={invalidPaths.has(`${base}.quantity`)}
          onChange={(v) => onChange({ quantity: v })}
        />
        <div className="field">
          <label className="label" htmlFor={`${base}-date`}>
            Date
          </label>
          <input
            id={`${base}-date`}
            className="input"
            type="date"
            value={row.date}
            onChange={(e) => onChange({ date: e.target.value })}
          />
        </div>
        <TextField
          id={`${base}-evidence`}
          label="Evidence reference"
          value={row.evidenceReference}
          onChange={(v) => onChange({ evidenceReference: v })}
          placeholder="e.g. DS-01"
          className="sm:col-span-2"
        />
      </div>
      {canRemove && (
        <div className="mt-3 flex justify-end">
          <button type="button" className="btn btn-danger btn-sm" onClick={onRemove}>
            Remove destination
          </button>
        </div>
      )}
    </fieldset>
  );
}

// ---------------------------------------------------------------------------
// Results
// ---------------------------------------------------------------------------

function money(value: number | null, currency: string): string {
  if (value === null) return "—";
  const prefix = currency.trim() === "" ? "" : `${currency.trim()} `;
  return `${prefix}${formatNumber(value)}`;
}

function ResultsView({ result, currency }: { result: AssessmentResult; currency: string }) {
  const statusClass =
    result.status === "consistent"
      ? "alert alert-ok"
      : result.status === "needs_review"
        ? "alert alert-warn"
        : "alert alert-info";

  return (
    <div className="flex flex-col gap-5 animate-in">
      <div className={statusClass} role="status">
        <span aria-hidden="true">
          {result.status === "consistent" ? "✓" : result.status === "needs_review" ? "!" : "ⓘ"}
        </span>
        <div>
          <p className="font-semibold">{result.statusLabel}</p>
          <p className="text-sm">{result.statusDetail}</p>
        </div>
      </div>

      <section aria-labelledby="financial-heading" className="card card-pad">
        <h3 id="financial-heading" className="text-base font-semibold">
          Financial reconciliation
        </h3>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <Metric label="Contributions received" value={money(result.financial.contributionsReceived, currency)} />
          <Metric label="Amount allocated" value={money(result.financial.amountAllocated, currency)} />
          <Metric label="Expenditure recorded" value={money(result.financial.expenditureRecorded, currency)} />
          <Metric
            label="Unallocated"
            value={money(result.financial.unallocated, currency)}
            hint="Contributions minus allocations."
          />
          <Metric
            label="Allocation %"
            value={
              result.financial.allocationPct === null
                ? "—"
                : `${formatNumber(result.financial.allocationPct)}%`
            }
            hint="Share of contributions allocated."
          />
          <Metric
            label="Unspent of allocation"
            value={money(result.financial.unspentOfAllocation, currency)}
            hint="Allocation minus expenditure."
          />
        </div>
      </section>

      <section aria-labelledby="evidence-heading" className="card card-pad">
        <h3 id="evidence-heading" className="text-base font-semibold">
          Evidence coverage
        </h3>
        <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
          {result.evidence.totalRecords === 0
            ? "No records to cover."
            : `${result.evidence.recordsWithReference} of ${result.evidence.totalRecords} records carry a reference${
                result.evidence.pct === null ? "" : ` (${result.evidence.pct}%)`
              }.`}
        </p>
        {result.evidence.totalRecords > 0 && (
          <div className="progress mt-3" aria-hidden="true">
            <span style={{ width: `${result.evidence.pct ?? 0}%` }} />
          </div>
        )}
      </section>

      {result.resources.length > 0 && (
        <section aria-labelledby="resource-heading" className="card card-pad">
          <h3 id="resource-heading" className="text-base font-semibold">
            Resource reconciliation
          </h3>
          <div className="mt-3 overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Batch</th>
                  <th scope="col" className="num">
                    Expected remaining
                  </th>
                  <th scope="col" className="num">
                    Physical count
                  </th>
                  <th scope="col" className="num">
                    Variance
                  </th>
                  <th scope="col">Missing terms</th>
                </tr>
              </thead>
              <tbody>
                {result.resources.map((r) => (
                  <tr key={r.id}>
                    <td>
                      {r.name || "Unnamed"}
                      <span className="help block">{r.unit}</span>
                    </td>
                    <td className="num">{r.expectedRemaining === null ? "—" : formatNumber(r.expectedRemaining)}</td>
                    <td className="num">{r.observedRemaining === null ? "—" : formatNumber(r.observedRemaining)}</td>
                    <td className="num">
                      {r.variance === null ? (
                        "—"
                      ) : r.variance === 0 ? (
                        <span className="badge badge-ok">0</span>
                      ) : (
                        <span className="badge badge-warn">{formatNumber(r.variance)}</span>
                      )}
                    </td>
                    <td className="help">{r.missingTerms.join(", ") || "none"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {(result.destinations.byDestination.length > 0 ||
        result.destinations.unmatchedResources.length > 0) && (
        <section aria-labelledby="destination-heading" className="card card-pad">
          <h3 id="destination-heading" className="text-base font-semibold">
            Distribution breakdown
          </h3>
          {result.destinations.byDestination.length > 0 && (
            <div className="mt-3 overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Destination</th>
                    <th scope="col" className="num">
                      Quantity
                    </th>
                    <th scope="col" className="num">
                      Records
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {result.destinations.byDestination.map((d) => (
                    <tr key={d.destination}>
                      <td>{d.destination}</td>
                      <td className="num">{formatNumber(d.quantity)}</td>
                      <td className="num">{d.records}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {result.destinations.unmatchedResources.length > 0 && (
            <p className="help mt-3">
              Resources referenced only in destinations:{" "}
              {result.destinations.unmatchedResources.join(", ")}
            </p>
          )}
        </section>
      )}

      <section aria-labelledby="findings-heading" className="card card-pad">
        <h3 id="findings-heading" className="text-base font-semibold">
          Findings
        </h3>
        {result.findings.length === 0 ? (
          <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
            No findings. The figures you entered are internally consistent.
          </p>
        ) : (
          <ul className="mt-3 flex flex-col gap-3">
            {result.findings.map((f) => (
              <li key={f.id} className="panel">
                <div className="flex items-start justify-between gap-3">
                  <span className={SEVERITY_BADGE[f.severity]}>{f.severity}</span>
                  <span className="help mono">{f.category}</span>
                </div>
                <p className="mt-2 font-medium">{f.title}</p>
                <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
                  {f.detail}
                </p>
                {f.inputs.length > 0 && (
                  <p className="mt-2 help">
                    <span className="font-medium">Inputs:</span> {f.inputs.join("; ")}
                  </p>
                )}
                <p className="mt-1 text-sm">
                  <span className="font-medium">Recommended:</span>{" "}
                  {f.recommendation}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="assumptions-heading" className="card card-pad">
        <h3 id="assumptions-heading" className="text-base font-semibold">
          What this assessment assumed
        </h3>
        <ul className="prose-lite mt-2 list-disc pl-5 text-sm">
          {result.assumptions.map((a) => (
            <li key={a}>{a}</li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="limitations-heading" className="card card-pad">
        <h3 id="limitations-heading" className="text-base font-semibold">
          What this assessment cannot tell you
        </h3>
        <ul className="prose-lite mt-2 list-disc pl-5 text-sm">
          {result.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function Metric({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="kpi">
      <p className="kpi-label">{label}</p>
      <p className="kpi-value">{value}</p>
      {hint && <p className="kpi-hint">{hint}</p>}
    </div>
  );
}
