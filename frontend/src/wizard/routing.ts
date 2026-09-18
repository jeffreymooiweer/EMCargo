import type { DgEntry, LineItem } from "../api/client";

export interface Party { name: string; address: string; country: string; contact: string }
export interface Location extends Party { id: string; kind: "pickup" | "delivery"; party: Party }
export interface Distribution { id: string; goods_id: string; quantity: string; pickup_id: string; delivery_id: string; unit_ids: string[]; dangerous_goods: DgEntry[]; dg_confirmation: Record<string, unknown> | null; available?: string }
export interface Routing { version: 1; locations: Location[]; distributions: Distribution[] }
export const emptyRouting = (): Routing => ({ version: 1, locations: [], distributions: [] });
export const emptyParty = (): Party => ({ name: "", address: "", country: "", contact: "" });
export const goodsId = (line: LineItem, index: number) => String(line.cargo_goods_id ?? line.line_id ?? `line-${index}`);
export function routingFromLegacy(values: Record<string, string>, lines: LineItem[]): Routing {
  const routing = emptyRouting();
  for (const [kind, prefix, field] of [["pickup", "consignor", "loading_point"], ["delivery", "consignee", "delivery_point"]] as const) {
    const party = Object.fromEntries(Object.keys(emptyParty()).map(key => [key, values[`${prefix}_${key}`] || ""])) as unknown as Party;
    const address = values[field] || party.address;
    if (party.name || address) routing.locations.push({ ...party, address, party, kind, id: `legacy-${kind}` });
  }
  if (routing.locations.length === 2) routing.distributions = lines.filter(l => l.include).map((line, i) => ({ id: crypto.randomUUID(), goods_id: goodsId(line, i), quantity: String(line.quantity), pickup_id: "legacy-pickup", delivery_id: "legacy-delivery", unit_ids: [], dangerous_goods: [], dg_confirmation: null }));
  return routing;
}
export function dgConfirmation(distribution: Distribution, lines: LineItem[], entries: DgEntry[], locations: Location[] = []) {
  const goods = lines.find((line, i) => goodsId(line, i) === distribution.goods_id);
  return { goods, entries: entries.filter(e => String(e.line_id) === String(goods?.line_id)), quantity: distribution.quantity,
    pickup_id: distribution.pickup_id, delivery_id: distribution.delivery_id, locations: locations.filter(p => p.id === distribution.pickup_id || p.id === distribution.delivery_id), unit_ids: distribution.unit_ids, declarations: distribution.dangerous_goods };
}

export const stableJson = (value: unknown): string => JSON.stringify(value, (_key, item) => item && typeof item === "object" && !Array.isArray(item) ? Object.fromEntries(Object.entries(item).sort(([a], [b]) => a.localeCompare(b))) : item);
