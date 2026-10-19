import {
  emptyDestination,
  emptyResource,
  isFiniteNumber,
  type DestinationInput,
  type ResourceInput,
  type ScenarioInput,
} from "./assessment.ts";

/**
 * Form <-> scenario conversion plus import/export for the Assessment Lab.
 *
 * Numeric form fields are kept as strings so a visitor can type "1." or ""
 * without the input fighting them. Conversion to numbers happens only when an
 * assessment is run or a scenario is exported. Everything stays in the browser;
 * nothing is uploaded and nothing reaches ImpactLedger's operational tables.
 */

export type NumField = string;

export interface ResourceForm {
  id: string;
  name: string;
  unit: string;
  openingQuantity: NumField;
  received: NumField;
  transfersIn: NumField;
  distributed: NumField;
  transfersOut: NumField;
  losses: NumField;
  disposed: NumField;
  observedRemaining: NumField;
  fundingReference: string;
  evidenceReference: string;
}

export interface DestinationForm {
  id: string;
  resourceName: string;
  destination: string;
  quantity: NumField;
  date: string;
  evidenceReference: string;
}

export interface ScenarioForm {
  scenarioName: string;
  currency: string;
  contributionsReceived: NumField;
  amountAllocated: NumField;
  expenditureRecorded: NumField;
  resources: ResourceForm[];
  destinations: DestinationForm[];
}

// ---------------------------------------------------------------------------
// Conversions
// ---------------------------------------------------------------------------

/** "" -> null (unknown); "abc" -> NaN (invalid, reported by validation). */
function toNumber(value: NumField): number | null {
  const trimmed = value.trim();
  if (trimmed === "") return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

function resourceToForm(resource: ResourceInput): ResourceForm {
  return {
    id: resource.id,
    name: resource.name,
    unit: resource.unit,
    openingQuantity: toNumField(resource.openingQuantity),
    received: toNumField(resource.received),
    transfersIn: toNumField(resource.transfersIn),
    distributed: toNumField(resource.distributed),
    transfersOut: toNumField(resource.transfersOut),
    losses: toNumField(resource.losses),
    disposed: toNumField(resource.disposed),
    observedRemaining: toNumField(resource.observedRemaining),
    fundingReference: resource.fundingReference ?? "",
    evidenceReference: resource.evidenceReference ?? "",
  };
}

function toNumField(value: number | null): NumField {
  return value === null ? "" : String(value);
}

export function scenarioToForm(input: ScenarioInput): ScenarioForm {
  return {
    scenarioName: input.scenarioName,
    currency: input.currency,
    contributionsReceived: toNumField(input.contributionsReceived),
    amountAllocated: toNumField(input.amountAllocated),
    expenditureRecorded: toNumField(input.expenditureRecorded),
    resources:
      input.resources.length > 0
        ? input.resources.map(resourceToForm)
        : [emptyScenarioForm().resources[0]],
    destinations:
      input.destinations.length > 0
        ? input.destinations.map(destinationToForm)
        : [emptyScenarioForm().destinations[0]],
  };
}

function destinationToForm(input: DestinationInput): DestinationForm {
  return {
    id: input.id,
    resourceName: input.resourceName,
    destination: input.destination,
    quantity: toNumField(input.quantity),
    date: input.date ?? "",
    evidenceReference: input.evidenceReference ?? "",
  };
}

function resourceToInput(form: ResourceForm): ResourceInput {
  return {
    id: form.id,
    name: form.name,
    unit: form.unit,
    openingQuantity: toNumber(form.openingQuantity),
    received: toNumber(form.received),
    transfersIn: toNumber(form.transfersIn),
    distributed: toNumber(form.distributed),
    transfersOut: toNumber(form.transfersOut),
    losses: toNumber(form.losses),
    disposed: toNumber(form.disposed),
    observedRemaining: toNumber(form.observedRemaining),
    fundingReference: form.fundingReference,
    evidenceReference: form.evidenceReference,
  };
}

function destinationToInput(form: DestinationForm): DestinationInput {
  return {
    id: form.id,
    resourceName: form.resourceName,
    destination: form.destination,
    quantity: toNumber(form.quantity),
    date: form.date.trim() === "" ? null : form.date,
    evidenceReference: form.evidenceReference,
  };
}

export function formToScenario(form: ScenarioForm): ScenarioInput {
  return {
    scenarioName: form.scenarioName,
    currency: form.currency,
    contributionsReceived: toNumber(form.contributionsReceived),
    amountAllocated: toNumber(form.amountAllocated),
    expenditureRecorded: toNumber(form.expenditureRecorded),
    resources: form.resources.map(resourceToInput),
    destinations: form.destinations.map(destinationToInput),
  };
}

export function emptyScenarioForm(): ScenarioForm {
  return {
    scenarioName: "",
    currency: "INR",
    contributionsReceived: "",
    amountAllocated: "",
    expenditureRecorded: "",
    resources: [resourceFormFrom(emptyResource())],
    destinations: [destinationFormFrom(emptyDestination())],
  };
}

export function resourceFormFrom(input: ResourceInput): ResourceForm {
  return resourceToForm(input);
}

export function destinationFormFrom(input: DestinationInput): DestinationForm {
  return destinationToForm(input);
}

// ---------------------------------------------------------------------------
// Export / import
// ---------------------------------------------------------------------------

export const EXPORT_KIND = "impactledger.assessment-lab";
export const EXPORT_VERSION = 1;

export interface ExportedScenario {
  kind: typeof EXPORT_KIND;
  version: number;
  exportedAt: string;
  input: ScenarioInput;
}

export function createExport(
  input: ScenarioInput,
  now: string = new Date().toISOString(),
): ExportedScenario {
  return {
    kind: EXPORT_KIND,
    version: EXPORT_VERSION,
    exportedAt: now,
    input,
  };
}

export type ImportResult =
  | { ok: true; input: ScenarioInput }
  | { ok: false; error: string };

export function parseImport(text: string): ImportResult {
  let raw: unknown;
  try {
    raw = JSON.parse(text);
  } catch {
    return { ok: false, error: "The file is not valid JSON." };
  }
  if (!raw || typeof raw !== "object") {
    return { ok: false, error: "The file does not contain a scenario object." };
  }
  const obj = raw as Record<string, unknown>;
  if (obj.kind !== EXPORT_KIND) {
    return {
      ok: false,
      error: "This file was not exported from the Impact Assessment Lab.",
    };
  }
  const input = normalizeScenario(obj.input);
  if (!input) {
    return { ok: false, error: "The exported scenario is missing or malformed." };
  }
  return { ok: true, input };
}

function asNumberOrNull(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function normalizeResource(value: unknown): ResourceInput | null {
  if (!value || typeof value !== "object") return null;
  const r = value as Record<string, unknown>;
  return {
    id: asString(r.id) || emptyResource().id,
    name: asString(r.name),
    unit: asString(r.unit, "unit"),
    openingQuantity: asNumberOrNull(r.openingQuantity),
    received: asNumberOrNull(r.received),
    transfersIn: asNumberOrNull(r.transfersIn),
    distributed: asNumberOrNull(r.distributed),
    transfersOut: asNumberOrNull(r.transfersOut),
    losses: asNumberOrNull(r.losses),
    disposed: asNumberOrNull(r.disposed),
    observedRemaining: asNumberOrNull(r.observedRemaining),
    fundingReference: asString(r.fundingReference),
    evidenceReference: asString(r.evidenceReference),
  };
}

function normalizeDestination(value: unknown): DestinationInput | null {
  if (!value || typeof value !== "object") return null;
  const d = value as Record<string, unknown>;
  return {
    id: asString(d.id) || emptyDestination().id,
    resourceName: asString(d.resourceName),
    destination: asString(d.destination),
    quantity: asNumberOrNull(d.quantity),
    date: typeof d.date === "string" && d.date !== "" ? d.date : null,
    evidenceReference: asString(d.evidenceReference),
  };
}

export function normalizeScenario(value: unknown): ScenarioInput | null {
  if (!value || typeof value !== "object") return null;
  const s = value as Record<string, unknown>;
  const resources = Array.isArray(s.resources)
    ? s.resources
        .map(normalizeResource)
        .filter((r): r is ResourceInput => r !== null)
    : [];
  const destinations = Array.isArray(s.destinations)
    ? s.destinations
        .map(normalizeDestination)
        .filter((d): d is DestinationInput => d !== null)
    : [];
  return {
    scenarioName: asString(s.scenarioName),
    currency: asString(s.currency, "INR"),
    contributionsReceived: asNumberOrNull(s.contributionsReceived),
    amountAllocated: asNumberOrNull(s.amountAllocated),
    expenditureRecorded: asNumberOrNull(s.expenditureRecorded),
    resources: resources.length > 0 ? resources : [emptyResource()],
    destinations:
      destinations.length > 0 ? destinations : [emptyDestination()],
  };
}

/** True when a numeric form field string is blank or parses to a finite number. */
export function isValidNumberString(value: string): boolean {
  if (value.trim() === "") return true;
  return isFiniteNumber(Number(value));
}
