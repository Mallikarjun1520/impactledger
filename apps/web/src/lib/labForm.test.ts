import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { assessScenario } from "./assessment.ts";
import {
  createExport,
  emptyScenarioForm,
  formToScenario,
  parseImport,
  scenarioToForm,
} from "./labForm.ts";
import { STARTER_SCENARIOS } from "./scenarios.ts";

describe("labForm — round trip", () => {
  it("preserves figures through form and back", () => {
    const original = STARTER_SCENARIOS[0].input;
    const roundTripped = formToScenario(scenarioToForm(original));
    assert.deepEqual(roundTripped, original);
  });

  it("keeps unknown (blank) fields as null, never zero", () => {
    const form = emptyScenarioForm();
    const scenario = formToScenario(form);
    assert.equal(scenario.contributionsReceived, null);
    assert.equal(scenario.resources[0].openingQuantity, null);
    assert.equal(scenario.destinations[0].quantity, null);
  });

  it("treats a non-numeric field as invalid rather than silently dropping it", () => {
    const form = emptyScenarioForm();
    form.contributionsReceived = "not a number";
    const scenario = formToScenario(form);
    assert.ok(scenario.contributionsReceived !== null);
    assert.ok(!Number.isFinite(scenario.contributionsReceived as number));
  });

  it("treats empty form as an incomplete scenario", () => {
    const { status } = assessScenario(formToScenario(emptyScenarioForm()));
    assert.equal(status, "incomplete");
  });
});

describe("labForm — import/export", () => {
  it("round trips an exported scenario", () => {
    const input = STARTER_SCENARIOS[1].input;
    const data = createExport(input);
    const result = parseImport(JSON.stringify(data));
    assert.equal(result.ok, true);
    if (result.ok) {
      assert.deepEqual(result.input, input);
    }
  });

  it("rejects invalid JSON", () => {
    const result = parseImport("{not json");
    assert.equal(result.ok, false);
  });

  it("rejects a file that is not an exported scenario", () => {
    const result = parseImport(JSON.stringify({ hello: "world" }));
    assert.equal(result.ok, false);
  });

  it("repairs a partially malformed export instead of failing", () => {
    const partial = {
      kind: "impactledger.assessment-lab",
      version: 1,
      exportedAt: "2026-01-01T00:00:00.000Z",
      input: {
        scenarioName: "Partial",
        currency: "INR",
        contributionsReceived: "5000",
        amountAllocated: 4000,
        resources: [
          {
            name: "Kits",
            unit: "kit",
            received: 10,
            distributed: 10,
            fundingReference: "PO-1",
          },
        ],
        destinations: [{ resourceName: "Kits", destination: "Camp", quantity: 10 }],
      },
    };
    const result = parseImport(JSON.stringify(partial));
    assert.equal(result.ok, true);
    if (result.ok) {
      assert.equal(result.input.contributionsReceived, 5000);
      assert.equal(result.input.resources[0].name, "Kits");
      assert.equal(result.input.destinations[0].quantity, 10);
      const assessment = assessScenario(result.input);
      assert.equal(assessment.status, "consistent");
    }
  });
});
