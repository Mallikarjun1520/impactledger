import { describe, it } from "node:test";
import assert from "node:assert/strict";

import {
  assessScenario,
  emptyScenario,
  formatNumber,
  round,
  validateScenario,
  type DestinationInput,
  type ResourceInput,
  type ScenarioInput,
} from "./assessment.ts";

function res(
  partial: Partial<ResourceInput> & { id: string },
): ResourceInput {
  return {
    name: "Item",
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
    ...partial,
  };
}

function dst(
  partial: Partial<DestinationInput> & { id: string },
): DestinationInput {
  return {
    resourceName: "",
    destination: "Camp",
    quantity: null,
    date: null,
    evidenceReference: "",
    ...partial,
  };
}

describe("formatNumber", () => {
  it("groups thousands deterministically", () => {
    assert.equal(formatNumber(500000), "500,000");
    assert.equal(formatNumber(1234.5), "1,234.5");
    assert.equal(formatNumber(0), "0");
  });
});

describe("round", () => {
  it("is stable against floating point drift", () => {
    assert.equal(round(0.1 + 0.2, 4), 0.3);
  });
});

describe("validateScenario", () => {
  it("rejects negative amounts", () => {
    const issues = validateScenario({
      scenarioName: "x",
      currency: "INR",
      contributionsReceived: -5,
      amountAllocated: null,
      expenditureRecorded: null,
      resources: [],
      destinations: [],
    });
    assert.ok(issues.some((i) => i.path === "contributionsReceived"));
  });

  it("requires a currency when money is present", () => {
    const issues = validateScenario({
      scenarioName: "x",
      currency: "",
      contributionsReceived: 100,
      amountAllocated: null,
      expenditureRecorded: null,
      resources: [],
      destinations: [],
    });
    assert.ok(issues.some((i) => i.path === "currency"));
  });

  it("accepts unknown (null) values", () => {
    const issues = validateScenario({
      scenarioName: "x",
      currency: "INR",
      contributionsReceived: null,
      amountAllocated: null,
      expenditureRecorded: null,
      resources: [res({ id: "r1", name: "Kit", received: null })],
      destinations: [],
    });
    assert.equal(issues.length, 0);
  });
});

describe("assessScenario — financial", () => {
  it("reports unallocated funds without inventing activity", () => {
    const result = assessScenario({
      scenarioName: "x",
      currency: "INR",
      contributionsReceived: 50000,
      amountAllocated: 30000,
      expenditureRecorded: null,
      resources: [],
      destinations: [],
    });
    assert.equal(result.financial.unallocated, 20000);
    assert.equal(result.financial.allocationPct, 60);
    const finding = result.findings.find((f) => f.title.includes("unallocated"));
    assert.ok(finding, "expected an unallocated finding");
    assert.equal(finding?.severity, "info");
    assert.ok(finding?.detail.includes("20,000"));
  });

  it("flags allocations above contributions as an error", () => {
    const result = assessScenario({
      scenarioName: "x",
      currency: "INR",
      contributionsReceived: 100,
      amountAllocated: 150,
      expenditureRecorded: null,
      resources: [],
      destinations: [],
    });
    assert.equal(result.status, "needs_review");
    assert.ok(result.findings.some((f) => f.severity === "error"));
  });

  it("does not compare against an unknown contribution total", () => {
    const result = assessScenario({
      scenarioName: "x",
      currency: "INR",
      contributionsReceived: null,
      amountAllocated: 100,
      expenditureRecorded: null,
      resources: [],
      destinations: [],
    });
    assert.equal(result.financial.unallocated, null);
    assert.equal(result.financial.allocationPct, null);
    assert.equal(result.status, "incomplete");
  });
});

describe("assessScenario — resource reconciliation", () => {
  it("accounts for the distribution shortfall of received quantity", () => {
    const result = assessScenario({
      scenarioName: "x",
      currency: "INR",
      contributionsReceived: null,
      amountAllocated: null,
      expenditureRecorded: null,
      resources: [
        res({ id: "r1", name: "Blankets", unit: "unit", received: 500, distributed: 250 }),
      ],
      destinations: [],
    });
    const row = result.resources[0];
    assert.equal(row.unaccountedOfReceived, 250);
    assert.ok(
      result.findings.some((f) => f.title.includes("250") && f.title.includes("500")),
    );
  });

  it("flags distribution exceeding receipts as an error", () => {
    const result = assessScenario({
      scenarioName: "x",
      currency: "INR",
      contributionsReceived: null,
      amountAllocated: null,
      expenditureRecorded: null,
      resources: [res({ id: "r1", name: "Food kits", received: 100, distributed: 120 })],
      destinations: [],
    });
    assert.equal(result.status, "needs_review");
    assert.ok(result.findings.some((f) => f.severity === "error"));
  });

  it("computes expected remaining from supplied terms only", () => {
    const result = assessScenario({
      scenarioName: "x",
      currency: "INR",
      contributionsReceived: null,
      amountAllocated: null,
      expenditureRecorded: null,
      resources: [
        res({
          id: "r1",
          name: "Water",
          unit: "can",
          openingQuantity: 100,
          received: 50,
          distributed: 30,
          losses: 5,
        }),
      ],
      destinations: [],
    });
    const row = result.resources[0];
    // 100 + 50 - 30 - 5 = 115 ; transfers out / disposals were not supplied
    assert.equal(row.expectedRemaining, 115);
    assert.ok(row.missingTerms.includes("transfers out"));
    assert.ok(row.missingTerms.includes("disposals"));
  });

  it("reports a physical count variance", () => {
    const result = assessScenario({
      scenarioName: "x",
      currency: "INR",
      contributionsReceived: null,
      amountAllocated: null,
      expenditureRecorded: null,
      resources: [
        res({
          id: "r1",
          name: "Tents",
          unit: "unit",
          received: 40,
          distributed: 10,
          observedRemaining: 25,
        }),
      ],
      destinations: [],
    });
    const row = result.resources[0];
    assert.equal(row.expectedRemaining, 30);
    assert.equal(row.variance, -5);
    assert.ok(
      result.findings.some((f) => f.severity === "warning" && f.title.includes("count")),
    );
  });

  it("treats a missing receipt as incomplete, not zero", () => {
    const result = assessScenario({
      scenarioName: "x",
      currency: "INR",
      contributionsReceived: null,
      amountAllocated: null,
      expenditureRecorded: null,
      resources: [res({ id: "r1", name: "Kits", distributed: 200 })],
      destinations: [],
    });
    assert.equal(result.status, "incomplete");
    assert.equal(result.resources[0].unaccountedOfReceived, null);
  });
});

describe("assessScenario — linkage, destinations, evidence", () => {
  it("flags a resource batch with no funding reference when money exists", () => {
    const result = assessScenario({
      scenarioName: "x",
      currency: "INR",
      contributionsReceived: 1000,
      amountAllocated: 1000,
      expenditureRecorded: null,
      resources: [res({ id: "r1", name: "Blankets", received: 10 })],
      destinations: [],
    });
    assert.ok(result.findings.some((f) => f.category === "linkage"));
  });

  it("detects duplicate destination records", () => {
    const result = assessScenario({
      scenarioName: "x",
      currency: "INR",
      contributionsReceived: null,
      amountAllocated: null,
      expenditureRecorded: null,
      resources: [res({ id: "r1", name: "Kits", distributed: 20 })],
      destinations: [
        dst({
          id: "d1",
          resourceName: "Kits",
          destination: "Camp A",
          quantity: 10,
          date: "2026-01-01",
        }),
        dst({
          id: "d2",
          resourceName: "Kits",
          destination: "Camp A",
          quantity: 10,
          date: "2026-01-01",
        }),
      ],
    });
    assert.ok(result.findings.some((f) => f.title.includes("duplicate")));
  });

  it("warns when the destination breakdown exceeds distributions", () => {
    const result = assessScenario({
      scenarioName: "x",
      currency: "INR",
      contributionsReceived: null,
      amountAllocated: null,
      expenditureRecorded: null,
      resources: [res({ id: "r1", name: "Kits", distributed: 15 })],
      destinations: [
        dst({ id: "d1", resourceName: "Kits", destination: "Camp A", quantity: 20 }),
      ],
    });
    assert.ok(
      result.findings.some(
        (f) => f.category === "destinations" && f.severity === "warning",
      ),
    );
  });

  it("does not show a misleading 0% evidence coverage", () => {
    const result = assessScenario({
      scenarioName: "x",
      currency: "INR",
      contributionsReceived: null,
      amountAllocated: null,
      expenditureRecorded: null,
      resources: [res({ id: "r1", name: "Kits", received: 10, distributed: 10 })],
      destinations: [],
    });
    assert.equal(result.evidence.pct, null);
  });

  it("computes evidence coverage from supplied references", () => {
    const result = assessScenario({
      scenarioName: "x",
      currency: "INR",
      contributionsReceived: null,
      amountAllocated: null,
      expenditureRecorded: null,
      resources: [
        res({
          id: "r1",
          name: "Kits",
          received: 10,
          distributed: 10,
          evidenceReference: "DN-1",
        }),
      ],
      destinations: [
        dst({ id: "d1", resourceName: "Kits", destination: "Camp A", quantity: 10 }),
      ],
    });
    assert.equal(result.evidence.recordsWithReference, 1);
    assert.equal(result.evidence.totalRecords, 2);
    assert.equal(result.evidence.pct, 50);
  });
});

describe("assessScenario — determinism", () => {
  it("produces identical output for identical input", () => {
    const input: ScenarioInput = {
      scenarioName: "x",
      currency: "INR",
      contributionsReceived: 1000,
      amountAllocated: 800,
      expenditureRecorded: null,
      resources: [res({ id: "r1", name: "Kits", received: 100, distributed: 80 })],
      destinations: [
        dst({ id: "d1", resourceName: "Kits", destination: "Camp", quantity: 80 }),
      ],
    };
    assert.deepEqual(assessScenario(input), assessScenario(input));
  });

  it("treats an empty scenario as incomplete", () => {
    const result = assessScenario(emptyScenario());
    assert.equal(result.status, "incomplete");
    assert.ok(result.findings.length >= 1);
  });
});
