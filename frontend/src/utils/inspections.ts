import type { ContainerTemplate, EquipmentInspection, EquipmentItem } from "../api/client";

export const inspectionKinds = ["general", "csc", "nen3140", "fgas", "apk", "lifting", "water", "fire", "other"] as const;
export const facilities = ["electricity", "water", "air_conditioning", "heating", "sanitary"];
export const containerUses = ["freight", "storage", "workshop", "office", "sanitary", "accommodation", "other"];
export function localDay(now = new Date()): string {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}
export function inspectionStatus(item: EquipmentInspection, today = localDay()) {
  if (item.archived) return "archived";
  if (item.result === "not_applicable") return "not_applicable";
  if (item.result === "failed" || item.result === "conditional") return item.result;
  if (item.performed_on && item.performed_on > today) return "planned";
  if (item.due_on && item.due_on < today) return "overdue";
  if (item.due_on && Date.parse(item.due_on) - Date.parse(today) <= 30 * 86400000) return "due_soon";
  if (item.result === "passed" && item.performed_on && item.due_on) return "current";
  if (item.due_on) return "planned";
  return "unknown";
}
export function needsInspectionAttention(item: EquipmentInspection, today = localDay()) {
  return ["failed", "conditional", "overdue", "due_soon"].includes(inspectionStatus(item, today));
}
export function templatePatch(template: ContainerTemplate, item: EquipmentItem, language: string): Partial<EquipmentItem> {
  return {
    kind: "container", container_template_id: template.id, container_type: template.name,
    specifications: item.specifications || template.language_labels[language.split("-")[0]] || template.name,
    source: "container_catalog", container_use: template.container_use,
    length_cm: template.length_cm, width_cm: template.width_cm, height_cm: template.height_cm,
    inner_length_cm: template.inner_length_cm ?? null, inner_width_cm: template.inner_width_cm ?? null,
    inner_height_cm: template.inner_height_cm ?? null, weight_kg: template.weight_kg ?? 0,
    max_payload_kg: template.max_payload_kg ?? null, max_gross_kg: template.max_gross_kg ?? null,
  };
}
