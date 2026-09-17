import HistoryStatus from "../components/HistoryStatus";
import DensityCatalogue from "../components/DensityCatalogue";
import type { User } from "../api/client";
import { PlusIcon, ChevronDownIcon } from "../components/icons";
/** The articles library: the organisation's own codes for what it ships.
 *
 *  One article per code — the code is what the office types on a goods
 *  line — with what the library knows about the substance (UN number,
 *  proper shipping name, packing group) and its packaging. A spreadsheet
 *  goes in and out in the same columns. Kept beside the history, like the
 *  address book: the page says so where the history is off.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, Article, ArticleIn, type ArticleImportResult, type ApiMessage, translateMessage } from "../api/client";
import { usePreferences } from "../settings/preferences";
import ConfirmDialog from "../toast/ConfirmDialog";
import { useToast } from "../toast/ToastProvider";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm min-h-[40px]";
const buttonPrimary =
  "bg-brand-600 text-white px-4 py-2.5 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50 min-h-[44px] text-sm";
const buttonSecondary =
  "px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 min-h-[44px] text-sm";

const FIELDS: (keyof ArticleIn)[] = [
  "code", "name", "un_number", "proper_shipping_name", "technical_name", "class",
  "packing_group", "type_of_package", "net_per_package", "notes",
];

function empty(): ArticleIn {
  return {
    code: "", name: "", un_number: "", proper_shipping_name: "", technical_name: "", class: "",
    packing_group: "", type_of_package: "", net_per_package: "", notes: "", active: true,
  };
}

export default function ArticlesPage({ user }: { user?: User }) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<"own" | "densities">("own");
  return <div className="collection-page page-enter space-y-4 sm:space-y-6">
    <h2 className="text-2xl font-semibold">{t("articles.title")}</h2>
    <div className="flex gap-2" role="group" aria-label={t("nav.library")}>
      {(["own", "densities"] as const).map(value => <button key={value} type="button" aria-pressed={tab === value} onClick={() => setTab(value)} className={tab === value ? buttonPrimary : buttonSecondary}>{t(`densities.tabs.${value}`)}</button>)}
    </div>
    <div hidden={tab !== "own"}><OwnGoods user={user} /></div>
    {tab === "densities" && <DensityCatalogue />}
  </div>;
}

function OwnGoods({ user }: { user?: User }) {
  const { t } = useTranslation();
  const toast = useToast();
  const { publicSettings } = usePreferences();
  const historyOn = !!publicSettings?.history_enabled;
  const [items, setItems] = useState<Article[]>([]);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState<ArticleIn>(empty());
  const [formOpen, setFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [removing, setRemoving] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);
  const [failure, setFailure] = useState("");
  const [importing, setImporting] = useState(false);
  const [importReport, setImportReport] = useState<ArticleImportResult | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const load = async () => {
    setLoading(true); setFailure("");
    try { setItems(await api.articles()); }
    catch (cause) { setFailure(String(cause)); }
    finally { setLoading(false); }
  };
  useEffect(() => {
    if (historyOn) void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [historyOn]);

  const shown = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return items;
    return items.filter((a) =>
      [a.code, a.name, a.un_number, a.proper_shipping_name].some((f) => f.toLowerCase().includes(needle)),
    );
  }, [items, search]);

  const save = async () => {
    if (!form.code.trim()) return;
    setSaving(true);
    try {
      if (editingId !== null) await api.updateArticle(editingId, form);
      else await api.saveArticle(form);
      setForm(empty());
      setFormOpen(false);
      setEditingId(null);
      await load();
      toast.success(t("articles.saved"));
    } catch (e) {
      toast.error(String(e));
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!removing) return;
    try {
      await api.deleteArticle(removing.id);
      setRemoving(null);
      await load();
    } catch (e) {
      toast.error(String(e));
    }
  };

  const importFile = async (file: File | undefined) => {
    if (!file || importing) return;
    setImporting(true); setImportReport(null);
    try {
      const result = await api.importArticlesFile(file);
      if (result.errors.length || result.skipped) setImportReport(result);
      else toast.success(t("articles.imported", { created: result.created, updated: result.updated, skipped: result.skipped }));
      await load();
    } catch (e) {
      toast.error(String(e));
    } finally {
      setImporting(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  if (!historyOn) return <HistoryStatus title={t("densities.tabs.own")} admin={user?.role === "admin"} />;

  return (
    <div className="collection-page page-enter space-y-4 sm:space-y-6">
      <div className="flex flex-wrap gap-2">
          <button type="button" className={buttonSecondary} onClick={() => api.downloadArticleTemplate().catch((e) => toast.error(String(e)))}>
            {t("articles.template")}
          </button>
          <button type="button" className={buttonSecondary} onClick={() => api.exportArticles().catch((e) => toast.error(String(e)))}>
            {t("articles.export")}
          </button>
          <button type="button" className={buttonSecondary} disabled={importing} onClick={() => fileInput.current?.click()}>
            {t(importing ? "import.importingFile" : "articles.import")}
          </button>
            <input
              ref={fileInput}
              type="file"
              disabled={importing}
              accept=".xlsx,.csv,.txt"
              className="sr-only"
              tabIndex={-1}
              aria-label={t("articles.import")}
              onChange={(e) => void importFile(e.target.files?.[0])}
            />
      </div>

      {importReport && <section className="surface p-4 space-y-2" aria-label={t("materieel.importDone")}>
        <p role="status" className="text-sm">{t("articles.imported", { created: importReport.created, updated: importReport.updated, skipped: importReport.skipped })}</p>
        {!!importReport.errors.length && <ul role="alert" className="space-y-2 text-sm text-amber-700 dark:text-amber-300">{importReport.errors.map((error, index) => <li key={index}>{error && typeof error === "object" && "code" in error ? translateMessage(error as ApiMessage) : String(error)}</li>)}</ul>}
      </section>}

      <details className="surface collection-form" open={formOpen} onToggle={(event) => setFormOpen(event.currentTarget.open)}>
        <summary><PlusIcon /><span>{editingId === null ? t("articles.add") : t("articles.edit")}</span><ChevronDownIcon /></summary>
        <div className="collection-form-body">
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {(["code", "name"] as const).map(key => <label key={key} className="text-sm text-slate-600 dark:text-slate-300">{t(`articles.fields.${key}`)}<input className={`${inputClass} mt-1`} value={form[key]} onChange={event => setForm({ ...form, [key]: event.target.value })} /></label>)}
          <details className="sm:col-span-2 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
            <summary className="cursor-pointer text-sm font-medium">{t("equipmentSimple.moreDetails")}</summary>
            <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {FIELDS.filter(key => key !== "code" && key !== "name").map(key => <label key={key} className={`text-sm text-slate-600 dark:text-slate-300 ${key === "notes" ? "sm:col-span-2 lg:col-span-3" : ""}`}>
                {t(`articles.fields.${key}`)}
                {key === "notes" ? <textarea className={`${inputClass} mt-1`} value={form[key] as string} onChange={event => setForm({ ...form, [key]: event.target.value })} /> : <input className={`${inputClass} mt-1`} value={form[key] as string} onChange={event => setForm({ ...form, [key]: event.target.value })} />}
              </label>)}
            </div>
          </details>
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} className="h-4 w-4 rounded text-brand-600" />
            {t("articles.fields.active")}
          </label>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" className={buttonPrimary} disabled={saving || !form.code.trim()} onClick={() => void save()}>
            {editingId === null ? t("articles.create") : t("articles.save")}
          </button>
          {editingId !== null && (
            <button type="button" className={buttonSecondary} onClick={() => { setForm(empty()); setEditingId(null); }}>
              {t("articles.cancel")}
            </button>
          )}
        </div>
        </div>
      </details>

      <section className={`${panelClass} p-4 sm:p-6`}>
        <input className={inputClass} placeholder={t("articles.search")} aria-label={t("articles.search")} value={search} onChange={(e) => setSearch(e.target.value)} />
        {failure ? <div role="alert" className="mt-3 space-y-2"><p className="text-sm text-red-600 dark:text-red-400">{failure}</p><button type="button" className={buttonSecondary} onClick={() => void load()}>{t("overview.retry")}</button></div> : loading ? <p className="mt-3 text-sm" role="status">{t("wizard.loading")}</p> : shown.length === 0 ? (
          <div className="mt-3 space-y-3"><p className="text-sm text-slate-500 dark:text-slate-400">{t(search ? "articles.noResults" : "articles.empty")}</p>{search && <button className={buttonSecondary} onClick={() => setSearch("")}>{t("history.clearFilters")}</button>}</div>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800">
                  <th className="px-2 py-1">{t("articles.fields.code")}</th>
                  <th className="px-2 py-1">{t("articles.fields.name")}</th>
                  <th className="px-2 py-1">UN</th>
                  <th className="px-2 py-1">{t("articles.fields.packing_group")}</th>
                  <th className="px-2 py-1">{t("articles.fields.type_of_package")}</th>
                  <th className="px-2 py-1">{t("articles.fields.net_per_package")}</th>
                  <th className="px-2 py-1"></th>
                </tr>
              </thead>
              <tbody>
                {shown.map((article) => (
                  <tr key={article.id} className={`border-b border-slate-100 dark:border-slate-800/60 ${article.active ? "" : "opacity-50"}`}>
                    <td className="px-2 py-2 font-medium text-slate-900 dark:text-slate-100">{article.code}</td>
                    <td className="px-2 py-2 text-slate-800 dark:text-slate-200">{article.name}</td>
                    <td className="px-2 py-2 text-slate-800 dark:text-slate-200">{article.un_number ? `UN ${article.un_number}` : "—"}</td>
                    <td className="px-2 py-2 text-slate-800 dark:text-slate-200">{article.packing_group || "—"}</td>
                    <td className="px-2 py-2 text-slate-800 dark:text-slate-200">{article.type_of_package || "—"}</td>
                    <td className="px-2 py-2 text-slate-800 dark:text-slate-200">{article.net_per_package || "—"}</td>
                    <td className="px-2 py-2 whitespace-nowrap">
                      <button type="button" className="text-brand-700 hover:underline dark:text-brand-300" onClick={() => { setEditingId(article.id); setFormOpen(true); setForm({ ...article }); window.scrollTo({ top: 0, behavior: "auto" }); }}>
                        {t("articles.edit")}
                      </button>
                      <button type="button" className="ml-3 text-red-700 hover:underline dark:text-red-300" onClick={() => setRemoving(article)}>
                        {t("articles.remove")}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <ConfirmDialog
        open={removing !== null}
        title={t("articles.remove")}
        body={t("articles.confirmRemove", { code: removing?.code ?? "" })}
        confirmLabel={t("articles.remove")}
        onConfirm={() => void remove()}
        onCancel={() => setRemoving(null)}
      />
    </div>
  );
}
