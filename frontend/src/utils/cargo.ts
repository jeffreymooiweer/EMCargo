import type { CargoAllocation, CargoGood, CargoManifest, CargoUnit, PackagingTemplate } from "../api/cargo";

export const CARGO_MAX_UNITS = 2000;
export const CARGO_MAX_DEPTH = 20;
const EPSILON = 0.000001;
const round = (value: number) => Math.round(value * 1e6) / 1e6;
export const cargoId = () => crypto.randomUUID();
export function emptyCargo(): CargoManifest { return { schema_version: 1, revision: 0, shipment_id: cargoId(), units: [], allocations: [] }; }
export class CargoError extends Error {
  constructor(public code: string) { super(code); this.name = "CargoError"; }
}
export function createCargoUnit(template: PackagingTemplate, options: Partial<CargoUnit> = {}): CargoUnit {
  const id = cargoId();
  const prefix = options.kind === "ctu" ? "CTU" : template.category === "pallet" ? "PAL" : template.category === "box" ? "BOX" : "LU";
  const { id: _templateId, language_labels: _labels, active: _active, version: _version, builtin: _builtin, ...properties } = template;
  return { ...properties, id, code: `${prefix}-${id.replace(/-/g, "").slice(0, 12).toUpperCase()}`, template_id: template.id || null,
    kind: "package", parent_id: null, ...options };
}
/** A new shipment copies a packing recipe, never its physical identities. */
export function cloneCargo(value: CargoManifest): CargoManifest {
  const units = value.units.map(unit => createCargoUnit(unit, { ...unit, template_id: unit.template_id ?? null, id: cargoId(), code: "", equipment_id: null, legacy_goods_id: null, external_reference: "", source: "unknown", measured_gross_kg: null }));
  const ids = new Map(value.units.map((unit, i) => [unit.id, units[i].id]));
  const groups = new Map<string, string>();
  units.forEach(unit => {
    const prefix = unit.kind === "ctu" ? "CTU" : unit.category === "pallet" ? "PAL" : unit.category === "box" ? "BOX" : "LU";
    unit.code = `${prefix}-${unit.id.replace(/-/g, "").slice(0, 12).toUpperCase()}`;
    unit.parent_id = unit.parent_id ? ids.get(unit.parent_id) ?? null : null;
    if (unit.group_id) { if (!groups.has(unit.group_id)) groups.set(unit.group_id, cargoId()); unit.group_id = groups.get(unit.group_id); }
  });
  return { ...emptyCargo(), units, allocations: value.allocations.map(a => ({ ...a, id: cargoId(), unit_id: ids.get(a.unit_id)! })) };
}
/** Link imported equipment to its existing identity without refreshing snapshots. */
export function bindReusableCargo(value: CargoManifest, reusable: CargoUnit[]): CargoManifest {
  const known = new Map(reusable.filter(unit => unit.equipment_id != null).map(unit => [unit.equipment_id, unit]));
  const links = new Map<string, CargoUnit>();
  value.units.forEach(unit => {
    const physical = unit.equipment_id != null ? known.get(unit.equipment_id) : undefined;
    if (physical && physical.id !== unit.id) links.set(unit.id, physical);
  });
  if (!links.size) return value;
  return { ...value, revision: value.revision + 1,
    units: value.units.map(unit => ({ ...unit, id: links.get(unit.id)?.id ?? unit.id, code: links.get(unit.id)?.code ?? unit.code, parent_id: unit.parent_id ? links.get(unit.parent_id)?.id ?? unit.parent_id : null })),
    allocations: value.allocations.map(allocation => ({ ...allocation, unit_id: links.get(allocation.unit_id)?.id ?? allocation.unit_id })),
  };
}
export function isWholeUnit(unit: string): boolean {
  return ["pcs", "pc", "piece", "pieces", "st", "stuks", "stuk", "ea", "each", "unit", "units", "count"].includes(unit.trim().toLowerCase());
}
export function allocatedQuantity(value: CargoManifest, goodsId: number): number { return round(value.allocations.filter(a => a.goods_id === goodsId).reduce((sum, a) => sum + a.quantity, 0)); }
export function remainingQuantity(value: CargoManifest, good: CargoGood): number | null { return good.quantity === null ? null : round(good.quantity - allocatedQuantity(value, good.id)); }
export function descendantIds(value: CargoManifest, ids: Iterable<string>): Set<string> {
  const all = new Set(ids);
  for (let index = 0; index < CARGO_MAX_DEPTH + 1; index++) {
    let added = false;
    value.units.forEach(unit => { if (unit.parent_id && all.has(unit.parent_id) && !all.has(unit.id)) { all.add(unit.id); added = true; } });
    if (!added) break;
  }
  return all;
}
/** Parent selection wins. This prevents moving both a box and its content. */
export function topSelectedUnitIds(value: CargoManifest, selected: Iterable<string>): string[] {
  const chosen = new Set(selected), map = new Map(value.units.map(unit => [unit.id, unit]));
  return [...chosen].filter(id => {
    let parent = map.get(id)?.parent_id; const seen = new Set<string>();
    while (parent && !seen.has(parent)) { if (chosen.has(parent)) return false; seen.add(parent); parent = map.get(parent)?.parent_id; }
    return map.has(id);
  });
}
export function validateCargo(value: CargoManifest, goods: CargoGood[]): void {
  if (value.units.length > CARGO_MAX_UNITS) throw new CargoError("tooManyUnits");
  const map = new Map(value.units.map(unit => [unit.id, unit]));
  if (map.size !== value.units.length) throw new CargoError("duplicateId");
  const codes = new Set(value.units.map(unit => unit.code));
  if (codes.size !== value.units.length) throw new CargoError("duplicateId");
  if (new Set(value.allocations.map(a => a.id)).size !== value.allocations.length) throw new CargoError("duplicateId");
  const equipment = value.units.filter(unit => unit.equipment_id != null).map(unit => unit.equipment_id);
  if (new Set(equipment).size !== equipment.length) throw new CargoError("duplicateId");
  for (const unit of value.units) {
    if (unit.kind === "ctu" && unit.parent_id && map.get(unit.parent_id)?.kind === "package") throw new CargoError("invalidParent");
    const seen = new Set([unit.id]); let parent = unit.parent_id;
    while (parent) {
      if (seen.has(parent)) throw new CargoError("cycle");
      seen.add(parent);
      if (seen.size > CARGO_MAX_DEPTH) throw new CargoError("tooDeep");
      if (!map.has(parent)) throw new CargoError("missingUnit");
      parent = map.get(parent)!.parent_id;
    }
  }
  const allGoods = new Map(goods.map(good => [good.id, good]));
  const assigned = new Map<number, number>();
  for (const item of value.allocations) {
    const good = allGoods.get(item.goods_id);
    if (!good) throw new CargoError("missingGoods");
    if (!map.has(item.unit_id)) throw new CargoError("missingUnit");
    if (!Number.isFinite(item.quantity) || item.quantity <= 0 || (isWholeUnit(good.unit) && !Number.isInteger(item.quantity))) throw new CargoError("invalidQuantity");
    assigned.set(good.id, round((assigned.get(good.id) ?? 0) + item.quantity));
  }
  for (const [id, amount] of assigned) {
    const good = allGoods.get(id)!;
    if (good.quantity === null || amount > good.quantity + EPSILON) throw new CargoError("overallocated");
  }
}

export interface CargoSelection { unit_ids: string[]; goods: { goods_id: number; quantity: number; allocation_id?: string }[] }
export interface PlaceCargoOptions {
  destination_id?: string | null;
  template?: PackagingTemplate; unit_options?: Partial<CargoUnit>; count?: number;
  mode?: "total" | "per_unit";
}
function commit(value: CargoManifest, goods: CargoGood[]): CargoManifest { validateCargo(value, goods); return { ...value, revision: value.revision + 1 }; }
export function placeCargo(value: CargoManifest, goods: CargoGood[], selection: CargoSelection, options: PlaceCargoOptions): CargoManifest {
  const next: CargoManifest = structuredClone(value);
  const unitIds = topSelectedUnitIds(value, selection.unit_ids);
  const covered = descendantIds(value, unitIds);
  const selectedGoods = selection.goods.filter(item => !item.allocation_id || !covered.has(value.allocations.find(a => a.id === item.allocation_id)?.unit_id ?? ""));
  const count = options.template ? (options.count ?? 1) : 1;
  if (!Number.isInteger(count) || count < 1 || count > CARGO_MAX_UNITS || (count > 1 && unitIds.length)) throw new CargoError("invalidCount");
  if (options.destination_id && covered.has(options.destination_id)) throw new CargoError("cycle");
  let destinations = [options.destination_id ?? null];
  if (options.template) {
    const group = count > 1 ? cargoId() : null;
    const created = Array.from({ length: count }, () => createCargoUnit(options.template!, { ...options.unit_options, group_id: group }));
    next.units.push(...created); destinations = created.map(unit => unit.id);
  }
  if (destinations[0] && !next.units.some(unit => unit.id === destinations[0])) throw new CargoError("missingUnit");
  for (const id of unitIds) {
    const unit = next.units.find(item => item.id === id)!;
    unit.parent_id = destinations[0];
    if (unit.group_id && value.units.some(other => other.group_id === unit.group_id && !unitIds.includes(other.id))) unit.group_id = null;
  }
  for (const selected of selectedGoods) {
    const good = goods.find(item => item.id === selected.goods_id);
    if (!good || !Number.isFinite(selected.quantity) || selected.quantity <= 0 || (isWholeUnit(good.unit) && !Number.isInteger(selected.quantity))) throw new CargoError("invalidQuantity");
    let perUnit = options.mode === "per_unit" ? selected.quantity : selected.quantity / count;
    perUnit = isWholeUnit(good.unit) ? Math.floor(perUnit) : Math.floor(perUnit * 1e6) / 1e6;
    if (perUnit <= 0) throw new CargoError("emptyDistribution");
    const total = round(perUnit * count);
    const original = selected.allocation_id ? next.allocations.find(a => a.id === selected.allocation_id) : null;
    const available = original?.quantity ?? remainingQuantity(next, good);
    if (available === null || total > available + EPSILON || (selected.allocation_id && (!original || original.goods_id !== selected.goods_id))) throw new CargoError("overallocated");
    if (original) {
      original.quantity = round(original.quantity - total);
      if (original.quantity <= EPSILON) next.allocations = next.allocations.filter(a => a.id !== original.id);
    }
    for (const destination of destinations) {
      if (!destination) continue;
      const existing = next.allocations.find(a => a.goods_id === good.id && a.unit_id === destination);
      if (existing) existing.quantity = round(existing.quantity + perUnit);
      else next.allocations.push({ id: cargoId(), goods_id: good.id, unit_id: destination, quantity: perUnit });
    }
  }
  return commit(next, goods);
}
export function unpackCargo(value: CargoManifest, goods: CargoGood[], ids: string[]): CargoManifest {
  const next = structuredClone(value);
  for (const id of topSelectedUnitIds(value, ids)) {
    const unit = next.units.find(u => u.id === id)!;
    next.units.forEach(child => { if (child.parent_id === id) child.parent_id = unit.parent_id; });
    next.allocations = next.allocations.flatMap(a => a.unit_id !== id ? [a] : unit.parent_id ? [{ ...a, unit_id: unit.parent_id }] : []);
    next.units = next.units.filter(u => u.id !== id);
  }
  return commit(next, goods);
}
export function detachCargoGroup(value: CargoManifest, id: string): CargoManifest {
  return { ...value, revision: value.revision + 1, units: value.units.map(unit => unit.id === id ? { ...unit, group_id: null } : unit) };
}
/** Group only genuinely identical direct content, never merely matching labels. */
export function cargoUnitGroups(value: CargoManifest, parent: string | null): CargoUnit[][] {
  const groups = new Map<string, CargoUnit[]>();
  for (const unit of value.units.filter(u => u.parent_id === parent)) {
    const content = value.allocations.filter(a => a.unit_id === unit.id).map(a => [a.goods_id, a.quantity]).sort((a, b) => a[0] - b[0]);
    const hasChildren = value.units.some(u => u.parent_id === unit.id);
    const { id: _id, code: _code, group_id: _group, ...specification } = unit;
    const key = unit.group_id && !hasChildren ? `${unit.group_id}:${JSON.stringify(specification)}:${JSON.stringify(content)}` : unit.id;
    groups.set(key, [...(groups.get(key) ?? []), unit]);
  }
  return [...groups.values()];
}
export function cargoUnitWeight(value: CargoManifest, goods: CargoGood[], unitId: string): number | null {
  const units = new Map(value.units.map(unit => [unit.id, unit]));
  function weigh(id: string, seen: Set<string>): number | null {
    const unit = units.get(id);
    if (!unit || seen.has(id) || seen.size > CARGO_MAX_DEPTH) return null;
    if (unit.tare_kg == null) return null;
    let weight = unit.tare_kg; const visited = new Set([...seen, id]);
    for (const allocation of value.allocations.filter(a => a.unit_id === id)) {
      const good = goods.find(g => g.id === allocation.goods_id);
      if (!good || good.weight_kg === null || !good.quantity) return null;
      weight += good.weight_kg * allocation.quantity / good.quantity;
    }
    for (const child of value.units.filter(u => u.parent_id === id)) {
      const childWeight = weigh(child.id, visited); if (childWeight === null) return null; weight += childWeight;
    }
    return round(weight);
  }
  return weigh(unitId, new Set());
}

/** Keep old snapshots readable; identity is allocated once when importing. */
export function readCargo(raw: unknown): CargoManifest | null {
  if (!raw || typeof raw !== "object") return null;
  const value = raw as Partial<CargoManifest>;
  if (value.schema_version !== 1 || !Array.isArray(value.units) || !Array.isArray(value.allocations)) return null;
  if (value.units.some(u => !u || typeof u.id !== "string" || typeof u.code !== "string" || typeof u.name !== "string")
      || value.allocations.some(a => !a || typeof a.id !== "string" || typeof a.goods_id !== "number" || typeof a.unit_id !== "string" || typeof a.quantity !== "number")) return null;
  return { ...value, schema_version: 1, revision: Number.isInteger(value.revision) ? value.revision! : 0, units: value.units, allocations: value.allocations };
}
