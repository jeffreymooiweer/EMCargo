"""Keep declarations attached to whole source lines; never scale DG quantities."""
import copy
from collections import defaultdict
from decimal import Decimal

from app.core.messages import error


def selected_entries(value, part, shipment_id):
    from app.services import deliveries as d
    export = value["sources"][str(shipment_id)]["export"]
    if export.get("routing"):
        from app.services.delivery_routing import distributions
        ds = distributions(export)
        result = []
        for a in d.selected(value, part["id"]):
            if a["shipment_id"] != shipment_id:
                continue
            distribution = ds.get(a.get("source_distribution_id"))
            if not distribution:
                raise error(422, "routing.references")
            goods = d.source_goods(export)[a["goods_id"]]
            entries = distribution.get("dangerous_goods") or [e for e in export.get("dangerous_goods", []) if str(e.get("line_id")) == str(goods.get("line_id"))]
            if entries and d.decimal(a["quantity"]) != d.decimal(distribution["quantity"]):
                raise error(422, "routing.dg_split")
            result.extend(copy.deepcopy(entries))
        return result
    entries = export.get("dangerous_goods") or []
    goods = d.source_goods(export)
    quantities = defaultdict(Decimal)
    for allocation in d.selected(value, part["id"]):
        if allocation["shipment_id"] == shipment_id:
            quantities[allocation["goods_id"]] += d.decimal(allocation["quantity"])
    flagged = {gid for gid, g in goods.items() if g.get("dangerous_goods") or g.get("un_number") or g.get("is_dangerous") or g.get("detected_un_numbers")}
    if not entries:
        if flagged & set(quantities):
            raise error(422, "delivery.dg_split")
        return []
    if set(quantities) == set(goods) and all(quantities[g] == d.decimal(goods[g]["quantity"]) for g in goods):
        return copy.deepcopy(entries)
    mapped, result = set(), []
    for entry in entries:
        matches = [gid for gid, line in goods.items() if entry.get("line_id") is not None and str(line.get("line_id")) == str(entry["line_id"])]
        if len(matches) != 1:
            raise error(422, "delivery.dg_split")
        gid = matches[0]
        mapped.add(gid)
        if gid not in quantities:
            continue
        if quantities[gid] != d.decimal(goods[gid]["quantity"]):
            raise error(422, "delivery.dg_split")
        result.append(copy.deepcopy(entry))
    if (flagged & set(quantities)) - mapped:
        raise error(422, "delivery.dg_split")
    return result
