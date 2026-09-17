import DeliveryActivity from "../components/DeliveryActivity";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { useTranslation } from "react-i18next";
import { api, type User, type WorkBucket, type WorkItem, type WorkPage } from "../api/client";
import { ArrowRightIcon, CheckIcon, CloseIcon, ImportIcon, MoreIcon, PlusIcon, RefreshIcon } from "../components/icons";
import HistoryStatus from "../components/HistoryStatus";
import { usePreferences } from "../settings/preferences";
import { isModalityAvailable } from "./ModalitySelectPage";
import "./overview.css";

function localDate() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

export function workDestination(item: WorkItem): string {
  if (!isModalityAvailable(item.modality || "preparation")) return item.kind === "review" ? `/dg-reviews/${item.id}` : "/shipments";
  if (item.kind === "review") return item.status === "review" || item.status === "waiting"
    ? `/dg-reviews/${item.id}` : `/wizard/${item.modality || "preparation"}?review=${item.id}`;
  return item.is_draft ? `/wizard/${item.modality || "preparation"}` : `/wizard/${item.modality || "preparation"}?shipment=${item.id}`;
}

export default function OverviewPage({ user }: { user?: User }) {
  const { t, i18n } = useTranslation();
  const { publicSettings, preferences } = usePreferences();
  const [bucket, setBucket] = useState<WorkBucket>("attention");
  const [query, setQuery] = useState("");
  const [mine, setMine] = useState(false);
  const [page, setPage] = useState(1);
  const [day, setDay] = useState(localDate);
  const [data, setData] = useState<WorkPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [failure, setFailure] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [editing, setEditing] = useState<WorkItem | null>(null);
  const [people, setPeople] = useState<{ id: number; name: string }[]>([]);
  const [owner, setOwner] = useState("");
  const [peopleLoading, setPeopleLoading] = useState(false);
  const [peopleFailure, setPeopleFailure] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState("");
  const sequence = useRef(0);
  const editor = useRef<HTMLDivElement>(null);
  const mounted = useRef(true);
  const preferred = isModalityAvailable(preferences.default_modality) ? preferences.default_modality : "road";

  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    const update = () => { setDay(localDate()); setRefresh(value => value + 1); };
    const visible = () => { if (!document.hidden) update(); };
    const interval = setInterval(visible, 60_000);
    document.addEventListener("visibilitychange", visible);
    return () => { clearInterval(interval); document.removeEventListener("visibilitychange", visible); };
  }, []);
  useEffect(() => {
    const current = ++sequence.current;
    setLoading(true); setFailure("");
    void api.work({ day, bucket, q: query, mine, page }).then(result => {
      if (sequence.current !== current) return;
      const last = Math.max(1, Math.ceil(result.total / result.per_page));
      if (page > last) { setPage(last); return; }
      setData(result);
    }).catch(() => { if (sequence.current === current) setFailure(t("work.loadFailed")); })
      .finally(() => { if (sequence.current === current) setLoading(false); });
    return () => { ++sequence.current; };
  }, [day, bucket, query, mine, page, refresh, i18n.language]);

  useEffect(() => {
    if (!editing) return;
    let alive = true;
    setPeople([]); setPeopleLoading(true); setPeopleFailure(""); setOwner(String(editing.owner_id ?? ""));
    void api.workPeople(Number(editing.id)).then(result => { if (alive) setPeople(result); })
      .catch(() => { if (alive) setPeopleFailure(t("work.peopleFailed")); })
      .finally(() => { if (alive) setPeopleLoading(false); });
    const trigger = document.activeElement as HTMLElement | null;
    editor.current?.querySelector<HTMLElement>("button")?.focus();
    const keys = (event: KeyboardEvent) => {
      if (event.key === "Escape") setEditing(null);
      if (event.key !== "Tab") return;
      const controls = Array.from(editor.current?.querySelectorAll<HTMLElement>("button:not(:disabled), select:not(:disabled)") || []);
      if (event.shiftKey && document.activeElement === controls[0]) { event.preventDefault(); controls[controls.length - 1]?.focus(); }
      else if (!event.shiftKey && document.activeElement === controls[controls.length - 1]) { event.preventDefault(); controls[0]?.focus(); }
    };
    document.addEventListener("keydown", keys);
    return () => { alive = false; document.removeEventListener("keydown", keys); trigger?.focus(); };
  }, [editing, i18n.language]);

  function filter(next: WorkBucket) { setBucket(next); setPage(1); }
  async function change(item: WorkItem, update: { owner_id?: number; completed?: boolean }) {
    if (saving) return;
    setSaving(true); setPeopleFailure(""); setSaved("");
    try {
      await api.changeWork(Number(item.id), { version: item.version, ...update });
      if (!mounted.current) return;
      setEditing(null); setRefresh(value => value + 1); setSaved(t("work.saved"));
    } catch (cause) {
      if (mounted.current) setPeopleFailure(String(cause));
    } finally { if (mounted.current) setSaving(false); }
  }

  const actionKey = (item: WorkItem) => item.completed_at ? "open" : !isModalityAvailable(item.modality || "preparation") ? "view"
    : item.is_draft ? "continue" : ({ prepare: "complete", documents: "documents", ready: "open",
        review_required: "release", review: "review", waiting: "view", changes: "correct", approved: "documents" } as const)[item.status];
  const name = (item: WorkItem) => item.reference || item.consignee || t("work.unnamed");
  const total = data?.total ?? 0;
  const perPage = data?.per_page ?? 20;
  const hour = new Date().getHours();

  return <div className="overview-workspace collection-page page-enter work-overview">
    <header className="page-heading"><div><p className="eyebrow">{t("nav.overview")}</p>
      <h2>{t(`overview.${hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening"}`)}{user && <span className="overview-name"> {user.display_name || user.username}</span>}</h2>
      </div>
      <div className="work-create"><Link to="/" className="action-primary"><PlusIcon />{t("nav.new")}</Link>
        <Link to={`/wizard/${preferred}?input=document`} className="action-secondary"><ImportIcon />{t("work.import")}</Link></div>
    </header>
    <div className="work-buckets" aria-label={t("work.filters")}>
      {(["attention", "waiting", "today", "ready"] as WorkBucket[]).map(key => <button type="button" key={key}
        className="work-bucket" data-active={bucket === key} aria-pressed={bucket === key} onClick={() => filter(key)}>
        <span>{t(`work.bucket.${key}`)}</span><strong>{data ? data.counts[key] : "—"}</strong></button>)}
    </div>
    <section className="surface work-surface" aria-label={t("work.list")} aria-busy={loading}>
      <div className="work-toolbar"><label className="work-search"><span className="sr-only">{t("work.search")}</span>
        <input type="search" value={query} maxLength={120} placeholder={t("work.search")} onChange={event => { setQuery(event.target.value); setPage(1); }} /></label>
        <label className="work-mine"><input type="checkbox" checked={mine} onChange={event => { setMine(event.target.checked); setPage(1); }} />{t("work.mine")}</label>
        <label><span className="sr-only">{t("work.filters")}</span><select value={bucket} onChange={event => filter(event.target.value as WorkBucket)}>
          {(["attention", "waiting", "today", "ready", "all", "closed"] as WorkBucket[]).map(key => <option key={key} value={key}>{t(`work.bucket.${key}`)}</option>)}
        </select></label>
        <button type="button" className="work-icon" aria-label={t("work.refresh")} disabled={loading} onClick={() => setRefresh(value => value + 1)}><RefreshIcon /></button>
      </div>
      {failure ? <div className="work-empty" role="alert"><p>{failure}</p><button className="action-secondary" onClick={() => setRefresh(value => value + 1)}>{t("overview.retry")}</button></div>
        : !data || loading && !data.items.length ? <p className="work-empty" role="status">{t("overview.loading")}</p>
        : !data.items.length ? <div className="work-empty"><CheckIcon /><h3>{t("work.empty")}</h3>{query || mine ? <button className="action-secondary" onClick={() => { setQuery(""); setMine(false); setPage(1); }}>{t("history.clearFilters")}</button> : <Link className="action-secondary" to="/">{t("nav.new")}</Link>}</div>
        : <><div className="work-row work-column-labels" aria-hidden="true"><span>{t("work.shipment")}</span><span>{t("work.next")}</span><span>{t("work.owner")}</span><span>{t("work.loadingDate")}</span><span /></div>
          <ul className="work-list">{data.items.map(item => <li className="work-row" key={`${item.kind}:${item.id}`}>
            <div className="work-shipment"><Link to={workDestination(item)}>{name(item)}</Link>
              <p>{item.consignor && item.consignee ? `${item.consignor} → ${item.consignee}` : t(`modality.${item.modality || "preparation"}`)}</p>
              {item.is_draft && <span className="work-private">{t("work.privateDraft")}</span>}</div>
            <div className="work-next"><span className="work-status" data-status={item.completed_at ? "closed" : item.status}>{t(`work.status.${item.completed_at ? "closed" : item.status}`)}</span>
              {!item.completed_at && item.issues.length > 0 && <p>{t(`work.issue.${item.issues[0]}`, { defaultValue: t("work.issue.reopen") })}</p>}</div>
            <div className="work-owner"><span className="work-mobile-label">{t("work.owner")}</span>{item.status === "review" || item.status === "waiting" ? t("work.specialistTeam") : item.owner_name || t("work.unassigned")}</div>
            <div className="work-date" data-overdue={item.overdue}><span className="work-mobile-label">{t("work.loadingDate")}</span>
              {item.due_date ? <><time dateTime={item.due_date}>{new Date(`${item.due_date}T12:00:00`).toLocaleDateString(i18n.language, { day: "numeric", month: "short" })}</time>{item.overdue && <small>{t("work.overdue")}</small>}</> : <span>{t("work.noDate")}</span>}</div>
            <div className="work-actions"><Link className="work-primary" to={workDestination(item)}>{t(`work.action.${actionKey(item)}`)}<ArrowRightIcon /></Link>
              {item.kind === "shipment" && !item.is_draft && <button type="button" className="work-icon" disabled={loading || saving} aria-label={t("work.manage", { name: name(item) })} onClick={() => setEditing(item)}><MoreIcon /></button>}</div>
          </li>)}</ul></>}
      {data && !failure && <div className="work-pagination"><span role="status">{loading ? t("overview.loading") : t("work.count", { count: total })}</span>
        {total > perPage && <div><button type="button" className="action-secondary" disabled={loading || page === 1} onClick={() => setPage(value => value - 1)}>{t("wizard.back")}</button>
          <span>{page} / {Math.ceil(total / perPage)}</span><button type="button" className="action-secondary" disabled={loading || page * perPage >= total} onClick={() => setPage(value => value + 1)}>{t("wizard.next")}</button></div>}</div>}
    </section>
    <p className="work-feedback" role="status">{saved}</p>
    {publicSettings?.history_enabled && <DeliveryActivity compact />}
    {!publicSettings?.history_enabled && <HistoryStatus title={t("nav.shipments")} admin={user?.role === "admin" || user?.role === "super_user"} embedded />}
    {editing && <div className="work-modal-backdrop"><div ref={editor} className="surface work-editor" role="dialog" aria-modal="true" aria-labelledby="work-editor-title">
      <header><h3 id="work-editor-title">{name(editing)}</h3><button className="work-icon" aria-label={t("work.close")} disabled={saving} onClick={() => setEditing(null)}><CloseIcon /></button></header>
      <label>{t("work.owner")}<select value={owner} disabled={peopleLoading || saving} onChange={event => setOwner(event.target.value)}>
        <option value="">{t(peopleLoading ? "overview.loading" : "work.chooseOwner")}</option>
        {people.map(person => <option key={person.id} value={person.id}>{person.name}</option>)}
      </select></label>
      <button className="action-primary" disabled={saving || !owner || Number(owner) === editing.owner_id} onClick={() => void change(editing, { owner_id: Number(owner) })}>{t("work.assign")}</button>
      {(editing.completed_at || editing.status === "ready") && <div className="work-completion">
        <button className="action-secondary" disabled={saving} onClick={() => void change(editing, { completed: !editing.completed_at })}>{t(editing.completed_at ? "work.reopen" : "work.finish")}</button></div>}
      {peopleFailure && <p role="alert" className="editor-feedback" data-kind="error">{peopleFailure}</p>}
    </div></div>}
  </div>;
}
