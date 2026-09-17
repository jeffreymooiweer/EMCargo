import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type DocumentTemplate } from "../api/client";

const input = "w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-3";

export default function DocumentTemplatesPanel() {
  const { t } = useTranslation();
  const [items, setItems] = useState<DocumentTemplate[]>([]);
  const [key, setKey] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [source, setSource] = useState("");
  const [basis, setBasis] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  const [loading, setLoading] = useState(true);
  const submitting = useRef(false);
  const load = async () => {
    setLoading(true);
    try { setItems(await api.documentTemplates()); }
    finally { setLoading(false); }
  };
  const retry = () => {
    setMessage(""); setFailed(false);
    void load().catch((e: Error) => { setFailed(true); setMessage(e.message); });
  };
  useEffect(() => { retry(); }, []);
  const selected = items.find((item) => item.id === key);
  return <section className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4" aria-busy={busy || loading}>
    <h3 className="text-lg font-semibold">{t("templates.title")}</h3>
    <label className="block space-y-1"><span>{t("templates.choose")}</span>
      <select className={input} value={key} disabled={busy || loading || items.length === 0} onChange={(e) => { setKey(e.target.value); setMessage(""); setFailed(false); setFile(null); setSource(""); setBasis(""); }}>
        <option value="">{t(loading ? "wizard.loading" : !failed && items.length === 0 ? "templates.empty" : "templates.choose")}</option>
        {items.map((item) => <option key={item.id} value={item.id}>{item.name} — {t(item.available ? "templates.available" : "templates.missing")}</option>)}
      </select>
    </label>
    {selected && <form key={key} className="space-y-4" onSubmit={async (e) => {
      e.preventDefault(); if (!file || submitting.current) return;
      submitting.current = true;
      setBusy(true); setMessage(""); setFailed(false);
      try { await api.importDocumentTemplate(key, file, source, basis); await load(); setMessage(t("templates.saved")); }
      catch (err) { setFailed(true); setMessage((err as Error).message); }
      finally { submitting.current = false; setBusy(false); }
    }}>
      <p className="text-sm">{selected.filename} · {t("templates.pages", { count: selected.pages })}</p>
      {selected.available && <a className="text-brand-600 underline" href={`/api/settings/document-templates/${encodeURIComponent(key)}/preview`} target="_blank" rel="noreferrer">{t("templates.preview")}</a>}
      <fieldset disabled={busy} className="space-y-4">
        <label className="block space-y-1"><span>{t("templates.file")}</span><input className={input} type="file" accept="application/pdf,.pdf" required onChange={(e) => setFile(e.target.files?.[0] || null)} /></label>
        <label className="block space-y-1"><span>{t("templates.source")}</span><input className={input} value={source} maxLength={1000} required onChange={(e) => setSource(e.target.value)} /></label>
        <label className="block space-y-1"><span>{t("templates.usageRights")}</span><textarea className={input} value={basis} maxLength={1000} required onChange={(e) => setBasis(e.target.value)} /></label>
      </fieldset>
      <button type="submit" disabled={busy || !file || !source.trim() || !basis.trim()} className="rounded-lg bg-brand-600 px-5 py-3 text-white disabled:opacity-50">{t(busy ? "templates.importing" : "templates.import")}</button>
    </form>}
    {message && <p role={failed ? "alert" : "status"} className={failed ? "text-red-700 dark:text-red-300" : "text-green-700 dark:text-green-300"}>{message}</p>}
    {failed && !items.length && <button type="button" className="action-secondary" disabled={loading} onClick={retry}>{t("history.retry")}</button>}
  </section>;
}
