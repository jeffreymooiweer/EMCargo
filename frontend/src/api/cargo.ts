import { apiRequest } from "./client";

export interface CargoDimensions { length: number | null; width: number | null; height: number | null }
export interface PackagingTemplate {
  id: string; name: string; language_labels?: Record<string, string>; category: string;
  dimensions_mm?: CargoDimensions | null; inner_dimensions_mm?: CargoDimensions | null;
  tare_kg?: number | null; max_payload_kg?: number | null; max_gross_kg?: number | null;
  max_stack_load_kg?: number | null; stackable?: boolean | null; keep_upright?: boolean | null;
  can_rotate?: boolean | null; reusable?: boolean; active?: boolean; version?: number;
  builtin?: boolean;
}
export interface CargoUnit extends Omit<PackagingTemplate, "active" | "version" | "language_labels" | "builtin"> {
  code: string; kind: "package" | "ctu"; parent_id: string | null;
  template_id?: string | null; group_id?: string | null; equipment_id?: number | null;
  external_reference?: string; loaded_dimensions_mm?: CargoDimensions | null;
  measured_gross_kg?: number | null; source?: "own" | "external" | "unknown";
  legacy_goods_id?: number | null;
}
export interface CargoAllocation { id: string; goods_id: number; unit_id: string; quantity: number }
export interface CargoManifest {
  schema_version: 1; revision: number; shipment_id?: string;
  units: CargoUnit[]; allocations: CargoAllocation[];
}
export interface CargoGood {
  id: number; name: string; quantity: number | null; unit: string;
  weight_kg: number | null; dimensions_mm?: CargoDimensions | null;
}

export interface CargoAssessment {
  cargo: CargoManifest;
  units: { id: string; calculated_gross_kg: number | null; measured_gross_kg: number | null; complete: boolean; [key: string]: unknown }[];
  totals: { goods_kg: number | null; packaging_kg: number | null; cargo_gross_kg: number | null; transport_tare_kg: number | null; transport_gross_kg: number | null; occupied_volume_m3: number | null; complete: boolean };
  loose: { goods_id: number; quantity: number | null; weight_kg: number | null }[];
  issues: { code: string; unit_id?: string; goods_id?: number; [key: string]: unknown }[];
}
const request = <T,>(path: string, options: RequestInit = {}) => apiRequest<T>(`/cargo${path}`, options);

/** Catalogues and physical units deliberately have different wire contracts. */
function templatePayload(value: Partial<PackagingTemplate>) {
  const keys: (keyof PackagingTemplate)[] = ["name", "category", "language_labels", "dimensions_mm", "inner_dimensions_mm", "tare_kg", "max_payload_kg", "max_gross_kg", "max_stack_load_kg", "stackable", "keep_upright", "can_rotate", "reusable", "active", "version"];
  return Object.fromEntries(keys.filter(key => value[key] !== undefined).map(key => [key, value[key]]));
}

export const cargoApi = {
  templates: () => request<PackagingTemplate[]>("/templates"),
  reusableUnits: (query = "", equipmentId?: number) => request<CargoUnit[]>(`/units?q=${encodeURIComponent(query)}${equipmentId == null ? "" : `&equipment_id=${equipmentId}`}`),
  createTemplate: (value: Omit<PackagingTemplate, "id">) => request<PackagingTemplate>("/templates", { method: "POST", body: JSON.stringify(templatePayload(value)) }),
  updateTemplate: (value: PackagingTemplate) => request<PackagingTemplate>(`/templates/${encodeURIComponent(value.id)}`, { method: "PUT", body: JSON.stringify(templatePayload(value)) }),
  archiveTemplate: (value: PackagingTemplate) => request<PackagingTemplate>(`/templates/${encodeURIComponent(value.id)}?version=${value.version ?? 1}`, { method: "DELETE" }),
  assess: (cargo: CargoManifest, lines: unknown[], signal?: AbortSignal) => request<CargoAssessment>("/v1/assess", { method: "POST", body: JSON.stringify({ cargo, lines }), signal }),
};
