import { describe, expect, it } from "vitest";
import type { CargoGood, PackagingTemplate } from "../api/cargo";
import { bindReusableCargo, cargoUnitGroups, cargoUnitWeight, cloneCargo, createCargoUnit, detachCargoGroup, emptyCargo, placeCargo, remainingQuantity, unpackCargo, validateCargo } from "./cargo";

const box: PackagingTemplate = { id: "box", name: "Box", category: "box", tare_kg: 1, dimensions_mm: { length: 400, width: 300, height: 200 } };
const pallet: PackagingTemplate = { id: "pallet", name: "Pallet", category: "pallet", tare_kg: 20 };
const goods: CargoGood[] = [
  { id: 7, name: "Bolts", quantity: 100, unit: "pcs", weight_kg: 10 },
  { id: 22, name: "Nuts", quantity: 40, unit: "pcs", weight_kg: 4 },
];

describe("cargo ownership and quantities", () => {
  it("packs mixed articles, nests that box with loose goods, and counts every tare exactly once", () => {
    const original = emptyCargo();
    const packed = placeCargo(original, goods, { unit_ids: [], goods: [{ goods_id: 7, quantity: 70 }, { goods_id: 22, quantity: 20 }] }, { template: box });
    expect(remainingQuantity(packed, goods[0])).toBe(30);
    expect(remainingQuantity(packed, goods[1])).toBe(20);
    expect(cargoUnitWeight(packed, goods, packed.units[0].id)).toBe(10);
    const nested = placeCargo(packed, goods, { unit_ids: [packed.units[0].id], goods: [{ goods_id: 7, quantity: 30 }] }, { template: pallet });
    expect(nested.units[0].id).toBe(packed.units[0].id);
    expect(nested.units[0].parent_id).toBe(nested.units[1].id);
    expect(cargoUnitWeight(nested, goods, nested.units[1].id)).toBe(33);
    expect(original.units).toHaveLength(0);
    expect(packed.units[0].parent_id).toBeNull();
  });

  it("distributes whole items with an explicit remainder and preserves a thousand physical identities compactly", () => {
    const distributed = placeCargo(emptyCargo(), goods, { unit_ids: [], goods: [{ goods_id: 7, quantity: 100 }] }, { template: box, count: 3 });
    expect(distributed.allocations.map(a => a.quantity)).toEqual([33, 33, 33]);
    expect(remainingQuantity(distributed, goods[0])).toBe(1);
    expect(new Set(distributed.units.map(unit => unit.id)).size).toBe(3);
    expect(new Set(distributed.units.map(unit => unit.code)).size).toBe(3);
    expect(cargoUnitGroups(distributed, null)).toHaveLength(1);
    const separated = detachCargoGroup(distributed, distributed.units[0].id);
    expect(cargoUnitGroups(separated, null).map(group => group.length)).toEqual([1, 2]);
    const large = placeCargo(emptyCargo(), [], { unit_ids: [], goods: [] }, { template: box, count: 1000 });
    expect(cargoUnitGroups(large, null)).toHaveLength(1);
    expect(new Set(large.units.map(unit => unit.id)).size).toBe(1000);
  });

  it("supports per-box recipes without reusing IDs or assigning the remainder", () => {
    const next = placeCargo(emptyCargo(), goods, { unit_ids: [], goods: [{ goods_id: 7, quantity: 10 }, { goods_id: 22, quantity: 4 }] }, { template: box, count: 10, mode: "per_unit" });
    expect(next.units).toHaveLength(10);
    expect(next.allocations).toHaveLength(20);
    expect(remainingQuantity(next, goods[0])).toBe(0);
    expect(remainingQuantity(next, goods[1])).toBe(0);
    expect(() => placeCargo(emptyCargo(), goods, { unit_ids: [], goods: [{ goods_id: 7, quantity: 11 }] }, { template: box, count: 10, mode: "per_unit" })).toThrow("overallocated");
  });

  it("moves part of an existing allocation, and unpacking preserves the rest and child identities", () => {
    let value = placeCargo(emptyCargo(), goods, { unit_ids: [], goods: [{ goods_id: 7, quantity: 100 }] }, { template: box });
    const originalId = value.units[0].id;
    value = placeCargo(value, goods, { unit_ids: [], goods: [{ goods_id: 7, quantity: 25, allocation_id: value.allocations[0].id }] }, { template: box });
    expect(value.allocations.map(a => a.quantity)).toEqual([75, 25]);
    value = placeCargo(value, goods, { unit_ids: value.units.map(unit => unit.id), goods: [] }, { template: pallet });
    const palletId = value.units[2].id;
    value = unpackCargo(value, goods, [palletId]);
    expect(value.units.map(unit => unit.id)).toContain(originalId);
    expect(value.units.every(unit => unit.parent_id === null)).toBe(true);
    expect(remainingQuantity(value, goods[0])).toBe(0);
    value = unpackCargo(value, goods, [originalId]);
    expect(remainingQuantity(value, goods[0])).toBe(75);
  });

  it("excludes selected descendants and rejects cycles, missing parents, duplicates and over-allocation", () => {
    let value = placeCargo(emptyCargo(), goods, { unit_ids: [], goods: [{ goods_id: 7, quantity: 100 }] }, { template: box });
    value = placeCargo(value, goods, { unit_ids: [value.units[0].id], goods: [] }, { template: pallet });
    const child = value.units[0], parent = value.units[1];
    expect(() => placeCargo(value, goods, { unit_ids: [parent.id], goods: [] }, { destination_id: child.id })).toThrow("cycle");
    const moved = placeCargo(value, goods, { unit_ids: [parent.id, child.id], goods: [{ goods_id: 7, quantity: 100, allocation_id: value.allocations[0].id }] }, { template: pallet });
    expect(moved.units[0].parent_id).toBe(parent.id);
    expect(moved.allocations).toEqual(value.allocations);
    expect(() => validateCargo({ ...value, units: [...value.units, value.units[0]] }, goods)).toThrow("duplicateId");
    expect(() => placeCargo(value, goods, { unit_ids: [], goods: [{ goods_id: 7, quantity: 1 }] }, { destination_id: child.id })).toThrow("overallocated");
  });

  it("loads bulk and long goods directly on external transport without a package or known weight", () => {
    const bulk: CargoGood[] = [{ id: 2, name: "Sand", quantity: 12.5, unit: "m3", weight_kg: null }];
    const value = placeCargo(emptyCargo(), bulk, { unit_ids: [], goods: [{ goods_id: 2, quantity: 12.5 }] }, { template: { id: "", name: "Tipper", category: "vehicle" }, unit_options: { kind: "ctu", source: "external" } });
    expect(value.units).toHaveLength(1);
    expect(value.units[0].kind).toBe("ctu");
    expect(cargoUnitWeight(value, bulk, value.units[0].id)).toBeNull();
    expect(remainingQuantity(value, bulk[0])).toBe(0);
    expect(() => placeCargo(value, bulk, { unit_ids: [value.units[0].id], goods: [] }, { template: box })).toThrow("invalidParent");
  });

  it("keeps measured totals separate from unknown article weights", () => {
    const unknown = [{ ...goods[0], weight_kg: null }];
    const value = placeCargo(emptyCargo(), unknown, { unit_ids: [], goods: [{ goods_id: 7, quantity: 100 }] }, { template: box, unit_options: { measured_gross_kg: 80 } });
    expect(value.units[0].measured_gross_kg).toBe(80);
    expect(cargoUnitWeight(value, unknown, value.units[0].id)).toBeNull();
  });

  it("copies packing recipes with new identities and without reserving a previously used physical asset", () => {
    const value = placeCargo(emptyCargo(), goods, { unit_ids: [], goods: [{ goods_id: 7, quantity: 100 }] }, { template: box, unit_options: { reusable: true, equipment_id: 9, external_reference: "OLD", measured_gross_kg: 11, legacy_goods_id: 3 } });
    const copied = cloneCargo(value);
    expect(copied.shipment_id).not.toBe(value.shipment_id);
    expect(copied.units[0]).toMatchObject({ template_id: "box", equipment_id: null, external_reference: "", measured_gross_kg: null, legacy_goods_id: null });
    expect(copied.units[0].id).not.toBe(value.units[0].id);
    expect(copied.units[0].code).not.toBe(value.units[0].code);
    expect(copied.allocations[0].unit_id).toBe(copied.units[0].id);
    expect(copied.allocations[0].goods_id).toBe(7);
    expect(copied.allocations[0].quantity).toBe(100);
  });

  it("strips catalogue metadata forbidden by the versioned physical-unit contract", () => {
    const unit = createCargoUnit({ ...box, builtin: true, active: true, version: 5, language_labels: { nl: "Doos", en: "Box", de: "Karton", fr: "Carton" } });
    expect(unit).not.toHaveProperty("builtin");
    expect(unit).not.toHaveProperty("active");
    expect(unit).not.toHaveProperty("version");
    expect(unit).not.toHaveProperty("language_labels");
  });

  it("binds imported own equipment to one known identity without rewriting its old dimensions or contents", () => {
    const value = placeCargo(emptyCargo(), goods, { unit_ids: [], goods: [{ goods_id: 7, quantity: 100 }] }, { template: box, unit_options: { kind: "ctu", equipment_id: 9 } });
    const physical = createCargoUnit({ ...box, name: "Current specification", tare_kg: 999 }, { kind: "ctu", equipment_id: 9 });
    const bound = bindReusableCargo(value, [physical]);
    expect(bound.units[0]).toMatchObject({ id: physical.id, code: physical.code, name: "Box", tare_kg: 1 });
    expect(bound.allocations[0].unit_id).toBe(physical.id);
    expect(value.units[0].id).not.toBe(physical.id);
    expect(bindReusableCargo(bound, [physical])).toBe(bound);
  });

  it("rejects oversized batches and fractional pieces atomically, preserving the current manifest", () => {
    const value = emptyCargo();
    expect(() => placeCargo(value, [], { unit_ids: [], goods: [] }, { template: box, count: 2001 })).toThrow("invalidCount");
    const full = placeCargo(value, [], { unit_ids: [], goods: [] }, { template: box, count: 2000 });
    expect(() => placeCargo(full, [], { unit_ids: [], goods: [] }, { template: box })).toThrow("tooManyUnits");
    expect(full.units).toHaveLength(2000);
    expect(value.units).toHaveLength(0);
    expect(() => placeCargo(value, goods, { unit_ids: [], goods: [{ goods_id: 7, quantity: 1.5 }] }, { template: box })).toThrow("invalidQuantity");
  });
});
