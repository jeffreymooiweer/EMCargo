/** Equipment selection is a snapshot, and allocation follows stable draft IDs.
 * These tests prevent library edits or reordered rows from changing a saved
 * load, and prevent a shipment-wide mass correction from scaling empty tare.
 */
import { describe, expect, it } from "vitest";
import type { CalcResult, EquipmentItem, LineItem } from "../api/client";
import { equipmentSnapshot, equipmentPatch } from "./equipment";
import { dimensionOverridesFromDrafts, recalcTotals, scaleLinesToTotalWeight } from "./lineWeights";
import { containerAutoValues } from "./containerValues";
import { readSnapshot, SNAPSHOT_VERSION } from "../wizard/snapshot";
import type { DraftLine } from "../components/ReviewLinesPanel";

const asset: EquipmentItem = { id: 7, version: 2, kind: "machine", specifications: "DEMO telehandler", asset_code: "DEMO-07", weight_kg: 7000,
  length_cm: 500, width_cm: 230, height_cm: 250, configurations: [{ name: "Lowered", weight_kg: 6800, height_cm: 210 }] };
const draft = (id: number, description: string): DraftLine => ({ id, description, quantity: 1, unit: "pcs" });
const output = (id: number, weight: number, extra: Partial<LineItem> = {}): LineItem => ({ line_id: id, raw: "DEMO", description: "DEMO", output_description: "DEMO", quantity: 1, unit: "pcs", material: null, product_type: null, weight_each_kg: weight, weight_total_kg: weight, material_volume_m3: null, transport_volume_m3: null, length_cm: null, width_cm: null, height_cm: null, include: true, status: "ok", messages: [], ...extra });

describe("equipment in a shipment", () => {
  it("copies physical data and configurations, and preserves them on reopening", () => {
    const item = structuredClone(asset);
    const selected = equipmentSnapshot(item);
    const line = { ...draft(3, ""), ...equipmentPatch(selected) };
    item.weight_kg = 9000; item.configurations![0].height_cm = 400;
    selected.weight_kg = 8000;
    const restored = readSnapshot(JSON.parse(JSON.stringify({ version: SNAPSHOT_VERSION, draftLines: [line] })))!;
    expect(restored.draftLines[0].equipment?.weight_kg).toBe(7000);
    expect(restored.draftLines[0].equipment?.configurations?.[0].height_cm).toBe(210);
    expect(restored.draftLines[0].length_cm).toBe(500);
    expect(restored.draftLines[0].weight_each_kg).toBe(7000);
  });
  it("maps a reordered container reference past blank rows, and keeps a deleted parent invalid", () => {
    const child = { ...draft(90, "DEMO goods"), container_line_id: 40 };
    const parent = { ...draft(40, "DEMO container"), equipment: { ...equipmentSnapshot(asset), kind: "container" as const }, equipment_role: "container" as const };
    expect(dimensionOverridesFromDrafts([child, draft(5, ""), parent])[0]).toMatchObject({ line_id: 1, container_line_id: 2 });
    expect(dimensionOverridesFromDrafts([child])[0]).toMatchObject({ line_id: 1, container_line_id: -1 });
  });
  it("keeps tare fixed during a total-weight correction", () => {
    const scaled = scaleLinesToTotalWeight([output(1, 2200, { equipment_role: "container" }), output(2, 5000, { container_line_id: 1 })], 8200);
    expect(scaled.map(line => line.weight_total_kg)).toEqual([2200, 6000]);
    expect(recalcTotals(scaled).total_weight_kg).toBe(8200);
  });
  it("suggests cargo mass without tare and never invents a VGM", () => {
    const lines = [output(1, 2200, { equipment_role: "container", equipment: { ...equipmentSnapshot(asset), kind: "container", container_number: "DEMO000001" } }), output(2, 5000, { container_line_id: 1 })];
    const result: CalcResult = { success: true, lines, totals: recalcTotals(lines), errors: [], column_map: {} };
    expect(containerAutoValues(result, "")).toEqual({ total_weight_kg: "7200", container_cargo_weight_kg: "5000", container_tare_kg: "2200", selected_container_number: "DEMO000001" });
    expect(containerAutoValues(result, "OTHER").container_cargo_weight_kg).toBe("");
    expect(containerAutoValues({ ...result, lines: [...lines, { ...lines[0], line_id: 3 }] }, "").container_tare_kg).toBe("");
  });
});
