import { useTranslation } from "react-i18next";
import type { TripConsignment, TripResult } from "../../api/client";
import { CheckIcon, InfoIcon, RefreshIcon, WarningIcon } from "../../components/icons";
import { assessmentTone, profilesFor } from "./tripState";

interface Props {
  readOnly?: boolean;
  result: TripResult | null;
  consignments: TripConsignment[];
  pending: boolean;
  failed: boolean;
  invalidMass: boolean;
  savedAt?: string;
  editions?: Record<string, unknown>;
  onRetry: () => void;
}

export default function TripAssessment({ result, consignments, pending, failed, invalidMass, savedAt, editions, onRetry, readOnly }: Props) {
  const { t, i18n } = useTranslation();
  const tone = result ? assessmentTone(result, consignments) : "neutral";
  const state = invalidMass ? "invalidMass" : failed ? "failed" : pending ? "checking" : !consignments.length ? "empty" : result ? tone : "checking";
  const Glyph = tone === "blocked" || tone === "attention" || tone === "incomplete" || failed || invalidMass ? WarningIcon : tone === "complete" ? CheckIcon : InfoIcon;
  const points = result?.adr_points;
  const hasDg = consignments.some(c => c.entries.length);
  const otherProfiles = profilesFor(consignments).filter(profile => profile !== "ADR");
  const findings = [...(result?.mixed_loading ?? []), ...(result?.lq_eq?.warnings ?? [])];
  const needsAttention = findings.filter(f => f.severity !== "info");
  const lq = result?.lq_marking;
  const unfinished = (result?.lq_eq?.rows ?? []).flatMap(row => [row.lq, row.eq].filter(check => check?.status === "incomplete").map(check => ({ product: row.product, message: check!.message })));

  return <section className={`trip-assessment trip-tone-${failed || invalidMass ? "incomplete" : result ? tone : "neutral"}`} aria-labelledby="trip-assessment-title" aria-busy={pending}>
    <div className="trip-assessment-heading">
      <span className="trip-assessment-icon">{pending ? <RefreshIcon className="trip-checking" /> : <Glyph />}</span>
      <div role="status" aria-live="polite">
        <h3 id="trip-assessment-title">{t(`tripWorkspace.assessment.${state}`)}</h3>
        {state !== "empty" && state !== "checking" && state !== "neutral" && state !== "invalidMass" && <p>{t(`tripWorkspace.assessment.${state}Hint`)}</p>}
      </div>
      {!readOnly && (failed || savedAt) && <button type="button" className="trip-text-button" onClick={onRetry} disabled={pending || invalidMass}>
        <RefreshIcon />{t("tripWorkspace.recheck")}
      </button>}
    </div>
    {result && !invalidMass && <>
      {savedAt && <p className="trip-snapshot">{t("tripWorkspace.snapshot", { date: new Date(savedAt).toLocaleString(i18n.language, { dateStyle: "medium", timeStyle: "short" }) })}</p>}
      {hasDg && <>
        <div className="trip-check-summary">
          <div><span>{t("tripWorkspace.points")}</span><strong>{points?.total_points?.toLocaleString(i18n.language) ?? "—"}<small> / {points?.threshold ?? 1000}</small></strong></div>
          <div><span>{t("groupage.mixedLoading")}</span><strong className="trip-verdict-label">{t(needsAttention.length ? "tripWorkspace.reviewFindings" : "tripWorkspace.noFindings")}</strong></div>
          <div><span>{t("tripWorkspace.lq")}</span><strong className="trip-verdict-label">{t(unfinished.length ? "tripWorkspace.moreInfo" : (lq?.lq_gross_kg ?? 0) === 0 ? "tripWorkspace.noLq" : lq?.required === null ? "tripWorkspace.moreInfo" : lq?.required ? "tripWorkspace.markRequired" : "tripWorkspace.markNotRequired")}</strong></div>
        </div>
        <div className="trip-findings">
          {!!otherProfiles.length && <p>{t("tripWorkspace.otherProfiles", { profiles: otherProfiles.join(", ") })}</p>}
          {!!points?.forbidden_products?.length && <p>{t("tripWorkspace.forbidden")}: {points.forbidden_products.join(", ")}</p>}
          {!!points?.incomplete_products?.length && <p>{t("tripWorkspace.missingQuantities")}: {points.incomplete_products.join(", ")}</p>}
          {result.exemption_lost && <p>{result.exemption_lost.message}</p>}
          {!result.exemption_lost && (points?.status === "above_threshold" || points?.status === "not_exempt") && <p>{t("tripWorkspace.noExemption")}</p>}
          {points?.mode_note && <p>{points.mode_note}</p>}
          {unfinished.map((finding, index) => <div key={`unfinished-${index}`}><p>{finding.message}</p><p className="trip-muted">{finding.product}</p></div>)}
          {needsAttention.map((finding, index) => <div key={index} className="trip-finding"><p>{finding.message}</p>{finding.products && <p className="trip-muted">{finding.products}</p>}</div>)}
          {(lq?.lq_gross_kg ?? 0) > 0 && (lq?.required !== false) && <p>{lq?.message}</p>}
        </div>
        <details className="trip-details">
          <summary>{t("tripWorkspace.details")}</summary>
          <table><caption className="sr-only">{t("groupage.apartAndTogether")}</caption><thead><tr><th>{t("tripWorkspace.shipment")}</th><th>{t("tripWorkspace.points")}</th><th>{t("tripWorkspace.exemption")}</th></tr></thead>
            <tbody>{result.consignments.map((c, index) => <tr key={index}><td>{c.name}</td><td>{c.points ?? "—"}</td><td>{t(c.exempt === true ? "groupage.exempt" : c.exempt === false ? "groupage.notExempt" : "groupage.incomplete")}</td></tr>)}</tbody>
          </table>
          {lq && <p>{lq.message}</p>}
          {points?.still_required && <p>{points.still_required}</p>}
          {points?.basis_note && <p>{points.basis_note}</p>}
          {findings.filter(f => f.severity === "info").map((f, index) => <p key={index}>{f.message}</p>)}
          {editions && <p>{Object.entries(editions).map(([key, value]) => `${key.toUpperCase()} ${String(value)}`).join(" · ")}</p>}
        </details>
      </>}
    </>}
  </section>;
}
