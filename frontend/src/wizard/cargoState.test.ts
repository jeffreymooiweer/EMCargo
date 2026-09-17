import { describe, expect, it } from "vitest";
import { cargoGoods, cargoLines, editCargo, migrateCargo, preservesCargo, templateCargoDrafts } from "./cargoState";
import { cloneCargo } from "../utils/cargo";
import type { DraftLine } from "../components/ReviewLinesPanel";

const drafts: DraftLine[] = [
  { id: 7, description: "Steel pipe", quantity: 20, unit: "pcs", weight_total_kg: 600, container_line_id: 12 },
  { id: 12, description: "Carrier", quantity: 1, unit: "pcs", equipment_role: "container", equipment: { equipment_id: 42, specifications: "Carrier", weight_kg: 2300 } as DraftLine["equipment"] },
];

describe("cargo wizard state", () => {
  it("retains non-positional goods identities and unknown measurements for bulk drafts", () => {
    const lines = cargoLines([{ id: 19, description: "Gravel", quantity: 12000, unit: "kg" }], null);
    expect(lines[0]).toMatchObject({ cargo_goods_id: 19, quantity: 12000, weight_total_kg: null, length_cm: null });
    expect(cargoGoods(lines, migrateCargo([], undefined))[0]).toMatchObject({ id: 19, quantity: 12000, weight_kg: null });
  });

  it("separates legacy carrier tare from goods and copies a recipe without old asset identity", () => {
    const cargo = migrateCargo(drafts);
    expect(cargo.units[0]).toMatchObject({ legacy_goods_id: 12, equipment_id: 42, tare_kg: 2300 });
    expect(cargo.allocations[0]).toMatchObject({ goods_id: 7, quantity: 20, unit_id: cargo.units[0].id });
    expect(cargoGoods(cargoLines(drafts, null), cargo).map(g => g.id)).toEqual([7]);
    const copy = cloneCargo(cargo);
    expect(copy.units[0]).toMatchObject({ equipment_id: null, legacy_goods_id: null, tare_kg: 2300 });
    expect(copy.units[0].id).not.toBe(cargo.units[0].id);
    expect(templateCargoDrafts(drafts, cargo)).toEqual([{ ...drafts[0], container_line_id: undefined }]);
  });

  it("unpacks and undoes migrated carriers without counting tare as goods", () => {
    const cargo = migrateCargo(drafts);
    const unpacked = editCargo(drafts, cargo, { ...cargo, units: [], allocations: [] });
    expect(unpacked.drafts.map(d => d.id)).toEqual([7]);
    expect(unpacked.drafts[0].container_line_id).toBeUndefined();
    const undone = editCargo(unpacked.drafts, unpacked.cargo, cargo);
    expect(undone.drafts.map(d => d.id)).toEqual([7]);
    expect(undone.cargo.units[0]).toMatchObject({ id: cargo.units[0].id, tare_kg: 2300, legacy_goods_id: null });
    expect(cargoGoods(cargoLines(undone.drafts, null), undone.cargo).map(g => g.id)).toEqual([7]);
  });

  it("rejects assistant replacements that lose packed goods or overallocate them", () => {
    const cargo = migrateCargo(drafts);
    expect(preservesCargo(drafts, cargo)).toBe(true);
    expect(preservesCargo([drafts[1]], cargo)).toBe(false);
    expect(preservesCargo([{ ...drafts[0], quantity: 2 }, drafts[1]], cargo)).toBe(false);
  });
});
