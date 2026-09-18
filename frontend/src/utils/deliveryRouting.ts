import { newLeg, type DeliveryInput, type Source, type Stop } from "../api/deliveries";
export const stopLabel = (point: Stop) => [point.name, point.address, point.country].filter(Boolean).join(", ");
export function routeStops<T extends DeliveryInput & { sources: Record<string, Source> }>(draft: T, stops: Stop[]): T {
  const legs = stops.slice(0, -1).map((stop, i) => {
    const next = stops[i + 1];
    const previous = draft.legs.find(p => p.origin_stop_id === stop.id && p.destination_stop_id === next.id);
    return { ...(previous || newLeg()), origin_stop_id: stop.id, destination_stop_id: next.id, origin: stopLabel(stop), destination: stopLabel(next) };
  });
  const allocations = draft.allocations.map(a => {
    const source = draft.sources[String(a.shipment_id)];
    const distribution = (source.routing || source.export?.routing)?.distributions.find(d => d.id === a.source_distribution_id);
    if (!distribution) return a;
    const start = stops.findIndex(s => s.shipment_id === a.shipment_id && s.location_id === distribution.pickup_id);
    const end = stops.findIndex(s => s.shipment_id === a.shipment_id && s.location_id === distribution.delivery_id);
    return { ...a, leg_ids: start >= 0 && end > start ? legs.slice(start, end).map(l => l.id) : [] };
  });
  return { ...draft, stops, legs, allocations };
}
