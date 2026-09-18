import ShipmentRoutingSummary from "../components/ShipmentRoutingSummary";
import type { Routing } from "../wizard/routing";
import DeliveryActivity from "../components/DeliveryActivity";
import { canOversee } from "../permissions";
import HistoryStatus from "../components/HistoryStatus";
import CargoSummary from "../components/cargo/CargoSummary";
import { cargoGoods, cargoLines } from "../wizard/cargoState";
import { readSnapshot } from "../wizard/snapshot";
import { readCargo } from "../utils/cargo";
import type { LineItem } from "../api/client";
/**
 * The shipments this installation kept.
 *
 * Exists only where the history is switched on; elsewhere the page says so
 * rather than showing an empty table over a 404. A table on a wide screen,
 * cards on a phone — the same split the equipment library uses — with three
 * filters: a search over reference and parties, the transport mode, and a
 * date range. Opening a row shows the record and offers the three things
 * one does with a kept shipment: open it in the wizard, download its
 * documents again, or remove it.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";

import { api, Department, ShipmentDetail, ShipmentSummary, User } from "../api/client";
import { usePreferences } from "../settings/preferences";
import ConfirmDialog from "../toast/ConfirmDialog";
import { useToast } from "../toast/ToastProvider";
import { localDateFilters } from "../utils/dateRanges";
import { MODALITIES } from "./ModalitySelectPage";
import { ArrowRightIcon, CloseIcon, CodeIcon, CopyIcon, DownloadIcon, PenIcon, RefreshIcon, RoadIcon, SearchIcon, SettingsIcon, TrashIcon } from "../components/icons";
import "./shipments.css";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2.5 text-sm min-h-[44px]";
const actionClass =
  "font-medium text-brand-700 underline hover:text-brand-800 disabled:opacity-50 dark:text-brand-300";

const PER_PAGE = 25;

function when(iso: string, language: string): string {
  try {
    return new Date(iso).toLocaleString(language, { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
}

/** The wizard address a kept shipment opens at: its own mode, its own id. */
export function wizardLinkFor(shipment: ShipmentSummary): string {
  return `/wizard/${shipment.modality || "preparation"}?shipment=${shipment.id}`;
}

/** The wizard address that starts a new shipment from a kept one: the same
 *  goods, parties and route, without the reference, the dates or the
 *  record's identity. */
export function templateLinkFor(shipment: ShipmentSummary): string {
  return `/wizard/${shipment.modality || "preparation"}?template=${shipment.id}`;
}

export default function ShipmentsPage({ user }: { user?: User | null }) {
  const { t, i18n } = useTranslation();
  const { publicSettings } = usePreferences();
  const { id } = useParams();
  // Roles with oversight can filter departments. The server restricts
  // other viewers to their own department regardless of query parameters.
  const admin = canOversee(user);

  if (!publicSettings?.history_enabled) return <HistoryStatus title={t("history.title")} admin={user?.role === "admin"} />;

  if (id) return <ShipmentView id={Number(id)} language={i18n.language} />;
  return <ShipmentList language={i18n.language} admin={admin} />;
}

function ShipmentList({ language, admin }: { language: string; admin: boolean }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const toast = useToast();
  const [items, setItems] = useState<ShipmentSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [modality, setModality] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [department, setDepartment] = useState("");
  const [departments, setDepartments] = useState<Department[]>([]);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState<ShipmentSummary | null>(null);
  const requestVersion = useRef(0);
  const actionRunning = useRef(false);
  // The entry this viewer is in the middle of. It is not a kept shipment and
  // the list does not hold it — but it is the thing they are most likely to
  // have come here for, so it stands above the list with the way back into it.
  const [draft, setDraft] = useState<ShipmentDetail | null>(null);
  // The shipments picked for a trip. Kept by id, so paging does not lose them.
  const [picked, setPicked] = useState<number[]>([]);

  useEffect(() => {
    if (!admin) return;
    api.departments().then(setDepartments).catch(() => setDepartments([]));
  }, [admin]);

  useEffect(() => {
    api.runningDraft().then(setDraft).catch(() => setDraft(null));
  }, []);

  const load = useCallback(async () => {
    const version = ++requestVersion.current;
    setLoading(true);
    try {
      const answer = await api.shipments({
        q,
        modality,
        ...localDateFilters(from, to),
        page,
        per_page: PER_PAGE,
        department: admin ? department : undefined,
      });
      if (version !== requestVersion.current) return;
      setLoadFailed(false);
      const lastPage = Math.max(1, Math.ceil(answer.total / PER_PAGE));
      if (page > lastPage) {
        setPage(lastPage);
        return;
      }
      setItems(answer.items);
      setTotal(answer.total);
    } catch (e) {
      if (version === requestVersion.current) {
        setLoadFailed(true);
        toast.error(String(e));
      }
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
    // toast is stable for the provider's lifetime.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, modality, from, to, page, department, admin]);
  const latestLoad = useRef(load);
  latestLoad.current = load;

  // The search waits for the typing to stop; the other filters act at once.
  useEffect(() => {
    const handle = setTimeout(() => void load(), q ? 250 : 0);
    return () => {
      clearTimeout(handle);
      requestVersion.current += 1;
    };
  }, [load, q]);

  const pages = Math.max(1, Math.ceil(total / PER_PAGE));
  const open = (shipment: ShipmentSummary) => navigate(`/shipments/${shipment.id}`);
  const toggle = (id: number) =>
    setPicked((current) => (current.includes(id) ? current.filter((one) => one !== id) : [...current, id]));
  const [busy, setBusy] = useState(false);
  const documentsAgain = async (shipment: ShipmentSummary) => {
    if (actionRunning.current) return;
    actionRunning.current = true;
    setBusy(true);
    try {
      await api.shipmentDocuments(shipment.id);
    } catch (e) {
      toast.error(String(e));
    } finally {
      actionRunning.current = false;
      setBusy(false);
    }
  };
  const remove = async () => {
    if (!confirmRemove || actionRunning.current) return;
    const shipment = confirmRemove;
    actionRunning.current = true;
    setConfirmRemove(null);
    setBusy(true);
    try {
      await api.forgetShipment(shipment.id);
      requestVersion.current += 1;
      setItems(current => current.filter(item => item.id !== shipment.id));
      setTotal(current => Math.max(0, current - 1));
      setPicked(current => current.filter(id => id !== shipment.id));
      toast.success(t("history.removed"));
      await latestLoad.current();
    } catch (e) {
      toast.error(String(e));
    } finally {
      actionRunning.current = false;
      setBusy(false);
    }
  };
  const reference = (s: ShipmentSummary) => s.reference || t("history.noReference");
  const parties = (s: ShipmentSummary) => [s.consignor_name, s.consignee_name].filter(Boolean).join(" → ") || "—";
  const activeFilters = [modality, from, to, department].filter(Boolean).length;
  const clearFilters = () => {
    setModality("");
    setFrom("");
    setTo("");
    setDepartment("");
    setPage(1);
  };

  return (
    <div className="shipments-page page-enter">
      <header className="shipments-heading">
        <h2>{t("history.title")}</h2>
      </header>

      <section className="shipments-controls" aria-label={t("history.filters")}>
        <div className="shipments-search-row">
          <div className="shipments-search">
            <SearchIcon />
            <input
              type="search"
              maxLength={120}
              placeholder={t("history.searchShort")}
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
              }}
              aria-label={t("history.search")}
            />
          </div>
          <button type="button" className="shipment-action shipments-filter-toggle" aria-label={t("history.filters")}
            title={t("history.filters")} aria-expanded={filtersOpen} aria-controls="shipment-filters"
            data-active={activeFilters > 0} onClick={() => setFiltersOpen(current => !current)}>
            <SettingsIcon />
            {activeFilters > 0 && <span className="shipments-filter-count">{activeFilters}</span>}
          </button>
        </div>
        <div id="shipment-filters" hidden={!filtersOpen} className="shipments-filters">
          <label className="shipments-mode-filter">
            {t("history.modality")}
            <select
              className={inputClass}
              value={modality}
              onChange={(e) => {
                setModality(e.target.value);
                setPage(1);
              }}
              aria-label={t("history.modality")}
            >
              <option value="">{t("history.allModalities")}</option>
              {MODALITIES.map((key) => (
                <option key={key} value={key}>
                  {t(`modality.${key}`)}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("history.from")}
            <input type="date" className={`${inputClass} mt-1`} value={from} onChange={(e) => { setFrom(e.target.value); setPage(1); }} />
          </label>
          <label>
            {t("history.to")}
            <input type="date" className={`${inputClass} mt-1`} value={to} onChange={(e) => { setTo(e.target.value); setPage(1); }} />
          </label>
          {admin && departments.length > 0 && (
            <label className="shipments-department-filter">
              {t("departments.userDepartment")}
              <select
                className={inputClass}
                value={department}
                onChange={(e) => {
                  setDepartment(e.target.value);
                  setPage(1);
                }}
                aria-label={t("departments.userDepartment")}
              >
                <option value="">{t("departments.all")}</option>
                <option value="none">{t("departments.unassigned")}</option>
                {departments.map((d) => (
                  <option key={d.id} value={String(d.id)}>
                    {d.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          {activeFilters > 0 && <button type="button" className="shipments-reset" onClick={clearFilters}>
            <CloseIcon />{t("history.clearFilters")}
          </button>}
        </div>
        <div className="shipments-listbar" data-selected={picked.length > 0}>
          <span role="status">{picked.length > 0 ? t("history.selectedShort", { count: picked.length })
            : loading ? t("history.loading") : t("history.count", { count: items.length, total })}</span>
          {picked.length > 0 && <div className="shipments-selection-actions">
            <Link to={`/deliveries/new?shipments=${picked.join(",")}`} className="shipment-action shipment-action-primary"
              aria-label={t("history.toDelivery", { count: picked.length })} title={t("history.toDelivery", { count: picked.length })}>
              <RoadIcon />
            </Link>
            <button type="button" className="shipment-action" onClick={() => setPicked([])}
              aria-label={t("history.clearPicked")} title={t("history.clearPicked")}><CloseIcon /></button>
          </div>}
        </div>
      </section>

      {draft && (
        <div className={`${panelClass} flex flex-wrap items-center gap-x-3 gap-y-2 p-4`}>
          <Status shipment={draft} />
          <span className="min-w-0 truncate text-sm font-medium text-slate-900 dark:text-slate-100">
            {draft.reference || t("history.noReference")}
          </span>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {t(`modality.${draft.modality || "preparation"}`)} · {when(draft.updated_at, language)}
          </span>
          <Link to={wizardLinkFor(draft)} className={`${actionClass} ml-auto`}>
            {t("history.resumeDraft")}
          </Link>
        </div>
      )}

      {loadFailed && <div className="shipments-load-error" role="alert">
        <span>{t("history.loadFailed")}</span>
        <button type="button" className="shipment-action" disabled={loading} onClick={() => void load()}
          aria-label={t("history.retry")} title={t("history.retry")}><RefreshIcon /></button>
      </div>}
      {!loading && !loadFailed && items.length === 0 && (
        <div className={`${panelClass} p-5 space-y-3`}><p className="text-sm text-slate-600 dark:text-slate-300">{t("history.empty")}</p>{q || activeFilters ? <button className="action-secondary" onClick={() => { setQ(""); clearFilters(); }}>{t("history.clearFilters")}</button> : <Link className="action-primary" to="/">{t("nav.new")}</Link>}</div>
      )}

      {/* Phone: cards */}
      <div className="shipments-cards lg:hidden" aria-busy={loading}>
        {items.map((s) => (
          <article key={s.id} className="shipment-card" data-selected={picked.includes(s.id)}>
            <div className="shipment-card-heading">
              <Link to={`/shipments/${s.id}`} className="shipment-card-reference">{reference(s)}</Link>
              <label className="shipment-pick" title={t("history.pick")}>
                <input type="checkbox" checked={picked.includes(s.id)} onChange={() => toggle(s.id)}
                  aria-label={`${t("history.pick")} — ${reference(s)}`} />
              </label>
            </div>
            <p className="shipment-card-parties">{parties(s)}</p>
            <div className="shipment-card-meta">
              <span>{t(`modality.${s.modality || "preparation"}`)} · {when(s.created_at, language)}</span>
              <span>
                {s.created_by || ""}{s.department ? ` · ${s.department}` : ""}
              </span>
            </div>
            <div className="shipment-card-footer">
              <div className="shipment-card-badges">
                <Status shipment={s} />
                <Badges shipment={s} />
              </div>
              <RowActions shipment={s} onAgain={documentsAgain} onRemove={setConfirmRemove} busy={busy} />
            </div>
          </article>
        ))}
      </div>

      {/* Desktop: table */}
      {items.length > 0 && (
        <div className={`${panelClass} hidden overflow-x-auto lg:block`} aria-busy={loading}>
          <table className="w-full text-sm text-slate-800 dark:text-slate-200">
            <thead className="bg-slate-50 dark:bg-slate-800/80">
              <tr>
                <th className="px-3 py-2 text-left">
                  <span className="sr-only">{t("history.pick")}</span>
                </th>
                <th className="px-3 py-2 text-left">{t("history.reference")}</th>
                <th className="px-3 py-2 text-left">{t("history.parties")}</th>
                <th className="px-3 py-2 text-left">{t("history.modality")}</th>
                <th className="px-3 py-2 text-left">{t("history.kept")}</th>
                <th className="px-3 py-2 text-left">{t("history.by")}</th>
                {admin && departments.length > 0 && (
                  <th className="px-3 py-2 text-left">{t("departments.userDepartment")}</th>
                )}
                <th className="px-3 py-2 text-right">{t("history.goods")}</th>
                <th className="px-3 py-2 text-left">{t("history.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((s) => (
                <tr
                  key={s.id}
                  onClick={() => open(s)}
                  className="border-t border-slate-100 dark:border-slate-800 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/60"
                >
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={picked.includes(s.id)}
                      onChange={() => toggle(s.id)}
                      onClick={(e) => e.stopPropagation()}
                      aria-label={`${t("history.pick")} — ${reference(s)}`}
                      className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <span className="flex flex-wrap items-center gap-2">
                      <Link to={`/shipments/${s.id}`} className="font-medium text-brand-700 dark:text-brand-300 hover:underline" onClick={(e) => e.stopPropagation()}>
                        {reference(s)}
                      </Link>
                      <Status shipment={s} />
                      <Badges shipment={s} />
                    </span>
                  </td>
                  <td className="px-3 py-2">{parties(s)}</td>
                  <td className="px-3 py-2 whitespace-nowrap">{t(`modality.${s.modality || "preparation"}`)}</td>
                  <td className="px-3 py-2 whitespace-nowrap">{when(s.created_at, language)}</td>
                  <td className="px-3 py-2">{s.created_by || "—"}</td>
                  {admin && departments.length > 0 && <td className="px-3 py-2">{s.department || "—"}</td>}
                  <td className="px-3 py-2 text-right">{s.goods_count}</td>
                  <td className="px-3 py-2">
                    <RowActions shipment={s} onAgain={documentsAgain} onRemove={setConfirmRemove} busy={busy} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {pages > 1 && (
        <div className="flex items-center justify-between gap-3">
          <button type="button" className="shipment-action" disabled={loading || page <= 1} onClick={() => setPage((p) => p - 1)}
            aria-label={t("history.previous")} title={t("history.previous")}>
            <ArrowRightIcon className="rotate-180" />
          </button>
          <span className="text-sm text-slate-500 dark:text-slate-400">{t("history.page", { page, pages })}</span>
          <button type="button" className="shipment-action" disabled={loading || page >= pages} onClick={() => setPage((p) => p + 1)}
            aria-label={t("history.next")} title={t("history.next")}>
            <ArrowRightIcon />
          </button>
        </div>
      )}
      <ConfirmDialog open={!!confirmRemove} title={t("history.remove")}
        body={<><p className="mb-2 break-words font-semibold">{confirmRemove && reference(confirmRemove)}</p>{t("history.confirmRemove")}</>}
        confirmLabel={t("history.remove")} onConfirm={remove} onCancel={() => setConfirmRemove(null)} />
    </div>
  );
}

/** What one does with a kept shipment, on the row it is about.
 *
 *  The baseline found no reuse action on the list at all: opening the detail
 *  page was compulsory before anything could be done. Keep these actions on
 *  each row, including removal with an explicit confirmation. */
function RowActions({ shipment, onAgain, onRemove, busy }: {
  shipment: ShipmentSummary;
  onAgain: (shipment: ShipmentSummary) => void;
  onRemove: (shipment: ShipmentSummary) => void;
  busy: boolean;
}) {
  const { t } = useTranslation();
  const stop = (event: { stopPropagation: () => void }) => event.stopPropagation();
  return (
    <div className="shipment-row-actions" role="group" aria-label={`${t("history.actions")} — ${shipment.reference || t("history.noReference")}`}>
      <Link to={wizardLinkFor(shipment)} onClick={stop} className="shipment-action"
        aria-label={t("history.edit")} title={t("history.edit")}>
        <PenIcon />
      </Link>
      <Link to={templateLinkFor(shipment)} onClick={stop} className="shipment-action"
        aria-label={t("history.useTemplate")} title={t("history.useTemplate")}>
        <CopyIcon />
      </Link>
      {shipment.has_documents && (
        <button
          type="button"
          disabled={busy}
          onClick={(event) => {
            stop(event);
            onAgain(shipment);
          }}
          className="shipment-action" aria-label={t("history.documents")} title={t("history.documents")}
        >
          <DownloadIcon />
        </button>
      )}
      <button type="button" className="shipment-action shipment-action-danger" disabled={busy}
        aria-label={t("history.remove")} title={t("history.remove")}
        onClick={event => { stop(event); onRemove(shipment); }}><TrashIcon /></button>
    </div>
  );
}

/** Preparation readiness is independent of delivery document issuance. */
function Status({ shipment }: { shipment: ShipmentSummary }) {
  const { t } = useTranslation();
  const [key, className] = shipment.is_draft
    ? ["history.stateDraft", "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200"]
    : shipment.work_status === "ready"
      ? ["history.stateReady", "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200"]
      : ["history.stateOpen", "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"];
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${className}`}>{t(key)}</span>
  );
}

function Badges({ shipment }: { shipment: ShipmentSummary }) {
  const { t } = useTranslation();
  return (
    <>
      {shipment.has_dangerous_goods && (
        <span
          className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"
          title={t("history.dg")}
        >
          {shipment.regulations.join("/") || "DG"}
        </span>
      )}
    </>
  );
}

function ShipmentView({ id, language }: { id: number; language: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const toast = useToast();
  const [shipment, setShipment] = useState<ShipmentDetail | null>(null);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .shipment(id)
      .then((detail) => {
        if (!cancelled) setShipment(detail);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (failed) {
    return (
      <div className={`${panelClass} p-5 space-y-3`}>
        <p className="text-sm text-slate-600 dark:text-slate-300">{t("history.loadFailed")}</p>
        <Link to="/shipments" className="text-sm text-brand-700 dark:text-brand-300 hover:underline">{t("history.back")}</Link>
      </div>
    );
  }
  if (!shipment) return null;

  const documents = Array.isArray(shipment.export.documents) ? (shipment.export.documents as string[]) : [];
  const snapshot = readSnapshot(shipment.snapshot);
  const cargo = readCargo(shipment.export.cargo) ?? snapshot?.cargo;
  const lines = Array.isArray(shipment.export.goods) ? shipment.export.goods as LineItem[] : snapshot ? cargoLines(snapshot.draftLines, snapshot.result) : [];
  const downloadAgain = async () => {
    setBusy(true);
    try {
      await api.shipmentDocuments(shipment.id);
    } catch (e) {
      toast.error(String(e));
    } finally {
      setBusy(false);
    }
  };
  const remove = async () => {
    setConfirmRemove(false);
    setBusy(true);
    try {
      await api.forgetShipment(shipment.id);
      toast.success(t("history.removed"));
      navigate("/shipments");
    } catch (e) {
      toast.error(String(e));
      setBusy(false);
    }
  };

  const row = (label: string, value: string | number) => (
    <div className="flex justify-between gap-4 border-b border-slate-100 py-2 text-sm dark:border-slate-800 last:border-b-0">
      <span className="text-slate-500 dark:text-slate-400">{label}</span>
      <span className="text-right text-slate-800 dark:text-slate-100">{value}</span>
    </div>
  );

  return (
    <div className="collection-page page-enter space-y-4 sm:space-y-6 max-w-3xl">
      <Link to="/shipments" className="text-sm text-brand-700 dark:text-brand-300 hover:underline">
        ← {t("history.back")}
      </Link>

      <div className={`${panelClass} p-5 sm:p-8 space-y-4`}>
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-xl sm:text-2xl font-semibold text-slate-900 dark:text-slate-100">
            {shipment.reference || t("history.noReference")}
          </h2>
          <Badges shipment={shipment} />
        </div>
        <div>
          {row(t("history.modality"), t(`modality.${shipment.modality || "preparation"}`))}
          {row(t("history.parties"), [shipment.consignor_name, shipment.consignee_name].filter(Boolean).join(" → ") || "—")}
          {row(t("history.goods"), shipment.goods_count)}
          {row(t("history.regulations"), shipment.regulations.join(", ") || "—")}
          {documents.length > 0 && row(t("history.documentsOf"), documents.join(", "))}
          {row(t("history.kept"), `${when(shipment.created_at, language)}${shipment.created_by ? ` · ${shipment.created_by}` : ""}`)}
          {shipment.department && row(t("departments.userDepartment"), shipment.department)}
          {shipment.updated_at !== shipment.created_at && row(t("history.updated"), when(shipment.updated_at, language))}
        </div>

        <div className="shipment-detail-actions">
          <Link to={wizardLinkFor(shipment)} className="shipment-action shipment-action-primary" aria-label={t("history.open")} title={t("history.open")}>
            <PenIcon /><span className="shipment-action-label">{t("history.open")}</span>
          </Link>
          <Link to={templateLinkFor(shipment)} className="shipment-action" aria-label={t("history.useTemplate")} title={t("history.useTemplate")}>
            <CopyIcon /><span className="shipment-action-label">{t("history.useTemplate")}</span>
          </Link>
          {shipment.has_documents ? (
            <button type="button" className="shipment-action" disabled={busy} onClick={downloadAgain} aria-label={t("history.documents")} title={t("history.documents")}>
              <DownloadIcon /><span className="shipment-action-label">{t("history.documents")}</span>
            </button>
          ) : null}
          <a className="shipment-action" href={api.shipmentExportUrl(shipment.id)} download aria-label={t("history.exportJson")} title={t("history.exportJson")}>
            <CodeIcon /><span className="shipment-action-label">{t("history.exportJson")}</span>
          </a>
          <button type="button" className="shipment-action shipment-action-danger" disabled={busy} onClick={() => setConfirmRemove(true)} aria-label={t("history.remove")} title={t("history.remove")}>
            <TrashIcon /><span className="shipment-action-label">{t("history.remove")}</span>
          </button>
        </div>
        {!shipment.has_documents && <p className="text-xs text-slate-500 dark:text-slate-400">{t("routing.documentsLater")}</p>}
      </div>
      {shipment.export.routing != null && <ShipmentRoutingSummary routing={shipment.export.routing as Routing} lines={lines} />}
      <DeliveryActivity shipmentId={shipment.id} />
      {cargo && <div className={`${panelClass} p-4 sm:p-6`}><CargoSummary value={cargo} goods={cargoGoods(lines, cargo)} /></div>}

      <ConfirmDialog
        open={confirmRemove}
        title={t("history.remove")}
        body={t("history.confirmRemove")}
        confirmLabel={t("history.remove")}
        onConfirm={remove}
        onCancel={() => setConfirmRemove(false)}
      />
    </div>
  );
}
