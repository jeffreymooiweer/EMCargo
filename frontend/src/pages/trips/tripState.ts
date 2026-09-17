import type { TripConsignment, TripResult } from "../../api/client";

export function readMass(value: string): number | null | undefined {
  if (!value.trim()) return null;
  if (!/^\d+(?:[.,]\d+)?$/.test(value.trim())) return undefined;
  const mass = Number(value.trim().replace(",", "."));
  return Number.isFinite(mass) && mass > 0 && mass <= 200 ? mass : undefined;
}

export function profilesFor(consignments: TripConsignment[]): string[] {
  return [...new Set(consignments.flatMap(c => c.profiles ?? []))].sort();
}

export function productCount(consignment: TripConsignment): number {
  return consignment.entries.reduce((total, entry) => total + (Array.isArray(entry.products) ? entry.products.length : 0), 0);
}

/** Keep the complete entries. Partial imports must never become reassuring empty loads. */
export function readConsignment(value: unknown, fallback: string, shipmentId?: number): TripConsignment {
  if (!value || typeof value !== "object") throw new Error("invalid");
  const payload = value as Record<string, unknown>;
  // The exporter omits empty DG entries and regulations. Recognise an
  // ordinary load only when every included goods row explicitly confirms it.
  // A missing declaration without those facts must still be rejected.
  const goods = payload.goods;
  const ordinary = Array.isArray(goods) && goods.length > 0
    && goods.every(line => line && typeof line === "object" && !Array.isArray(line)
      && (line.include === false || (line.dangerous_goods === false
        && Array.isArray(line.detected_un_numbers) && line.detected_un_numbers.length === 0)));
  const entries = payload.dangerous_goods === undefined && ordinary ? [] : payload.dangerous_goods;
  const regulations = payload.regulations === undefined && ordinary ? [] : payload.regulations;
  if (payload.format !== "emcargo.shipment" || !Array.isArray(entries)
      || !Array.isArray(regulations) || !payload.consignment || typeof payload.consignment !== "object") throw new Error("invalid");
  if (entries.some(entry => !entry || typeof entry !== "object" || !Array.isArray(entry.products)
      || !entry.products.length || entry.products.some((product: unknown) => !product || typeof product !== "object" || Array.isArray(product)))) throw new Error("invalid");
  const profiles = regulations.map(profile => String(profile).toUpperCase()).map(profile => profile === "IATA" ? "IATA_DGR" : profile);
  if (profiles.some(profile => !["ADR", "RID", "ADN", "IMDG", "IATA_DGR"].includes(profile))) throw new Error("invalid");
  const values = payload.consignment as Record<string, unknown>;
  const name = values.reference || values.shipment_reference || values.consignor_name || fallback.replace(/\.json$/i, "");
  return {
    name: String(name).slice(0, 120), entries, profiles, shipment_id: shipmentId ?? null,
    route_label: [values.consignor_name, values.consignee_name].filter(Boolean).join(" → ").slice(0, 500),
  };
}

/** Source ids deduplicate history; content deduplicates exports and history/file overlap. */
export function sameConsignment(a: TripConsignment, b: TripConsignment): boolean {
  return !!(a.shipment_id && a.shipment_id === b.shipment_id)
    || JSON.stringify([a.name, a.entries, a.profiles, a.route_label]) === JSON.stringify([b.name, b.entries, b.profiles, b.route_label]);
}

export type AssessmentTone = "neutral" | "complete" | "attention" | "incomplete" | "blocked";

export function assessmentTone(result: TripResult, consignments: TripConsignment[]): AssessmentTone {
  const findings = [...(result.mixed_loading ?? []), ...(result.lq_eq?.warnings ?? [])];
  const points = result.adr_points;
  if (points.forbidden_products?.length || findings.some(f => f.severity === "error")) return "blocked";
  if (!consignments.some(c => c.entries.length)) return "neutral";
  if (profilesFor(consignments).some(profile => profile !== "ADR")) return "incomplete";
  if (points.status === "incomplete" || points.incomplete_products?.length || result.lq_eq?.status === "incomplete"
      || !["exempt_possible", "above_threshold", "not_exempt", "not_available_for_mode"].includes(points.status)
      || ((result.lq_marking?.lq_gross_kg ?? 0) > 0 && result.lq_marking.required === null)) return "incomplete";
  if (points.status !== "exempt_possible" || points.total_points > points.threshold || result.exemption_lost
      || findings.some(f => f.severity !== "info") || result.lq_marking?.required) return "attention";
  return "complete";
}
