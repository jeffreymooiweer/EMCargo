import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useToast } from "../toast/ToastProvider";
import { api, EquipmentItem, EquipmentFile, EquipmentEvent } from "../api/client";
import { ImportIcon, DownloadIcon, PlusIcon } from "../components/icons";
import EquipmentImportDialog from "../components/EquipmentImportDialog";
import EquipmentDialog from "../components/EquipmentDialog";
import EquipmentForm from "../components/EquipmentForm";
import { invalidateEquipmentLibrary } from "../components/EquipmentCombobox";

const inputClass = "min-h-[44px] rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950";
const empty = (): EquipmentItem => ({ specifications: "", kind: "machine", weight_kg: 0, aliases: [], active: true, availability: "available", condition: "unknown", configurations: [] });
const dimensions = (item: EquipmentItem) => [item.length_cm, item.width_cm, item.height_cm].map(value => value ?? "—").join(" × ") + " cm";

export default function MaterieelPage() {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const [items, setItems] = useState<EquipmentItem[]>([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [archived, setArchived] = useState(false);
  const [loading, setLoading] = useState(true);
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

  const load = async () => { invalidateEquipmentLibrary(); try { setItems(await api.listEquipment()); } catch (e) { toast.error(String(e)); } finally { setLoading(false); } };
  useEffect(() => { void load(); }, []);
  const filtered = useMemo(() => items.filter(item => {
    if (!archived && item.active === false) return false;
    const kind = item.kind ?? "other";
    if (filter === "vehicles" ? !["vehicle", "machine"].includes(kind) : filter !== "all" && kind !== filter) return false;
    return [item.specifications, item.asset_code, item.container_number, item.registration, item.serial_number,
      item.brand, item.model_name, item.current_location, ...(item.aliases ?? [])].filter(Boolean).join(" ").toLowerCase().includes(search.trim().toLowerCase());
  }), [items, search, filter, archived]);
  const open = async (id: number) => {
    try {
      const [record, history] = await Promise.all([api.getEquipment(id), api.equipmentEvents(id)]);
      setSelected(record); setEvents(history.events); setNextBefore(history.next_before); setMoveOpen(false); setError("");
    } catch (e) { toast.error(String(e)); }
  };
  const save = async (record: EquipmentItem) => {
    setBusy(true); setError("");
    try {
      const saved = record.id ? await api.updateEquipment(record.id, record) : await api.createEquipment(record);
      setForm(null); await load(); await open(saved.id!); toast.success(t("assets.saved"));
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  };
  const duplicate = (item: EquipmentItem) => {
    const copy = structuredClone(item);
    delete copy.id; delete copy.version;
    setSelected(null); setForm({ ...copy, asset_code: "", container_number: "", registration: "", serial_number: "", current_location: "", planned_reference: "", planned_date: null, availability: "unknown", photo_url: null, file_count: 0, active: true }); setError("");
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
  return <div className="collection-page page-enter space-y-6">
    <header><h2 className="text-2xl font-semibold">{t("nav.materieel")}</h2><p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{t("assets.intro")}</p>
      <div className="mt-5 flex flex-wrap gap-2"><button className="action-primary" onClick={() => { setForm(empty()); setError(""); }}><PlusIcon />{t("materieel.add")}</button>
        <button className="action-secondary" onClick={() => setImportOpen(true)}><ImportIcon />{t("materieel.import")}</button>
        <button className="action-secondary" onClick={() => api.exportEquipmentLibrary().catch(e => toast.error(String(e)))}><DownloadIcon />{t("materieel.exportLibrary")}</button>
        <button className="action-secondary" onClick={() => api.downloadEquipmentTemplate().catch(e => toast.error(String(e)))}>{t("import.downloadTemplate")}</button>
      </div>
    </header>
    <div className="equipment-toolbar"><div className="equipment-filters" role="group" aria-label={t("assets.filter")}>
      {["all", "vehicles", "container", "other"].map(value => <button key={value} type="button" aria-pressed={filter === value} onClick={() => setFilter(value)}>{t(`assets.filters.${value}`)}</button>)}
    </div><input className={inputClass} type="search" aria-label={t("assets.search")} placeholder={t("assets.search")} value={search} onChange={event => setSearch(event.target.value)} />
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={archived} onChange={event => setArchived(event.target.checked)} />{t("assets.showArchived")}</label>
    </div>
    <p className="text-sm text-slate-500">{t("materieel.count", { count: filtered.length, total: items.length })}</p>
    {loading ? <p role="status">{t("assets.loading")}</p> : !filtered.length ? <div className="surface p-8"><p>{t(items.length ? "assets.noResults" : "assets.empty")}</p></div> : <div className="equipment-cards">
      {filtered.map(item => <button type="button" className="equipment-card" key={item.id} onClick={() => void open(item.id!)}>
        {item.photo_url ? <img src={item.photo_url} alt="" loading="lazy" /> : <span className="equipment-placeholder" aria-hidden>{(item.asset_code || item.specifications).slice(0, 2).toUpperCase()}</span>}
        <div className="min-w-0"><span className="equipment-kind">{t(`assets.kindValues.${item.kind ?? "other"}`)}{item.active === false && ` · ${t("assets.archived")}`}</span>
          <h3>{item.specifications}</h3><p className="text-sm text-slate-500 dark:text-slate-400">{[item.asset_code, item.container_number || item.registration, item.brand, item.model_name].filter(Boolean).join(" · ") || "—"}</p>
        </div>
        <div className="equipment-card-facts"><span>{dimensions(item)}</span><strong>{number.format(item.weight_kg)} kg</strong><span>{item.current_location || t("assets.locationUnknown")}</span><span>{t(`assets.availabilityValues.${item.availability || "unknown"}`)}</span></div>
      </button>)}
    </div>}
    {form && <EquipmentDialog title={form.id ? t("materieel.edit") : t("materieel.add")} onClose={() => { if (!busy) setForm(null); }}>
      {error && <p role="alert" className="mb-4 text-red-600">{error}</p>}<EquipmentForm initial={form} onSave={save} onClose={() => setForm(null)} busy={busy} />
    </EquipmentDialog>}
    {selected && !form && <EquipmentDialog title={selected.specifications} onClose={() => { if (!busy) setSelected(null); }}>
      {error && <p role="alert" className="mb-4 text-red-600">{error} <button className="underline" onClick={() => void open(selected.id!)}>{t("assets.reload")}</button></p>}
      <div className="space-y-6">
        {selected.photo_url && <img className="max-h-64 w-full rounded-xl object-contain" src={selected.photo_url} alt={selected.specifications} />}
        <div className="flex flex-wrap gap-2"><button className="action-primary" disabled={busy} onClick={() => { setForm(selected); setError(""); }}>{t("materieel.edit")}</button><button className="action-secondary" disabled={busy} onClick={() => duplicate(selected)}>{t("materieel.duplicate")}</button><button className="action-secondary" disabled={busy} onClick={() => void archive()}>{t(selected.active === false ? "assets.restore" : "assets.archive")}</button></div>
        <dl className="equipment-facts">{[["kind", t(`assets.kindValues.${selected.kind ?? "other"}`)], ["asset_code", selected.asset_code], ["container_number", selected.container_number], ["registration", selected.registration], ["serial_number", selected.serial_number], ["brand", selected.brand], ["model_name", selected.model_name], ["dimensions", dimensions(selected)], [selected.kind === "container" ? "tare_kg" : "weight_kg", `${number.format(selected.weight_kg)} kg`], ["max_payload_kg", selected.max_payload_kg], ["max_gross_kg", selected.max_gross_kg], ["container_type", selected.container_type], ["inspection_due", selected.inspection_due], ["current_location", selected.current_location || t("assets.locationUnknown")], ["availability", t(`assets.availabilityValues.${selected.availability || "unknown"}`)], ["condition", t(`assets.conditionValues.${selected.condition || "unknown"}`)], ["planned_reference", selected.planned_reference], ["planned_date", selected.planned_date]].filter(([, value]) => value != null && value !== "").map(([key, value]) => <div key={String(key)}><dt>{t(`assets.${key}`)}</dt><dd>{value}</dd></div>)}</dl>
        {(selected.transport_instructions || selected.accessories || selected.notes) && <section className="space-y-2">{(["transport_instructions", "accessories", "notes"] as const).map(key => selected[key] && <div key={key}><h4 className="font-semibold">{t(`assets.${key}`)}</h4><p className="whitespace-pre-wrap text-sm">{selected[key]}</p></div>)}</section>}
        <section><h4 className="font-semibold">{t("assets.transfer")}</h4><p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{t("assets.moveHint")}</p>
          {!moveOpen ? <button className="action-secondary mt-3" disabled={busy || selected.active === false} onClick={() => setMoveOpen(true)}>{t("assets.transfer")}</button> : <form onSubmit={transfer} className="mt-3 grid gap-3 md:grid-cols-2"><fieldset className="contents" disabled={busy}>
            <label className="equipment-field">{t("assets.destination")}<input className={inputClass} required maxLength={200} value={destination} onChange={event => setDestination(event.target.value)} /></label>
            <label className="equipment-field">{t("assets.availability")}<select className={inputClass} value={availability} onChange={event => setAvailability(event.target.value)}>{["available", "planned", "in_transit", "maintenance", "unknown"].map(value => <option value={value} key={value}>{t(`assets.availabilityValues.${value}`)}</option>)}</select></label>
            <label className="equipment-field">{t("assets.reference")}<input className={inputClass} maxLength={120} value={reference} onChange={event => setReference(event.target.value)} /></label>
            <label className="equipment-field">{t("assets.notes")}<textarea className={inputClass} maxLength={2000} value={notes} onChange={event => setNotes(event.target.value)} /></label>
            <div className="flex gap-2"><button className="action-primary" type="submit">{t("assets.transfer")}</button><button className="action-secondary" type="button" onClick={() => setMoveOpen(false)}>{t("materieel.cancel")}</button></div>
          </fieldset></form>}
        </section>
        <section><h4 className="font-semibold">{t("assets.files")}</h4><p className="my-2 text-xs text-slate-500 dark:text-slate-400">{t("assets.fileHint")}</p>
          <label className="equipment-field"><span className="sr-only">{t("assets.upload")}</span><input type="file" disabled={busy} accept=".pdf,.jpg,.jpeg,.png,.webp" onChange={event => { void upload(event.target.files?.[0]); event.target.value = ""; }} /></label>
          <ul className="mt-3 space-y-2">{selected.files.map(file => <li key={file.id} className="flex items-center justify-between gap-2 text-sm"><a className="min-w-0 break-all text-brand-600 underline dark:text-brand-300" href={`/api/equipment/${selected.id}/files/${file.id}`} target="_blank" rel="noreferrer">{file.name}</a><button type="button" className="action-secondary" disabled={busy} onClick={async () => { setBusy(true); try { await api.deleteEquipmentFile(selected.id!, file.id); await load(); await open(selected.id!); } catch (e) { setError(String(e)); } finally { setBusy(false); } }}>{t("assets.removeFile")}</button></li>)}</ul>
        </section>
        <section><h4 className="mb-3 font-semibold">{t("assets.history")}</h4><ol className="equipment-history">{events.map(event => <li key={event.id}><strong>{t(`assets.events.${event.action}`)}</strong><span>{event.from_location ? `${event.from_location} → ` : ""}{event.to_location || "—"}</span><span>{[event.reference, event.notes].filter(Boolean).join(" · ")}</span><small>{new Date(event.created_at.endsWith("Z") ? event.created_at : event.created_at + "Z").toLocaleString(i18n.language)} · {event.actor_name || "—"}</small></li>)}</ol>
          {nextBefore && <button className="action-secondary mt-3" disabled={busy} onClick={async () => { setBusy(true); try { const next = await api.equipmentEvents(selected.id!, nextBefore); setEvents(previous => [...previous, ...next.events]); setNextBefore(next.next_before); } catch (e) { setError(String(e)); } finally { setBusy(false); } }}>{t("assets.moreHistory")}</button>}
        </section>
      </div>
    </EquipmentDialog>}
    <EquipmentImportDialog open={importOpen} onClose={() => setImportOpen(false)} onComplete={() => void load()} />
  </div>;
}
