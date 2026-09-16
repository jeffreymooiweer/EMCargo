import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { EquipmentInspection } from "../api/client";
import { inspectionKinds, inspectionStatus, needsInspectionAttention } from "../utils/inspections";

export function InspectionBadge({ inspection }: { inspection: EquipmentInspection }) {
  const { t } = useTranslation();
  const state = inspectionStatus(inspection);
  return <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${needsInspectionAttention(inspection) ? "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200" : state === "current" ? "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"}`}>{t(state === "current" ? "equipmentSimple.current" : `inspections.status.${state}`)}</span>;
}

export function InspectionSummary({ items = [] }: { items?: EquipmentInspection[] }) {
  const { t } = useTranslation();
  const active = items.filter(item => !item.archived);
  const attention = active.filter(item => needsInspectionAttention(item)).length;
  return <>{!!active.length && <span className="equipment-count">{active.length}</span>}{!!attention && <span className="equipment-attention">{t("equipmentSimple.attention", { count: attention })}</span>}</>;
}

function InspectionRow({ item, change, renew, remove, editable, canRenew }: {
  item: EquipmentInspection; change: (patch: Partial<EquipmentInspection>) => void;
  renew: () => void; remove: () => void; editable: boolean; canRenew: boolean;
}) {
  const { t, i18n } = useTranslation();
  const [expanded, setExpanded] = useState(editable && !item.performed_on && !item.due_on);
  const name = item.name || t(`inspections.kinds.${item.kind}`);
  const dateLabel = (value: string) => new Date(`${value}T12:00:00`).toLocaleDateString(i18n.language);
  const field = (key: "name" | "scope" | "performed_on" | "due_on" | "inspector" | "reference", date = false) =>
    <label className="equipment-field" key={key}>{t(`inspections.${key}`)}<input className="equipment-input" type={date ? "date" : "text"} value={item[key] ?? ""} required={(key === "name" && item.kind === "other") || (key === "performed_on" && ["passed", "failed", "conditional"].includes(item.result))} min={key === "due_on" ? item.performed_on ?? undefined : undefined} onChange={event => change({ [key]: event.target.value || (date ? null : "") })} /></label>;
  return <details className="equipment-inspection" open={expanded} onToggle={event => setExpanded(event.currentTarget.open)}>
    <summary><span className="min-w-0"><strong>{name}</strong><small>{item.due_on ? t("inspections.dueSummary", { date: dateLabel(item.due_on) }) : t("inspections.noDueDate")}</small></span><InspectionBadge inspection={item} /></summary>
    {editable ? <div className="space-y-3 pt-4"><div className="grid gap-3 sm:grid-cols-2">
      <label className="equipment-field">{t("inspections.kind")}<select className="equipment-input" value={item.kind} onChange={event => change({ kind: event.target.value as EquipmentInspection["kind"] })}>{inspectionKinds.map(kind => <option value={kind} key={kind}>{t(`inspections.kinds.${kind}`)}</option>)}</select></label>
      <label className="equipment-field">{t("inspections.result")}<select className="equipment-input" value={item.result} onChange={event => change({ result: event.target.value as EquipmentInspection["result"] })}>{["unknown", "passed", "failed", "conditional", "not_applicable"].map(result => <option value={result} key={result}>{t(`inspections.results.${result}`)}</option>)}</select></label>
      {item.kind === "other" && field("name")}{field("performed_on", true)}{field("due_on", true)}
    </div>
    <details className="equipment-section"><summary>{t("equipmentSimple.reportDetails")}</summary><div className="equipment-section-body grid gap-3 sm:grid-cols-2">
      {item.kind !== "other" && field("name")}{field("scope")}{field("inspector")}{field("reference")}
      <label className="equipment-field sm:col-span-2">{t("assets.notes")}<textarea rows={2} className="equipment-input" value={item.notes ?? ""} onChange={event => change({ notes: event.target.value })} /></label>
    </div></details>
    <div className="flex flex-wrap gap-x-4">
      {!item.archived && !!(item.performed_on || item.due_on) && <button type="button" className="equipment-text-button" disabled={!canRenew} onClick={renew}>{t("inspections.renew")}</button>}
      {(item.archived || !!(item.performed_on || item.due_on)) && <button type="button" className="equipment-text-button" onClick={() => change({ archived: !item.archived })}>{t(item.archived ? "assets.restore" : "assets.archive")}</button>}
      <button type="button" className="equipment-text-button" onClick={remove}>{t("inspections.remove")}</button>
    </div></div> : <dl className="equipment-facts mt-4"><div><dt>{t("inspections.result")}</dt><dd>{t(`inspections.results.${item.result}`)}</dd></div>{(["scope", "performed_on", "due_on", "inspector", "reference", "notes"] as const).filter(key => item[key]).map(key => <div key={key}><dt>{t(key === "notes" ? "assets.notes" : `inspections.${key}`)}</dt><dd className="whitespace-pre-wrap">{key === "performed_on" || key === "due_on" ? dateLabel(item[key]!) : item[key]}</dd></div>)}</dl>}
  </details>;
}

export default function EquipmentInspections({ items = [], onChange }: {
  items?: EquipmentInspection[]; onChange?: (items: EquipmentInspection[]) => void;
}) {
  const { t } = useTranslation();
  const [history, setHistory] = useState(false);
  const update = (id: string, patch: Partial<EquipmentInspection>) => onChange?.(items.map(item => item.id === id ? { ...item, ...patch } : item));
  const blank = (kind: EquipmentInspection["kind"] = "general"): EquipmentInspection => ({ id: crypto.randomUUID(), kind, result: "unknown" });
  return <div className="space-y-3">
    {!items.filter(item => !item.archived).length && <p className="text-sm text-slate-500">{t("inspections.empty")}</p>}
    {items.filter(item => history || !item.archived).map(item => <InspectionRow key={item.id} item={item} editable={!!onChange} canRenew={items.length < 100}
      change={patch => update(item.id, patch)} remove={() => onChange?.(items.filter(row => row.id !== item.id))}
      renew={() => { if (items.length < 100) onChange?.([...items.map(row => row.id === item.id ? { ...row, archived: true } : row), { ...blank(item.kind), name: item.name, scope: item.scope }]); }} />)}
    {items.some(item => item.archived) && <label className="equipment-check"><input type="checkbox" checked={history} onChange={event => setHistory(event.target.checked)} />{t("inspections.showHistory")}</label>}
    {onChange && <button type="button" className="action-secondary" disabled={items.length >= 100} onClick={() => onChange([...items, blank()])}>{t("inspections.add")}</button>}
  </div>;
}
