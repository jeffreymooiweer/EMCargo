import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { apiRequest, describeDetail, type ShipmentIn } from "../api/client";
import { modes, newLeg, type Assessment, type Leg, type Mode } from "../api/deliveries";
import "../pages/deliveries.css";

/** All state stays in this page; the server returns a portable issued archive. */
export default function TemporaryDelivery({ shipment }: { shipment: ShipmentIn }) {
  const { t, i18n } = useTranslation();
  const [part, setPart] = useState<Leg>(() => ({ ...newLeg(),
    mode: modes.includes(shipment.modality as Mode) ? shipment.modality as Mode : "road",
    origin: String(shipment.values.loading_point || shipment.values.place_of_receipt || ""),
    destination: String(shipment.values.discharge_point || shipment.values.place_of_delivery || ""),
    carrier: String(shipment.values.carrier_name || "") }));
  const [result, setResult] = useState<(Assessment & { can_review: boolean }) | null>(null);
  const [reason, setReason] = useState("");
  const [token, setToken] = useState("");
  const [failure, setFailure] = useState("");
  const [busy, setBusy] = useState(false);
  const { status: _status, ...planning } = part;
  const payload = { shipment, leg: planning, document_keys: shipment.documents, language: i18n.language.slice(0, 2) };
  const binding = JSON.stringify(payload);
  const currentBinding = useRef(binding); currentBinding.current = binding;
  useEffect(() => { setResult(null); setToken(""); setFailure(""); }, [binding]);
  async function run(action: "assessment" | "review" | "documents") {
    if (busy) return;
    setBusy(true); setFailure("");
    try {
      const body = JSON.stringify({ ...payload, reason, review_token: token });
      const options = { method: "POST", body };
      if (action === "assessment") { const value = await apiRequest<Assessment & { can_review: boolean }>("/temporary-deliveries/v1/assessment", options); if (currentBinding.current === binding) setResult(value); }
      if (action === "review") { const value = await apiRequest<{ token: string }>("/temporary-deliveries/v1/review", options); if (currentBinding.current === binding) setToken(value.token); }
      if (action === "documents") {
        const response = await fetch("/api/temporary-deliveries/v1/documents", { ...options, credentials: "include", headers: { "Content-Type": "application/json" } });
        if (!response.ok) { const detail = await response.json(); throw new Error(describeDetail(detail.detail)); }
        const archive = await response.blob();
        if (currentBinding.current !== binding) return;
        const url = URL.createObjectURL(archive);
        const link = document.createElement("a"); link.href = url; link.download = "temporary-delivery.zip";
        document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
    } catch (error) { setFailure(error instanceof Error ? error.message : String(error)); }
    finally { setBusy(false); }
  }
  const change = (update: Partial<Leg>) => setPart(old => ({ ...old, ...update }));
  return <details className="surface delivery-panel"><summary>{t("deliveries.temporary")}</summary><div className="deliveries-page">
    <p className="delivery-callout">{t("deliveries.temporaryHint")}</p>
    {failure && <p className="delivery-error" role="alert">{failure}</p>}
    <fieldset disabled={busy} className="delivery-form-grid">
      <label>{t("deliveries.mode")}<select value={part.mode} onChange={e => change({ mode: e.target.value as Mode })}>{modes.map(mode => <option key={mode} value={mode}>{t(`deliveries.modes.${mode}`)}</option>)}</select></label>
      {(["origin", "destination", "carrier", "vehicle", "reference"] as const).map(key => <label key={key}>{t(`deliveries.${key}`)}<input value={part[key]} onChange={e => change({ [key]: e.target.value })} /></label>)}
      <label>{t("deliveries.start")}<input type="datetime-local" onChange={e => change({ planned_start: e.target.value ? new Date(e.target.value).toISOString() : null })} /></label>
      <label>{t("deliveries.maxMass")}<input type="number" min="0.000001" step="any" value={part.max_mass_tonnes || ""} onChange={e => change({ max_mass_tonnes: e.target.value || null })} /></label>
    </fieldset>
    <button className="action-secondary" disabled={busy || !shipment.documents.length} onClick={() => run("assessment")}>{t("deliveries.assess")}</button>
    {result && <p className="delivery-callout">{t(result.blocked ? "deliveries.blocked" : result.manual_required ? "deliveries.partialCoverage" : "deliveries.ordinary")}</p>}
    {result?.manual_required && result.can_review && <><label>{t("deliveries.reason")}<textarea value={reason} onChange={e => { setReason(e.target.value); setToken(""); }} /></label><button className="action-secondary" disabled={busy || reason.trim().length < 10} onClick={() => run("review")}>{t("deliveries.review")}</button></>}
    <button className="action-primary" disabled={busy || !result || result.blocked || (result.manual_required && !token)} onClick={() => run("documents")}>{t("deliveries.temporaryIssue")}</button>
  </div></details>;
}
