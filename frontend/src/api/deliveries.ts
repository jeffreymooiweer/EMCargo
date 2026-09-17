import { apiRequest, describeDetail } from "./client";

export const modes = ["road", "rail", "inland", "sea", "air"] as const;
export type Mode = typeof modes[number];
export type State = "draft" | "planned" | "released" | "in_progress" | "partial" | "completed" | "closed" | "cancelled";
export interface Leg {
  id: string; mode: Mode; origin: string; destination: string; carrier: string; vehicle: string;
  reference: string; load_unit_id?: string | null; planned_start: string | null; planned_end: string | null;
  max_mass_tonnes: string | null; equipment_ids: number[]; status?: State;
  document_values?: Record<string, Record<string, string>>;
  review?: { actor: number; at: string; reason: string; fingerprint: string; document_ids: string[] };
  assessment?: Assessment;
}
export interface Allocation { id: string; shipment_id: number; goods_id: string; quantity: string; leg_ids: string[]; unit_ids?: string[] | null; leg_quantities?: Record<string, string> }
export interface PackingUnit { id: string; code: string; name: string; goods: Record<string, string>; available?: boolean }
export interface Goods { delivery_goods_id?: string; cargo_goods_id?: string; line_id?: string; id?: string; description?: string; quantity?: number; unit?: string }
export interface Source { packing_units?: PackingUnit[]; reference: string; export?: { goods: Goods[]; consignment?: Record<string, string> }; goods?: Goods[] }
export interface DeliveryFile { id: string; leg_id: string; filename: string; kind: string; current: boolean; metadata: Record<string, unknown> }
export interface ReceiptLine { allocation_id: string; quantity: string; damaged: string; refused: string }
export interface DeliveryEvent { unit_ids?: string[]; followup_id?: string; followup_complete?: boolean; resolution?: string; corrected_kind?: string; file_ids?: string[]; request_id: string; leg_id: string; kind: string; recipient: string; occurred_at: string; reason: string; lines: ReceiptLine[] }
export interface Assessment { blocked: boolean; manual_required: boolean; coverage: string; has_dg: boolean; checks: Record<string, unknown>; trip: Record<string, unknown> }
export interface Delivery {
  id: string; name: string; version: number; status: State; legs: Leg[]; allocations: Allocation[];
  sources: Record<string, Source>; events: DeliveryEvent[]; files: DeliveryFile[];
  unpack_legs?: string[];
  packing_units?: Record<string, PackingUnit[]>;
  cargo_units?: Record<string, { id: string; code: string; name: string; released: boolean }[]>;
  legacy_consignments?: { name: string; shipment_id?: number }[];
  receipt_totals?: Record<string, Record<string, Omit<ReceiptLine, "allocation_id">>>;
  followup?: { parent_id: string; kind: string };
  can_plan: boolean; can_review: boolean;
  assignments: { id: string; role: string; leg_id: string; shipment_ids: number[] }[];
  history?: { at: string; actor: number; action: string }[];
}
export interface DeliveryInput { name: string; version?: number; legs: Leg[]; allocations: Allocation[] }
export interface Balances { goods: { id: string; description: string; unit: string; quantity: string; reserved: string; available: string; received: string; returned: string }[]; deliveries: { id: string; name: string; status: State }[] }
export interface Operations { states: Record<string, number>; rows: { delivery_id: string; delivery: string; shipment: string; goods: string; unit: string; movement: string; quantity: string; damaged: string; refused: string }[] }
export interface Grant { id: string; user_id: number; leg_id: string; role: string; shipment_ids: number[]; expires_at: string; revoked: boolean }
const base = "/deliveries/v1";
const post = <T>(path: string, body: unknown, method = "POST") => apiRequest<T>(base + path, { method, body: JSON.stringify(body) });
export const deliveries = {
  balances: (id: number) => apiRequest<Balances>(`${base}/sources/${id}/balances`),
  operations: (from = "", to = "") => apiRequest<Operations>(`${base}/operations?${new URLSearchParams({ ...(from ? { date_from: from } : {}), ...(to ? { date_to: to } : {}) })}`),
  import: async (file: File) => {
    const body = new FormData(); body.append("file", file);
    const response = await fetch(`/api${base}/import`, { method: "POST", credentials: "include", body });
    if (!response.ok) { const result = await response.json(); throw new Error(describeDetail(result.detail)); }
    return response.json() as Promise<Delivery>;
  },
  list: (query = "") => apiRequest<{ items: Pick<Delivery, "id" | "name" | "status" | "version">[]; total: number; can_plan: boolean }>(base + query),
  get: (id: string) => apiRequest<Delivery>(`${base}/${id}`),
  create: (input: DeliveryInput) => post<Delivery>("", input),
  save: (id: string, input: DeliveryInput) => post<Delivery>(`/${id}`, input, "PUT"),
  source: (id: number) => apiRequest<{ id: number; reference: string; goods: Goods[]; packing_units?: PackingUnit[]; consignment: Record<string, unknown> }>(`${base}/sources/${id}`),
  action: (id: string, leg: string, version: number, action: string, reason: string, language = "en") => post<Delivery>(`/${id}/legs/${leg}/action`, { version, action, reason, language: language.slice(0, 2) }),
  assessment: (id: string, leg: string, language = "en") => apiRequest<Assessment>(`${base}/${id}/legs/${leg}/assessment?language=${encodeURIComponent(language.slice(0, 2))}`),
  review: (id: string, leg: string, version: number, reason: string, document_ids: string[], language = "en") => post<Delivery>(`/${id}/legs/${leg}/review`, { version, reason, document_ids, language: language.slice(0, 2) }),
  unload: (id: string, leg: string, body: unknown) => post<Delivery>(`/${id}/legs/${leg}/unloading`, body),
  event: (id: string, leg: string, body: unknown) => post<Delivery>(`/${id}/legs/${leg}/events`, body),
  issue: (id: string, leg: string, body: unknown) => post<Delivery>(`/${id}/legs/${leg}/documents`, body),
  mail: (id: string, body: unknown) => post<{ ok: boolean }>(`/${id}/bundle/mail`, body),
  bundle: async (id: string, version: number, file_ids: string[]) => {
    const response = await fetch(`/api${base}/${id}/bundle`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ version, file_ids }) });
    if (!response.ok) { const result = await response.json(); throw new Error(describeDetail(result.detail)); }
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a"); link.href = url; link.download = "delivery-documents.zip";
    document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
  grants: (id: string) => apiRequest<Grant[]>(`${base}/${id}/grants`),
  invite: (id: string, body: unknown) => post<{ id: string }>(`/${id}/grants`, body),
  revoke: (id: string, grant: string) => post(`/${id}/grants/${grant}`, {}, "DELETE"),
  convert: (id: number) => post<Delivery>(`/from-trip/${id}`, {}),
  account: (id: number) => apiRequest<{ roles: string[]; modes: Mode[] }>(`${base}/accounts/${id}`),
  saveAccount: (id: number, roles: string[], modes: Mode[]) => post(`${"/accounts/"}${id}`, { roles, modes }, "PUT"),
  upload: async (id: string, leg: string, version: number, kind: string, shipmentIds: number[], file: File): Promise<Delivery> => {
    const body = new FormData();
    body.append("version", String(version)); body.append("kind", kind); body.append("shipment_ids", JSON.stringify(shipmentIds)); body.append("file", file);
    const response = await fetch(`/api${base}/${id}/legs/${leg}/files`, { method: "POST", credentials: "include", body });
    if (!response.ok) { const result = await response.json(); throw new Error(describeDetail(result.detail)); }
    return response.json();
  },
};

export const newLeg = (): Leg => ({ id: crypto.randomUUID(), mode: "road", origin: "", destination: "", carrier: "", vehicle: "", reference: "", planned_start: null, planned_end: null, max_mass_tonnes: null, equipment_ids: [], status: "draft" });
export function inputOf(record: DeliveryInput): DeliveryInput {
  return { name: record.name, version: record.version, allocations: record.allocations,
    legs: record.legs.map(({ id, mode, origin, destination, carrier, vehicle, reference, planned_start, planned_end, max_mass_tonnes, equipment_ids, document_values, load_unit_id }) =>
      ({ id, mode, origin, destination, carrier, vehicle, reference, planned_start, planned_end, max_mass_tonnes, equipment_ids, load_unit_id: load_unit_id || null, document_values: document_values || {} })) };
}
