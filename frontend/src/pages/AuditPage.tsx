/**
 * The administrator's audit log: who did what, when.
 *
 * Metadata only, by the server's design — the page shows an action code
 * translated into a sentence, the actor, a short summary in the
 * application's own words (a reference, a document key, the settings keys
 * that changed) and the address the request came from. Four filters — the
 * actor, the action or its group, a date range — a paged table, and the
 * same selection as CSV for whoever keeps records elsewhere.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { api, AuditEvent } from "../api/client";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2.5 text-sm min-h-[44px]";
const buttonSecondary =
  "px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 min-h-[44px] text-sm inline-flex items-center";

const PER_PAGE = 50;

/** The groups the action filter offers before the individual codes. */
export const ACTION_GROUPS = ["auth", "user", "settings", "shipment", "dg_review", "trip", "documents", "report"];

function when(iso: string, language: string): string {
  try {
    return new Date(iso).toLocaleString(language, { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export default function AuditPage() {
  const { t, i18n } = useTranslation();
  const [items, setItems] = useState<AuditEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [actor, setActor] = useState("");
  const [action, setAction] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [failure, setFailure] = useState("");
  const request = useRef(0);
  const [actions, setActions] = useState<string[]>([]);
  const [actors, setActors] = useState<string[]>([]);

  useEffect(() => {
    api.auditActions()
      .then((answer) => {
        setActions(answer.actions);
        setActors(answer.actors);
      })
      .catch(() => {
        setActions([]);
        setActors([]);
      });
  }, []);

  const query = useCallback(() => ({
    actor,
    action,
    since: from ? `${from}T00:00:00` : undefined,
    until: to ? `${to}T23:59:59` : undefined,
  }), [actor, action, from, to]);

  const load = useCallback(async () => {
    const current = ++request.current;
    setLoading(true);
    setFailure("");
    setItems([]);
    try {
      const answer = await api.audit({ ...query(), page, per_page: PER_PAGE });
      if (current !== request.current) return;
      setItems(answer.items);
      setTotal(answer.total);
    } catch (e) {
      if (current === request.current) setFailure(String(e));
    } finally {
      if (current === request.current) setLoading(false);
    }
  }, [query, page]);

  useEffect(() => {
    void load();
    return () => { request.current += 1; };
  }, [load]);

  const pages = Math.max(1, Math.ceil(total / PER_PAGE));
  // A code the interface has no sentence for is shown as the code itself —
  // a new action on the server must not become an empty cell here.
  const label = (code: string) => {
    const key = `audit.actions.${code}`;
    const text = t(key);
    return text === key ? code : text;
  };
  const groupLabel = (group: string) => {
    const key = `audit.groups.${group}`;
    const text = t(key);
    return text === key ? group : text;
  };

  return (
    <div className="collection-page page-enter space-y-4 sm:space-y-6">
      <div className={`${panelClass} p-5 sm:p-8 flex flex-wrap items-start justify-between gap-3`}>
        <div>
          <h2 className="text-xl sm:text-2xl font-semibold text-slate-900 dark:text-slate-100">{t("audit.title")}</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          <a className={buttonSecondary} href={api.auditExportUrl(query())} download="emcargo-audit.csv">
            {t("audit.export")}
          </a>
          <Link to="/admin/settings/organisation" className={buttonSecondary}>
            {t("audit.retention")}
          </Link>
        </div>
      </div>

      <div className={`${panelClass} p-4 sm:p-5 grid items-end gap-3 md:grid-cols-4`}>
        <select
          className={inputClass}
          value={actor}
          onChange={(e) => {
            setActor(e.target.value);
            setPage(1);
          }}
          aria-label={t("audit.actor")}
        >
          <option value="">{t("audit.allActors")}</option>
          {actors.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
        <select
          className={inputClass}
          value={action}
          onChange={(e) => {
            setAction(e.target.value);
            setPage(1);
          }}
          aria-label={t("audit.action")}
        >
          <option value="">{t("audit.allActions")}</option>
          {ACTION_GROUPS.map((group) => (
            <optgroup key={group} label={groupLabel(group)}>
              <option value={group}>{t("audit.wholeGroup", { group: groupLabel(group) })}</option>
              {actions.filter((code) => code.startsWith(`${group}.`)).map((code) => (
                <option key={code} value={code}>
                  {label(code)}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
        <label className="text-xs text-slate-500 dark:text-slate-400">
          {t("audit.from")}
          <input type="date" className={`${inputClass} mt-1`} max={to || undefined} value={from} onChange={(e) => { setFrom(e.target.value); setPage(1); }} />
        </label>
        <label className="text-xs text-slate-500 dark:text-slate-400">
          {t("audit.to")}
          <input type="date" className={`${inputClass} mt-1`} min={from || undefined} value={to} onChange={(e) => { setTo(e.target.value); setPage(1); }} />
        </label>
        <div className="flex flex-wrap items-center justify-between gap-3 md:col-span-4">
          <p role="status" className="text-sm text-slate-500 dark:text-slate-400">
            {loading ? t("wizard.loading") : !failure && t("audit.count", { count: items.length, total })}
          </p>
          {(actor || action || from || to) && <button type="button" className={buttonSecondary} onClick={() => {
            setActor(""); setAction(""); setFrom(""); setTo(""); setPage(1);
          }}>{t("history.clearFilters")}</button>}
        </div>
      </div>

      {failure && <div className={`${panelClass} p-5 space-y-3`}>
        <p role="alert">{failure}</p>
        <button type="button" className={buttonSecondary} onClick={() => void load()}>{t("historyAccess.retry")}</button>
      </div>}
      {!loading && !failure && items.length === 0 && (
        <p className={`${panelClass} p-5 text-sm text-slate-600 dark:text-slate-300`}>{t("audit.empty")}</p>
      )}

      {/* Phone: cards */}
      <div className="space-y-3 md:hidden">
        {items.map((e) => (
          <div key={e.id} className={`${panelClass} shadow-sm p-4 space-y-1`}>
            <div className="flex items-center gap-2">
              <span className="min-w-0 truncate font-semibold text-slate-900 dark:text-slate-100">{label(e.action)}</span>
            </div>
            <p className="break-words text-sm text-slate-700 dark:text-slate-200">
              {e.actor_username || "—"}
              {e.summary ? ` · ${e.summary}` : ""}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {when(e.at, i18n.language)}
              {e.client ? ` · ${e.client}` : ""}
            </p>
          </div>
        ))}
      </div>

      {/* Desktop: table */}
      {items.length > 0 && (
        <div className={`${panelClass} hidden overflow-x-auto md:block`}>
          <table className="w-full text-sm text-slate-800 dark:text-slate-200">
            <thead className="bg-slate-50 dark:bg-slate-800/80">
              <tr>
                <th className="px-3 py-2 text-left">{t("audit.when")}</th>
                <th className="px-3 py-2 text-left">{t("audit.actor")}</th>
                <th className="px-3 py-2 text-left">{t("audit.action")}</th>
                <th className="px-3 py-2 text-left">{t("audit.summary")}</th>
                <th className="px-3 py-2 text-left">{t("audit.client")}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((e) => (
                <tr key={e.id} className="border-t border-slate-100 dark:border-slate-800">
                  <td className="px-3 py-2 whitespace-nowrap">{when(e.at, i18n.language)}</td>
                  <td className="px-3 py-2">{e.actor_username || "—"}</td>
                  <td className="px-3 py-2" title={e.action}>{label(e.action)}</td>
                  <td className="px-3 py-2">
                    {e.summary || "—"}
                    {e.target_type && e.target_id ? (
                      <span className="ml-2 text-xs text-slate-500 dark:text-slate-400">
                        {e.target_type} {/^\d+$/.test(e.target_id) ? `#${e.target_id}` : e.target_id}
                      </span>
                    ) : null}
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap text-slate-500 dark:text-slate-400">{e.client || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && !failure && pages > 1 && (
        <div className="flex items-center justify-between gap-3">
          <button type="button" className={buttonSecondary} disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            {t("audit.previous")}
          </button>
          <span className="text-sm text-slate-500 dark:text-slate-400">{t("audit.page", { page, pages })}</span>
          <button type="button" className={buttonSecondary} disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>
            {t("audit.next")}
          </button>
        </div>
      )}
    </div>
  );
}
