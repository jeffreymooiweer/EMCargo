import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, ComplianceWarning, DgComplianceResult, DgEntry } from "../api/client";
import { documentLanguage } from "../i18n/language";
import CollapsibleSection, { SummaryChip } from "./CollapsibleSection";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";

interface Props {
  entries: DgEntry[];
  profiles: string[];
}

const STATUS_STYLES: Record<string, string> = {
  exempt_possible: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  above_threshold: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  not_exempt: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  incomplete: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  // Not a failure and not a pass: the exemption is simply not on offer for this
  // mode, so neither green nor red would be honest.
  not_available_for_mode: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
};

// Within the limits is green, outside it amber: a missed exemption is not an
// offence, so red would be too heavy here.
const LQEQ_STATUS_STYLES: Record<string, string> = {
  within_limits: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  not_within: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  not_permitted: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  incomplete: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  no_data: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
};

// The tunnel outcome is not a pass/fail. "Exempt" is the best answer there is —
// 8.6.3.3 takes the goods out of the determination — while "derived" simply
// states which categories are barred, which is information rather than a fault.
const TUNNEL_STATUS_STYLES: Record<string, string> = {
  exempt: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  unrestricted: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  derived: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
  lq_marking_only: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
  incomplete: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  unknown_code: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  not_checked: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
};

export default function DgCompliancePanel({ entries, profiles }: Props) {
  const { t, i18n } = useTranslation();
  const lang = documentLanguage(i18n.language);
  const [result, setResult] = useState<DgComplianceResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Every check gets a sequence number. Two checks can run at once — the user
  // keeps typing while the previous one is still on its way — and then a slow
  // older response can arrive *after* a faster new one. Without this comparison
  // that old outcome overwrites the new one, and the screen shows a result
  // belonging to input from two changes ago.
  const latestRequest = useRef(0);

  const run = useCallback(async () => {
    if (entries.length === 0 || profiles.length === 0) return;
    const sequence = ++latestRequest.current;
    setLoading(true);
    setError("");
    try {
      const outcome = await api.dgCompliance(entries, profiles, lang);
      if (sequence !== latestRequest.current) return;
      setResult(outcome);
    } catch (e) {
      if (sequence !== latestRequest.current) return;
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (sequence === latestRequest.current) setLoading(false);
    }
  }, [entries, profiles, lang]);

  // If the input changes, the previous result is invalid immediately: clear it
  // first (do not leave old green standing) and check again automatically after
  // a short debounce. A stale outcome that lingers while the user changes the
  // substances is more dangerous than briefly having no outcome.
  const entriesSignature = JSON.stringify(entries);
  useEffect(() => {
    setResult(null);
    const timer = window.setTimeout(run, 400);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entriesSignature, profiles.join(",")]);

  if (entries.length === 0 || profiles.length === 0) return null;

  const adr = result?.adr_points;
  const tankAdmission = result?.adr_tank_admission;
  const bulkAdmission = result?.adr_bulk_admission;
  const tankFit = result?.adr_tank_fit;
  const filling = result?.adr_filling_degree;
  const adnAdmission = result?.adn_carriage_admission;
  const adn = result?.adn_exemption;
  const separation = result?.adn_hold_separation;
  const signals = result?.adn_signals;
  const tunnel = result?.adr_tunnel;
  const equipment = result?.adr_equipment;
  const placarding = result?.adr_placarding;
  const adnPlacarding = result?.adn_placarding;
  const ridPlacarding = result?.rid_placarding;
  const imdgPlacarding = result?.imdg_placarding;
  const security = result?.adr_security;
  // An expired rule set comes before all substantive findings: those findings
  // were computed with it.
  const warnings: ComplianceWarning[] = [
    ...(result?.rule_set_warnings ?? []),
    ...(result?.adr_mixed_loading ?? []),
    ...(result?.imdg_segregation ?? []),
    ...(result?.iata_segregation ?? []),
    // What 5.4.1.1.1 adds per regime: the hazard identification number for
    // rail, the confirmation of stabilisation for inland waterway. Both are
    // provisions about the document, so they belong with the findings that
    // travel to it rather than in a card of their own.
    ...(result?.rid_transport_document ?? []),
    ...(result?.adn_stabilisation ?? []),
    // Special provision 274: an N.O.S. entry without its technical name is an
    // incomplete description, and it has to speak before the document does.
    ...(result?.technical_name_findings ?? []),
    ...(result?.imdg_source_findings ?? []),
  ];

  // The headings carry the outcome in figures, so that a collapsed section
  // never conceals a finding: counts per severity and per LQ/EQ status.
  const severityCounts: Record<ComplianceWarning["severity"], number> = {
    error: 0,
    warning: 0,
    info: 0,
  };
  for (const warning of warnings) severityCounts[warning.severity] += 1;

  const lqEqCounts: Record<string, number> = {};
  for (const row of result?.lq_eq?.rows ?? []) {
    for (const status of [row.lq.status, row.eq.status]) {
      lqEqCounts[status] = (lqEqCounts[status] ?? 0) + 1;
    }
  }
  const lqEqWarningCount = result?.lq_eq?.warnings.length ?? 0;
  const qExceeded = (result?.q_values ?? []).some((q) => q.exceeded);
  const qIncomplete = !qExceeded && (result?.q_values ?? []).some((q) => q.exceeded == null);

  return (
    <div className={`${panelClass} space-y-4 p-4 sm:p-6`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="font-semibold text-slate-900 dark:text-slate-100">{t("compliance.title")}</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {t("compliance.intro", { profiles: profiles.join(", ") })}
          </p>
        </div>
        <button
          type="button"
          onClick={run}
          disabled={loading}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          {loading ? t("compliance.checking") : t("compliance.recheck")}
        </button>
      </div>

      {error && (
        <p className="whitespace-pre-line text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      )}

      {adr && (
        <CollapsibleSection
          title={t("compliance.adrPointsTitle")}
          defaultOpen={adr.status === "not_exempt"}
          chips={
            <>
              <SummaryChip className={STATUS_STYLES[adr.status]}>
                {t(`compliance.status.${adr.status}`)}
              </SummaryChip>
              <span className="text-xs text-slate-600 dark:text-slate-300">
                {t("compliance.totalPoints", { total: adr.total_points, threshold: adr.threshold })}
              </span>
            </>
          }
        >
          <div className="overflow-x-auto">
            <table className="w-full min-w-[480px] text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-700 dark:text-slate-400">
                  <th className="py-1.5 pr-2 font-medium">{t("compliance.colProduct")}</th>
                  <th className="py-1.5 pr-2 font-medium">{t("compliance.colCategory")}</th>
                  <th className="py-1.5 pr-2 font-medium">{t("compliance.colQuantity")}</th>
                  <th className="py-1.5 pr-2 font-medium">{t("compliance.colFactor")}</th>
                  <th className="py-1.5 font-medium">{t("compliance.colPoints")}</th>
                </tr>
              </thead>
              <tbody className="text-slate-700 dark:text-slate-300">
                {adr.rows.map((row, i) => (
                  <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="py-1.5 pr-2">{row.product}</td>
                    <td className="py-1.5 pr-2">{row.transport_category ?? "—"}</td>
                    <td className="py-1.5 pr-2">{row.quantity ?? "—"}</td>
                    <td className="py-1.5 pr-2">{row.factor != null ? `×${row.factor}` : "—"}</td>
                    <td className="py-1.5 font-medium">{row.points ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {adr.status === "incomplete" && (
            <p className="text-xs text-amber-600 dark:text-amber-300">
              {t("compliance.incompleteHint", { products: adr.incomplete_products.join(", ") })}
            </p>
          )}
          {adr.status === "not_exempt" && (
            <p className="text-xs text-red-600 dark:text-red-400">
              {t("compliance.category0Hint", { products: adr.category0_products.join(", ") })}
            </p>
          )}
          {(adr.forbidden_products?.length ?? 0) > 0 && (
            <p className="text-xs text-red-600 dark:text-red-400">
              {t("compliance.forbiddenSkipped", { products: adr.forbidden_products!.join(", ") })}
            </p>
          )}
          <p className="text-[11px] text-slate-500 dark:text-slate-400">{adr.quantity_units_note}</p>

          {/* For rail and inland waterway the ADR tables are what was computed
              with. The user should not have to guess that from a heading that
              says "ADR 1.1.3.6". */}
          {adr.basis_note && (
            <p className="rounded-lg border border-amber-200 bg-amber-50 px-2 py-1.5 text-[11px] text-amber-800 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-200">
              {adr.basis_note}
            </p>
          )}

          {adr.mode_note && (
            <p className="text-xs text-sky-700 dark:text-sky-300">{adr.mode_note}</p>
          )}
          {adr.status === "exempt_possible" && (
            <details className="text-xs text-slate-600 dark:text-slate-300">
              <summary className="cursor-pointer font-medium">{t("compliance.exemptDetails")}</summary>
              <p className="mt-1 font-medium">{t("compliance.exemptFrom")}</p>
              <ul className="ml-4 list-disc">{adr.exempt_provisions.map((x, i) => <li key={i}>{x}</li>)}</ul>
              <p className="mt-1 font-medium">{t("compliance.stillRequired")}</p>
              <ul className="ml-4 list-disc">{adr.still_required.map((x, i) => <li key={i}>{x}</li>)}</ul>
            </details>
          )}
          {adr.status === "above_threshold" && (
            <p className="text-xs text-amber-700 dark:text-amber-300">{t("compliance.aboveThresholdHint")}</p>
          )}
        </CollapsibleSection>
      )}

      {/* ADR 3.2.1 — may these goods travel in a tank at all? Only appears once
          somebody has said they do; a packages consignment never sees it. The
          two tank columns differ: (12) is an outright prohibition where empty,
          (10) leaves room for the competent authority under 6.7.1.3, and the
          card keeps them apart rather than rounding both to "no". */}
      {tankAdmission && tankAdmission.status !== "not_checked" && (
        <CollapsibleSection
          title={t("compliance.tankAdmissionTitle")}
          defaultOpen={tankAdmission.status === "not_permitted"}
          chips={
            <SummaryChip
              className={
                tankAdmission.status === "not_permitted"
                  ? "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300"
                  : "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
              }
            >
              {t(`compliance.tankAdmission.${tankAdmission.status}`)}
            </SummaryChip>
          }
        >
          <ul className="space-y-2">
            {tankAdmission.items.map((item, i) => (
              <li key={i} className="text-xs">
                <p
                  className={
                    item.permitted
                      ? "text-slate-700 dark:text-slate-300"
                      : item.subject_to_approval
                        ? "text-amber-600 dark:text-amber-300"
                        : "text-red-600 dark:text-red-400"
                  }
                >
                  {item.message}
                </p>
                {(item.tank_provisions || item.portable_tank_provisions) && (
                  <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                    {t("compliance.tankProvisions", {
                      codes: item.tank_provisions || item.portable_tank_provisions,
                    })}
                  </p>
                )}
              </li>
            ))}
          </ul>
          {tankAdmission.source && (
            <p className="text-[11px] text-slate-500 dark:text-slate-400">{tankAdmission.source}</p>
          )}
        </CollapsibleSection>
      )}

      {/* ADR 7.3.1.1 — the same admission question for bulk, on its own two
          columns: a BK code opens bulk containers, a VC code opens sheeted or
          closed vehicles, and neither means no. */}
      {bulkAdmission && bulkAdmission.status !== "not_checked" && (
        <CollapsibleSection
          title={t("compliance.bulkAdmissionTitle")}
          defaultOpen={bulkAdmission.status === "not_permitted"}
          chips={
            <SummaryChip
              className={
                bulkAdmission.status === "not_permitted"
                  ? "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300"
                  : "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
              }
            >
              {t(`compliance.bulkAdmission.${bulkAdmission.status}`)}
            </SummaryChip>
          }
        >
          <ul className="space-y-2">
            {bulkAdmission.items.map((item, i) => (
              <li key={i} className="text-xs">
                <p
                  className={
                    item.permitted
                      ? "text-slate-700 dark:text-slate-300"
                      : "text-red-600 dark:text-red-400"
                  }
                >
                  {item.message}
                </p>
              </li>
            ))}
          </ul>
          {bulkAdmission.source && (
            <p className="text-[11px] text-slate-500 dark:text-slate-400">{bulkAdmission.source}</p>
          )}
        </CollapsibleSection>
      )}

      {/* ADR 4.3 — and it comes straight after the admission card, because it
          is the next question in the same conversation: the goods may travel in
          a tank, but may they travel in *this* one? The card leads with the
          outcome per position, and "cannot be assessed" is shown as its own
          state rather than folded into either yes or no. */}
      {tankFit && tankFit.status !== "not_checked" && (
        <CollapsibleSection
          title={t("compliance.tankFitTitle")}
          defaultOpen={tankFit.status === "not_permitted"}
          chips={
            <SummaryChip
              className={
                tankFit.status === "not_permitted"
                  ? "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300"
                  : "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
              }
            >
              {t(`compliance.tankFit.${tankFit.status}`)}
            </SummaryChip>
          }
        >
          <ul className="space-y-2">
            {tankFit.items.map((item, i) => (
              <li key={i} className="text-xs">
                <p
                  className={
                    item.fit === "fits"
                      ? "text-slate-700 dark:text-slate-300"
                      : item.fit === "does_not_fit"
                        ? "text-red-600 dark:text-red-400"
                        : "text-amber-600 dark:text-amber-300"
                  }
                >
                  {item.message}
                </p>
                {item.provisions_note && (
                  <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                    {item.provisions_note}
                  </p>
                )}
              </li>
            ))}
          </ul>
          {tankFit.source && (
            <p className="text-[11px] text-slate-500 dark:text-slate-400">{tankFit.source}</p>
          )}
        </CollapsibleSection>
      )}

      {/* ADR 4.3.2.2 — how full that tank may be. The formula is the answer
          even when the densities to put in it are missing, so the card shows it
          either way and says which of the four cases it picked and why. */}
      {filling && filling.status !== "not_checked" && (
        <CollapsibleSection
          title={t("compliance.fillingDegreeTitle")}
          chips={
            <SummaryChip className="bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200">
              {t(
                filling.items.some((item) => item.status === "computed")
                  ? "compliance.fillingDegree.computed"
                  : "compliance.fillingDegree.formula",
              )}
            </SummaryChip>
          }
        >
          <ul className="space-y-2">
            {filling.items.map((item, i) => (
              <li key={i} className="text-xs">
                <p
                  className={
                    item.status === "computed"
                      ? "text-slate-700 dark:text-slate-300"
                      : "text-amber-600 dark:text-amber-300"
                  }
                >
                  {item.message}
                </p>
                {item.formula && (
                  <p className="mt-0.5 font-mono text-[11px] text-slate-500 dark:text-slate-400">
                    {item.formula}
                  </p>
                )}
                {item.derivation && (
                  <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                    {item.derivation}
                  </p>
                )}
              </li>
            ))}
          </ul>
          {filling.source && (
            <p className="text-[11px] text-slate-500 dark:text-slate-400">{filling.source}</p>
          )}
        </CollapsibleSection>
      )}

      {/* ADN 3.2.1, column (8) — the water's counterpart of the tank admission
          card above, and it comes first for the same reason: everything below it
          is chapter 7.1, which is the chapter for dry cargo vessels. A cargo tank
          load is not on one, and where column (8) does permit a tank vessel the
          honest end of the answer is that table C is not in this application. */}
      {adnAdmission && adnAdmission.status !== "not_checked" && (
        <CollapsibleSection
          title={t("compliance.adnAdmissionTitle")}
          defaultOpen={adnAdmission.status === "not_permitted"}
          chips={
            <SummaryChip
              className={
                adnAdmission.status === "not_permitted"
                  ? "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300"
                  : "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
              }
            >
              {t(`compliance.adnAdmission.${adnAdmission.status}`)}
            </SummaryChip>
          }
        >
          <ul className="space-y-2">
            {adnAdmission.items.map((item, i) => (
              <li key={i} className="text-xs">
                <p
                  className={
                    item.permitted
                      ? "text-slate-700 dark:text-slate-300"
                      : "text-red-600 dark:text-red-400"
                  }
                >
                  {item.message}
                </p>
                {item.vessel_message && (
                  <p className="mt-0.5 font-medium text-slate-900 dark:text-slate-100">
                    {item.vessel_message}
                  </p>
                )}
              </li>
            ))}
          </ul>
          {adnAdmission.single_reading_note && (
            <p className="text-xs text-amber-600 dark:text-amber-300">
              {adnAdmission.single_reading_note}
            </p>
          )}
          {adnAdmission.conditions_note && (
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              {adnAdmission.conditions_note}
            </p>
          )}
          {adnAdmission.not_assessed && (
            <p className="text-xs text-amber-600 dark:text-amber-300">
              {adnAdmission.not_assessed}
            </p>
          )}
          {adnAdmission.source && (
            <p className="text-[11px] text-slate-500 dark:text-slate-400">{adnAdmission.source}</p>
          )}
        </CollapsibleSection>
      )}

      {/* The ADN has no points calculation. Its exemption of 1.1.3.6.1 is about
          gross mass with its own limit per class, and that outcome can be the
          opposite of the ADR points above. Hence a card of its own rather than a
          footnote to a calculation that does not apply here. */}
      {adn && (
        <CollapsibleSection
          title={t("compliance.adnExemptionTitle")}
          defaultOpen={adn.status === "not_exempt" || adn.status === "above_threshold"}
          chips={
            <>
              <SummaryChip className={STATUS_STYLES[adn.status]}>
                {t(`compliance.status.${adn.status}`)}
              </SummaryChip>
              <span className="text-xs text-slate-600 dark:text-slate-300">
                {t("compliance.adnTotalMass", {
                  total: adn.total_gross_mass_kg,
                  threshold: adn.threshold,
                })}
              </span>
            </>
          }
        >
          {adn.mode_note && (
            <p className="text-xs text-sky-700 dark:text-sky-300">{adn.mode_note}</p>
          )}
          <div className="overflow-x-auto">
            <table className="w-full min-w-[420px] text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-700 dark:text-slate-400">
                  <th className="py-1.5 pr-2 font-medium">{t("compliance.colProduct")}</th>
                  <th className="py-1.5 pr-2 font-medium">{t("compliance.colClass")}</th>
                  <th className="py-1.5 pr-2 font-medium">{t("compliance.colQuantity")}</th>
                  <th className="py-1.5 font-medium">{t("compliance.colAdnLimit")}</th>
                </tr>
              </thead>
              <tbody className="text-slate-700 dark:text-slate-300">
                {adn.rows.map((row, i) => (
                  <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="py-1.5 pr-2">{row.product}</td>
                    <td className="py-1.5 pr-2">{row.class ?? "—"}</td>
                    <td className="py-1.5 pr-2">{row.quantity ?? "—"}</td>
                    <td className="py-1.5 font-medium">
                      {row.limit != null ? `${row.limit} kg` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {adn.over_class_limit.length > 0 && (
            <ul className="ml-4 list-disc text-xs text-red-600 dark:text-red-400">
              {adn.over_class_limit.map((over, i) => (
                <li key={i}>
                  {t("compliance.adnOverClass", {
                    cls: over.class,
                    carried: over.carried,
                    limit: over.limit,
                  })}
                </li>
              ))}
            </ul>
          )}
          {adn.status === "incomplete" && (
            <p className="text-xs text-amber-600 dark:text-amber-300">
              {t("compliance.incompleteHint", { products: adn.incomplete_products.join(", ") })}
            </p>
          )}
          <p className="text-[11px] text-slate-500 dark:text-slate-400">{adn.note}</p>
          <details className="text-xs text-slate-600 dark:text-slate-300">
            <summary className="cursor-pointer font-medium">
              {t("compliance.adnConditions")}
            </summary>
            <ul className="ml-4 mt-1 list-disc">
              {adn.conditions.map((x, i) => <li key={i}>{x}</li>)}
            </ul>
          </details>
        </CollapsibleSection>
      )}

      {/* ADN 7.1.4.3 — separation in the holds. Not the road rule renamed: ADR
          7.5.2 asks whether two packages may share a vehicle and answers yes or
          no, this one answers in metres. Two of its three provisions are stated
          in blue cones, and a substance whose cone count could not be settled is
          named rather than guessed at. */}
      {separation && separation.status !== "not_checked" && (
        <CollapsibleSection
          title={t("compliance.adnSeparationTitle")}
          defaultOpen={separation.findings.length > 0}
          chips={
            <>
              <SummaryChip
                className={
                  separation.status === "not_available_for_mode"
                    ? STATUS_STYLES.not_available_for_mode
                    : separation.findings.length > 0
                      ? "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
                      : "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
                }
              >
                {separation.status === "not_available_for_mode"
                  ? t("compliance.status.not_available_for_mode")
                  : separation.findings.length > 0
                    ? t("compliance.adnSeparationFindings", { count: separation.findings.length })
                    : t("compliance.adnSeparationNone")}
              </SummaryChip>
              {separation.cones_not_settled && separation.cones_not_settled.length > 0 && (
                <SummaryChip className="bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                  {t("compliance.adnConesUnsettled", {
                    count: separation.cones_not_settled.length,
                  })}
                </SummaryChip>
              )}
            </>
          }
        >
          {separation.mode_note ? (
            <p className="text-xs text-sky-700 dark:text-sky-300">{separation.mode_note}</p>
          ) : separation.findings.length === 0 ? (
            <p className="text-xs text-slate-600 dark:text-slate-300">
              {t("compliance.adnSeparationNoneHint")}
            </p>
          ) : (
            <ul className="space-y-2">
              {separation.findings.map((finding, i) => (
                <li key={i} className="text-xs text-slate-700 dark:text-slate-300">
                  <span className="font-medium text-slate-900 dark:text-slate-100">
                    {finding.provision}
                  </span>
                  {finding.metres != null && (
                    <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-[11px] font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                      {finding.metres} m
                    </span>
                  )}
                  <p className="mt-0.5">{finding.message}</p>
                  {finding.two_cones && finding.one_cone_flammable && (
                    <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                      {finding.two_cones.join(", ")} ↔ {finding.one_cone_flammable.join(", ")}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
          {separation.not_assessed && (
            <p className="text-xs text-amber-600 dark:text-amber-300">{separation.not_assessed}</p>
          )}
          {separation.source && (
            <p className="text-[11px] text-slate-500 dark:text-slate-400">{separation.source}</p>
          )}
        </CollapsibleSection>
      )}

      {/* ADN 7.1.5.0 — the signals the vessel must show. Nought cones is an
          answer, not a silence, and it is the commonest one: a card that only
          appeared when cones were needed would teach the user that an absent
          card means safe. Under 7.1.5.0.4 the heaviest signal on board wins, so
          one package can set the signals for everything else. */}
      {signals && signals.status !== "not_checked" && (signals.cones != null || signals.mode_note) && (
        <CollapsibleSection
          title={t("compliance.adnSignalsTitle")}
          defaultOpen={(signals.cones ?? 0) > 0}
          chips={
            <>
              <SummaryChip
                className={
                  signals.mode_note
                    ? STATUS_STYLES.not_available_for_mode
                    : (signals.cones ?? 0) > 0
                      ? "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300"
                      : "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
                }
              >
                {signals.mode_note
                  ? t("compliance.status.not_available_for_mode")
                  : signals.cones}
              </SummaryChip>
              {signals.message && (
                <span className="text-xs text-slate-600 dark:text-slate-300">{signals.message}</span>
              )}
            </>
          }
        >
          {signals.mode_note && (
            <p className="text-xs text-sky-700 dark:text-sky-300">{signals.mode_note}</p>
          )}
          {signals.set_by && signals.set_by.length > 0 && (
            <p className="text-xs text-slate-700 dark:text-slate-300">
              {t("compliance.adnSignalsSetBy", { products: signals.set_by.join(", ") })}
            </p>
          )}
          {signals.highest_wins && (
            <p className="text-xs text-slate-700 dark:text-slate-300">{signals.highest_wins}</p>
          )}
          {signals.not_assessed && (
            <p className="text-xs text-amber-600 dark:text-amber-300">{signals.not_assessed}</p>
          )}
          {signals.containers_note && (
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              {signals.containers_note}
            </p>
          )}
          {signals.source && (
            <p className="text-[11px] text-slate-500 dark:text-slate-400">{signals.source}</p>
          )}
        </CollapsibleSection>
      )}

      {result?.lq_eq && result.lq_eq.rows.length > 0 && (
        <CollapsibleSection
          title={t("compliance.lqEqTitle")}
          chips={
            <>
              {(["within_limits", "not_within", "not_permitted", "incomplete", "no_data"] as const)
                .filter((status) => lqEqCounts[status])
                .map((status) => (
                  <SummaryChip key={status} className={LQEQ_STATUS_STYLES[status]}>
                    {lqEqCounts[status]} × {t(`compliance.lqeqStatus.${status}`)}
                  </SummaryChip>
                ))}
              {lqEqWarningCount > 0 && (
                <SummaryChip className="bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                  {lqEqWarningCount} × {t("compliance.sevWarning")}
                </SummaryChip>
              )}
            </>
          }
        >
          {result.lq_eq.rows.map((row, i) => (
            <div
              key={i}
              className="rounded-lg border border-slate-200 px-3 py-2 text-xs dark:border-slate-700"
            >
              <p className="font-semibold text-slate-800 dark:text-slate-200">{row.product}</p>
              <div className="mt-1 flex items-start gap-2">
                <span
                  className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${LQEQ_STATUS_STYLES[row.lq.status]}`}
                >
                  LQ{row.lq.value ? ` ${row.lq.value}` : ""} · {t(`compliance.lqeqStatus.${row.lq.status}`)}
                </span>
                <span className="text-slate-600 dark:text-slate-300">{row.lq.message}</span>
              </div>
              <div className="mt-1 flex items-start gap-2">
                <span
                  className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${LQEQ_STATUS_STYLES[row.eq.status]}`}
                >
                  EQ{row.eq.code ? ` ${row.eq.code}` : ""} · {t(`compliance.lqeqStatus.${row.eq.status}`)}
                </span>
                <span className="text-slate-600 dark:text-slate-300">{row.eq.message}</span>
              </div>
            </div>
          ))}
          {result.lq_eq.warnings.map((w, i) => (
            <div
              key={`w-${i}`}
              className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-300"
            >
              <p className="font-semibold">{w.rule}</p>
              <p className="mt-0.5">{w.message}</p>
              <p className="mt-0.5 opacity-80">{w.products}</p>
            </div>
          ))}
          {result.lq_eq.basis_note && (
            <p className="rounded-lg border border-amber-200 bg-amber-50 px-2 py-1.5 text-[11px] text-amber-800 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-200">
              {result.lq_eq.basis_note}
            </p>
          )}
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            {result.lq_eq.note} ({result.lq_eq.basis})
          </p>
        </CollapsibleSection>
      )}

      {tunnel && tunnel.rows.length > 0 && (
        <CollapsibleSection
          title={t("compliance.tunnelTitle")}
          chips={
            <>
              <SummaryChip className={TUNNEL_STATUS_STYLES[tunnel.status]}>
                {t(`compliance.tunnelStatus.${tunnel.status}`)}
              </SummaryChip>
              {tunnel.code && (
                <span className="font-mono text-xs text-slate-700 dark:text-slate-200">
                  ({tunnel.code})
                </span>
              )}
            </>
          }
        >
          <p className="text-xs text-slate-700 dark:text-slate-200">{tunnel.message}</p>
          <div className="flex flex-wrap gap-1.5">
            {tunnel.rows.map((row, i) => (
              <span
                key={i}
                className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-700 dark:bg-slate-800 dark:text-slate-200"
              >
                {row.product} · {row.code ? `(${row.code})` : t("compliance.tunnelNoCode")}
              </span>
            ))}
          </div>
          {tunnel.explosive_mass_kg != null && (
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              {t("compliance.tunnelExplosiveMass", { mass: tunnel.explosive_mass_kg })}
            </p>
          )}
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            {tunnel.note} ({tunnel.basis})
          </p>
        </CollapsibleSection>
      )}

      {security && security.status !== "not_checked" && (
        <CollapsibleSection
          title={t("compliance.securityTitle")}
          chips={
            <SummaryChip
              className={
                security.status === "high_consequence"
                  ? "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"
                  : "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200"
              }
            >
              {security.status === "high_consequence"
                ? t("compliance.securityHigh")
                : t("compliance.securityNone")}
            </SummaryChip>
          }
        >
          <div className="flex items-start gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs dark:border-slate-700">
            <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200">
              {security.provision}
            </span>
            <span className="text-slate-700 dark:text-slate-200">{security.message}</span>
          </div>
          {security.items.map((item, i) => (
            <div
              key={i}
              className="flex items-start gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs dark:border-slate-700"
            >
              {item.un_number && (
                <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-mono text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                  UN {item.un_number}
                </span>
              )}
              <span className="text-slate-700 dark:text-slate-200">{item.reason}</span>
            </div>
          ))}
        </CollapsibleSection>
      )}

      {/* 5.3 mostly answers "no", and that answer has to be as visible as a
          "yes": an absent section reads as a check that did not run, and a user
          who cannot tell those apart will placard to be safe. */}
      {placarding && placarding.status !== "not_checked" && (
        <CollapsibleSection
          title={t("compliance.placardingTitle")}
          chips={
            <>
              <SummaryChip
                className={
                  placarding.placards_required
                    ? "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"
                    : "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200"
                }
              >
                {placarding.placards_required
                  ? t("compliance.placardingRequired")
                  : t("compliance.placardingNone")}
              </SummaryChip>
              <SummaryChip className="bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {t("compliance.placardingPackages")}
              </SummaryChip>
            </>
          }
        >
          {[...placarding.placards, ...placarding.marks].map((item, i) => (
            <div
              key={i}
              className="flex items-start gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs dark:border-slate-700"
            >
              <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                {item.provision}
              </span>
              <span className="text-slate-700 dark:text-slate-200">{item.message}</span>
            </div>
          ))}
        </CollapsibleSection>
      )}

      {adnPlacarding && adnPlacarding.status !== "not_checked" && (
        <CollapsibleSection
          title={t("compliance.adnPlacardingTitle")}
          chips={
            <>
              <SummaryChip
                className={
                  adnPlacarding.placards_required
                    ? "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"
                    : "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200"
                }
              >
                {adnPlacarding.placards_required
                  ? t("compliance.placardingRequired")
                  : t("compliance.placardingNone")}
              </SummaryChip>
              <SummaryChip className="bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {t("compliance.adnPlacardingCtu")}
              </SummaryChip>
            </>
          }
        >
          {adnPlacarding.mode_note && (
            <p className="text-xs text-slate-600 dark:text-slate-300">{adnPlacarding.mode_note}</p>
          )}
          {[...(adnPlacarding.placards ?? []), ...(adnPlacarding.marks ?? [])].map((item, i) => (
            <div
              key={i}
              className="flex items-start gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs dark:border-slate-700"
            >
              <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                {item.provision}
              </span>
              <span className="text-slate-700 dark:text-slate-200">{item.message}</span>
            </div>
          ))}
        </CollapsibleSection>
      )}

      {ridPlacarding && ridPlacarding.status !== "not_checked" && (
        <CollapsibleSection
          title={t("compliance.ridPlacardingTitle")}
          chips={
            <>
              <SummaryChip
                className={
                  ridPlacarding.placards_required
                    ? "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"
                    : "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200"
                }
              >
                {ridPlacarding.placards_required
                  ? t("compliance.placardingRequired")
                  : t("compliance.placardingNone")}
              </SummaryChip>
              <SummaryChip className="bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {t("compliance.ridPlacardingWagon")}
              </SummaryChip>
            </>
          }
        >
          {[...(ridPlacarding.placards ?? []), ...(ridPlacarding.marks ?? [])].map((item, i) => (
            <div
              key={i}
              className="flex items-start gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs dark:border-slate-700"
            >
              <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                {item.provision}
              </span>
              <span className="text-slate-700 dark:text-slate-200">{item.message}</span>
            </div>
          ))}
        </CollapsibleSection>
      )}

      {imdgPlacarding && imdgPlacarding.status !== "not_checked" && (
        <CollapsibleSection
          title={t("compliance.imdgPlacardingTitle")}
          chips={
            <>
              <SummaryChip
                className={
                  imdgPlacarding.placards_required
                    ? "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"
                    : "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200"
                }
              >
                {imdgPlacarding.placards_required
                  ? t("compliance.placardingRequired")
                  : t("compliance.placardingNone")}
              </SummaryChip>
              <SummaryChip className="bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {t("compliance.imdgPlacardingUnit")}
              </SummaryChip>
              {imdgPlacarding.marks?.some((m) => m.kind === "marine_pollutant") && (
                <SummaryChip className="bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200">
                  {t("compliance.imdgPlacardingPollutant")}
                </SummaryChip>
              )}
            </>
          }
        >
          {[...(imdgPlacarding.placards ?? []), ...(imdgPlacarding.marks ?? [])].map((item, i) => (
            <div
              key={i}
              className="flex items-start gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs dark:border-slate-700"
            >
              <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                {item.provision}
              </span>
              <span className="text-slate-700 dark:text-slate-200">{item.message}</span>
            </div>
          ))}
        </CollapsibleSection>
      )}

      {equipment && equipment.items.length > 0 && (
        <CollapsibleSection
          title={t("compliance.equipmentTitle")}
          chips={
            <>
              <SummaryChip className="bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {t("compliance.equipmentCount", { count: equipment.items.length })}
              </SummaryChip>
              {equipment.labels.map((label) => (
                <span
                  key={label}
                  className="rounded-full bg-slate-100 px-2 py-0.5 font-mono text-[11px] text-slate-700 dark:bg-slate-800 dark:text-slate-200"
                >
                  {label}
                </span>
              ))}
            </>
          }
        >
          {equipment.items.map((item, i) => (
            <div
              key={i}
              className="flex items-start gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs dark:border-slate-700"
            >
              <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                {item.rule}
              </span>
              <span className="text-slate-700 dark:text-slate-200">{item.text}</span>
            </div>
          ))}
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            {equipment.note} ({equipment.basis})
          </p>
        </CollapsibleSection>
      )}

      {warnings.length > 0 && (
        <CollapsibleSection
          title={t("compliance.segregationTitle")}
          defaultOpen={severityCounts.error > 0}
          chips={
            <>
              {severityCounts.error > 0 && (
                <SummaryChip className="bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300">
                  {severityCounts.error} × {t("compliance.sevError")}
                </SummaryChip>
              )}
              {severityCounts.warning > 0 && (
                <SummaryChip className="bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                  {severityCounts.warning} × {t("compliance.sevWarning")}
                </SummaryChip>
              )}
              {severityCounts.info > 0 && (
                <SummaryChip className="bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300">
                  {severityCounts.info} × {t("compliance.sevInfo")}
                </SummaryChip>
              )}
            </>
          }
        >
          {warnings.map((w, i) => (
            <div
              key={i}
              className={`rounded-lg border px-3 py-2 text-xs ${
                w.severity === "error"
                  ? "border-red-200 bg-red-50 text-red-800 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300"
                  : w.severity === "info"
                    ? "border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/50 dark:bg-sky-900/20 dark:text-sky-300"
                    : "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-300"
              }`}
            >
              <p className="font-semibold">{w.rule}</p>
              <p className="mt-0.5">{w.message}</p>
              <p className="mt-0.5 opacity-80">{w.products}</p>
            </div>
          ))}
          {result?.adr_mixed_loading_basis_note && (
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              {result.adr_mixed_loading_basis_note}
            </p>
          )}
        </CollapsibleSection>
      )}
      {result && warnings.length === 0 &&
        (result.adr_mixed_loading || result.imdg_segregation || result.iata_segregation ||
          result.rid_transport_document || result.adn_stabilisation ||
          result.technical_name_findings || result.imdg_source_findings) && (
          <p className="text-xs text-emerald-700 dark:text-emerald-300">{t("compliance.noSegregationIssues")}</p>
        )}
      {result?.regulatory_manifest && (
        <p className="text-[11px] text-slate-400 dark:text-slate-500">
          {t("compliance.manifest", {
            id: result.regulatory_manifest.manifest_id,
            editions: Object.values(result.regulatory_manifest.editions).join(" · "),
          })}
        </p>
      )}
      {result?.imdg_note && (
        <p className="text-[11px] text-slate-500 dark:text-slate-400">{result.imdg_note}</p>
      )}

      {result?.imdg_segregation_groups && (
        <CollapsibleSection title={t("compliance.segGroupsTitle")}>
          <p className="text-xs text-slate-600 dark:text-slate-300">{result.imdg_segregation_groups.note}</p>
          <ul className="grid gap-x-4 gap-y-0.5 text-xs sm:grid-cols-2">
            {result.imdg_segregation_groups.groups.map((group) => (
              <li key={group.code} className="text-slate-600 dark:text-slate-300">
                <span className="font-mono font-semibold">{group.code}</span> — {group.label}
              </li>
            ))}
          </ul>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {result.imdg_segregation_groups.class8_exception}
          </p>
        </CollapsibleSection>
      )}

      {(result?.q_values?.length ?? 0) > 0 && (
        <CollapsibleSection
          title={t("compliance.qTitle")}
          defaultOpen={qExceeded}
          chips={
            <SummaryChip
              className={
                qExceeded
                  ? "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300"
                  : qIncomplete
                    ? "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                    : "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
              }
            >
              {qExceeded ? "Q > 1" : qIncomplete ? t("compliance.lqeqStatus.incomplete") : "Q ≤ 1"}
            </SummaryChip>
          }
        >
          {result!.q_values!.map((q, i) => (
            <div
              key={i}
              className={`rounded-lg border px-3 py-2 text-xs ${
                q.exceeded
                  ? "border-red-200 bg-red-50 text-red-800 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300"
                  : "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-900/20 dark:text-emerald-300"
              }`}
            >
              <p className="font-semibold">
                {t("compliance.qValueFor", { position: String(q.position), value: q.q_value })}
                {q.exceeded ? ` — ${t("compliance.qExceeded")}` : ""}
              </p>
              <p className="mt-0.5 opacity-80">
                {q.components.map((c) => `${c.product}: ${c.net_quantity}/${c.max_per_package}`).join("  ·  ")}
              </p>
            </div>
          ))}
          <p className="text-[11px] text-slate-500 dark:text-slate-400">{result!.q_values![0].note}</p>
        </CollapsibleSection>
      )}

      {(result?.cargo_aircraft_only_products?.length ?? 0) > 0 && (
        <p className="text-xs text-amber-700 dark:text-amber-300">
          {t("compliance.caoHint", { products: result!.cargo_aircraft_only_products!.join(", ") })}
        </p>
      )}

      <p className="text-[11px] italic text-slate-400 dark:text-slate-500">{t("compliance.disclaimer")}</p>
    </div>
  );
}
