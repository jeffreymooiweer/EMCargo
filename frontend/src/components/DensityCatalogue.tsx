import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, DensityPage } from "../api/client";
import DensityReference from "./DensityReference";
import { ChevronDownIcon } from "./icons";

const PAGE_SIZE = 30;
const CATEGORIES = ["wood", "chemical", "plastic", "metal", "food", "insulation", "construction", "concrete", "bulk_material", "agri", "liquid", "ore_mineral", "paper", "textile", "waste", "general_cargo"];

export default function DensityCatalogue() {
  const { t, i18n } = useTranslation();
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [category, setCategory] = useState("");
  const [page, setPage] = useState<DensityPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let current = true;
    setLoading(true);
    setError("");
    const timer = window.setTimeout(() => {
      api.densities(query, offset, PAGE_SIZE, category).then(result => {
        if (current) setPage(result);
      }).catch(reason => {
        if (current) setError(String(reason));
      }).finally(() => {
        if (current) setLoading(false);
      });
    }, query ? 200 : 0);
    return () => { current = false; window.clearTimeout(timer); };
  }, [query, offset, category, i18n.language, attempt]);

  return <section className="surface p-4 sm:p-6 space-y-4" aria-label={t("densities.title")}>
    <select value={category} onChange={event => { setCategory(event.target.value); setOffset(0); }} aria-label={t("densities.category")} className="w-full sm:w-auto rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-3 text-sm">
      <option value="">{t("densities.allCategories")}</option>
      {CATEGORIES.map(value => <option key={value} value={value}>{t(`densities.categories.${value}`)}</option>)}
    </select>
    <input type="search" value={query} maxLength={200} onChange={event => { setQuery(event.target.value); setOffset(0); }} aria-label={t("densities.search")} placeholder={t("densities.search")} className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-3 text-sm" />
    {error ? <div role="alert"><p>{error}</p><button className="mt-2 underline" onClick={() => setAttempt(value => value + 1)}>{t("densities.retry")}</button></div>
      : loading ? <p role="status" className="text-sm">{t("densities.loading")}</p>
      : page && <>
        <p className="text-sm text-slate-500" role="status">{t("densities.count", { count: page.total })}</p>
        <div className="divide-y divide-slate-200 dark:divide-slate-800">
          {page.results.map(item => <details key={item.canonical_name} className="py-3">
            <summary className="flex cursor-pointer list-none items-center gap-3">
              <span className="min-w-0 flex-1 text-sm font-medium">{item.label}</span>
              <span className="shrink-0 text-sm tabular-nums">{item.density_kg_m3.toLocaleString(i18n.language, { maximumFractionDigits: 6 })} <span className="text-xs text-slate-500">kg/m³</span></span>
              <ChevronDownIcon className="h-4 w-4 shrink-0 text-slate-400" />
            </summary>
            <div className="pt-3"><DensityReference value={item} /></div>
          </details>)}
        </div>
        {page.total > PAGE_SIZE && <div className="flex items-center justify-between gap-3 text-sm">
          <button className="min-h-11 px-3 rounded-lg border dark:border-slate-700 disabled:opacity-40" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>{t("densities.previous")}</button>
          <span>{Math.floor(offset / PAGE_SIZE) + 1} / {Math.ceil(page.total / PAGE_SIZE)}</span>
          <button className="min-h-11 px-3 rounded-lg border dark:border-slate-700 disabled:opacity-40" disabled={offset + PAGE_SIZE >= page.total} onClick={() => setOffset(offset + PAGE_SIZE)}>{t("densities.next")}</button>
        </div>}
      </>}
  </section>;
}
