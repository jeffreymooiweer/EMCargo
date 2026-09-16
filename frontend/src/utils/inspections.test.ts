/** Dates describe separate checks; an absent expiry never proves approval.
 * Applying a catalog example must not copy identity, inspections or stale limits.
 */
import { describe, expect, it } from "vitest";
import type { ContainerTemplate, EquipmentInspection, EquipmentItem } from "../api/client";
import { inspectionStatus, needsInspectionAttention, templatePatch } from "./inspections";

const check: EquipmentInspection = { id: "demo", kind: "nen3140", performed_on: "2026-01-01", due_on: "2027-01-01", result: "passed" };
const today = "2026-09-16";
describe("independent inspection status", () => {
  it("distinguishes approval, missing dates, failure, archived reports and due dates", () => {
    expect(inspectionStatus(check, today)).toBe("current");
    expect(inspectionStatus({ ...check, due_on: null }, today)).toBe("unknown");
    expect(inspectionStatus({ ...check, result: "unknown" }, today)).toBe("planned");
    expect(inspectionStatus({ ...check, performed_on: "2026-12-01" }, today)).toBe("planned");
    expect(inspectionStatus({ ...check, result: "failed" }, today)).toBe("failed");
    expect(needsInspectionAttention({ ...check, result: "conditional" }, today)).toBe(true);
    expect(needsInspectionAttention({ ...check, archived: true, result: "failed" }, today)).toBe(false);
    expect(needsInspectionAttention({ ...check, result: "not_applicable", due_on: "2020-01-01" }, today)).toBe(false);
  });
  it("uses calendar day boundaries including today and exactly thirty days", () => {
    expect(inspectionStatus({ ...check, due_on: "2026-09-15" }, today)).toBe("overdue");
    expect(inspectionStatus({ ...check, due_on: today }, today)).toBe("due_soon");
    expect(inspectionStatus({ ...check, due_on: "2026-10-16" }, today)).toBe("due_soon");
    expect(inspectionStatus({ ...check, due_on: "2026-10-17" }, today)).toBe("current");
  });
});

it("applies a model without inventing identity or approval and clears unknown specifications", () => {
  const model: ContainerTemplate = { id: "demo-shell", name: "20ft workshop", language_labels: { nl: "Werkplaats" }, family: "site", size_ft: 20,
    supplier: "DEMO", source_url: "https://example.com", checked_on: today, basis: "base_shell", container_use: "workshop", length_cm: 605.8, width_cm: 243.8, height_cm: 289.6 };
  const asset: EquipmentItem = { specifications: "", weight_kg: 1000, container_number: "DEMO123", asset_code: "DEMO", inspections: [check], max_payload_kg: 50000, inner_length_cm: 500 };
  const patch = templatePatch(model, asset, "nl-NL");
  expect(patch).toMatchObject({ specifications: "Werkplaats", weight_kg: 0, max_payload_kg: null, max_gross_kg: null, inner_length_cm: null, height_cm: 289.6 });
  expect(patch).not.toHaveProperty("inspections"); expect(patch).not.toHaveProperty("facilities"); expect(patch).not.toHaveProperty("container_number"); expect(patch).not.toHaveProperty("asset_code");
  expect(templatePatch(model, { ...asset, specifications: "Our workshop" }, "en").specifications).toBe("Our workshop");
  expect(asset.weight_kg).toBe(1000);
});
