import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate, useParams, useSearchParams } from "react-router";
import { useTranslation } from "react-i18next";
import { api, type TripDetail, type User } from "../api/client";
import { deliveries } from "../api/deliveries";
import { canOversee } from "../permissions";
import { usePreferences } from "../settings/preferences";
import TripLibrary from "./trips/TripLibrary";
import TripAssessment from "./trips/TripAssessment";
import "./trips/trips.css";
import "./deliveries.css";

export function LegacyTripRoute() {
  const { id } = useParams();
  return <Navigate to={`/trips?trip=${encodeURIComponent(id ?? "")}`} replace />;
}

/** Historical calculations remain as saved; conversion starts an empty concept. */
export default function TripsPage({ user }: { user?: User | null }) {
  const { t } = useTranslation();
  const { publicSettings } = usePreferences();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const id = Number(params.get("trip")) || null;
  const [record, setRecord] = useState<TripDetail | null>(null);
  const [failure, setFailure] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let cancelled = false;
    setRecord(null); setFailure("");
    if (!id || !publicSettings?.history_enabled) return;
    setBusy(true);
    api.trip(id).then(value => { if (!cancelled) setRecord(value); })
      .catch(error => { if (!cancelled) setFailure(error.message); })
      .finally(() => { if (!cancelled) setBusy(false); });
    return () => { cancelled = true; };
  }, [id, publicSettings?.history_enabled]);
  async function convert() {
    if (!id || busy) return;
    setBusy(true); setFailure("");
    try { const draft = await deliveries.convert(id); navigate(`/deliveries/${draft.id}`); }
    catch (error) { setFailure(error instanceof Error ? error.message : String(error)); }
    finally { setBusy(false); }
  }
  return <div className="deliveries-page">
    <header className="page-heading"><h2>{t("deliveries.legacy")}</h2><Link to="/deliveries">{t("deliveries.title")}</Link></header>
    <p className="delivery-callout">{t("deliveries.legacyHint")}</p>
    {failure && <p className="delivery-error" role="alert">{failure}</p>}
    {!publicSettings?.history_enabled ? <p>{t("deliveries.noHistory")}</p> : <>
      <TripLibrary activeId={id} revision={0} oversee={!!user && canOversee(user)} disabled={busy} onSelect={value => setParams({ trip: String(value) })} />
      {record && <section className="surface delivery-panel">
        <h3>{record.name}</h3><p>{new Date(record.updated_at).toLocaleString()}</p>
        <ul>{record.consignments.map((c, i) => <li key={i}>{c.name}</li>)}</ul>
        <TripAssessment result={record.result} consignments={record.consignments} pending={false} failed={false} invalidMass={false} savedAt={record.updated_at} editions={record.editions} onRetry={() => {}} readOnly />
        <button className="action-primary" disabled={busy} onClick={convert}>{t("deliveries.convertLegacy")}</button>
      </section>}
    </>}
  </div>;
}
