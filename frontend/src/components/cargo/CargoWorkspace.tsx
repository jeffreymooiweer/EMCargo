import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type EquipmentSnapshot } from "../../api/client";
import { cargoApi, type CargoAssessment, type CargoGood, type CargoManifest, type CargoUnit, type PackagingTemplate } from "../../api/cargo";
import { equipmentSnapshot } from "../../utils/equipment";
import { cargoUnitGroups, cargoUnitWeight, CARGO_MAX_UNITS, CargoError, descendantIds, detachCargoGroup, isWholeUnit, placeCargo, remainingQuantity, topSelectedUnitIds, unpackCargo, validateCargo, type CargoSelection } from "../../utils/cargo";
import EquipmentDialog from "../EquipmentDialog";
import EquipmentMenu from "../EquipmentMenu";
import NumberInput from "../NumberInput";
import { ChevronDownIcon, CloseIcon, LayersIcon, PlusIcon, RoadIcon } from "../icons";
import CargoUnitFields, { blankTemplate } from "./CargoUnitFields";
import "./cargo.css";

export interface CargoWorkspaceProps {
  value: CargoManifest; goods: CargoGood[]; onChange: (value: CargoManifest) => void;
  templates?: PackagingTemplate[]; equipment?: EquipmentSnapshot[];
  canManageTemplates?: boolean; disabled?: boolean;
  assessment?: CargoAssessment | null;
}
type Selected = { type: "unit"; id: string } | { type: "goods"; id: number; allocation_id?: string };
const keyOf = (item: Selected) => item.type === "unit" ? `u:${item.id}` : `g:${item.id}:${item.allocation_id ?? "loose"}`;
const recentTemplatesKey = "emcargo-cargo-recent-templates";

export default function CargoWorkspace({ value, goods, onChange, templates, equipment, canManageTemplates = false, disabled = false, assessment }: CargoWorkspaceProps) {
  const { t, i18n } = useTranslation();
  const number = (value: number) => new Intl.NumberFormat(i18n.language, { maximumFractionDigits: 3 }).format(value);
  const [selected, setSelected] = useState<Selected[]>([]);
  const [openUnits, setOpenUnits] = useState<Set<string>>(new Set());
  const [openGroups, setOpenGroups] = useState<Set<string>>(new Set());
  const [limit, setLimit] = useState(50);
  const [placing, setPlacing] = useState(false);
  const [editing, setEditing] = useState<CargoUnit | null>(null);
  const [undo, setUndo] = useState<CargoManifest[]>([]);
  const [error, setError] = useState("");
  const [announcement, setAnnouncement] = useState("");
  const lastValue = useRef(value);
  const lastGoods = useRef(goods);
  const [models, setModels] = useState<PackagingTemplate[]>(templates ?? []);
  const [assets, setAssets] = useState<EquipmentSnapshot[]>(equipment ?? []);
  const [reusableUnits, setReusableUnits] = useState<CargoUnit[]>([]);
  const [catalogueFailed, setCatalogueFailed] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let alive = true;
    if (!disabled) cargoApi.reusableUnits().then(data => { if (alive) setReusableUnits(data); }).catch(() => { /* Retention is optional. */ });
    if (templates) setModels(templates);
    else cargoApi.templates().then(data => { if (alive) { setModels(data); setCatalogueFailed(false); } }).catch(() => { if (alive) setCatalogueFailed(true); });
    if (equipment) setAssets(equipment);
    else api.listEquipment().then(data => { if (alive) setAssets(data.filter(item => item.active !== false && ["vehicle", "container"].includes(item.kind ?? "")).map(equipmentSnapshot)); }).catch(() => { /* An inline external destination remains available. */ });
    return () => { alive = false; };
  }, [templates, equipment, retry, disabled]);

  useEffect(() => {
    // Undo belongs to this exact goods state; stale history must not undo a later
    // article deletion or a shipment loaded by the surrounding wizard.
    const topology = (items: CargoGood[]) => JSON.stringify(items.map(item => [item.id, item.quantity, item.unit]));
    if (topology(lastGoods.current) !== topology(goods) || (lastValue.current !== value && lastValue.current.shipment_id !== value.shipment_id)) {
      setUndo([]); setSelected([]); setPlacing(false); setEditing(null);
    }
    lastValue.current = value; lastGoods.current = goods;
  }, [value, goods]);

  const fail = (cause: unknown) => setError(cause instanceof CargoError ? t(`cargo.errors.${cause.code}`) : cause instanceof Error ? cause.message : t("cargo.errors.failed"));
  const apply = (next: CargoManifest) => {
    setUndo(previous => [...previous.slice(-9), structuredClone(value)]); lastValue.current = next;
    onChange(next); setSelected([]); setError(""); setAnnouncement(t("cargo.updated"));
  };
  const toggle = (items: Selected[]) => {
    const keys = new Set(items.map(keyOf));
    const already = items.every(item => selected.some(current => keyOf(current) === keyOf(item)));
    setSelected(previous => already ? previous.filter(item => !keys.has(keyOf(item))) : [...previous.filter(item => !keys.has(keyOf(item))), ...items]);
  };
  const chosenUnits = topSelectedUnitIds(value, selected.filter((item): item is Extract<Selected, { type: "unit" }> => item.type === "unit").map(item => item.id));
  const covered = descendantIds(value, chosenUnits);
  const selection: CargoSelection = {
    unit_ids: chosenUnits,
    goods: selected.flatMap(item => {
      if (item.type !== "goods") return [];
      const good = goods.find(g => g.id === item.id);
      const allocation = value.allocations.find(a => a.id === item.allocation_id);
      if (!good || (allocation && covered.has(allocation.unit_id))) return [];
      const quantity = allocation?.quantity ?? remainingQuantity(value, good);
      return quantity !== null && quantity > 0 ? [{ goods_id: good.id, quantity, allocation_id: item.allocation_id }] : [];
    }),
  };
  let validation = "";
  try { validateCargo(value, goods); } catch (cause) { validation = cause instanceof CargoError ? t(`cargo.errors.${cause.code}`) : t("cargo.errors.failed"); }
  const summaryWeight = useMemo(() => {
    if (goods.some(good => good.weight_kg === null) || value.units.some(unit => unit.kind === "package" && unit.tare_kg == null)) return null;
    return goods.reduce((total, good) => total + (good.weight_kg ?? 0), 0) + value.units.filter(unit => unit.kind === "package").reduce((total, unit) => total + (unit.tare_kg ?? 0), 0);
  }, [value, goods]);
  const weightLabel = (weight: number | null) => weight === null ? t("cargo.weightUnknown") : `${number(weight)} kg`;
  const dimensions = (unit: CargoUnit) => {
    const d = unit.loaded_dimensions_mm ?? (unit.category === "pallet" ? null : unit.dimensions_mm);
    return d && [d.length, d.width, d.height].every(n => n != null) ? `${[d.length, d.width, d.height].map(n => number(n! / 10)).join(" × ")} cm` : null;
  };
  const goodRow = (good: CargoGood, quantity: number | null, allocationId?: string) => {
    const item: Selected = { type: "goods", id: good.id, allocation_id: allocationId };
    const weight = good.weight_kg === null || !good.quantity || quantity === null ? null : good.weight_kg * quantity / good.quantity;
    const checked = selected.some(current => keyOf(current) === keyOf(item));
    const parent = allocationId ? value.allocations.find(a => a.id === allocationId)?.unit_id : null;
    return <li key={keyOf(item)} className="cargo-good-row">
      <label className="cargo-row-select">{!disabled && <input type="checkbox" checked={checked} disabled={quantity === null || quantity <= 0 || !!parent && covered.has(parent)} onChange={() => toggle([item])} aria-label={t("cargo.selectItem", { name: good.name })} />}<span className="cargo-good-copy"><strong>{good.name}</strong><span>{quantity === null ? t("cargo.quantityUnknown") : `${number(quantity)} ${t(`units.${good.unit}`, { defaultValue: good.unit })}`}</span></span></label>
      <span className="cargo-row-weight">{weightLabel(weight)}</span>
    </li>;
  };
  const unitRow = (unit: CargoUnit, depth: number): React.ReactNode => {
    const open = openUnits.has(unit.id); const children = value.units.filter(u => u.parent_id === unit.id);
    const content = value.allocations.filter(a => a.unit_id === unit.id);
    const inheritedSelection = !!unit.parent_id && covered.has(unit.parent_id);
    return <li key={unit.id} className="cargo-unit">
      <div className="cargo-unit-row">
        {!disabled && <input type="checkbox" checked={selected.some(item => item.type === "unit" && item.id === unit.id)} disabled={inheritedSelection} onChange={() => toggle([{ type: "unit", id: unit.id }])} aria-label={t("cargo.selectItem", { name: unit.name })} />}
        <button type="button" className="cargo-unit-toggle" aria-expanded={open} onClick={() => setOpenUnits(previous => { const next = new Set(previous); next.has(unit.id) ? next.delete(unit.id) : next.add(unit.id); return next; })}>
          <span className="cargo-unit-icon">{unit.kind === "ctu" ? <RoadIcon /> : <LayersIcon />}</span><span className="cargo-unit-copy"><strong>{unit.name}</strong><span>{unit.external_reference || unit.code}{dimensions(unit) ? ` · ${dimensions(unit)}` : ""}</span></span><ChevronDownIcon className={open ? "cargo-chevron is-open" : "cargo-chevron"} />
        </button>
        <span className="cargo-row-weight">{weightLabel(cargoUnitWeight(value, goods, unit.id))}{unit.measured_gross_kg != null && <span className="cargo-measured">{t("cargo.measured", { weight: number(unit.measured_gross_kg) })}</span>}</span>
        {!disabled && <EquipmentMenu><button type="button" onClick={() => setEditing({ ...unit })}>{t("cargo.edit")}</button><button type="button" onClick={() => { setSelected([{ type: "unit", id: unit.id }]); setPlacing(true); }}>{t("cargo.place")}</button>
          {!!unit.group_id && <button type="button" onClick={() => apply(detachCargoGroup(value, unit.id))}>{t("cargo.splitOne")}</button>}
          <button type="button" onClick={() => { try { apply(unpackCargo(value, goods, [unit.id])); } catch (cause) { fail(cause); } }}>{t("cargo.unpack")}</button></EquipmentMenu>}
      </div>
      {open && depth < 20 && <ul className="cargo-contents">
        {content.map(a => { const good = goods.find(g => g.id === a.goods_id); return good ? goodRow(good, a.quantity, a.id) : null; })}
        {renderGroups(unit.id, depth + 1)}
        {!content.length && !children.length && <li className="cargo-empty">{t("cargo.emptyUnit")}</li>}
      </ul>}
    </li>;
  };
  function renderGroups(parent: string | null, depth: number): React.ReactNode {
    const groups = cargoUnitGroups(value, parent);
    return <>{groups.slice(0, limit).map(group => {
      if (group.length === 1) return unitRow(group[0], depth);
      const first = group[0], groupKey = `${first.group_id}:${first.id}`, open = openGroups.has(groupKey);
      const unitWeight = cargoUnitWeight(value, goods, first.id);
      return <li key={groupKey} className="cargo-unit cargo-unit-group"><div className="cargo-unit-row">
        {!disabled && <input type="checkbox" aria-label={t("cargo.selectItem", { name: `${group.length} × ${first.name}` })} disabled={!!parent && covered.has(parent)} checked={group.every(unit => selected.some(item => item.type === "unit" && item.id === unit.id))} onChange={() => toggle(group.map(unit => ({ type: "unit", id: unit.id })))} />}
        <button type="button" className="cargo-unit-toggle" aria-expanded={open} onClick={() => setOpenGroups(previous => { const next = new Set(previous); next.has(groupKey) ? next.delete(groupKey) : next.add(groupKey); return next; })}>
          <span className="cargo-unit-icon"><LayersIcon /></span><span className="cargo-unit-copy"><strong>{group.length} × {first.name}</strong><span>{dimensions(first) ?? t("cargo.identicalUnits")}</span></span><ChevronDownIcon className={open ? "cargo-chevron is-open" : "cargo-chevron"} /></button>
        <span className="cargo-row-weight">{weightLabel(unitWeight === null ? null : unitWeight * group.length)}</span>
      </div>{open && <ul className="cargo-contents">{group.slice(0, limit).map(unit => unitRow(unit, depth))}{group.length > limit && <li><button className="cargo-text-button" type="button" onClick={() => setLimit(count => count + 50)}>{t("cargo.showMore")}</button></li>}</ul>}</li>;
    })}{groups.length > limit && <li><button type="button" className="cargo-text-button" onClick={() => setLimit(count => count + 50)}>{t("cargo.showMore")}</button></li>}</>;
  }

  return <section className="cargo-workspace" aria-label={t("cargo.title")}>
    <header className="cargo-heading"><div><h3>{t("cargo.title")}</h3><span>{t("cargo.goodsCount", { count: goods.length })} · {weightLabel(summaryWeight)}</span></div>
      <div className="cargo-header-actions">{undo.length > 0 && !disabled && <button type="button" className="cargo-text-button" onClick={() => {
        const previous = undo[undo.length - 1]; const restored = { ...previous, revision: value.revision + 1 }; lastValue.current = restored;
        onChange(restored); setUndo(items => items.slice(0, -1)); setSelected([]); setError(""); setAnnouncement(t("cargo.undone"));
      }}>{t("cargo.undo")}</button>}
      {!disabled && <button type="button" className="cargo-button" onClick={() => { setSelected([]); setPlacing(true); }}><PlusIcon />{t("cargo.newUnit")}</button>}</div>
    </header>
    {(error || validation) && <div role="alert" className="cargo-error">{error || validation}</div>}
    {assessment?.issues.filter(issue => issue.code !== "cargo.weight_unknown").map((issue, index) => <p key={`${issue.code}:${issue.unit_id ?? ""}:${index}`} role="alert" className="cargo-error">{issue.unit_id ? `${value.units.find(unit => unit.id === issue.unit_id)?.name ?? ""}: ` : ""}{t(`errors.${issue.code}`)}</p>)}
    {catalogueFailed && <div className="cargo-error">{t("cargo.catalogueFailed")} <button type="button" onClick={() => setRetry(n => n + 1)}>{t("cargo.retry")}</button></div>}
    {!!selected.length && <div className="cargo-selection"><span>{t("cargo.selectedCount", { count: selection.unit_ids.length + selection.goods.length })}</span><button type="button" className="cargo-button cargo-primary" onClick={() => setPlacing(true)} disabled={!selection.unit_ids.length && !selection.goods.length}>{t("cargo.place")}</button>
      {!!selection.unit_ids.length && <button type="button" className="cargo-button" onClick={() => { try { apply(unpackCargo(value, goods, selection.unit_ids)); } catch (cause) { fail(cause); } }}>{t("cargo.unpack")}</button>}
      <button className="cargo-icon-button" type="button" onClick={() => setSelected([])} aria-label={t("cargo.clearSelection")}><CloseIcon /></button>
    </div>}
    <ul className="cargo-tree">{renderGroups(null, 0)}</ul>
    {goods.some(good => remainingQuantity(value, good) === null || remainingQuantity(value, good)! > 0) && <div className="cargo-loose"><h4>{t("cargo.loose")}</h4><ul>{goods.filter(good => remainingQuantity(value, good) === null || remainingQuantity(value, good)! > 0).slice(0, limit).map(good => goodRow(good, remainingQuantity(value, good)))}</ul>
      {goods.length > limit && <button type="button" className="cargo-text-button" onClick={() => setLimit(count => count + 50)}>{t("cargo.showMore")}</button>}
    </div>}
    {!value.units.length && !goods.length && <p className="cargo-empty">{t("cargo.empty")}</p>}
    <span className="sr-only" role="status">{announcement}</span>
    {placing && <PlacementDialog value={value} goods={goods} selection={selection} models={models} equipment={assets} reusableUnits={reusableUnits} canManageTemplates={canManageTemplates}
      onClose={() => setPlacing(false)} onApply={next => { apply(next); setPlacing(false); }} onTemplate={model => setModels(previous => [...previous, model])} />}
    {editing && <EquipmentDialog title={t("cargo.edit")} onClose={() => setEditing(null)}>
      <form className="cargo-form" onInvalid={event => { for (let node = (event.target as HTMLElement).parentElement; node; node = node.parentElement) if (node instanceof HTMLDetailsElement) node.open = true; }} onSubmit={event => { event.preventDefault(); try { const next = { ...value, revision: value.revision + 1, units: value.units.map(unit => unit.id === editing.id ? editing : unit) }; validateCargo(next, goods); apply(next); setEditing(null); } catch (cause) { fail(cause); } }}>
        <CargoUnitFields value={editing} unit onChange={next => setEditing(next as CargoUnit)} />{error && <p className="cargo-error" role="alert">{error}</p>}<div className="cargo-dialog-actions"><button type="button" className="cargo-button" onClick={() => setEditing(null)}>{t("cargo.cancel")}</button><button className="cargo-button cargo-primary" type="submit">{t("cargo.save")}</button></div>
      </form>
    </EquipmentDialog>}
  </section>;
}

function PlacementDialog({ value, goods, selection, models, equipment, reusableUnits, canManageTemplates, onClose, onApply, onTemplate }: {
  value: CargoManifest; goods: CargoGood[]; selection: CargoSelection; models: PackagingTemplate[]; equipment: EquipmentSnapshot[]; reusableUnits: CargoUnit[]; canManageTemplates: boolean;
  onClose: () => void; onApply: (value: CargoManifest) => void; onTemplate: (value: PackagingTemplate) => void;
}) {
  const { t, i18n } = useTranslation();
  const [destination, setDestination] = useState("");
  const [template, setTemplate] = useState<PackagingTemplate>(blankTemplate());
  const [unitOptions, setUnitOptions] = useState<Partial<CargoUnit>>({});
  const [count, setCount] = useState(1);
  const [mode, setMode] = useState<"total" | "per_unit">("total");
  const [quantities, setQuantities] = useState(selection.goods.map(good => good.quantity));
  const [saveModel, setSaveModel] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const existing = destination.startsWith("unit:");
  const loose = destination === "loose";
  const creating = !!destination && !existing && !loose;
  const canMultiply = creating && unitOptions.kind !== "ctu" && !selection.unit_ids.length && !destination.startsWith("reuse:");
  const blocked = descendantIds(value, selection.unit_ids);
  const number = (value: number) => new Intl.NumberFormat(i18n.language, { maximumFractionDigits: 6 }).format(value);
  const nameOf = (model: PackagingTemplate) => model.language_labels?.[i18n.language.slice(0, 2)] || model.name;
  const recent = useMemo(() => { try { const stored: unknown = JSON.parse(localStorage.getItem(recentTemplatesKey) || "[]"); return Array.isArray(stored) ? stored.filter((entry): entry is string => typeof entry === "string") : []; } catch { return []; } }, []);
  const sorted = [...models].filter(model => model.active !== false).sort((a, b) => (recent.indexOf(a.id) < 0 ? 100 : recent.indexOf(a.id)) - (recent.indexOf(b.id) < 0 ? 100 : recent.indexOf(b.id)));
  const choose = (choice: string) => {
    setDestination(choice); setError(""); setCount(1); setMode("total"); setQuantities(selection.goods.map(good => good.quantity)); setSaveModel(false); setUnitOptions({});
    if (choice.startsWith("model:")) { const found = models.find(model => model.id === choice.slice(6)); if (found) setTemplate({ ...found, name: nameOf(found) }); }
    else if (choice.startsWith("reuse:")) {
      const found = reusableUnits.find(unit => unit.id === choice.slice(6))!;
      setTemplate({ ...found, measured_gross_kg: null, loaded_dimensions_mm: null } as PackagingTemplate); setUnitOptions({ id: found.id, code: found.code, kind: found.kind, template_id: found.template_id, equipment_id: found.equipment_id, source: found.source, external_reference: found.external_reference, parent_id: null, group_id: null });
    }
    else if (choice.startsWith("asset:")) {
      const asset = equipment.find(item => item.equipment_id === Number(choice.slice(6)))!;
      const physical = reusableUnits.find(unit => unit.equipment_id === asset.equipment_id);
      setTemplate({ id: "", name: asset.specifications, category: asset.kind === "container" ? "container" : "vehicle", tare_kg: asset.weight_kg, reusable: true,
        dimensions_mm: { length: asset.length_cm == null ? null : asset.length_cm * 10, width: asset.width_cm == null ? null : asset.width_cm * 10, height: asset.height_cm == null ? null : asset.height_cm * 10 },
        inner_dimensions_mm: { length: asset.inner_length_cm == null ? null : asset.inner_length_cm * 10, width: asset.inner_width_cm == null ? null : asset.inner_width_cm * 10, height: asset.inner_height_cm == null ? null : asset.inner_height_cm * 10 },
        max_payload_kg: asset.max_payload_kg, max_gross_kg: asset.max_gross_kg });
      setUnitOptions({ kind: "ctu", ...(physical ? { id: physical.id, code: physical.code } : {}), equipment_id: asset.equipment_id, external_reference: asset.container_number || asset.registration || asset.asset_code || "", source: "own" });
    } else if (choice === "external" || choice === "unknown") {
      setTemplate({ id: "", name: t(choice === "external" ? "cargo.externalVehicle" : "cargo.unknownVehicle"), category: "vehicle", reusable: false }); setUnitOptions({ kind: "ctu", source: choice });
    } else setTemplate(blankTemplate());
  };
  const portions = selection.goods.map((item, index) => {
    const good = goods.find(g => g.id === item.goods_id)!;
    const amount = quantities[index] ?? 0; const divisor = canMultiply ? count : 1;
    const raw = mode === "per_unit" && canMultiply ? amount : amount / divisor;
    const each = isWholeUnit(good.unit) ? Math.floor(raw) : Math.floor(raw * 1e6) / 1e6;
    return { good, each, rest: Math.round((item.quantity - each * divisor) * 1e6) / 1e6 };
  });
  return <EquipmentDialog title={selection.unit_ids.length || selection.goods.length ? t("cargo.place") : t("cargo.newUnit")} onClose={() => { if (!submitting.current) onClose(); }}>
    <form className="cargo-form" onInvalid={event => { const field = event.target as HTMLElement; for (let node = field.parentElement; node; node = node.parentElement) if (node instanceof HTMLDetailsElement) node.open = true; }} onSubmit={async event => {
      event.preventDefault(); if (submitting.current) return; submitting.current = true; setError(""); setBusy(true);
      try {
        if (!destination) throw new CargoError("chooseDestination");
        let resolvedOptions = unitOptions;
        if (destination.startsWith("asset:") && unitOptions.equipment_id != null) {
          const existingUnit = (await cargoApi.reusableUnits("", unitOptions.equipment_id))[0];
          if (existingUnit) resolvedOptions = { ...unitOptions, id: existingUnit.id, code: existingUnit.code };
        }
        const selected = { ...selection, goods: selection.goods.map((item, index) => ({ ...item, quantity: quantities[index] })) };
        const options = { destination_id: existing ? destination.slice(5) : null, template: creating ? template : undefined, unit_options: resolvedOptions, count: canMultiply ? count : 1, mode: canMultiply ? mode : "total" as const };
        let next = placeCargo(value, goods, selected, options);
        if (saveModel && creating && canManageTemplates) {
          const { id: _id, ...body } = template;
          const saved = await cargoApi.createTemplate(body); onTemplate(saved);
          const oldIds = new Set(value.units.map(unit => unit.id));
          next = { ...next, units: next.units.map(unit => oldIds.has(unit.id) ? unit : { ...unit, template_id: saved.id }) };
        }
        if (creating && template.id) { try { localStorage.setItem(recentTemplatesKey, JSON.stringify([template.id, ...recent.filter(id => id !== template.id)].slice(0, 8))); } catch { /* Storage is optional. */ } }
        onApply(next);
      } catch (cause) { setError(cause instanceof CargoError ? t(`cargo.errors.${cause.code}`) : cause instanceof Error ? cause.message : t("cargo.errors.failed")); }
      finally { submitting.current = false; setBusy(false); }
    }}><fieldset disabled={busy} className="contents">
      <label>{t("cargo.destination")}<select autoFocus required value={destination} onChange={event => choose(event.target.value)}>
        <option value="">{t("cargo.chooseDestination")}</option>
        {value.units.some(unit => !blocked.has(unit.id)) && <optgroup label={t("cargo.existingUnits")}>{value.units.filter(unit => !blocked.has(unit.id)).map(unit => <option key={unit.id} value={`unit:${unit.id}`}>{unit.name} · {unit.external_reference || unit.code}</option>)}</optgroup>}
        <optgroup label={t("cargo.newPackage")}>{sorted.map(model => <option key={model.id} value={`model:${model.id}`}>{nameOf(model)}</option>)}<option value="custom">{t("cargo.customPackage")}</option></optgroup>
        {reusableUnits.some(unit => !value.units.some(current => current.id === unit.id)) && <optgroup label={t("cargo.reusableUnits")}>{reusableUnits.filter(unit => !value.units.some(current => current.id === unit.id)).map(unit => <option key={unit.id} value={`reuse:${unit.id}`}>{unit.name} · {unit.external_reference || unit.code}</option>)}</optgroup>}
        <optgroup label={t("cargo.transport")}>
          {equipment.filter(asset => !value.units.some(unit => unit.equipment_id === asset.equipment_id)).map(asset => <option key={asset.equipment_id} value={`asset:${asset.equipment_id}`}>{asset.specifications}{asset.registration || asset.container_number ? ` · ${asset.registration || asset.container_number}` : ""}</option>)}
          <option value="external">{t("cargo.externalVehicle")}</option><option value="unknown">{t("cargo.unknownVehicle")}</option>
          {(selection.unit_ids.length > 0 || selection.goods.some(item => item.allocation_id)) && <option value="loose">{t("cargo.loose")}</option>}
        </optgroup>
      </select></label>
      {creating && <>
        <CargoUnitFields value={{ ...template, ...unitOptions } as CargoUnit} onChange={next => { setTemplate(next); setUnitOptions(previous => ({ ...previous, external_reference: (next as CargoUnit).external_reference })); }} />
        {canMultiply && <div className="cargo-field-pair"><label>{t("cargo.packageCount")}<NumberInput required min="1" max={CARGO_MAX_UNITS - value.units.length} step="1" value={count} onChange={event => setCount(Number(event.target.value))} /></label>
          {count > 1 && selection.goods.length > 0 && <label>{t("cargo.fill")}<select value={mode} onChange={event => { const next = event.target.value as "total" | "per_unit"; setQuantities(current => current.map((quantity, index) => next === "per_unit" ? portions[index].each : quantity * count)); setMode(next); }}><option value="total">{t("cargo.distributeTotal")}</option><option value="per_unit">{t("cargo.perPackage")}</option></select></label>}
        </div>}
      </>}
      {selection.goods.length > 0 && <div className="cargo-quantity-list">{selection.goods.map((item, index) => {
        const { good, each, rest } = portions[index];
        return <div key={`${item.goods_id}:${item.allocation_id ?? "loose"}`} className="cargo-quantity-row"><label>{good.name}<span className="cargo-quantity-input"><NumberInput required min={isWholeUnit(good.unit) ? 1 : 0.000001} max={canMultiply && mode === "per_unit" ? item.quantity / count : item.quantity} step={isWholeUnit(good.unit) ? 1 : "any"} value={quantities[index] || ""} onChange={event => setQuantities(current => current.map((quantity, i) => i === index ? Number(event.target.value) : quantity))} /><span>{t(`units.${good.unit}`, { defaultValue: good.unit })}</span></span></label>
          {canMultiply && count > 1 && <span className="cargo-distribution">{t("cargo.eachAndRemaining", { each: number(each), remaining: number(rest) })}</span>}
        </div>;
      })}</div>}
      {creating && unitOptions.kind !== "ctu" && !destination.startsWith("reuse:") && canManageTemplates && <label className="cargo-checkbox"><input type="checkbox" checked={saveModel} onChange={event => setSaveModel(event.target.checked)} />{t("cargo.saveModel")}</label>}
      {error && <p role="alert" className="cargo-error">{error}</p>}
      <div className="cargo-dialog-actions"><button type="button" className="cargo-button" onClick={onClose} disabled={busy}>{t("cargo.cancel")}</button><button type="submit" disabled={!destination || busy} className="cargo-button cargo-primary">{t(busy ? "cargo.saving" : "cargo.apply")}</button></div>
    </fieldset></form>
  </EquipmentDialog>;
}
