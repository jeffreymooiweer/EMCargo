import type { LineItem } from "../api/client";
import { cloneCargo, emptyCargo, readCargo } from "../utils/cargo";
import { routingFromLegacy } from "./routing";
import { readSnapshot, SNAPSHOT_VERSION, type WizardSnapshot } from "./snapshot";

/** Import source facts into a new private draft, never an approval or execution. */
export function readShipmentFile(raw: unknown): WizardSnapshot | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const data = raw as Record<string, any>;
  let snapshot: WizardSnapshot | null;
  if (data.format === "emcargo.shipment") {
    if (!["1.0", "2.0", "2.1", "3.0"].includes(data.format_version) || !Array.isArray(data.goods)) return null;
    const lines: LineItem[] = data.goods.map((line: LineItem, i: number) => ({ ...line,
      line_id: line.line_id ?? i + 1, cargo_goods_id: line.cargo_goods_id ?? line.line_id ?? i + 1,
      description: String(line.description || ""), include: line.include !== false, messages: line.messages || [] }));
    const values = data.consignment || {};
    snapshot = readSnapshot({ version: SNAPSHOT_VERSION, modality: "preparation", stepKey: "details",
      docValues: values, cargo: data.cargo, routing: data.routing || routingFromLegacy(values, lines),
      dgEntries: data.dangerous_goods || [], draftLines: lines.map(line => ({ ...line, id: line.cargo_goods_id })),
      result: { success: true, lines, errors: [], column_map: {}, totals: {
        total_weight_kg: lines.reduce((n, line) => n + (Number(line.weight_total_kg) || 0), 0),
        total_transport_volume_m3: lines.reduce((n, line) => n + (Number(line.transport_volume_m3) || 0), 0),
      } } });
  } else snapshot = readSnapshot(data);
  if (!snapshot) return null;
  const previous = snapshot.cargo ? readCargo(snapshot.cargo) : emptyCargo();
  if (!previous) return null;
  const cargo = cloneCargo(previous);
  const ids = new Map(previous.units.map((unit, i) => [unit.id, cargo.units[i].id]));
  const routing = snapshot.routing || routingFromLegacy(snapshot.docValues, snapshot.result?.lines || []);
  return { ...snapshot, version: SNAPSHOT_VERSION, modality: "preparation", stepKey: "details",
    cargo, cargoBaseRevision: null, selectedDocs: [], signature: null, docLang: null,
    routing: { ...routing, distributions: routing.distributions.map(item => ({ ...item,
      id: crypto.randomUUID(), unit_ids: item.unit_ids.map(id => ids.get(id)).filter((id): id is string => !!id),
      dg_confirmation: null })) },
  };
}
