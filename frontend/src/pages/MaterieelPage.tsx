import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useToast } from "../toast/ToastProvider";
import { api, EquipmentItem, EquipmentFile, EquipmentEvent } from "../api/client";
import { ImportIcon, DownloadIcon, PlusIcon } from "../components/icons";
import EquipmentImportDialog from "../components/EquipmentImportDialog";
import EquipmentDialog from "../components/EquipmentDialog";
import EquipmentForm from "../components/EquipmentForm";
import EquipmentMenu from "../components/EquipmentMenu";
import EquipmentInspections, { InspectionSummary } from "../components/EquipmentInspections";
import { needsInspectionAttention } from "../utils/inspections";
import { invalidateEquipmentLibrary } from "../components/EquipmentCombobox";

const empty = (): EquipmentItem => ({ specifications: "", kind: "machine", weight_kg: 0, aliases: [], active: true, availability: "available", condition: "unknown", configurations: [] });
const dimensions = (item: EquipmentItem) => [item.length_cm, item.width_cm, item.height_cm].map(value => value ?? "—").join(" × ") + " cm";

export default function MaterieelPage() {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const [items, setItems] = useState<EquipmentItem[]>([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [archived, setArchived] = useState(false);
  const [inspectionFilter, setInspectionFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [listFailure, setListFailure] = useState("");
  const [form, setForm] = useState<EquipmentItem | null>(null);
  const [selected, setSelected] = useState<(EquipmentItem & { files: EquipmentFile[] }) | null>(null);
  const [events, setEvents] = useState<EquipmentEvent[]>([]);
  const [nextBefore, setNextBefore] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [importOpen, setImportOpen] = useState(false);
  const [moveOpen, setMoveOpen] = useState(false);
  const [destination, setDestination] = useState("");
  const [reference, setReference] = useState("");
  const [notes, setNotes] = useState("");
  const [availability, setAvailability] = useState("available");
  const number = new Intl.NumberFormat(i18n.language, { maximumFractionDigits: 2 });
  const activeFilters = inspectionFilter !== "all" || archived;

  const load = async () => {
    invalidateEquipmentLibrary(); setLoading(true); setListFailure("");
    try { setItems(await api.listEquipment()); }
    catch (cause) { setListFailure(String(cause)); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, []);
  const filtered = useMemo(() => items.filter(item => {
    if (!archived && item.active === false) return false;
    const kind = item.kind ?? "other";
    if (inspectionFilter === "attention" && !(item.inspections ?? []).some(entry => needsInspectionAttention(entry))) return false;
    if (inspectionFilter === "missing" && (item.inspections ?? []).some(entry => !entry.archived)) return false;
    if (filter === "vehicles" ? !["vehicle", "machine"].includes(kind) : filter !== "all" && kind !== filter) return false;
    return [item.specifications, item.asset_code, item.container_number, item.registration, item.serial_number,
      item.brand, item.model_name, item.current_location, ...(item.aliases ?? [])].filter(Boolean).join(" ").toLowerCase().includes(search.trim().toLowerCase());
  }), [items, search, filter, archived, inspectionFilter]);
  const open = async (id: number) => {
    try {
      const [record, history] = await Promise.all([api.getEquipment(id), api.equipmentEvents(id)]);
      setSelected(record); setEvents(history.events); setNextBefore(history.next_before); setMoveOpen(false); setError("");
    } catch (e) { toast.error(String(e)); }
  };
  const save = async (record: EquipmentItem) => {
    setBusy(true); setError("");
    try {
      if (record.id) await api.updateEquipment(record.id, record); else await api.createEquipment(record);
      setForm(null); setSelected(null); await load(); toast.success(t("assets.saved"));
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  };
  const duplicate = (item: EquipmentItem) => {
    const copy = structuredClone(item);
    delete copy.id; delete copy.version;
    setSelected(null); setForm({ ...copy, asset_code: "", container_number: "", registration: "", serial_number: "", current_location: "", planned_reference: "", planned_date: null, availability: "unknown", photo_url: null, file_count: 0, active: true, inspections: [], inspection_due: null }); setError("");
  };
  const archive = async () => {
    if (!selected?.id) return;
    setBusy(true); setError("");
    try { await api.updateEquipment(selected.id, { version: selected.version, active: selected.active === false }); await load(); await open(selected.id); }
    catch (e) { setError(String(e)); } finally { setBusy(false); }
  };
  const transfer = async (event: React.FormEvent) => {
    event.preventDefault(); if (!selected?.id) return;
    setBusy(true); setError("");
    try {
      await api.moveEquipment(selected.id, { version: selected.version ?? 1, to_location: destination, availability, reference, notes });
      await load(); await open(selected.id); setDestination(""); setReference(""); setNotes(""); toast.success(t("assets.transferSaved"));
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  };
  const upload = async (file?: File) => {
    if (!file || !selected?.id) return; setBusy(true); setError("");
    try { await api.uploadEquipmentFile(selected.id, file); await load(); await open(selected.id); }
    catch (e) { setError(String(e)); } finally { setBusy(false); }
  };
  const facts = (values: [string, React.ReactNode][]) => <dl className="equipment-facts">{values.filter(([, value]) => value != null && value !== "").map(([key, value]) => <div key={key}><dt>{t(`assets.${key}`)}</dt><dd>{value}</dd></div>)}</dl>;

  return <div className="collection-page page-enter space-y-6">
    <header><h2 className="text-2xl font-semibold">{t("nav.materieel")}</h2>
      <div className="mt-5 flex flex-wrap gap-2"><button className="action-primary" onClick={() => { setForm({ ...empty(), kind: filter === "container" ? "container" : filter === "other" ? "other" : "machine" }); setError(""); }}><PlusIcon />{t(filter === "container" ? "equipmentSimple.addContainer" : "materieel.add")}</button>
        <EquipmentMenu>
          <button onClick={() => setImportOpen(true)}><ImportIcon />{t("materieel.import")}</button>
          <button onClick={() => api.exportEquipmentLibrary().catch(e => toast.error(String(e)))}><DownloadIcon />{t("materieel.exportLibrary")}</button>
          <button onClick={() => api.downloadEquipmentTemplate().catch(e => toast.error(String(e)))}><DownloadIcon />{t("import.downloadTemplate")}</button>
        </EquipmentMenu>
      </div>
    </header>
    <div className="space-y-3">
      <div className="equipment-toolbar"><div className="equipment-filters" role="group" aria-label={t("assets.filter")}>
        {["all", "vehicles", "container", "other"].map(value => <button key={value} type="button" aria-pressed={filter === value} onClick={() => setFilter(value)}>{t(`assets.filters.${value}`)}</button>)}
      </div><input className="equipment-input" type="search" aria-label={t("assets.search")} placeholder={t("assets.search")} value={search} onChange={event => setSearch(event.target.value)} /></div>
      <details className="equipment-list-filters"><summary>{t("equipmentSimple.filters")}{activeFilters && <span className="equipment-count">{Number(archived) + Number(inspectionFilter !== "all")}</span>}</summary>
        <div className="flex flex-wrap items-end gap-4 pt-3">
          <label className="equipment-field">{t("inspections.filter")}<select className="equipment-input" value={inspectionFilter} onChange={event => setInspectionFilter(event.target.value)}>{["all", "attention", "missing"].map(value => <option key={value} value={value}>{t(`inspections.filters.${value}`)}</option>)}</select></label>
          <label className="equipment-check"><input type="checkbox" checked={archived} onChange={event => setArchived(event.target.checked)} />{t("assets.showArchived")}</label>
          {activeFilters && <button type="button" className="equipment-text-button" onClick={() => { setArchived(false); setInspectionFilter("all"); }}>{t("equipmentSimple.clearFilters")}</button>}
        </div>
      </details>
    </div>
    <p className="text-sm text-slate-500">{t("materieel.count", { count: filtered.length, total: items.length })}</p>
    {loading ? <p role="status">{t("assets.loading")}</p> : listFailure ? <div className="surface p-6 space-y-3" role="alert"><p>{listFailure}</p><button className="action-secondary" onClick={() => void load()}>{t("assets.reload")}</button></div> : !filtered.length ? <div className="surface p-8 space-y-3"><p>{t(items.length ? "assets.noResults" : "assets.empty")}</p>{(search || filter !== "all" || activeFilters) && <button className="action-secondary" onClick={() => { setSearch(""); setFilter("all"); setArchived(false); setInspectionFilter("all"); }}>{t("equipmentSimple.clearFilters")}</button>}</div> : <div className="equipment-cards">
      {filtered.map(item => <button type="button" className="equipment-card" key={item.id} onClick={() => void open(item.id!)}>
        {item.photo_url ? <img src={item.photo_url} alt="" loading="lazy" /> : <span className="equipment-placeholder" aria-hidden>{(item.asset_code || item.specifications).slice(0, 2).toUpperCase()}</span>}
        <div className="min-w-0"><span className="equipment-kind">{t(`assets.kindValues.${item.kind ?? "other"}`)}{item.active === false && ` · ${t("assets.archived")}`}</span>
          <h3>{item.specifications}</h3><p className="text-sm text-slate-500 dark:text-slate-400">{[item.asset_code, item.container_number || item.registration].filter(Boolean).join(" · ")}</p>
        </div>
        <div className="equipment-card-facts"><span>{dimensions(item)}</span><strong>{number.format(item.weight_kg)} kg</strong><span>{item.current_location || t("assets.locationUnknown")}</span><span>{t(`assets.availabilityValues.${item.availability || "unknown"}`)}</span></div>
        {(item.inspections ?? []).some(entry => needsInspectionAttention(entry)) && <span className="col-span-2 text-xs font-medium text-amber-700 dark:text-amber-300">{t("inspections.attentionCount", { count: item.inspections!.filter(entry => needsInspectionAttention(entry)).length })}</span>}
      </button>)}
    </div>}
    {form && <EquipmentDialog busy={busy} title={form.id ? t("materieel.edit") : t(form.kind === "container" ? "equipmentSimple.addContainer" : "materieel.add")} onClose={() => { if (!busy) setForm(null); }} footer={<>
      <button type="button" className="action-secondary" disabled={busy} onClick={() => setForm(null)}>{t("materieel.cancel")}</button>
      <button type="submit" form="equipment-editor" className="action-primary" disabled={busy}>{t("materieel.save")}</button>
    </>}>
      {error && <p role="alert" className="mb-4 text-red-600">{error}</p>}<EquipmentForm formId="equipment-editor" initial={form} onSave={save} busy={busy} />
    </EquipmentDialog>}
    {selected && !form && <EquipmentDialog busy={busy} title={selected.specifications} onClose={() => { if (!busy) setSelected(null); }}>
      {error && <p role="alert" className="mb-4 text-red-600">{error} <button className="underline" onClick={() => void open(selected.id!)}>{t("assets.reload")}</button></p>}
      <div className="space-y-5">
        {selected.photo_url && <img className="max-h-56 w-full rounded-xl object-contain" src={selected.photo_url} alt={selected.specifications} />}
        <div className="flex flex-wrap gap-2">
          <button className="action-primary" disabled={busy} onClick={() => { setForm(selected); setError(""); }}>{t("materieel.edit")}</button>
          <button className="action-secondary" disabled={busy || selected.active === false} onClick={() => { setMoveOpen(value => !value); setAvailability(selected.availability || "available"); }}>{t("equipmentSimple.changeLocation")}</button>
          <EquipmentMenu><button disabled={busy} onClick={() => duplicate(selected)}>{t("materieel.duplicate")}</button><button disabled={busy} onClick={() => void archive()}>{t(selected.active === false ? "assets.restore" : "assets.archive")}</button></EquipmentMenu>
        </div>
        {moveOpen && <form onSubmit={transfer} className="rounded-xl border border-slate-200 p-4 dark:border-slate-700"><fieldset disabled={busy} className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2"><label className="equipment-field">{t("assets.destination")}<input className="equipment-input" required maxLength={200} value={destination} onChange={event => setDestination(event.target.value)} /></label>
            <label className="equipment-field">{t("assets.availability")}<select className="equipment-input" value={availability} onChange={event => setAvailability(event.target.value)}>{["available", "planned", "in_transit", "maintenance", "unknown"].map(value => <option value={value} key={value}>{t(`assets.availabilityValues.${value}`)}</option>)}</select></label></div>
          <details className="equipment-section"><summary>{t("equipmentSimple.moreDetails")}</summary><div className="equipment-section-body grid gap-3 sm:grid-cols-2">
            <label className="equipment-field">{t("assets.reference")}<input className="equipment-input" maxLength={120} value={reference} onChange={event => setReference(event.target.value)} /></label>
            <label className="equipment-field">{t("assets.notes")}<textarea className="equipment-input" maxLength={2000} value={notes} onChange={event => setNotes(event.target.value)} /></label>
          </div></details>
          <div className="flex flex-wrap gap-2"><button className="action-primary" type="submit">{t("assets.transfer")}</button><button className="action-secondary" type="button" onClick={() => setMoveOpen(false)}>{t("materieel.cancel")}</button></div>
        </fieldset></form>}
        {facts([["asset_code", selected.asset_code], ["container_number", selected.container_number], ["registration", selected.registration], ["dimensions", dimensions(selected)], [selected.kind === "container" ? "tare_kg" : "weight_kg", `${number.format(selected.weight_kg)} kg`], ["current_location", selected.current_location || t("assets.locationUnknown")], ["availability", t(`assets.availabilityValues.${selected.availability || "unknown"}`)]])}
        <div className="equipment-sections">
          <details className="equipment-section"><summary>{t("equipmentSimple.moreDetails")}</summary><div className="equipment-section-body space-y-4">
            {facts([["kind", t(`assets.kindValues.${selected.kind ?? "other"}`)], ["serial_number", selected.serial_number], ["brand", selected.brand], ["model_name", selected.model_name], ["max_payload_kg", selected.max_payload_kg], ["max_gross_kg", selected.max_gross_kg], ["container_type", selected.container_type], ["condition", t(`assets.conditionValues.${selected.condition || "unknown"}`)], ["planned_reference", selected.planned_reference], ["planned_date", selected.planned_date]])}
            {selected.kind === "container" && <p className="text-sm">{t(`assets.container_useValues.${selected.container_use || "freight"}`)}{(selected.facilities ?? []).map(value => ` · ${t(`assets.facilityValues.${value}`)}`)}</p>}
            {(["transport_instructions", "accessories", "notes"] as const).map(key => selected[key] && <div key={key}><h4 className="text-sm font-semibold">{t(`assets.${key}`)}</h4><p className="whitespace-pre-wrap text-sm">{selected[key]}</p></div>)}
          </div></details>
          <details className="equipment-section"><summary>{t("inspections.filter")}<InspectionSummary items={selected.inspections} /></summary><div className="equipment-section-body"><EquipmentInspections items={selected.inspections} /></div></details>
          <details className="equipment-section"><summary>{t("assets.files")}{!!selected.files.length && <span className="equipment-count">{selected.files.length}</span>}</summary><div className="equipment-section-body">
            <label className="equipment-field"><span className="sr-only">{t("assets.upload")}</span><input className="max-w-full text-sm" type="file" disabled={busy} accept=".pdf,.jpg,.jpeg,.png,.webp" onChange={event => { void upload(event.target.files?.[0]); event.target.value = ""; }} /></label>
            <ul className="mt-3 space-y-2">{selected.files.map(file => <li key={file.id} className="flex items-center justify-between gap-2 text-sm"><a className="min-w-0 break-all text-brand-600 underline dark:text-brand-300" href={`/api/equipment/${selected.id}/files/${file.id}`} target="_blank" rel="noreferrer">{file.name}</a><button type="button" className="equipment-text-button" disabled={busy} onClick={async () => { setBusy(true); try { await api.deleteEquipmentFile(selected.id!, file.id); await load(); await open(selected.id!); } catch (e) { setError(String(e)); } finally { setBusy(false); } }}>{t("assets.removeFile")}</button></li>)}</ul>
          </div></details>
          <details className="equipment-section"><summary>{t("assets.history")}</summary><div className="equipment-section-body"><ol className="equipment-history">{events.map(event => <li key={event.id}><strong>{t(`assets.events.${event.action}`)}</strong><span>{event.from_location ? `${event.from_location} → ` : ""}{event.to_location || "—"}</span><span>{[event.reference, event.notes].filter(Boolean).join(" · ")}</span><small>{new Date(event.created_at.endsWith("Z") ? event.created_at : event.created_at + "Z").toLocaleString(i18n.language)} · {event.actor_name || "—"}</small></li>)}</ol>
            {nextBefore && <button className="action-secondary mt-3" disabled={busy} onClick={async () => { setBusy(true); try { const next = await api.equipmentEvents(selected.id!, nextBefore); setEvents(previous => [...previous, ...next.events]); setNextBefore(next.next_before); } catch (e) { setError(String(e)); } finally { setBusy(false); } }}>{t("assets.moreHistory")}</button>}
          </div></details>
        </div>
      </div>
    </EquipmentDialog>}
    <EquipmentImportDialog open={importOpen} onClose={() => setImportOpen(false)} onComplete={() => void load()} />
  </div>;
}
