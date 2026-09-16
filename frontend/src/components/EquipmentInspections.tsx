import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { EquipmentInspection } from "../api/client";
import { inspectionKinds, inspectionStatus, needsInspectionAttention } from "../utils/inspections";

const fieldClass = "min-h-[44px] w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950";
export function InspectionBadge({ inspection }: { inspection: EquipmentInspection }) {
  const { t } = useTranslation();
  const state = inspectionStatus(inspection);
  return <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${needsInspectionAttention(inspection) ? "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200" : state === "current" ? "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"}`}>{t(`inspections.status.${state}`)}</span>;
}

function InspectionRow({ item, change, renew, remove, editable, canRenew }: {
  item: EquipmentInspection; change: (patch: Partial<EquipmentInspection>) => void;
  renew: () => void; remove: () => void; editable: boolean; canRenew: boolean;
}) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(editable && !item.performed_on && !item.due_on);
  const name = item.name || t(`inspections.kinds.${item.kind}`);
  const field = (key: "name" | "scope" | "performed_on" | "due_on" | "inspector" | "reference", date = false) =>
    <label className="equipment-field" key={key}>{t(`inspections.${key}`)}<input className={fieldClass} type={date ? "date" : "text"} value={item[key] ?? ""} required={(key === "name" && item.kind === "other") || (key === "performed_on" && ["passed", "failed", "conditional"].includes(item.result))} min={key === "due_on" ? item.performed_on ?? undefined : undefined} onChange={event => change({ [key]: event.target.value || (date ? null : "") })} /></label>;
  return <details className="rounded-xl border border-slate-200 p-3 dark:border-slate-700" open={expanded} onToggle={event => setExpanded(event.currentTarget.open)}>
    <summary className="cursor-pointer text-sm"><span className="ml-1 font-semibold">{name}{item.scope && ` · ${item.scope}`}</span><span className="ml-2"><InspectionBadge inspection={item} /></span>
      <span className="mt-1 block pl-5 text-xs text-slate-500">{item.due_on ? t("inspections.dueSummary", { date: item.due_on }) : t("inspections.noDueDate")}</span>
    </summary>
    {editable ? <div className="mt-4 space-y-3"><div className="grid gap-3 md:grid-cols-2">
      <label className="equipment-field">{t("inspections.kind")}<select className={fieldClass} value={item.kind} onChange={event => change({ kind: event.target.value as EquipmentInspection["kind"] })}>{inspectionKinds.map(kind => <option value={kind} key={kind}>{t(`inspections.kinds.${kind}`)}</option>)}</select></label>
      {field("name")}{field("scope")}
      <label className="equipment-field">{t("inspections.result")}<select className={fieldClass} value={item.result} onChange={event => change({ result: event.target.value as EquipmentInspection["result"] })}>{["unknown", "passed", "failed", "conditional", "not_applicable"].map(result => <option value={result} key={result}>{t(`inspections.results.${result}`)}</option>)}</select></label>
      {field("performed_on", true)}{field("due_on", true)}{field("inspector")}{field("reference")}
      <label className="equipment-field md:col-span-2">{t("assets.notes")}<textarea rows={2} className={fieldClass} value={item.notes ?? ""} onChange={event => change({ notes: event.target.value })} /></label>
    </div><div className="flex flex-wrap gap-2">
      {!item.archived && <button type="button" className="action-secondary" disabled={!canRenew} onClick={renew}>{t("inspections.renew")}</button>}
      <button type="button" className="action-secondary" onClick={() => change({ archived: !item.archived })}>{t(item.archived ? "assets.restore" : "assets.archive")}</button>
      <button type="button" className="action-secondary" onClick={remove}>{t("inspections.remove")}</button>
    </div></div> : <dl className="equipment-facts mt-4"><div><dt>{t("inspections.result")}</dt><dd>{t(`inspections.results.${item.result}`)}</dd></div>{(["performed_on", "due_on", "inspector", "reference", "notes"] as const).filter(key => item[key]).map(key => <div key={key}><dt>{t(key === "notes" ? "assets.notes" : `inspections.${key}`)}</dt><dd className="whitespace-pre-wrap">{item[key]}</dd></div>)}</dl>}
  </details>;
}

export default function EquipmentInspections({ items = [], onChange }: {
  items?: EquipmentInspection[]; onChange?: (items: EquipmentInspection[]) => void;
}) {
  const { t } = useTranslation();
  const [history, setHistory] = useState(false);
  const update = (id: string, patch: Partial<EquipmentInspection>) => onChange?.(items.map(item => item.id === id ? { ...item, ...patch } : item));
  const blank = (kind: EquipmentInspection["kind"] = "general"): EquipmentInspection => ({ id: crypto.randomUUID(), kind, result: "unknown" });
  return <section className="space-y-3"><h4 className="font-semibold">{t("inspections.title")}</h4>
    <p className="text-sm text-slate-500 dark:text-slate-400">{t("inspections.hint")}</p>
    {!items.filter(item => !item.archived).length && <p className="text-sm text-slate-500">{t("inspections.empty")}</p>}
    {items.filter(item => history || !item.archived).map(item => <InspectionRow key={item.id} item={item} editable={!!onChange} canRenew={items.length < 100}
      change={patch => update(item.id, patch)} remove={() => onChange?.(items.filter(row => row.id !== item.id))}
      renew={() => { if (items.length < 100) onChange?.([...items.map(row => row.id === item.id ? { ...row, archived: true } : row), { ...blank(item.kind), name: item.name, scope: item.scope }]); }} />)}
    {items.some(item => item.archived) && <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={history} onChange={event => setHistory(event.target.checked)} />{t("inspections.showHistory")}</label>}
    {onChange && <button type="button" className="action-secondary" disabled={items.length >= 100} onClick={() => onChange([...items, blank()])}>{t("inspections.add")}</button>}
  </section>;
}
