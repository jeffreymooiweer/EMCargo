import type { CalcResult } from "../api/client";

/** Cargo mass excludes the carrying container's tare. It is never a VGM. */
export function containerAutoValues(result: CalcResult | null, number: string) {
  const containers = result?.lines.filter(line => line.include && line.equipment_role === "container") ?? [];
  const selected = containers.length === 1 && (!number.trim() || !containers[0].equipment?.container_number || containers[0].equipment.container_number === number.trim().toUpperCase()) ? containers[0] : undefined;
  const cargo = selected ? result!.lines.filter(line => line.include && line.container_line_id === selected.line_id) : [];
  return {
    total_weight_kg: result?.totals.total_weight_kg != null ? String(result.totals.total_weight_kg) : "",
    container_cargo_weight_kg: containers.length ? selected && cargo.every(line => line.weight_total_kg != null) ? String(cargo.reduce((sum, line) => sum + (line.weight_total_kg ?? 0), 0)) : "" : result?.totals.total_weight_kg != null ? String(result.totals.total_weight_kg) : "",
    container_tare_kg: selected?.weight_total_kg != null ? String(selected.weight_total_kg) : "",
    selected_container_number: selected?.equipment?.container_number ?? "",
  };
}
