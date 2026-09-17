import { canUseDgsa } from "../permissions";
import { Navigate } from "react-router";
/** The safety adviser's annual report (ADR 1.8.3.3), drawn over the kept
 *  shipments of one calendar year.
 *
 *  The server counts; this page shows the count and hands over the workbook.
 *  The adviser's own duties — the practices 1.8.3.3 says the adviser must
 *  check — are listed at the end as headings with nothing filled in: a
 *  generated opinion on training or emergency procedures would be worse
 *  than a blank, so the blank is the deliberate part of the report.
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { api, Department, DgsaFormResponse, DgsaReport, User } from "../api/client";
import DgsaReportForm from "../components/DgsaReportForm";
import HistoryStatus from "../components/HistoryStatus";
import { documentLanguage } from "../i18n/language";
import { usePreferences } from "../settings/preferences";
import { useToast } from "../toast/ToastProvider";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2.5 text-sm min-h-[44px]";
const buttonPrimary =
  "bg-brand-600 text-white px-4 py-2.5 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50 min-h-[44px] text-sm";
const buttonSecondary =
  "px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 min-h-[44px] text-sm";
const th = "px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400";
const td = "px-3 py-2 text-sm text-slate-800 dark:text-slate-200";
const num = `${td} text-right tabular-nums`;

function amount(value: number): string {
  return value === 0 ? "—" : value.toLocaleString(undefined, { maximumFractionDigits: 3 });
}

function Table({ headers, rows, caption }: { headers: string[]; rows: (string | number)[][]; caption: string }) {
  const { t } = useTranslation();
  return (
    <section className={`${panelClass} p-4 sm:p-6`}>
      <h3 className="font-semibold text-slate-900 dark:text-slate-100">{caption}</h3>
      {rows.length === 0 ? (
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{t("dgsa.nothing")}</p>
      ) : (
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800">
                {headers.map((h, i) => (
                  <th key={h} className={`${th} ${i > 0 && typeof rows[0]?.[i] === "number" ? "text-right" : ""}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, r) => (
                <tr key={r} className="border-b border-slate-100 dark:border-slate-800/60 last:border-0">
                  {row.map((cell, c) => (
                    <td key={c} className={typeof cell === "number" ? num : td}>
                      {typeof cell === "number" ? amount(cell) : cell || "—"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default function DgsaReportPage({ user }: { user?: User | null }) {
  const { publicSettings, loaded } = usePreferences();
  const { t } = useTranslation();
  if (!loaded) return <p role="status">{t("wizard.loading")}</p>;
  if (!canUseDgsa(user, publicSettings)) return <Navigate to="/shipments" replace />;
  return <DgsaReportContent user={user} />;
}

function DgsaReportContent({ user }: { user?: User | null }) {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const { publicSettings } = usePreferences();
  const historyOn = !!publicSettings?.history_enabled;
  const admin = !!user && ["admin", "super_user", "dg_specialist"].includes(user.role);
  const language = documentLanguage(i18n.language);

  const [years, setYears] = useState<number[]>([]);
  const [year, setYear] = useState<number>(new Date().getFullYear());
  const [departments, setDepartments] = useState<Department[]>([]);
  const [department, setDepartment] = useState("");
  const [report, setReport] = useState<DgsaReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  // The two faces of the report: the figures, and the form in the DVSA's
  // shape that the adviser fills in and keeps.
  const [view, setView] = useState<"figures" | "form">("figures");
  const [form, setForm] = useState<DgsaFormResponse | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  useEffect(() => {
    if (!historyOn) return;
    api
      .reportYears()
      .then(({ years: found }) => {
        setYears(found);
        if (found.length > 0 && !found.includes(year)) setYear(found[0]);
      })
      .catch(() => setYears([]));
    if (admin) api.departments().then(setDepartments).catch(() => setDepartments([]));
    // Once: the years and departments on offer do not change while reading.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [historyOn, admin]);

  useEffect(() => {
    if (!historyOn) return;
    let cancelled = false;
    setLoading(true);
    api
      .dgsaReport(year, department, language)
      .then((r) => {
        if (!cancelled) setReport(r);
      })
      .catch((e) => {
        if (!cancelled) toast.error(String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // toast is stable for the page's lifetime.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [historyOn, year, department, language]);

  useEffect(() => {
    if (!historyOn || view !== "form") return;
    let cancelled = false;
    api
      .dgsaReportForm(year, department, language)
      .then((f) => {
        if (cancelled) return;
        setForm(f);
        setSavedAt(f.saved_at);
      })
      .catch((e) => {
        if (!cancelled) toast.error(String(e));
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [historyOn, view, year, department, language]);

  const downloadPdf = async () => {
    setDownloadingPdf(true);
    try {
      await api.downloadDgsaReportPdf(year, department, language);
    } catch (e) {
      toast.error(String(e));
    } finally {
      setDownloadingPdf(false);
    }
  };

  const download = async () => {
    setDownloading(true);
    try {
      await api.downloadDgsaReport(year, department, language);
    } catch (e) {
      toast.error(String(e));
    } finally {
      setDownloading(false);
    }
  };

  if (!historyOn) return <HistoryStatus title={t("dgsa.title")} admin={admin} />;

  const monthName = (m: number) => new Date(year, m - 1, 1).toLocaleString(i18n.language, { month: "long" });
  const yearChoices = years.includes(year) ? years : [year, ...years];

  return (
    <div className="collection-page page-enter space-y-4 sm:space-y-6">
      <Link to="/shipments" className="text-sm text-brand-700 dark:text-brand-300 hover:underline">
        {t("history.back")}
      </Link>
      <div className={`${panelClass} p-5 sm:p-8`}>
        <h2 className="text-xl sm:text-2xl font-semibold text-slate-900 dark:text-slate-100">{t("dgsa.title")}</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-[10rem_1fr_auto] items-end">
          <label className="text-xs text-slate-500 dark:text-slate-400">
            {t("dgsa.year")}
            <select className={`${inputClass} mt-1`} value={year} onChange={(e) => setYear(Number(e.target.value))}>
              {yearChoices.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </label>
          {admin && departments.length > 0 ? (
            <label className="text-xs text-slate-500 dark:text-slate-400">
              {t("departments.userDepartment")}
              <select className={`${inputClass} mt-1`} value={department} onChange={(e) => setDepartment(e.target.value)}>
                <option value="">{t("departments.all")}</option>
                <option value="none">{t("departments.none")}</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </label>
          ) : (
            <span />
          )}
          <div className="flex flex-wrap gap-2">
            <button type="button" className={buttonPrimary} disabled={downloadingPdf} onClick={() => void downloadPdf()}>
              {downloadingPdf ? t("dgsa.downloading") : t("dgsa.downloadPdf")}
            </button>
            <button type="button" className={buttonSecondary} disabled={downloading || !report} onClick={() => void download()}>
              {downloading ? t("dgsa.downloading") : t("dgsa.download")}
            </button>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2" role="tablist">
          {(["figures", "form"] as const).map((key) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={view === key}
              onClick={() => setView(key)}
              className={`rounded-full border px-4 py-1.5 text-sm font-medium transition ${
                view === key
                  ? "border-brand-600 bg-brand-600 text-white"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
              }`}
            >
              {t(key === "figures" ? "dgsa.viewFigures" : "dgsa.viewForm")}
            </button>
          ))}
          {view === "form" && savedAt && (
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {t("dgsa.savedAt", { time: new Date(savedAt).toLocaleString(i18n.language) })}
            </span>
          )}
        </div>
      </div>

      {view === "form" && (
        <>
          {form ? (
            <DgsaReportForm year={year} department={department} language={language} form={form} onSaved={setSavedAt} />
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400">{t("dgsa.loading")}</p>
          )}
        </>
      )}

      {view === "figures" && loading && !report && <p className="text-sm text-slate-500 dark:text-slate-400">{t("dgsa.loading")}</p>}

      {view === "figures" && report && (
        <>
          <div className={`${panelClass} p-4 sm:p-6 space-y-2`}>
            <p className="text-sm text-slate-700 dark:text-slate-300">{report.basis}</p>
            <p className="text-xs text-slate-500 dark:text-slate-400">{report.counted_note}</p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {t("dgsa.scope")}: {report.scope} · {t("dgsa.generatedBy")}: {report.generated_by}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {(
              [
                ["shipments", report.totals.shipments],
                ["withDangerousGoods", report.totals.with_dangerous_goods],
                ["withoutDangerousGoods", report.totals.without_dangerous_goods],
                ["products", report.totals.products],
                ["quantityKg", report.totals.quantity_kg],
                ["quantityL", report.totals.quantity_l],
              ] as [string, number][]
            ).map(([key, value]) => (
              <div key={key} className={`${panelClass} p-4`}>
                <div className="text-xs text-slate-500 dark:text-slate-400">{t(`dgsa.${key}`)}</div>
                <div className="mt-1 text-2xl font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                  {value.toLocaleString(undefined, { maximumFractionDigits: 3 })}
                </div>
              </div>
            ))}
          </div>
          {report.totals.quantity_unknown > 0 && (
            <p className="text-xs text-amber-700 dark:text-amber-300">
              {t("dgsa.unknownNote", { count: report.totals.quantity_unknown })}
            </p>
          )}

          <Table
            caption={t("dgsa.byClass")}
            headers={[t("dgsa.class"), t("dgsa.shipments"), t("dgsa.products"), t("dgsa.quantityKg"), t("dgsa.quantityL"), t("dgsa.quantityUnknown")]}
            rows={report.by_class.map((c) => [c.class, c.shipments, c.products, c.quantity_kg, c.quantity_l, c.quantity_unknown])}
          />
          <Table
            caption={t("dgsa.byUnNumber")}
            headers={[t("dgsa.unNumber"), t("dgsa.name"), t("dgsa.class"), t("dgsa.packingGroup"), t("dgsa.shipments"), t("dgsa.products"), t("dgsa.quantityKg"), t("dgsa.quantityL")]}
            rows={report.by_un_number.map((u) => [
              u.un_number ? `UN ${u.un_number}` : "", u.name, u.class, u.packing_group, u.shipments, u.products, u.quantity_kg, u.quantity_l,
            ])}
          />
          <section className={`${panelClass} p-4 sm:p-6`}>
            <h3 className="font-semibold text-slate-900 dark:text-slate-100">{t("dgsa.adrPoints")}</h3>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{t("dgsa.adrPointsNote")}</p>
            {report.adr_points.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{t("dgsa.nothing")}</p>
            ) : (
              <ul className="mt-3 space-y-1">
                {report.adr_points.map((row) => (
                  <li key={row.status} className="flex justify-between gap-3 text-sm text-slate-800 dark:text-slate-200">
                    <span>{row.label}</span>
                    <span className="tabular-nums">{row.shipments}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <div className="grid gap-4 lg:grid-cols-2">
            <Table
              caption={t("dgsa.byMonth")}
              headers={[t("dgsa.month"), t("dgsa.shipments"), t("dgsa.withDangerousGoods")]}
              rows={report.by_month.map((m) => [monthName(m.month), m.shipments, m.with_dangerous_goods])}
            />
            <div className="space-y-4">
              <Table
                caption={t("dgsa.byModality")}
                headers={[t("dgsa.modality"), t("dgsa.shipments"), t("dgsa.withDangerousGoods")]}
                rows={report.by_modality.map((m) => [m.label, m.shipments, m.with_dangerous_goods])}
              />
              <Table
                caption={t("dgsa.byRegulation")}
                headers={[t("dgsa.regulation"), t("dgsa.shipments")]}
                rows={report.by_regulation.map((r) => [r.regulation, r.shipments])}
              />
              <Table
                caption={t("dgsa.byDepartment")}
                headers={[t("departments.userDepartment"), t("dgsa.shipments"), t("dgsa.withDangerousGoods")]}
                rows={report.by_department.map((d) => [d.department, d.shipments, d.with_dangerous_goods])}
              />
              <Table
                caption={t("dgsa.documents")}
                headers={[t("dgsa.document"), t("dgsa.shipments")]}
                rows={report.documents.map((d) => [d.label, d.shipments])}
              />
            </div>
          </div>

          <section className={`${panelClass} p-4 sm:p-6`}>
            <h3 className="font-semibold text-slate-900 dark:text-slate-100">{report.duties_heading}</h3>
            <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-slate-800 dark:text-slate-200">
              {report.duties.map((d) => (
                <li key={d.key}>{d.text}</li>
              ))}
            </ol>
          </section>
          <p className="text-xs text-slate-500 dark:text-slate-400">{report.source}</p>
        </>
      )}
    </div>
  );
}
