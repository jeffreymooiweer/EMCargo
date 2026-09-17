import { CalcResult, LineItem, EquipmentSnapshot } from "../api/client";

function round2(value: number): number {
  return Math.round(value * 100) / 100;
}

export function recalcTotals(lines: LineItem[]): CalcResult["totals"] {
  const included = lines.filter((line) => line.include);
  const withWeight = included.filter((line) => line.weight_total_kg != null);
  return {
    line_count: lines.length,
    included_count: included.length,
    total_quantity: included.reduce((sum, line) => sum + (line.quantity || 0), 0),
    total_weight_kg: round2(withWeight.reduce((sum, line) => sum + (line.weight_total_kg || 0), 0)),
    total_material_volume_m3: round2(included.reduce((sum, line) => sum + (line.material_volume_m3 || 0), 0)),
    total_transport_volume_m3: round2(included.reduce((sum, line) => sum + (line.transport_volume_m3 || 0), 0)),
    warning_count: lines.filter((line) => line.status === "warning" || line.status === "needs_review").length,
    error_count: lines.filter((line) => line.status === "error").length,
  };
}

export function applyLineWeightChange(
  lines: LineItem[],
  lineId: number,
  field: "weight_each_kg" | "weight_total_kg",
  value: number | null,
): LineItem[] {
  return lines.map((line) => {
    if (line.line_id !== lineId) return line;
    const qty = line.quantity && line.quantity > 0 ? line.quantity : 1;
    if (value == null || Number.isNaN(value)) {
      return { ...line, weight_each_kg: null, weight_total_kg: null };
    }
    if (field === "weight_each_kg") {
      return {
        ...line,
        weight_each_kg: round2(value),
        weight_total_kg: round2(value * qty),
      };
    }
    return {
      ...line,
      weight_total_kg: round2(value),
      weight_each_kg: round2(value / qty),
    };
  });
}

export function scaleLinesToTotalWeight(lines: LineItem[], newTotal: number): LineItem[] {
  if (newTotal < 0 || Number.isNaN(newTotal)) return lines;
  const included = lines.filter((line) => line.include);
  if (included.length === 0) return lines;

  const fixed = included.filter(line => line.equipment_role === "container");
  if (fixed.length) {
    const tare = fixed.reduce((sum, line) => sum + (line.weight_total_kg ?? 0), 0);
    const cargo = included.filter(line => line.equipment_role !== "container");
    if (newTotal <= tare || !cargo.length) return lines;
    const current = cargo.reduce((sum, line) => sum + (line.weight_total_kg ?? 0), 0);
    return lines.map(line => {
      if (!line.include || line.equipment_role === "container") return line;
      const total = round2(current > 0 ? (line.weight_total_kg ?? 0) * (newTotal - tare) / current : (newTotal - tare) / cargo.length);
      return { ...line, weight_total_kg: total, weight_each_kg: round2(total / (line.quantity || 1)) };
    });
  }
  const currentTotal = included.reduce((sum, line) => sum + (line.weight_total_kg || 0), 0);
  if (currentTotal <= 0) {
    const perLine = newTotal / included.length;
    return lines.map((line) => {
      if (!line.include) return line;
      const qty = line.quantity && line.quantity > 0 ? line.quantity : 1;
      const total = round2(perLine);
      return { ...line, weight_total_kg: total, weight_each_kg: round2(total / qty) };
    });
  }

  const factor = newTotal / currentTotal;
  return lines.map((line) => {
    if (!line.include) return line;
    const qty = line.quantity && line.quantity > 0 ? line.quantity : 1;
    const base = line.weight_total_kg ?? 0;
    const total = round2(base * factor);
    return { ...line, weight_total_kg: total, weight_each_kg: round2(total / qty) };
  });
}

export function weightOverridesFromLines(lines: LineItem[]) {
  // Results round each weight independently. Reusing 18.62 kg per package
  // for two packages would turn a saved 37.25 kg total into 37.24 kg. Keep
  // the total authoritative, including manual corrections in older snapshots
  // that do not record whether a weight was calculated or entered by hand.
  // The wizard clears results whenever calculation inputs change.
  return lines
    .filter((line) => line.weight_each_kg != null || line.weight_total_kg != null)
    .map((line) => ({
      line_id: line.line_id,
      ...(line.weight_total_kg != null
        ? { weight_total_kg: line.weight_total_kg }
        : { weight_each_kg: line.weight_each_kg! }),
    }));
}


/**
 * Dimensions the user filled in in the table, as overrides.
 *
 * `line_id` in the backend is simply the order of the non-empty lines, and
 * `draftToText` sends exactly those lines. So the index is enough here and no
 * computed result is needed — dimensions have to count towards the *first*
 * calculation as well.
 *
 * Centimetres on the screen, metres to the backend: that computes in metres and
 * it is not for the user to know.
 */
export function dimensionOverridesFromDrafts(
  drafts: {
    id?: number;
    equipment?: EquipmentSnapshot;
    equipment_role?: "cargo" | "container";
    container_line_id?: number;
    description: string;
    cargo_form?: string;
    wall_thickness_mm?: number | "";
    length_cm?: number | "";
    width_cm?: number | "";
    height_cm?: number | "";
    weight_each_kg?: number | "";
    weight_total_kg?: number | "";
  }[],
) {
  const overrides: Record<string, unknown>[] = [];
  const filled = drafts.filter((draft) => draft.description.trim());
  const ids = new Map(filled.map((draft, index) => [draft.id, index + 1]));
  filled.forEach((draft, index) => {
      const entry: Record<string, unknown> = { line_id: index + 1, ...(draft.id != null ? { cargo_goods_id: draft.id } : {}) };
      let any = draft.id != null;
      if (draft.equipment) {
        entry.equipment = draft.equipment;
        entry.equipment_role = draft.equipment_role ?? "cargo";
        any = true;
      }
      if (draft.container_line_id != null) {
        // A missing parent stays invalid; never silently drop an allocation.
        entry.container_line_id = ids.get(draft.container_line_id) ?? -1;
        any = true;
      }
      if (draft.cargo_form) {
        entry.cargo_form = draft.cargo_form;
        any = true;
      }
      // A weight the consignor stated themselves — through the assistant, for
      // goods the catalogue does not know. It counts towards the first
      // calculation like any other thing they filled in.
      if (typeof draft.weight_total_kg === "number" && draft.weight_total_kg > 0) {
        entry.weight_total_kg = draft.weight_total_kg;
        any = true;
      } else if (typeof draft.weight_each_kg === "number" && draft.weight_each_kg > 0) {
        entry.weight_each_kg = draft.weight_each_kg;
        any = true;
      }
      // Millimetres on the screen for the wall thickness — nobody writes down a
      // wall of 0.8 cm — and metres to the backend.
      if (typeof draft.wall_thickness_mm === "number" && draft.wall_thickness_mm > 0) {
        entry.wall_thickness_m = draft.wall_thickness_mm / 1000;
        any = true;
      }
      ([["length_cm", "length_m"], ["width_cm", "width_m"], ["height_cm", "height_m"]] as const).forEach(
        ([from, to]) => {
          const value = draft[from];
          if (typeof value === "number" && value > 0) {
            entry[to] = value / 100;
            any = true;
          }
        },
      );
      if (any) overrides.push(entry);
    });
  return overrides;
}

/** Weight and dimension overrides together, merged per line. */
export function mergeOverrides(
  ...groups: Record<string, unknown>[][]
): Record<string, unknown>[] {
  const byLine = new Map<number, Record<string, unknown>>();
  groups.flat().forEach((entry) => {
    const id = Number(entry.line_id);
    const existing = byLine.get(id) ?? { line_id: id };
    byLine.set(id, { ...existing, ...entry });
  });
  return [...byLine.values()];
}
