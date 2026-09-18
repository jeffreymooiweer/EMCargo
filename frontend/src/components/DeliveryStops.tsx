import { useTranslation } from "react-i18next";
import type { Stop } from "../api/deliveries";
import { emptyParty } from "../wizard/routing";
import { stopLabel } from "../utils/deliveryRouting";

export default function DeliveryStops({ stops, onChange, disabled }: { stops: Stop[]; onChange: (stops: Stop[]) => void; disabled: boolean }) {
  const { t } = useTranslation();
  const move = (i: number, offset: number) => { const next = [...stops]; [next[i], next[i + offset]] = [next[i + offset], next[i]]; onChange(next); };
  return <fieldset disabled={disabled} className="space-y-3"><legend>{t("routing.stops")}</legend><p>{t("routing.routeHint")}</p>
    {stops.map((stop, i) => <div key={stop.id} className="delivery-stop-card space-y-3 rounded-xl border p-4"><strong>{i + 1}. {stop.kind === "transfer" ? t("deliveries.leg") : t(`routing.${stop.kind}`)}</strong>
      <details open={stop.kind === "transfer" && !stop.name}><summary>{stopLabel(stop) || t("routing.address")}</summary><div className="delivery-form-grid mt-3">{(["name", "address", "country", "contact"] as const).map(key => <label key={key}>{t(`routing.${key}`)}<input value={stop[key]} onChange={e => onChange(stops.map(s => s.id === stop.id ? { ...s, [key]: e.target.value } : s))} /></label>)}</div>
      {stop.original && <p>{t("routing.original")}: {stopLabel({ ...stop, ...stop.original })}</p>}
      {stop.kind !== "transfer" && <label>{t("routing.override")}<input value={stop.override_reason || ""} onChange={e => onChange(stops.map(s => s.id === stop.id ? { ...s, override_reason: e.target.value } : s))} /></label>}
      </details><div className="delivery-actions"><button type="button" className="action-secondary" disabled={i === 0} onClick={() => move(i, -1)}>{t("routing.up")}</button><button type="button" className="action-secondary" disabled={i === stops.length - 1} onClick={() => move(i, 1)}>{t("routing.down")}</button>{stop.kind === "transfer" && <button type="button" className="action-secondary" onClick={() => onChange(stops.filter(s => s.id !== stop.id))}>{t("routing.remove")}</button>}</div>
    </div>)}
    <button type="button" className="action-secondary" onClick={() => onChange([...stops.slice(0, -1), { ...emptyParty(), id: crypto.randomUUID(), kind: "transfer", override_reason: "" }, ...stops.slice(-1)])}>+ {t("deliveries.addLeg")}</button>
  </fieldset>;
}
