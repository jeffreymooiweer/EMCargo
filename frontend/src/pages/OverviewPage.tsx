import { ShieldIcon } from "../components/icons";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { api, ShipmentDetail, ShipmentSummary, type User } from "../api/client";
import { ModalityIcon } from "../components/WizardShell";
import { MoreIcon, ArrowRightIcon, PlusIcon, ShipmentsIcon, TripsIcon, ImportIcon } from "../components/icons";
import { usePreferences } from "../settings/preferences";
import HistoryStatus from "../components/HistoryStatus";
import { readSnapshot } from "../wizard/snapshot";
import { localDayRange } from "../utils/dateRanges";
import { AVAILABLE_MODALITIES, isModalityAvailable } from "./ModalitySelectPage";

export default function OverviewPage({ user }: { user?: User }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { publicSettings, preferences } = usePreferences();
  const history = !!publicSettings?.history_enabled;
  const [draft, setDraft] = useState<ShipmentDetail | null>(null);
  const [recent, setRecent] = useState<ShipmentSummary[]>([]);
  const [counts, setCounts] = useState<{ shipments: number; trips: number } | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(history);
  const [error, setError] = useState(false);
  const [discarding, setDiscarding] = useState(false);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    if (!history) { setDraft(null); setRecent([]); setCounts(null); setLoading(false); setError(false); return; }
    let alive = true;
    setLoading(true); setError(false); setDraft(null); setRecent([]); setCounts(null);
    const day = localDayRange();
    const fail = () => { if (alive) setError(true); };
    api.runningDraft().then((value) => { if (alive) setDraft(value); }).catch(fail);
    api.shipments({ per_page: 5, page: 1 })
      .then((page) => { if (alive) setRecent(page.items.filter((item) => !item.is_draft)); })
      .catch(fail).finally(() => { if (alive) setLoading(false); });
    Promise.all([
      api.shipments({ date_from: day.from, date_to: day.to, per_page: 1 }),
      api.trips({ date_from: day.from, date_to: day.to, per_page: 1 }),
    ]).then(([shipments, trips]) => { if (alive) setCounts({ shipments: shipments.total, trips: trips.total }); }).catch(fail);
    return () => { alive = false; };
  }, [history, reload]);

  const draftModality = draft ? readSnapshot(draft.snapshot)?.modality || draft.modality : "";
  const draftTime = draft ? new Date(draft.updated_at).toLocaleTimeString(i18n.language, { timeStyle: "short" }) : "";
  const filtered = recent.filter((item) => [item.reference, item.consignor_name, item.consignee_name].some((value) => value?.toLocaleLowerCase().includes(query.toLocaleLowerCase())));
  const preferred = isModalityAvailable(preferences.default_modality) ? preferences.default_modality : "road";
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";

  async function discard() {
    setDiscarding(true);
    try { await api.discardDraft(); setDraft(null); }
    catch { setError(true); }
    finally { setDiscarding(false); }
  }

  return (
    <div className="overview-workspace collection-page page-enter space-y-6">
      <div className="page-heading">
        <div>
          <p className="eyebrow">{t("nav.overview")}</p><h2>{t(`overview.${greeting}`)}{user?.username && <span className="overview-name"> {user.display_name || user.username}</span>}</h2>
          <p>{history ? t("overview.intro") : t("overview.introNoHistory")}</p>
        </div>
        <Link to="/" className="action-primary"><PlusIcon className="h-5 w-5" />{t("nav.new")}</Link>
      </div>
      <Link to="/dg-reviews" className="surface review-summary"><ShieldIcon className="h-7 w-7" /><div><h3 className="font-semibold">{t("dgReview.title")}</h3><p>{t(user?.role === "dg_specialist" || user?.role === "admin" ? "dgReview.queueHint" : "dgReview.mineHint")}</p></div></Link>
      {error && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
        <span>{t("overview.loadError")}</span>
        <button className="action-secondary" onClick={() => setReload((value) => value + 1)}>{t("overview.retry")}</button>
      </div>}
      {history && <section className="surface overview-today">
        <h3 className="surface-title">{t("overview.todayTitle")}</h3>
        <div className="overview-metrics">
          {[{ label: "overview.todayShipments", value: counts?.shipments, icon: ShipmentsIcon, to: "/shipments" }, { label: "overview.todayTrips", value: counts?.trips, icon: TripsIcon, to: "/trips" }].map(({ label, value, icon: Icon, to }) => <Link key={label} to={to} className="overview-metric">
            <span className="icon-tile"><Icon className="h-5 w-5" /></span>
            <div><p className="text-2xl font-semibold tabular-nums">{value ?? "—"}</p><p className="text-xs text-slate-500 dark:text-slate-400">{t(label)}</p></div>
          </Link>)}
        </div>
      </section>}

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
        <div className="min-w-0 space-y-6">
          {history && draft && <section data-testid="resume-entry" className="surface overview-resume p-5 sm:p-6">
            <h3 className="surface-title">{t("overview.resumeTitle")}</h3>
            <div className="overview-resume-content">
              <span className="icon-tile"><ModalityIcon modality={draftModality} className="h-6 w-6" /></span>
              <div className="min-w-0 flex-1 basis-44">
                <p className="break-words font-semibold">{draft.reference || draft.consignee_name || t("wizard.newShipment")}</p>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{t(`modality.${draftModality}`)} · {t("draft.savedAt", { time: draftTime })}</p>
              </div>
              <Link className="action-primary" to={`/wizard/${draftModality || "road"}`}>{t("overview.resume")}<ArrowRightIcon className="inline h-4 w-4" /></Link>
            </div>
            <div className="mt-2 text-right"><button disabled={discarding} className="min-h-[44px] px-2 text-xs text-slate-500 hover:underline dark:text-slate-400" onClick={() => void discard()}>{t("draft.discard")}</button></div>
          </section>}
          {history && <section className="surface">
            <div className="flex flex-wrap items-center justify-between gap-3 p-5 sm:p-6">
              <h3 className="surface-title">{t("overview.recentTitle")}</h3>
              <Link to="/shipments" className="text-sm font-medium text-brand-600 hover:underline dark:text-brand-300">{t("overview.allShipments")} <ArrowRightIcon className="inline h-4 w-4" /></Link>
              <label className="relative w-full">
                <span className="sr-only">{t("overview.search")}</span>
                <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("overview.search")} className="min-h-[44px] w-full rounded-lg border border-slate-200 bg-slate-50 px-4 text-sm dark:border-slate-700 dark:bg-slate-950/50" />
              </label>
            </div>
            {loading ? <p role="status" className="px-6 pb-6 text-sm text-slate-500">{t("overview.loading")}</p> : filtered.length === 0 ? <div className="px-6 pb-8 text-center">
              <ShipmentsIcon className="mx-auto mb-3 h-9 w-9 text-slate-400" />
              <p className="text-sm text-slate-500 dark:text-slate-400">{query ? t("overview.noResults") : error ? t("overview.unavailable") : t("overview.recentEmpty")}</p>
              {!query && !error && <Link to="/" className="action-secondary mt-4">{t("nav.new")}</Link>}
            </div> : <div>
              <div className="recent-table-head" aria-hidden="true"><span>{t("overview.reference")}</span><span>{t("overview.route")}</span><span>{t("overview.status")}</span><span>{t("overview.updated")}</span><span /></div>
              <ul className="divide-y divide-slate-200 dark:divide-slate-800">
              {filtered.map((shipment) => <li key={shipment.id} className="recent-table-row">
                <Link className="recent-reference min-w-0 break-words text-sm font-medium hover:text-brand-400" to={`/wizard/${shipment.modality || "road"}?shipment=${shipment.id}`}>{shipment.reference || shipment.consignee_name || `#${shipment.id}`}</Link>
                <div className="recent-route min-w-0 text-sm">
                  <p className="break-words">{shipment.consignor_name || "—"} <ArrowRightIcon className="inline h-4 w-4" /> {shipment.consignee_name || "—"}</p>
                  <span className="mt-1 inline-flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400"><ModalityIcon modality={shipment.modality} className="h-3.5 w-3.5" />{t(`modality.${shipment.modality}`)}{shipment.has_dangerous_goods && ` · ${t("overview.dg")}`}</span>
                </div>
                <span className={`recent-status text-xs ${shipment.has_documents ? "text-emerald-700 dark:text-emerald-300" : "text-slate-500 dark:text-slate-400"}`}>{shipment.has_documents ? t("overview.documentsAvailable") : t("overview.kept")}</span>
                <time className="recent-date text-xs text-slate-500 dark:text-slate-400" dateTime={shipment.updated_at}>{new Date(shipment.updated_at).toLocaleDateString(i18n.language)}</time>
                <details className="recent-menu relative">
                  <summary className="flex h-11 w-11 cursor-pointer list-none items-center justify-center rounded hover:bg-slate-100 dark:hover:bg-slate-800" aria-label={t("review.moreActions")}><MoreIcon /></summary>
                  <div className="absolute right-0 z-20 min-w-44 rounded-lg border border-slate-200 bg-white p-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">
                    <Link className="action-secondary w-full border-0 justify-start" to={`/wizard/${shipment.modality || "road"}?shipment=${shipment.id}`}>{t("overview.open")}</Link>
                    <Link className="action-secondary w-full border-0 justify-start" to={`/wizard/${shipment.modality || "road"}?template=${shipment.id}`}>{t("overview.asTemplate")}</Link>
                  </div>
                </details>
              </li>)}
            </ul></div>}
          </section>}
          {!history && <HistoryStatus title={t("nav.overview")} admin={user?.role === "admin"} embedded />}
        </div>
        <aside className="space-y-6">
          <section className="surface overview-quick p-5">
            <h3 className="surface-title">{t("overview.startTitle")}</h3>
            <div className="mt-4 space-y-2">
              <Link to={`/wizard/${preferred}?input=paste`} className="action-secondary w-full justify-between"><span className="flex items-center gap-2"><ImportIcon className="h-5 w-5" />{t("overview.paste")}</span><ArrowRightIcon className="inline h-4 w-4" /></Link>
              {AVAILABLE_MODALITIES.map((key) => <button key={key} type="button" onClick={() => navigate(`/wizard/${key}`)} className="action-secondary w-full justify-between">
                <span className="flex items-center gap-2"><ModalityIcon modality={key} className="h-5 w-5" />{t(`modality.${key}`)}</span><ArrowRightIcon className="inline h-4 w-4" />
              </button>)}
            </div>
            <Link to="/?choose=1" className="mt-3 inline-flex min-h-[44px] items-center text-xs text-slate-500 hover:underline dark:text-slate-400">{t("wizard.changeModality")}</Link>
          </section>
        </aside>
      </div>
    </div>
  );
}
