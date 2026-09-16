import type { EquipmentItem, EquipmentSnapshot } from "../api/client";
import type { DraftLine } from "../components/ReviewLinesPanel";

export function equipmentSnapshot(item: EquipmentItem): EquipmentSnapshot {
  const { id, version, specifications, kind, asset_code, container_number, registration, serial_number,
    length_cm, width_cm, height_cm, weight_kg, inner_length_cm, inner_width_cm, inner_height_cm,
    max_payload_kg, max_gross_kg, transport_instructions, accessories, configurations } = item;
  return { equipment_id: id!, version: version ?? 1, specifications, kind: kind ?? "other", asset_code,
    container_number, registration, serial_number, length_cm, width_cm, height_cm, weight_kg,
    inner_length_cm, inner_width_cm, inner_height_cm, max_payload_kg, max_gross_kg,
    transport_instructions, accessories, configurations: structuredClone(configurations ?? []), configuration: "" };
}

export function equipmentPatch(equipment: EquipmentSnapshot): Partial<DraftLine> {
  return { description: equipment.specifications, equipment: structuredClone(equipment),
    equipment_role: "cargo", container_line_id: undefined, quantity: 1, unit: "pcs",
    length_cm: equipment.length_cm ?? undefined, width_cm: equipment.width_cm ?? undefined,
    height_cm: equipment.height_cm ?? undefined, weight_each_kg: equipment.weight_kg, weight_total_kg: undefined,
    wall_thickness_mm: undefined, cargo_form: undefined, article: undefined };
}
