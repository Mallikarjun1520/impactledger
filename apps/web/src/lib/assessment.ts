/**
 * ImpactLedger — Interactive Impact Assessment Lab: deterministic engine.
 *
 * Pure TypeScript. No I/O, no network, no database. It assesses only the
 * hypothetical figures a visitor supplies in the sandbox.
 *
 * Two invariants drive every rule:
 *   1. Unknown is not zero. `null` means "not provided" and is never coerced
 *      to 0, because that would manufacture a misleading finding.
 *   2. Every finding names the inputs that triggered it, so a reader can see
 *      *why* a conclusion was produced rather than trusting a black box.
 */

export type Severity = "error" | "warning" | "info";
export type FindingCategory =
  | "financial"
  | "resources"
  | "destinations"
  | "linkage"
  | "evidence"
  | "completeness";

export type AssessmentStatus = "consistent" | "needs_review" | "incomplete";

export interface Finding {
  id: string;
  severity: Severity;
  category: FindingCategory;
  title: string;
  detail: string;
  inputs: string[];
  recommendation: string;
}

export interface ResourceInput {
  id: string;
  name: string;
  unit: string;
  openingQuantity: number | null;
  received: number | null;
  transfersIn: number | null;
  distributed: number | null;
  transfersOut: number | null;
  losses: number | null;
  disposed: number | null;
  observedRemaining: number | null;
  fundingReference: string | null;
  evidenceReference: string | null;
}

export interface DestinationInput {
  id: string;
  resourceName: string;
  destination: string;
  quantity: number | null;
  date: string | null;
  evidenceReference: string | null;
}

export interface ScenarioInput {
  scenarioName: string;
  currency: string;
  contributionsReceived: number | null;
  amountAllocated: number | null;
  expenditureRecorded: number | null;
  resources: ResourceInput[];
  destinations: DestinationInput[];
}

export interface ValidationIssue {
  path: string;
  message: string;
}

// ---------------------------------------------------------------------------
// Safe arithmetic + deterministic formatting
// ---------------------------------------------------------------------------

export function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

/** Round to a fixed number of decimals so reconciliation stays deterministic. */
export function round(value: number, decimals = 4): number {
  if (!Number.isFinite(value)) return value;
  const factor = 10 ** decimals;
  return Math.round((value + Number.EPSILON) * factor) / factor;
}

/** Deterministic thousands-separated formatting (no locale dependence). */
export function formatNumber(value: number, maxDecimals = 4): string {
  if (!Number.isFinite(value)) return "—";
  const rounded = round(value, maxDecimals);
  const negative = rounded < 0;
  const abs = Math.abs(rounded);
  const asString = String(abs);
  if (asString.includes("e") || asString.includes("E")) {
    return (negative ? "-" : "") + abs.toPrecision(12);
  }
  const [intPart, decPart] = asString.split(".");
  const grouped = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return (negative ? "-" : "") + grouped + (decPart ? "." + decPart : "");
}

// ---------------------------------------------------------------------------
// Data presence helpers
// ---------------------------------------------------------------------------

export function hasMonetaryData(input: ScenarioInput): boolean {
  return (
    input.contributionsReceived !== null ||
    input.amountAllocated !== null ||
    input.expenditureRecorded !== null
  );
}

function termsOf(resource: ResourceInput): { key: string; value: number }[] {
  const terms: { key: string; value: number | null }[] = [
    { key: "opening quantity", value: resource.openingQuantity },
    { key: "receipts", value: resource.received },
    { key: "transfers in", value: resource.transfersIn },
    { key: "distributions", value: resource.distributed },
    { key: "transfers out", value: resource.transfersOut },
    { key: "losses", value: resource.losses },
    { key: "disposals", value: resource.disposed },
  ];
  return terms
    .filter((t): t is { key: string; value: number } => isFiniteNumber(t.value))
    .map((t) => ({ key: t.key, value: t.value as number }));
}

function resourceHasAnyTerm(resource: ResourceInput): boolean {
  return termsOf(resource).length > 0 || isFiniteNumber(resource.observedRemaining);
}

/** A row is "meaningful" once the user has put anything real into it. */
function resourceIsMeaningful(resource: ResourceInput): boolean {
  return (
    resourceHasAnyTerm(resource) ||
    resource.name.trim() !== "" ||
    (resource.fundingReference?.trim() ?? "") !== "" ||
    (resource.evidenceReference?.trim() ?? "") !== ""
  );
}

function destinationIsMeaningful(row: DestinationInput): boolean {
  return (
    row.destination.trim() !== "" ||
    row.resourceName.trim() !== "" ||
    row.quantity !== null ||
    (row.evidenceReference?.trim() ?? "") !== ""
  );
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

/**
 * Validate that supplied numbers are finite and non-negative where required.
 * Missing values (`null`) are allowed; whether a field is *required* for a
 * given conclusion is decided by the assessment, not here.
 */
export function validateScenario(input: ScenarioInput): ValidationIssue[] {
  const issues: ValidationIssue[] = [];

  const moneyFields: [string, number | null][] = [
    ["contributionsReceived", input.contributionsReceived],
    ["amountAllocated", input.amountAllocated],
    ["expenditureRecorded", input.expenditureRecorded],
  ];
  for (const [name, value] of moneyFields) {
    if (value === null) continue;
    if (!isFiniteNumber(value)) {
      issues.push({ path: name, message: "Enter a finite number." });
    } else if (value < 0) {
      issues.push({ path: name, message: "Amounts cannot be negative." });
    }
  }

  if (input.currency.trim() === "" && hasMonetaryData(input)) {
    issues.push({
      path: "currency",
      message: "A currency is required once monetary amounts are entered.",
    });
  }

  const quantityFields: (keyof ResourceInput)[] = [
    "openingQuantity",
    "received",
    "transfersIn",
    "distributed",
    "transfersOut",
    "losses",
    "disposed",
    "observedRemaining",
  ];

  input.resources.forEach((resource, i) => {
    if (resource.name.trim() === "") {
      issues.push({
        path: `resources.${i}.name`,
        message: "Each resource row needs a name.",
      });
    }
    for (const field of quantityFields) {
      const value = resource[field];
      if (value === null || value === undefined) continue;
      if (typeof value !== "number" || !Number.isFinite(value)) {
        issues.push({
          path: `resources.${i}.${String(field)}`,
          message: "Enter a finite number.",
        });
      } else if (value < 0) {
        issues.push({
          path: `resources.${i}.${String(field)}`,
          message: "Quantities cannot be negative.",
        });
      }
    }
  });

  input.destinations.forEach((row, i) => {
    if (row.resourceName.trim() === "" && row.destination.trim() === "") return;
    if (row.quantity === null || row.quantity === undefined) return;
    if (typeof row.quantity !== "number" || !Number.isFinite(row.quantity)) {
      issues.push({
        path: `destinations.${i}.quantity`,
        message: "Enter a finite number.",
      });
    } else if (row.quantity < 0) {
      issues.push({
        path: `destinations.${i}.quantity`,
        message: "Quantities cannot be negative.",
      });
    }
  });

  return issues;
}

// ---------------------------------------------------------------------------
// Result shapes
// ---------------------------------------------------------------------------

export interface FinancialSummary {
  contributionsReceived: number | null;
  amountAllocated: number | null;
  expenditureRecorded: number | null;
  unallocated: number | null;
  allocationPct: number | null;
  unspentOfAllocation: number | null;
}

export interface ResourceAssessment {
  id: string;
  name: string;
  unit: string;
  openingQuantity: number | null;
  received: number | null;
  transfersIn: number | null;
  distributed: number | null;
  transfersOut: number | null;
  losses: number | null;
  disposed: number | null;
  expectedRemaining: number | null;
  observedRemaining: number | null;
  variance: number | null;
  providedTerms: string[];
  missingTerms: string[];
  unaccountedOfReceived: number | null;
}

export interface DestinationSummary {
  total: number;
  byDestination: { destination: string; quantity: number; records: number }[];
  unmatchedResources: string[];
  rows: {
    resourceName: string;
    destination: string;
    quantity: number | null;
    date: string | null;
  }[];
}

export interface EvidenceCoverage {
  recordsWithReference: number;
  totalRecords: number;
  pct: number | null;
}

export interface AssessmentResult {
  status: AssessmentStatus;
  statusLabel: string;
  statusDetail: string;
  financial: FinancialSummary;
  resources: ResourceAssessment[];
  destinations: DestinationSummary;
  evidence: EvidenceCoverage;
  findings: Finding[];
  assumptions: string[];
  limitations: string[];
  metrics: { resourceRows: number; destinationRecords: number };
}

// ---------------------------------------------------------------------------
// Assessment
// ---------------------------------------------------------------------------

const LIMITATIONS = [
  "The assessment uses only the figures you entered. It does not read ImpactLedger's database and does not verify that any activity actually happened.",
  "Amounts are assumed to share the single currency you selected; mixed-currency scenarios are not compared.",
  "Evidence coverage counts records that carry a reference string. It does not confirm that the referenced document exists or supports the claim.",
];

/**
 * Assess a hypothetical relief-operation scenario.
 *
 * Inventory reconciliation uses only the terms the user supplied:
 *   expected remaining = opening + receipts + transfers in
 *                        − distributions − transfers out − losses − disposals
 * Terms that were not supplied are omitted (and reported), never assumed zero.
 */
export function assessScenario(input: ScenarioInput): AssessmentResult {
  const findings: Finding[] = [];
  let findingIndex = 0;
  const push = (
    severity: Severity,
    category: FindingCategory,
    title: string,
    detail: string,
    inputs: string[],
    recommendation: string,
  ): void => {
    findings.push({
      id: `f${findingIndex++}`,
      severity,
      category,
      title,
      detail,
      inputs,
      recommendation,
    });
  };

  const currency = input.currency.trim();
  const symbol = currency ? `${currency} ` : "";

  // ---- Financial summary -------------------------------------------------
  const contributions = input.contributionsReceived;
  const allocated = input.amountAllocated;
  const expenditure = input.expenditureRecorded;

  const unallocated =
    contributions !== null && allocated !== null
      ? round(contributions - allocated)
      : null;
  const allocationPct =
    contributions !== null && allocated !== null && contributions > 0
      ? round((allocated / contributions) * 100, 2)
      : null;
  const unspentOfAllocation =
    allocated !== null && expenditure !== null
      ? round(allocated - expenditure)
      : null;

  const financial: FinancialSummary = {
    contributionsReceived: contributions,
    amountAllocated: allocated,
    expenditureRecorded: expenditure,
    unallocated,
    allocationPct,
    unspentOfAllocation,
  };

  // ---- Resource assessments ---------------------------------------------
  const resources: ResourceAssessment[] = [];

  for (const resource of input.resources) {
    if (!resourceHasAnyTerm(resource)) continue;
    const provided = termsOf(resource);
    const providedKeys = provided.map((t) => t.key);

    const inflowKeys = ["opening quantity", "receipts", "transfers in"];
    const outflowKeys = [
      "distributions",
      "transfers out",
      "losses",
      "disposals",
    ];
    const standardKeys = [...inflowKeys, ...outflowKeys];

    const inflow = provided
      .filter((t) => inflowKeys.includes(t.key))
      .reduce((sum, t) => sum + t.value, 0);
    const outflow = provided
      .filter((t) => outflowKeys.includes(t.key))
      .reduce((sum, t) => sum + t.value, 0);

    const expectedRemaining =
      provided.length > 0 ? round(inflow - outflow) : null;
    const observedRemaining = resource.observedRemaining;
    const variance =
      expectedRemaining !== null && observedRemaining !== null
        ? round(observedRemaining - expectedRemaining)
        : null;

    // Only reconcile against receipts when both sides of the comparison exist.
    const unaccountedOfReceived =
      resource.received !== null && resource.distributed !== null
        ? round(resource.received - resource.distributed)
        : null;

    resources.push({
      id: resource.id,
      name: resource.name,
      unit: resource.unit,
      openingQuantity: resource.openingQuantity,
      received: resource.received,
      transfersIn: resource.transfersIn,
      distributed: resource.distributed,
      transfersOut: resource.transfersOut,
      losses: resource.losses,
      disposed: resource.disposed,
      expectedRemaining,
      observedRemaining,
      variance,
      providedTerms: providedKeys,
      missingTerms: standardKeys.filter((k) => !providedKeys.includes(k)),
      unaccountedOfReceived,
    });
  }

  // ---- Financial findings ------------------------------------------------
  if (contributions !== null && allocated !== null) {
    if (allocated > contributions) {
      push(
        "error",
        "financial",
        "Allocated funds exceed recorded contributions",
        `Recorded allocations of ${symbol}${formatNumber(allocated)} exceed recorded contributions of ${symbol}${formatNumber(contributions)} by ${symbol}${formatNumber(allocated - contributions)}.`,
        [`contributions ${formatNumber(contributions)}`, `allocated ${formatNumber(allocated)}`],
        "Correct the allocation figure or record the additional contribution that funds it.",
      );
    } else if (unallocated !== null && unallocated > 0) {
      push(
        "info",
        "financial",
        "Contributions remain unallocated",
        `${symbol}${formatNumber(unallocated)} of ${symbol}${formatNumber(contributions)} recorded contributions remain unallocated.`,
        [`contributions ${formatNumber(contributions)}`, `allocated ${formatNumber(allocated)}`],
        "Confirm whether the remaining funds are intentionally held or still need a recorded purpose.",
      );
    }
  }

  if (allocated !== null && expenditure !== null) {
    if (expenditure > allocated) {
      push(
        "error",
        "financial",
        "Recorded expenditure exceeds the approved allocation",
        `Recorded expenditure of ${symbol}${formatNumber(expenditure)} exceeds the allocated ${symbol}${formatNumber(allocated)} by ${symbol}${formatNumber(expenditure - allocated)}.`,
        [`allocated ${formatNumber(allocated)}`, `expenditure ${formatNumber(expenditure)}`],
        "Check for a missing allocation or a mis-keyed expenditure figure.",
      );
    } else if (unspentOfAllocation !== null && unspentOfAllocation > 0) {
      push(
        "info",
        "financial",
        "Allocation not fully recorded as spent",
        `${symbol}${formatNumber(unspentOfAllocation)} of the ${symbol}${formatNumber(allocated)} allocation has no recorded expenditure yet.`,
        [`allocated ${formatNumber(allocated)}`, `expenditure ${formatNumber(expenditure)}`],
        "Record the outstanding purchase or payment, or note that spending is still in progress.",
      );
    }
  }

  if (contributions === null && hasMonetaryData(input)) {
    push(
      "info",
      "completeness",
      "No recorded contributions to compare against",
      "Allocations or expenditure were entered without a recorded contribution total, so funding cannot be compared against spending.",
      ["contributions not provided"],
      "Add the total contributions received if you want a funding reconciliation.",
    );
  }

  // ---- Resource findings -------------------------------------------------
  const fundingRefs = new Map<string, string[]>();
  for (const resource of input.resources) {
    if (!resourceHasAnyTerm(resource) && !resource.received) continue;

    const label = resource.name.trim() || "Unnamed resource";
    const unit = resource.unit.trim() || "units";

    const provided = termsOf(resource);
    const inflowKeys = ["opening quantity", "receipts", "transfers in"];
    const outflowKeys = [
      "distributions",
      "transfers out",
      "losses",
      "disposals",
    ];
    const inflow = provided
      .filter((t) => inflowKeys.includes(t.key))
      .reduce((sum, t) => sum + t.value, 0);
    const outflow = provided
      .filter((t) => outflowKeys.includes(t.key))
      .reduce((sum, t) => sum + t.value, 0);
    const expectedRemaining =
      provided.length > 0 ? round(inflow - outflow) : null;
    const variance =
      expectedRemaining !== null && resource.observedRemaining !== null
        ? round(resource.observedRemaining - expectedRemaining)
        : null;

    if (resource.received !== null && resource.distributed !== null) {
      if (resource.distributed > resource.received) {
        push(
          "error",
          "resources",
          `Distribution total exceeds recorded receipts for ${label}`,
          `Distribution records account for ${formatNumber(resource.distributed)} ${unit}, which exceeds the ${formatNumber(resource.received)} ${unit} recorded as received by ${formatNumber(resource.distributed - resource.received)} ${unit}.`,
          [`${label} received ${formatNumber(resource.received)}`, `${label} distributed ${formatNumber(resource.distributed)}`],
          "Reconcile the receipt and distribution records; one of the two totals is wrong or a receipt is missing.",
        );
      } else if (resource.distributed < resource.received) {
        push(
          "info",
          "resources",
          `Distribution records account for ${formatNumber(resource.distributed)} of ${formatNumber(resource.received)} ${unit} received (${label})`,
          `${formatNumber(resource.received - resource.distributed)} ${unit} are recorded as received but not yet distributed.`,
          [`${label} received ${formatNumber(resource.received)}`, `${label} distributed ${formatNumber(resource.distributed)}`],
          "Confirm whether the balance is held in stock, in transit, or missing a distribution record.",
        );
      }
    } else if (resource.distributed !== null && resource.received === null) {
      push(
        "info",
        "completeness",
        `Cannot reconcile ${label} against receipts`,
        `A distributed quantity of ${formatNumber(resource.distributed)} ${unit} was entered without a recorded received quantity, so no comparison is possible.`,
        [`${label} distributed ${formatNumber(resource.distributed)}`, `${label} received not provided`],
        "Add the quantity received to enable a reconciliation.",
      );
    } else if (resource.received !== null && resource.distributed === null) {
      push(
        "info",
        "resources",
        `Receipts recorded for ${label} without distributions`,
        `${formatNumber(resource.received)} ${unit} were recorded as received but no distribution quantity is recorded.`,
        [`${label} received ${formatNumber(resource.received)}`],
        "Record where the received units went, or state that they remain in stock.",
      );
    }

    if (variance !== null && Math.abs(variance) > 1e-9) {
      const direction = variance > 0 ? "more" : "fewer";
      push(
        "warning",
        "resources",
        `Physical count differs from the expected balance for ${label}`,
        `A counted balance of ${formatNumber(resource.observedRemaining as number)} ${unit} is ${formatNumber(Math.abs(variance))} ${unit} ${direction} than the expected ${formatNumber(expectedRemaining as number)} ${unit}.`,
        [
          `${label} expected ${formatNumber(expectedRemaining as number)}`,
          `${label} counted ${formatNumber(resource.observedRemaining as number)}`,
        ],
        "Investigate the difference: an unrecorded movement, loss or data-entry error.",
      );
    }

    if (
      hasMonetaryData(input) &&
      resource.received !== null &&
      resource.received > 0 &&
      (resource.fundingReference === null || resource.fundingReference.trim() === "")
    ) {
      push(
        "warning",
        "linkage",
        `No funding link recorded for ${label}`,
        `The scenario records money but the ${label} batch does not identify the purchase, commitment or allocation that funded it.`,
        [`${label} received ${formatNumber(resource.received)}`, `${label} funding reference not provided`],
        "Record the funding reference so the resource can be traced back to the money that paid for it.",
      );
    }

    const ref = resource.fundingReference?.trim();
    if (ref) {
      const existing = fundingRefs.get(ref) ?? [];
      existing.push(label);
      fundingRefs.set(ref, existing);
    }
  }

  for (const [ref, labels] of fundingRefs) {
    if (labels.length > 1) {
      push(
        "warning",
        "linkage",
        "Conflicting funding reference",
        `The reference "${ref}" is attached to more than one resource batch (${labels.join(", ")}), which makes the funding source ambiguous.`,
        [`funding reference "${ref}"`],
        "Use a unique reference per purchase or batch, or confirm the shared reference is intentional.",
      );
    }
  }

  // ---- Destination summary ----------------------------------------------
  const destinationMap = new Map<
    string,
    { destination: string; quantity: number; records: number }
  >();
  let destinationTotal = 0;
  const unmatched = new Set<string>();
  const resourceNames = input.resources.map((r) => r.name.trim().toLowerCase());

  for (const row of input.destinations) {
    if (!destinationIsMeaningful(row)) continue;
    if (row.quantity !== null) {
      destinationTotal += row.quantity;
    }
    const key = row.destination.trim() || "Unnamed destination";
    const current = destinationMap.get(key) ?? {
      destination: key,
      quantity: 0,
      records: 0,
    };
    current.quantity = round(current.quantity + (row.quantity ?? 0));
    current.records += 1;
    destinationMap.set(key, current);

    const resourceName = row.resourceName.trim();
    if (
      resourceName !== "" &&
      input.resources.length > 0 &&
      !resourceNames.includes(resourceName.toLowerCase())
    ) {
      unmatched.add(resourceName);
    }
  }

  const destinations: DestinationSummary = {
    total: round(destinationTotal),
    byDestination: [...destinationMap.values()].sort((a, b) =>
      a.destination.localeCompare(b.destination),
    ),
    unmatchedResources: [...unmatched].sort(),
    rows: input.destinations
      .filter((r) => r.destination.trim() !== "" || r.resourceName.trim() !== "")
      .map((r) => ({
        resourceName: r.resourceName,
        destination: r.destination,
        quantity: r.quantity,
        date: r.date,
      })),
  };

  // Destination findings
  if (destinations.unmatchedResources.length > 0) {
    push(
      "warning",
      "destinations",
      "Destination records reference unknown resources",
      `These resources appear only in destination records and not in the resource rows: ${destinations.unmatchedResources.join(", ")}.`,
      destinations.unmatchedResources.map((r) => `destination resource "${r}"`),
      "Add matching resource rows or correct the resource name on the destination.",
    );
  }

  for (const resource of resources) {
    if (resource.distributed === null) continue;
    const name = resource.name.trim().toLowerCase();
    const breakdown = input.destinations
      .filter((r) => r.resourceName.trim().toLowerCase() === name)
      .reduce((sum, r) => sum + (r.quantity ?? 0), 0);
    if (breakdown <= 0) continue;
    const unit = resource.unit.trim() || "units";
    if (round(breakdown) > resource.distributed) {
      push(
        "warning",
        "destinations",
        `Destination breakdown exceeds distributions for ${resource.name}`,
        `Destination records sum to ${formatNumber(breakdown)} ${unit}, more than the ${formatNumber(resource.distributed)} ${unit} recorded as distributed.`,
        [
          `${resource.name} distributed ${formatNumber(resource.distributed)}`,
          `${resource.name} destination total ${formatNumber(breakdown)}`,
        ],
        "Align the destination breakdown with the recorded distribution total.",
      );
    } else if (round(breakdown) < resource.distributed) {
      push(
        "info",
        "destinations",
        `Destination breakdown is incomplete for ${resource.name}`,
        `Destination records account for ${formatNumber(breakdown)} of ${formatNumber(resource.distributed)} ${unit} recorded as distributed.`,
        [
          `${resource.name} distributed ${formatNumber(resource.distributed)}`,
          `${resource.name} destination total ${formatNumber(breakdown)}`,
        ],
        "Add the missing destination records so every distributed unit has a destination.",
      );
    }
  }

  const duplicateCandidates = input.destinations.filter(destinationIsMeaningful);
  if (duplicateCandidates.length > 0) {
    const seen = new Map<string, number>();
    for (const row of duplicateCandidates) {
      const signature = [
        row.resourceName.trim().toLowerCase(),
        row.destination.trim().toLowerCase(),
        row.quantity ?? "?",
        row.date ?? "?",
      ].join("|");
      seen.set(signature, (seen.get(signature) ?? 0) + 1);
    }
    const duplicates = [...seen.values()].filter((n) => n > 1).length;
    if (duplicates > 0) {
      push(
        "warning",
        "destinations",
        "Possible duplicate destination records",
        `${duplicates} destination record${duplicates === 1 ? "" : "s"} appear identical in resource, destination, quantity and date.`,
        ["destination rows"],
        "Confirm the repeated entries are real separate deliveries and not duplicate records.",
      );
    }
  }

  // ---- Evidence coverage -------------------------------------------------
  // Blank placeholder rows never count as records; only rows the user
  // actually filled in contribute to coverage.
  const meaningfulResources = input.resources.filter(resourceIsMeaningful);
  const meaningfulDestinations = input.destinations.filter(destinationIsMeaningful);
  const totalRecords = meaningfulResources.length + meaningfulDestinations.length;
  let recordsWithReference = 0;
  for (const r of meaningfulResources) {
    if (r.evidenceReference && r.evidenceReference.trim() !== "") {
      recordsWithReference += 1;
    }
  }
  for (const r of meaningfulDestinations) {
    if (r.evidenceReference && r.evidenceReference.trim() !== "") {
      recordsWithReference += 1;
    }
  }
  const evidence: EvidenceCoverage = {
    recordsWithReference,
    totalRecords,
    pct:
      recordsWithReference > 0 && totalRecords > 0
        ? round((recordsWithReference / totalRecords) * 100, 0)
        : null,
  };
  if (totalRecords > 0 && recordsWithReference === 0) {
    push(
      "info",
      "evidence",
      "No evidence references supplied",
      "None of the records in this scenario carry a document or receipt reference, so no claim can be linked to supporting evidence.",
      ["evidence references"],
      "Add a reference (invoice, delivery note, receipt number) to at least the material records.",
    );
  } else if (evidence.pct !== null && evidence.pct < 100) {
    push(
      "info",
      "evidence",
      "Partial evidence coverage",
      `${recordsWithReference} of ${totalRecords} records carry a reference (${evidence.pct}%).`,
      ["evidence references"],
      "Add references to the remaining records if verification is required.",
    );
  }

  // ---- Completeness ------------------------------------------------------
  if (
    !hasMonetaryData(input) &&
    resources.length === 0 &&
    meaningfulDestinations.length === 0
  ) {
    push(
      "info",
      "completeness",
      "No assessable figures supplied",
      "The scenario currently contains no financial or resource figures, so no conclusions can be drawn.",
      ["scenario inputs"],
      "Enter at least a contribution total or a resource quantity and run the assessment again.",
    );
  }

  // ---- Status ------------------------------------------------------------
  const hasError = findings.some((f) => f.severity === "error");
  const hasWarning = findings.some((f) => f.severity === "warning");
  const hasCompleteness = findings.some((f) => f.category === "completeness");

  let status: AssessmentStatus;
  if (hasError || hasWarning) {
    status = "needs_review";
  } else if (hasCompleteness) {
    status = "incomplete";
  } else {
    status = "consistent";
  }

  const statusLabel =
    status === "consistent"
      ? "Consistent"
      : status === "needs_review"
        ? "Needs review"
        : "Incomplete data";

  const errorCount = findings.filter((f) => f.severity === "error").length;
  const warningCount = findings.filter((f) => f.severity === "warning").length;
  const statusDetail =
    status === "consistent"
      ? "The reported figures reconcile with each other under the rules below. This confirms internal consistency only — not that the activity occurred."
      : status === "needs_review"
        ? `${errorCount} error${errorCount === 1 ? "" : "s"} and ${warningCount} warning${warningCount === 1 ? "" : "s"} need attention before the figures can be treated as consistent.`
        : "Some inputs are missing, so the recorded lifecycle cannot yet be fully assessed.";

  // ---- Assumptions -------------------------------------------------------
  const assumptions: string[] = [
    "Fields left blank were treated as not provided, not as zero.",
  ];
  if (hasMonetaryData(input)) {
    assumptions.push(
      `All amounts use a single currency (${currency || "unspecified"}); currency conversion is not applied.`,
    );
  }
  if (resources.some((r) => r.expectedRemaining !== null)) {
    assumptions.push(
      "Expected remaining quantity = opening quantity + receipts + transfers in − distributions − transfers out − losses − disposals, using only the terms you provided.",
    );
  }
  if (input.resources.length > 0 && input.destinations.length === 0) {
    assumptions.push(
      "No destination records were entered, so distributions are assessed only in aggregate.",
    );
  }

  return {
    status,
    statusLabel,
    statusDetail,
    financial,
    resources,
    destinations,
    evidence,
    findings,
    assumptions,
    limitations: LIMITATIONS,
    metrics: {
      resourceRows: input.resources.length,
      destinationRecords: input.destinations.length,
    },
  };
}

// ---------------------------------------------------------------------------
// Factories
// ---------------------------------------------------------------------------

export function emptyResource(): ResourceInput {
  return {
    id: newId(),
    name: "",
    unit: "unit",
    openingQuantity: null,
    received: null,
    transfersIn: null,
    distributed: null,
    transfersOut: null,
    losses: null,
    disposed: null,
    observedRemaining: null,
    fundingReference: "",
    evidenceReference: "",
  };
}

export function emptyDestination(): DestinationInput {
  return {
    id: newId(),
    resourceName: "",
    destination: "",
    quantity: null,
    date: null,
    evidenceReference: "",
  };
}

export function emptyScenario(): ScenarioInput {
  return {
    scenarioName: "",
    currency: "INR",
    contributionsReceived: null,
    amountAllocated: null,
    expenditureRecorded: null,
    resources: [emptyResource()],
    destinations: [emptyDestination()],
  };
}

let idCounter = 0;
function newId(): string {
  idCounter += 1;
  return `row-${idCounter}-${Math.floor(Math.random() * 1e6).toString(36)}`;
}
