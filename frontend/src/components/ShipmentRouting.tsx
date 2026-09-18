import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type Address, type LineItem, type DgEntry, type DgProduct } from "../api/client";
import type { CargoManifest } from "../api/cargo";
import { stableJson, dgConfirmation, emptyParty, goodsId, type Routing, type Distribution, type Location } from "../wizard/routing";

const input = "w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent p-2 min-h-[44px]";
export default function ShipmentRouting({ value, onChange, lines, cargo, entries = [], review = false }: {
  value: Routing; onChange: (routing: Routing) => void; lines: LineItem[]; cargo?: CargoManifest; entries?: DgEntry[]; review?: boolean;
}) {
  const { t } = useTranslation();
  const [addresses, setAddresses] = useState<Address[]>([]);
  useEffect(() => { api.addresses().then(setAddresses).catch(() => {}); }, []);
  const updateLocation = (id: string, patch: Partial<Location>) => onChange({ ...value, locations: value.locations.map(p => p.id === id ? { ...p, ...patch } : p) });
  const update = (id: string, patch: Partial<Distribution>) => onChange({ ...value, distributions: value.distributions.map(a => a.id === id ? { ...a, ...patch, dg_confirmation: null } : a) });
  const goods = lines.map((line, i) => ({ line, id: goodsId(line, i) })).filter(({ line }) => line.include);
  const locationLabel = (id: string) => { const p = value.locations.find(p => p.id === id); return p ? `${p.name} · ${p.address}` : t("routing.choose"); };
  return <div className="space-y-5">
    <p>{t("routing.intro")}</p>
    {!review && (["pickup", "delivery"] as const).map(kind => <section key={kind} className="surface p-4 space-y-3">
      <h3 className="font-semibold">{t(`routing.${kind}`)}</h3>
      {value.locations.filter(p => p.kind === kind).map((p, index) => <fieldset key={p.id} className="border rounded-xl p-3 space-y-3">
        <legend>{t(`routing.${kind}`)} {index + 1}</legend>
        <label className="block">{t("routing.addressBook")}<select className={input} value="" onChange={e => { const a = addresses.find(a => String(a.id) === e.target.value); if (a) updateLocation(p.id, { name: a.name, address: a.address, contact: a.contact, party: { ...p.party, name: a.name, address: a.address, contact: a.contact } }); }}><option value="">{t("routing.choose")}</option>{addresses.map(a => <option key={a.id} value={a.id}>{a.name} · {a.address}</option>)}</select></label>
        <div className="grid gap-3 sm:grid-cols-2">{(["name", "address", "country", "contact"] as const).map(key => <label key={key}>{t(`routing.${key}`)}<input className={input} value={p[key]} onChange={e => updateLocation(p.id, { [key]: e.target.value, party: p.party[key] === p[key] ? { ...p.party, [key]: e.target.value } : p.party })} /></label>)}</div>
        <details><summary>{t("routing.legalParty")}</summary><div className="grid gap-3 sm:grid-cols-2 mt-3">{(["name", "address", "country", "contact"] as const).map(key => <label key={key}>{t(`routing.${key}`)}<input className={input} value={p.party[key]} onChange={e => updateLocation(p.id, { party: { ...p.party, [key]: e.target.value } })} /></label>)}</div></details>
        <button type="button" className="action-secondary" onClick={() => onChange({ ...value, locations: value.locations.filter(point => point.id !== p.id) })}>{t("routing.remove")}</button>
      </fieldset>)}
      <button type="button" className="action-secondary" onClick={() => onChange({ ...value, locations: [...value.locations, { ...emptyParty(), party: emptyParty(), id: crypto.randomUUID(), kind }] })}>+ {t(`routing.${kind}`)}</button>
    </section>)}
    <section className="surface p-4 space-y-4"><h3 className="font-semibold">{t("routing.distribution")}</h3>
      {goods.map(({ line, id }) => {
        const allocations = value.distributions.filter(a => a.goods_id === id);
        const total = allocations.reduce((sum, a) => sum + Number(a.quantity || 0), 0);
        const dg = entries.filter(e => String(e.line_id) === String(line.line_id));
        return <fieldset key={id} className="border rounded-xl p-3 space-y-3"><legend>{line.description}</legend>
          <p className={Math.abs(total - Number(line.quantity)) > 0.0000001 ? "text-amber-700 dark:text-amber-300" : ""}>{t("routing.distributed", { total, quantity: line.quantity, unit: line.unit })}</p>
          {allocations.map(a => <div key={a.id} className="space-y-3 border-t pt-3">
            {review ? <p>{a.quantity} {line.unit}: {locationLabel(a.pickup_id)} → {locationLabel(a.delivery_id)}</p> : <>
              <div className="grid gap-3 sm:grid-cols-3"><label>{t("routing.quantity")}<input className={input} type="number" min="0.000001" step="any" value={a.quantity} onChange={e => update(a.id, { quantity: e.target.value || "0" })} /></label>
                {(["pickup", "delivery"] as const).map(kind => <label key={kind}>{t(`routing.${kind}`)}<select className={input} value={a[`${kind}_id`]} onChange={e => update(a.id, { [`${kind}_id`]: e.target.value })}><option value="">{t("routing.choose")}</option>{value.locations.filter(p => p.kind === kind).map(p => <option key={p.id} value={p.id}>{p.name} · {p.address}</option>)}</select></label>)}</div>
              {cargo?.units.filter(u => !u.parent_id).map(u => <label key={u.id} className="block"><input type="checkbox" checked={a.unit_ids.includes(u.id)} onChange={e => update(a.id, { unit_ids: e.target.checked ? [...a.unit_ids, u.id] : a.unit_ids.filter(id => id !== u.id) })} /> {u.code} · {u.name}</label>)}
              <button type="button" className="action-secondary" onClick={() => onChange({ ...value, distributions: value.distributions.filter(item => item.id !== a.id) })}>{t("routing.remove")}</button>
            </>}
            {review && dg.length > 0 && allocations.length > 1 && <div className="space-y-2"><p>{t("routing.dgSplit")}</p>
              {!a.dangerous_goods.length ? <button className="action-secondary" type="button" onClick={() => update(a.id, { dangerous_goods: dg.map(e => ({ ...e, products: e.products.map(p => ({ ...p, quantity_packages: "", net_mass_liters_per_package: "", adr_total_quantity: "", gross_mass_per_package: "", net_explosive_mass: "", q_net_quantity: "" })) })) })}>{t("routing.declare")}</button> : a.dangerous_goods.map((entry, ei) => entry.products.map((product, pi) => <div key={`${ei}-${pi}`} className="grid gap-2 sm:grid-cols-2"><strong className="sm:col-span-2">UN {product.un_number} · {product.proper_shipping_name}</strong>{(["quantity_packages", "type_of_package", "net_mass_liters_per_package", "gross_mass_per_package", "adr_total_quantity", "net_explosive_mass"] as const).map(key => <label key={key}>{t(`routing.dgFields.${key}`)}<input className={input} value={product[key] || ""} onChange={e => update(a.id, { dangerous_goods: a.dangerous_goods.map((item, i) => i === ei ? { ...item, products: item.products.map((p, j) => j === pi ? { ...p, [key]: e.target.value } as DgProduct : p) } : item) })} /></label>)}</div>))}
              {a.dangerous_goods.length > 0 && <button type="button" className="action-secondary" onClick={() => onChange({ ...value, distributions: value.distributions.map(item => item.id === a.id ? { ...item, dg_confirmation: dgConfirmation(item, lines, entries, value.locations) } : item) })}>{t(a.dg_confirmation && stableJson(a.dg_confirmation) === stableJson(dgConfirmation(a, lines, entries, value.locations)) ? "routing.confirmed" : "routing.confirm")}</button>}
            </div>}
          </div>)}
          {!review && <button type="button" className="action-secondary" onClick={() => onChange({ ...value, distributions: [...value.distributions, { id: crypto.randomUUID(), goods_id: id, quantity: String(Math.max(0, Number(line.quantity) - total)), pickup_id: value.locations.find(p => p.kind === "pickup")?.id || "", delivery_id: value.locations.find(p => p.kind === "delivery")?.id || "", unit_ids: [], dangerous_goods: [], dg_confirmation: null }] })}>+ {t("routing.distribution")}</button>}
        </fieldset>;
      })}
    </section>
  </div>;
}
