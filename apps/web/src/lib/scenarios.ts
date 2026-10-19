import type {
  DestinationInput,
  ResourceInput,
  ScenarioInput,
} from "./assessment.ts";

/**
 * Starter scenarios for the Impact Assessment Lab.
 *
 * IMPORTANT: every scenario here is a hand-written *illustrative example*.
 * These are not ImpactLedger production records, they are not read from any
 * database, and they are never written back to one. They exist only to give a
 * visitor a realistic starting point they can edit.
 */

export interface StarterScenario {
  id: string;
  name: string;
  description: string;
  illustrative: true;
  input: ScenarioInput;
}

function resource(partial: Partial<ResourceInput> & { id: string; name: string }): ResourceInput {
  return {
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

function destination(
  partial: Partial<DestinationInput> & { id: string; destination: string },
): DestinationInput {
  return {
    resourceName: "",
    quantity: null,
    date: null,
    evidenceReference: "",
    ...partial,
  };
}

export const STARTER_SCENARIOS: StarterScenario[] = [
  {
    id: "flood-relief-blankets",
    name: "Flood relief — blankets and dry rations",
    description:
      "A funding-round closes, two relief batches are procured and distributed across two camps. Illustrated figures only.",
    illustrative: true,
    input: {
      scenarioName: "Flood relief — blankets and dry rations",
      currency: "INR",
      contributionsReceived: 500000,
      amountAllocated: 480000,
      expenditureRecorded: 300000,
      resources: [
        resource({
          id: "res-blankets",
          name: "Blankets",
          unit: "unit",
          received: 500,
          distributed: 500,
          fundingReference: "PO-2026-014",
          evidenceReference: "DN-1145",
        }),
        resource({
          id: "res-rations",
          name: "Dry ration kits",
          unit: "kit",
          received: 300,
          distributed: 250,
          fundingReference: "PO-2026-015",
          evidenceReference: "DN-1146",
        }),
      ],
      destinations: [
        destination({
          id: "dst-1",
          resourceName: "Blankets",
          destination: "Khairatabad relief camp",
          quantity: 300,
          date: "2026-06-04",
          evidenceReference: "DS-01",
        }),
        destination({
          id: "dst-2",
          resourceName: "Blankets",
          destination: "Musheerabad shelter",
          quantity: 200,
          date: "2026-06-05",
          evidenceReference: "DS-02",
        }),
        destination({
          id: "dst-3",
          resourceName: "Dry ration kits",
          destination: "Khairatabad relief camp",
          quantity: 250,
          date: "2026-06-06",
          evidenceReference: "DS-03",
        }),
      ],
    },
  },
  {
    id: "food-kit-gap",
    name: "Food-kit distribution — reconciliation gap",
    description:
      "Distribution records claim more kits than were received, and the batch is not linked to the purchase that funded it.",
    illustrative: true,
    input: {
      scenarioName: "Food-kit distribution — reconciliation gap",
      currency: "INR",
      contributionsReceived: 250000,
      amountAllocated: 250000,
      expenditureRecorded: 250000,
      resources: [
        resource({
          id: "res-food",
          name: "Food kits",
          unit: "kit",
          received: 1000,
          distributed: 1050,
        }),
      ],
      destinations: [
        destination({
          id: "dst-food-1",
          resourceName: "Food kits",
          destination: "Camp A",
          quantity: 600,
        }),
        destination({
          id: "dst-food-2",
          resourceName: "Food kits",
          destination: "Camp B",
          quantity: 450,
        }),
      ],
    },
  },
  {
    id: "medical-incomplete",
    name: "Medical-supply allocation — incomplete records",
    description:
      "A distribution is recorded but the matching receipt is missing, so the batch cannot be reconciled.",
    illustrative: true,
    input: {
      scenarioName: "Medical-supply allocation — incomplete records",
      currency: "INR",
      contributionsReceived: 100000,
      amountAllocated: null,
      expenditureRecorded: null,
      resources: [
        resource({
          id: "res-medicine",
          name: "Medicine kits",
          unit: "kit",
          distributed: 200,
        }),
      ],
      destinations: [],
    },
  },
];

export function findStarterScenario(id: string): StarterScenario | undefined {
  return STARTER_SCENARIOS.find((s) => s.id === id);
}
