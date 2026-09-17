import { useEffect, useMemo, useRef, useState } from "react";
import { Navigate, useNavigate, useParams, useSearchParams } from "react-router";
import { useTranslation } from "react-i18next";
import { api, type ShipmentSummary, type TripConsignment, type TripDetail, type TripIn, type TripResult, type User } from "../api/client";
import { canOversee } from "../permissions";
import { usePreferences } from "../settings/preferences";
import { useToast } from "../toast/ToastProvider";
import ConfirmDialog from "../toast/ConfirmDialog";
import { CheckIcon, CloseIcon, ImportIcon, PlusIcon, RoadIcon, ShipmentsIcon, TrashIcon } from "../components/icons";
import ShipmentPicker from "./trips/ShipmentPicker";
import TripLibrary from "./trips/TripLibrary";
import TripAssessment from "./trips/TripAssessment";
import { productCount, profilesFor, readConsignment, readMass, sameConsignment } from "./trips/tripState";
import "./trips/trips.css";

interface Draft { name: string; consignments: TripConsignment[]; mass: string }
interface Assessment { key: string; result: TripResult; savedAt?: string; editions?: Record<string, unknown> }
const emptyDraft = (): Draft => ({ name: "", consignments: [], mass: "" });
const draftKey = (draft: Draft) => JSON.stringify(draft);
const checkKeyFor = (draft: Draft, language: string) => JSON.stringify([draft.consignments, readMass(draft.mass), language]);

/** Old bookmarks open the editor directly, without an intermediate detail page. */
export function LegacyTripRoute() {
  const { id } = useParams();
  return <Navigate to={`/trips?trip=${encodeURIComponent(id ?? "")}`} replace />;
}

export default function TripsPage({ user }: { user?: User | null }) {
  const { t, i18n } = useTranslation();
  const { publicSettings } = usePreferences();
  const historyOn = !!publicSettings?.history_enabled;
  const toast = useToast();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const targetId = params.get("trip");
  const selection = params.get("shipments") ?? "";
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [baseline, setBaseline] = useState(draftKey(emptyDraft()));
  const [tripId, setTripId] = useState<number | null>(null);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [checkFailure, setCheckFailure] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const [revision, setRevision] = useState(0);
  const [opening, setOpening] = useState(false);
  const [openFailed, setOpenFailed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveFailure, setSaveFailure] = useState("");
  const [picker, setPicker] = useState(false);
  const [busyIds, setBusyIds] = useState<Set<number>>(new Set());
  const [importing, setImporting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [leaveAction, setLeaveAction] = useState<(() => void) | null>(null);
  const generation = useRef(0);
  const loadedTarget = useRef<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const addButton = useRef<HTMLButtonElement>(null);
  const nameInput = useRef<HTMLInputElement>(null);
  const vehicleDetails = useRef<HTMLDetailsElement>(null);
  const locked = saving || opening;
  const adding = busyIds.size > 0 || importing;
  const mass = readMass(draft.mass);
  const checkKey = useMemo(() => checkKeyFor(draft, i18n.language), [draft, i18n.language]);
  // The key gates rendering as well as request completion: no stale green frame.
  const current = assessment?.key === checkKey ? assessment : null;
  const dirty = draftKey(draft) !== baseline || (!!tripId && !!current && !current.savedAt);
  const failed = checkFailure === checkKey;
  const pending = !!draft.consignments.length && mass !== undefined && !current && !failed && !opening;
  const latestDraft = useRef(draft); latestDraft.current = draft;
  const pendingIds = useRef(new Set<number>());
  const needsVehicle = mass === undefined || (!!current?.result.lq_marking?.lq_gross_kg && current.result.lq_marking.required === null);

  useEffect(() => {
    // Reveal a missing fact without collapsing the field as soon as typing
    // makes it valid. Native disclosure state preserves the user's focus.
    if (needsVehicle && vehicleDetails.current) vehicleDetails.current.open = true;
  }, [needsVehicle, opening, draft.consignments.length]);

  function adopt(detail: TripDetail) {
    const next = { name: detail.name, mass: detail.unit_max_mass_tonnes == null ? "" : String(detail.unit_max_mass_tonnes),
      consignments: detail.consignments.map(c => ({ ...c, profiles: c.profiles ?? detail.regulations })) };
    setDraft(next); setBaseline(draftKey(next)); setTripId(detail.id);
    // Retain the language of the historical assessment. A language change triggers a new check.
    setAssessment({ key: checkKeyFor(next, detail.language), result: detail.result, savedAt: detail.updated_at, editions: detail.editions });
    setCheckFailure(null); setSaveFailure(""); setPicker(false);
  }

  useEffect(() => {
    const target = targetId ? `trip:${targetId}` : selection ? `selection:${selection}` : "new";
    if (loadedTarget.current === target) return;
    loadedTarget.current = target;
    const run = ++generation.current;
    setOpenFailed(false); setAssessment(null); setCheckFailure(null); setSaveFailure(""); setPicker(false);
    setDraft(emptyDraft()); setBaseline(draftKey(emptyDraft())); setTripId(null);
    pendingIds.current.clear(); setBusyIds(new Set());
    if (!targetId && !selection) { setOpening(false); return; }
    if (!historyOn) { setOpening(false); setOpenFailed(true); return; }
    setOpening(true);
    const load = async () => {
      try {
        if (targetId) {
          if (!/^\d+$/.test(targetId) || Number(targetId) < 1) throw new Error("invalid id");
          const detail = await api.trip(Number(targetId));
          if (run === generation.current) adopt(detail);
        } else {
          const ids = [...new Set(selection.split(",").filter(v => /^\d+$/.test(v)).map(Number).filter(v => v > 0))];
          if (!ids.length) throw new Error("empty selection");
          const answers = await Promise.allSettled(ids.map(async id => {
            const detail = await api.shipment(id);
            return readConsignment(detail.export, detail.reference || `#${id}`, id);
          }));
          if (run !== generation.current) return;
          const consignments = answers.flatMap(answer => answer.status === "fulfilled" ? [answer.value] : []);
          setDraft({ name: "", mass: "", consignments });
          if (answers.some(answer => answer.status === "rejected")) setSaveFailure(t("tripWorkspace.someMissing"));
        }
      } catch { if (run === generation.current) setOpenFailed(true); }
      finally { if (run === generation.current) setOpening(false); }
    };
    void load();
    // The location identifies the load. Interface text must not reopen an edited trip.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetId, selection, historyOn, revision]);

  useEffect(() => () => { generation.current += 1; loadedTarget.current = null; }, []);

  useEffect(() => {
    if (opening || !draft.consignments.length || mass === undefined || current) return;
    let cancelled = false;
    setCheckFailure(null);
    const timer = setTimeout(() => {
      api.dgTrip({ consignments: draft.consignments, profiles: profilesFor(draft.consignments), language: i18n.language, unit_max_mass_tonnes: mass })
        .then(result => { if (!cancelled) setAssessment({ key: checkKey, result }); })
        .catch(() => { if (!cancelled) setCheckFailure(checkKey); });
    }, 450);
    return () => { cancelled = true; clearTimeout(timer); };
    // Draft names do not affect the calculation; checkKey includes only assessment inputs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [checkKey, retry, opening]);

  useEffect(() => {
    if (!dirty) return;
    const unload = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    const followLink = (event: MouseEvent) => {
      const link = (event.target as HTMLElement).closest?.("a[href]") as HTMLAnchorElement | null;
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || !link || link.target === "_blank" || link.hasAttribute("download")) return;
      if (link.origin !== window.location.origin || link.pathname + link.search === window.location.pathname + window.location.search) return;
      event.preventDefault(); event.stopPropagation();
      setLeaveAction(() => () => navigate(link.pathname + link.search + link.hash));
    };
    window.addEventListener("beforeunload", unload);
    document.addEventListener("click", followLink, true);
    return () => { window.removeEventListener("beforeunload", unload); document.removeEventListener("click", followLink, true); };
  }, [dirty, navigate]);

  function change(action: () => void) {
    if (locked || adding) return;
    if (dirty) setLeaveAction(() => action); else action();
  }

  function startNew() {
    loadedTarget.current = null; generation.current += 1;
    setDraft(emptyDraft()); setBaseline(draftKey(emptyDraft())); setTripId(null); setAssessment(null); setSaveFailure(""); setOpenFailed(false); setPicker(false);
    navigate("/trips");
    nameInput.current?.focus();
  }

  function append(consignments: TripConsignment[]) {
    const fresh = [...latestDraft.current.consignments];
    let duplicate = false;
    for (const c of consignments) {
      if (fresh.some(existing => sameConsignment(existing, c))) duplicate = true;
      else fresh.push(c);
    }
    const next = { ...latestDraft.current, consignments: fresh };
    latestDraft.current = next; setDraft(next); setSaveFailure("");
    if (duplicate) toast.info(t("tripWorkspace.duplicate"));
  }

  async function addShipment(summary: ShipmentSummary) {
    if (pendingIds.current.has(summary.id)) return;
    const run = generation.current;
    pendingIds.current.add(summary.id); setBusyIds(new Set(pendingIds.current));
    try {
      const detail = await api.shipment(summary.id);
      if (run === generation.current) append([readConsignment(detail.export, detail.reference || `#${summary.id}`, summary.id)]);
    } catch { if (run === generation.current) setSaveFailure(t("tripWorkspace.addFailed", { name: summary.reference || `#${summary.id}` })); }
    finally { pendingIds.current.delete(summary.id); setBusyIds(new Set(pendingIds.current)); }
  }

  async function importFiles(files: FileList | null) {
    if (!files?.length) return;
    const run = generation.current;
    setImporting(true);
    const loaded: TripConsignment[] = [], refused: string[] = [];
    for (const file of Array.from(files)) {
      try {
        if (file.size > 4 * 1024 * 1024) throw new Error("too large");
        loaded.push(readConsignment(JSON.parse(await file.text()), file.name));
      } catch { refused.push(file.name); }
    }
    if (run === generation.current) {
      append(loaded);
      if (refused.length) setSaveFailure(t("tripWorkspace.importFailed", { names: refused.join(", ") }));
    }
    setImporting(false);
  }

  async function save() {
    if (!current || mass === undefined || !draft.consignments.length || saving || adding) return;
    setSaving(true); setSaveFailure("");
    const payload: TripIn = { name: draft.name.trim() || t("tripWorkspace.defaultName", { date: new Date().toLocaleDateString(i18n.language) }), consignments: draft.consignments, profiles: profilesFor(draft.consignments), language: i18n.language, unit_max_mass_tonnes: mass };
    try {
      const detail = tripId ? await api.updateTrip(tripId, payload) : await api.keepTrip(payload);
      loadedTarget.current = `trip:${detail.id}`;
      adopt(detail); setRevision(v => v + 1);
      navigate(`/trips?trip=${detail.id}`, { replace: true });
    } catch { setSaveFailure(t("tripWorkspace.saveFailed")); }
    finally { setSaving(false); }
  }

  async function removeTrip() {
    if (!tripId) return;
    setConfirmDelete(false); setSaving(true);
    try { await api.forgetTrip(tripId); startNew(); setRevision(v => v + 1); toast.success(t("trips.removed")); }
    catch { setSaveFailure(t("tripWorkspace.deleteFailed")); }
    finally { setSaving(false); }
  }

  const requestCheck = () => { setAssessment(null); setRetry(v => v + 1); };
  const closePicker = () => { setPicker(false); addButton.current?.focus(); };

  return <div className="trip-workspace page-enter">
    <header className="page-heading"><div><h1>{t("trips.title")}</h1></div>
      <button type="button" className="action-secondary" disabled={locked || adding} onClick={() => change(startNew)}><PlusIcon />{t("trips.newTrip")}</button>
    </header>
    {!historyOn && <p className="trip-storage-note">{t("tripWorkspace.noStorage")}</p>}
    <div className={`trip-layout ${!historyOn ? "trip-layout-solo" : ""}`}>
      {historyOn && <TripLibrary activeId={tripId} revision={revision} oversee={canOversee(user)} disabled={locked || adding} onSelect={id => { if (id !== tripId) change(() => navigate(`/trips?trip=${id}`)); }} />}
      <div className="trip-editor">
        {opening ? <div className="trip-loading surface" role="status">{t("trips.loading")}</div> : openFailed ? <div className="surface trip-load-error" role="alert"><h2>{t("trips.notFound")}</h2><p>{t("tripWorkspace.loadFailed")}</p><button type="button" className="action-secondary" onClick={() => { loadedTarget.current = null; setRevision(v => v + 1); }}>{t("tripWorkspace.retry")}</button></div> : <>
          <fieldset disabled={locked} className="surface trip-composer">
            <div className="trip-composer-header"><span className="trip-vehicle-icon"><RoadIcon /></span><div><label htmlFor="trip-name">{t("groupage.tripName")}</label><input ref={nameInput} id="trip-name" placeholder={t("tripWorkspace.namePlaceholder")} maxLength={120} value={draft.name} onChange={event => setDraft(d => ({ ...d, name: event.target.value }))} /></div></div>
            <div className="trip-load-heading"><h2>{t("tripWorkspace.onBoard")}<span>{draft.consignments.length}</span></h2>
              {!!draft.consignments.length && <button ref={addButton} className="trip-text-button" type="button" aria-expanded={picker} onClick={() => historyOn ? setPicker(v => !v) : fileInput.current?.click()}><PlusIcon />{t("tripWorkspace.add")}</button>}
            </div>
            {draft.consignments.length ? <ul className="trip-load">{draft.consignments.map((consignment, index) => <li key={consignment.shipment_id ? `shipment-${consignment.shipment_id}` : `file-${index}`}>
              <span className="trip-load-number">{String(index + 1).padStart(2, "0")}</span><div className="trip-load-copy"><input aria-label={`${t("groupage.consignmentName")} ${index + 1}`} maxLength={120} value={consignment.name} onChange={event => setDraft(d => ({ ...d, consignments: d.consignments.map((c, i) => i === index ? { ...c, name: event.target.value } : c) }))} />
                <p>{consignment.route_label || t(consignment.entries.length ? "tripWorkspace.dgPositions" : "tripWorkspace.generalGoods", { count: productCount(consignment) })}</p></div>
              {consignment.entries.length > 0 && <span className="trip-dg-tag">DG</span>}
              <button className="trip-icon-button" type="button" aria-label={t("tripWorkspace.removeShipment", { name: consignment.name })} onClick={() => setDraft(d => ({ ...d, consignments: d.consignments.filter((_, i) => i !== index) }))}><CloseIcon /></button>
            </li>)}</ul> : !picker && <div className="trip-empty"><ShipmentsIcon /><h3>{t("tripWorkspace.start")}</h3><button ref={addButton} className="action-primary" type="button" aria-expanded={picker} onClick={() => historyOn ? setPicker(true) : fileInput.current?.click()}><PlusIcon />{t("tripWorkspace.add")}</button></div>}
            {picker && historyOn && <ShipmentPicker selected={draft.consignments} busyIds={busyIds} onAdd={summary => void addShipment(summary)} onClose={closePicker} />}
            <div className="trip-composer-bottom"><button className="trip-text-button" type="button" disabled={importing} onClick={() => fileInput.current?.click()}><ImportIcon />{t(importing ? "tripWorkspace.adding" : "tripWorkspace.import")}</button>
              <input ref={fileInput} type="file" accept="application/json,.json" multiple className="sr-only" aria-label={t("tripWorkspace.import")} onChange={event => { void importFiles(event.target.files); event.target.value = ""; }} />
              {!!draft.consignments.length && <details ref={vehicleDetails} className="trip-vehicle"><summary>{t("tripWorkspace.vehicle")}{draft.mass && <span> · {draft.mass} t</span>}</summary><label htmlFor="trip-mass">{t("groupage.unitMass")}</label><input id="trip-mass" inputMode="decimal" placeholder={t("tripWorkspace.unknown")} value={draft.mass} aria-invalid={mass === undefined} aria-describedby={mass === undefined ? "trip-mass-error" : undefined} onChange={event => setDraft(d => ({ ...d, mass: event.target.value }))} />{mass === undefined && <p id="trip-mass-error" role="alert">{t("tripWorkspace.assessment.invalidMassHint")}</p>}</details>}
            </div>
          </fieldset>
          {saveFailure && <div className="trip-inline-error" role="alert">{saveFailure}</div>}
          {!!draft.consignments.length && <TripAssessment result={current?.result ?? null} consignments={draft.consignments} pending={pending} failed={failed} invalidMass={mass === undefined} savedAt={current?.savedAt} editions={current?.editions} onRetry={requestCheck} />}
          {(!!draft.consignments.length || !!tripId) && <footer className="trip-savebar">
            <span role="status" className="trip-save-status">{saving ? t("tripWorkspace.saving") : !historyOn ? t("tripWorkspace.sessionOnly") : tripId && !dirty ? <><CheckIcon />{t("tripWorkspace.saved")}</> : t("tripWorkspace.unsaved")}</span>
            {tripId && <button type="button" className="trip-icon-button trip-delete" aria-label={t("trips.remove")} disabled={locked || adding} onClick={() => setConfirmDelete(true)}><TrashIcon /></button>}
            {historyOn && <button className="action-primary" type="button" disabled={locked || adding || !current || !draft.consignments.length || mass === undefined || (!!tripId && !dirty && !!current.savedAt)} onClick={() => void save()}>{t("tripWorkspace.save")}</button>}
          </footer>}
        </>}
      </div>
    </div>
    <ConfirmDialog open={!!leaveAction} title={t("tripWorkspace.leaveTitle")} body={t("tripWorkspace.leaveHint")} confirmLabel={t("tripWorkspace.discard")} onCancel={() => setLeaveAction(null)} onConfirm={() => { const action = leaveAction; setLeaveAction(null); action?.(); }} />
    <ConfirmDialog open={confirmDelete} title={t("trips.remove")} body={t("tripWorkspace.deleteHint")} confirmLabel={t("trips.remove")} onCancel={() => setConfirmDelete(false)} onConfirm={() => void removeTrip()} />
  </div>;
}
