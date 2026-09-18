import { useEffect, useState } from "react";
import { Link } from "react-router";
import { useTranslation } from "react-i18next";
import { deliveries, type Balances, type Operations } from "../api/deliveries";
import "../pages/deliveries.css";

export default function DeliveryActivity({ shipmentId, compact = false }: { shipmentId?: number; compact?: boolean }) {
  const { t } = useTranslation();
  const [balance, setBalance] = useState<Balances | null>(null);
  const [operations, setOperations] = useState<Operations | null>(null);
  const [failure, setFailure] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  useEffect(() => {
    let active = true;
    setFailure("");
    const work = shipmentId ? deliveries.balances(shipmentId).then(value => { if (active) setBalance(value); })
      : deliveries.operations(from, to).then(value => { if (active) setOperations(value); });
    work.catch(error => { if (active) setFailure(error.message); });
    return () => { active = false; };
  }, [shipmentId, from, to]);
  return <section className="surface delivery-panel">
    <h3>{t(shipmentId ? "deliveries.balances" : "deliveries.operations")}</h3>
    <p>{t(shipmentId ? "deliveries.balanceHint" : "deliveries.operationsHint")}</p>
    {failure && <p className="delivery-error" role="alert">{failure}</p>}
    {balance && <><div className="delivery-table-wrap"><table><thead><tr>{["goods", "quantity", "reserved", "available", "received", "returned"].map(k => <th key={k}>{t(`deliveries.${k}`)}</th>)}</tr></thead><tbody>{balance.goods.map(g => <tr key={g.id}><th>{g.description} ({g.unit})</th>{(["quantity", "reserved", "available", "received", "returned"] as const).map(k => <td key={k}>{g[k]}</td>)}</tr>)}</tbody></table></div>
      <ul>{balance.deliveries.map(d => <li key={d.id}><Link to={`/deliveries/${d.id}`}>{d.name}</Link> · {t(`deliveries.status.${d.status}`)}</li>)}</ul>
      <Link to={`/deliveries/new?shipments=${shipmentId}`}>{t("deliveries.new")}</Link></>}
    {operations && <><div className="delivery-actions">{Object.entries(operations.states).map(([state, count]) => <span className={`delivery-status state-${state}`} key={state}>{t(`deliveries.status.${state}`)}: {count}</span>)}</div>
      {compact ? <Link to="/deliveries">{t("deliveries.title")}</Link> : <>
        <div className="delivery-form-grid"><label>{t("history.from")}<input type="date" value={from} onChange={e => setFrom(e.target.value)} /></label><label>{t("history.to")}<input type="date" value={to} min={from || undefined} onChange={e => setTo(e.target.value)} /></label></div>
        <div className="delivery-table-wrap"><table><thead><tr>{["title", "shipmentId", "goods", "movement", "received", "damaged", "refused"].map(k => <th key={k}>{t(`deliveries.${k}`)}</th>)}</tr></thead><tbody>{operations.rows.map((r, i) => <tr key={i}><td><Link to={`/deliveries/${r.delivery_id}`}>{r.delivery}</Link></td><td>{r.shipment}</td><td>{r.goods} ({r.unit})</td><td>{t(`deliveries.${r.movement === "delivery" ? "title" : r.movement}`)}</td><td>{r.quantity}</td><td>{r.damaged}</td><td>{r.refused}</td></tr>)}</tbody></table></div>
      </>}
    </>}
  </section>;
}
