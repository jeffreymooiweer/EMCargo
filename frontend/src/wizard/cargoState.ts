import type { CalcResult, LineItem } from "../api/client";
import type { CargoGood, CargoManifest, CargoUnit } from "../api/cargo";
import type { DraftLine } from "../components/ReviewLinesPanel";
import { cargoId, createCargoUnit, emptyCargo } from "../utils/cargo";

const positive = (value: unknown): number | null => typeof value === "number" && Number.isFinite(value) && value > 0 ? value : null;
const mm = (value: unknown) => positive(value) === null ? null : Number(value) * 10;

/** Draft identities survive sorting, deletion and every positional calculation. */
export function cargoLines(drafts: DraftLine[], result: CalcResult | null): LineItem[] {
  const filled = drafts.filter(line => line.description.trim());
  return filled.map((draft, index) => {
    const computed = result?.lines.find(line => line.cargo_goods_id === draft.id)
      ?? (result?.lines.every(line => line.cargo_goods_id == null) ? result.lines[index] : undefined);
    if (computed) return { ...computed, cargo_goods_id: draft.id };
    const quantity = positive(draft.quantity);
    const total = positive(draft.weight_total_kg)
      ?? (quantity !== null && positive(draft.weight_each_kg) !== null ? quantity * Number(draft.weight_each_kg) : null);
    return {
      line_id: index + 1, cargo_goods_id: draft.id, description: draft.description,
      output_description: draft.description, raw: draft.description, quantity, unit: draft.unit,
      include: true, weight_total_kg: total, weight_each_kg: total !== null && quantity ? total / quantity : null,
      length_cm: positive(draft.length_cm), width_cm: positive(draft.width_cm), height_cm: positive(draft.height_cm),
      transport_volume_m3: null, material_volume_m3: null, material: null, product_type: null,
      status: "needs_review", messages: [], detected_un_numbers: [],
      ...(draft.equipment ? { equipment: draft.equipment, equipment_role: draft.equipment_role } : {}),
    } as LineItem;
  });
}

export function cargoGoods(lines: LineItem[], cargo: CargoManifest): CargoGood[] {
  const legacy = new Set(cargo.units.map(unit => unit.legacy_goods_id).filter(id => id != null));
  return lines.filter(line => line.include && !legacy.has(line.cargo_goods_id ?? line.line_id)).map(line => ({
    id: line.cargo_goods_id ?? line.line_id, name: line.description,
    quantity: positive(line.quantity), unit: line.unit || "pcs", weight_kg: positive(line.weight_total_kg),
    dimensions_mm: { length: mm(line.length_cm), width: mm(line.width_cm), height: mm(line.height_cm) },
  }));
}

/** Convert one-level legacy containers once, retaining the original goods lines. */
export function migrateCargo(drafts: DraftLine[], existing?: CargoManifest): CargoManifest {
  if (existing) return existing;
  const cargo = emptyCargo();
  const containers = new Map<number, CargoUnit>();
  for (const line of drafts) {
    if (line.equipment_role !== "container" || !line.equipment) continue;
    const item = line.equipment;
    const unit = createCargoUnit({ id: "", name: line.description || item.specifications,
      category: "container", reusable: true, tare_kg: positive(line.weight_total_kg) ?? positive(line.weight_each_kg) ?? positive(item.weight_kg),
      dimensions_mm: { length: mm(line.length_cm ?? item.length_cm), width: mm(line.width_cm ?? item.width_cm), height: mm(line.height_cm ?? item.height_cm) },
      inner_dimensions_mm: { length: mm(item.inner_length_cm), width: mm(item.inner_width_cm), height: mm(item.inner_height_cm) },
      max_payload_kg: item.max_payload_kg ?? null, max_gross_kg: item.max_gross_kg ?? null,
    }, { kind: "ctu", equipment_id: item.equipment_id, external_reference: item.container_number || item.asset_code || "",
      legacy_goods_id: line.id, source: "own" });
    containers.set(line.id, unit); cargo.units.push(unit);
  }
  for (const line of drafts) {
    if (line.container_line_id == null) continue;
    const destination = containers.get(line.container_line_id);
    if (destination && positive(line.quantity) !== null) cargo.allocations.push({ id: cargoId(), goods_id: line.id, unit_id: destination.id, quantity: Number(line.quantity) });
  }
  return cargo;
}

/** Duplicating cargo detaches physical asset references from the copied lines. */
export function templateCargoDrafts(drafts: DraftLine[], cargo?: CargoManifest): DraftLine[] {
  if (!cargo?.units.length) return drafts;
  const carried = new Set(cargo.units.map(unit => unit.legacy_goods_id).filter(id => id != null));
  return drafts.filter(line => !carried.has(line.id)).map(line => ({ ...line, container_line_id: undefined }));
}

/** Once edited, legacy carriers live only in cargo; undo can restore their graph without recreating a goods row. */
export function editCargo(drafts: DraftLine[], previous: CargoManifest, next: CargoManifest) {
  const migrated = new Set([...previous.units, ...next.units].map(unit => unit.legacy_goods_id).filter(id => id != null));
  if (!migrated.size) return { drafts, cargo: next, migrated: false };
  return {
    drafts: drafts.filter(line => !migrated.has(line.id)).map(line => ({ ...line, container_line_id: undefined })),
    cargo: { ...next, units: next.units.map(unit => ({ ...unit, legacy_goods_id: null })) },
    migrated: true,
  };
}

/** Assistant replacement must not orphan a packed good or its legacy carrier. */
export function preservesCargo(drafts: DraftLine[], cargo: CargoManifest): boolean {
  const available = new Map(drafts.filter(line => line.description.trim()).map(line => [line.id, line]));
  const quantities = new Map<number, number>();
  for (const item of cargo.allocations) quantities.set(item.goods_id, (quantities.get(item.goods_id) ?? 0) + item.quantity);
  for (const [id, amount] of quantities) {
    const line = available.get(id);
    if (!line || positive(line.quantity) === null || amount > Number(line.quantity) + 1e-6) return false;
  }
  return cargo.units.every(unit => unit.legacy_goods_id == null || available.get(unit.legacy_goods_id)?.equipment_role === "container");
}
