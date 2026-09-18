import { useTranslation } from "react-i18next";
import type { LineItem } from "../api/client";
import { goodsId, type Routing } from "../wizard/routing";

/** Source locations and declarations remain inspectable outside the editor. */
export default function ShipmentRoutingSummary({ routing, lines }: { routing: Routing; lines: LineItem[] }) {
  const { t } = useTranslation();
  const location = (id: string) => routing.locations.find(p => p.id === id);
  const label = (id: string) => { const p = location(id); return p ? [p.name, p.address, p.country].filter(Boolean).join(", ") : "—"; };
  return <section className="surface p-4 space-y-3">
    <h3 className="font-semibold">{t("routing.distribution")}</h3>
    {routing.distributions.map(item => <div key={item.id} className="border-t pt-3 space-y-2">
      <strong>{lines.find((line, i) => goodsId(line, i) === item.goods_id)?.description || item.goods_id} · {item.quantity}</strong>
      <p>{label(item.pickup_id)} → {label(item.delivery_id)}</p>
      <details><summary>{t("routing.legalParty")}</summary>{[item.pickup_id, item.delivery_id].map(id => <p key={id}>{Object.values(location(id)?.party || {}).filter(Boolean).join(", ")}</p>)}</details>
      {item.dangerous_goods.flatMap(entry => entry.products).map((product, i) => <dl className="review-fields" key={i}>
        <div><dt>UN</dt><dd>{product.un_number} · {product.proper_shipping_name}</dd></div>
        {(["quantity_packages", "type_of_package", "net_mass_liters_per_package", "gross_mass_per_package", "adr_total_quantity", "net_explosive_mass"] as const).map(key => product[key] ? <div key={key}><dt>{t(`routing.dgFields.${key}`)}</dt><dd>{product[key]}</dd></div> : null)}
      </dl>)}
    </div>)}
  </section>;
}
