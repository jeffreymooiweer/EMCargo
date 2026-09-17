import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ContainerTemplate, EquipmentItem, TransportConfiguration } from "../api/client";
import NumberInput from "./NumberInput";
import ContainerTemplatePicker from "./ContainerTemplatePicker";
import EquipmentInspections, { InspectionSummary } from "./EquipmentInspections";
import { containerUses, facilities } from "../utils/inspections";
import { CloseIcon } from "./icons";

export default function EquipmentForm({ initial, onSave, busy, formId }: {
  initial: EquipmentItem; onSave: (item: EquipmentItem) => Promise<void>; busy: boolean; formId: string;
}) {
  const { t, i18n } = useTranslation();
  const [form, setForm] = useState<EquipmentItem>(() => structuredClone(initial));
  const [template, setTemplate] = useState<ContainerTemplate>();
  const [editDimensions, setEditDimensions] = useState(false);
  const [aliasDraft, setAliasDraft] = useState("");
  const aliasesWithDraft = (aliases = form.aliases) => [...new Set([...(aliases ?? []), ...aliasDraft.split(/[,\n]/)].map(value => value.trim()).filter(Boolean))];
  const addAlias = () => { setForm(previous => ({ ...previous, aliases: aliasesWithDraft(previous.aliases) })); setAliasDraft(""); };
  const patch = (values: Partial<EquipmentItem>) => setForm(previous => ({ ...previous, ...values }));
  const isContainer = form.kind === "container";
  const dimensionsKnown = [form.length_cm, form.width_cm, form.height_cm, form.weight_kg].every(value => value != null && value > 0);
  const compactDimensions = isContainer && !!form.container_template_id && dimensionsKnown && !editDimensions;
  const text = (key: keyof EquipmentItem, label = key as string, options: { required?: boolean; date?: boolean; disabled?: boolean } = {}) => <label className="equipment-field" key={key}>{t(`assets.${label}`)}<input className="equipment-input" required={options.required} disabled={options.disabled} type={options.date ? "date" : "text"} value={String(form[key] ?? "")} onChange={event => patch({ [key]: options.date ? event.target.value || null : event.target.value })} /></label>;
  const number = (key: keyof EquipmentItem, label = key as string, required = false) => <label className="equipment-field" key={key}>{t(`assets.${label}`)}<NumberInput className="equipment-input" min="0.001" step="any" required={required} value={(form[key] as number) || ""} onChange={event => patch({ [key]: event.target.value ? Number(event.target.value) : null })} /></label>;
  const select = (key: keyof EquipmentItem, options: string[]) => <label className="equipment-field">{t(`assets.${key}`)}<select className="equipment-input" value={String(form[key] ?? options[0])} onChange={event => patch({ [key]: event.target.value })}>{options.map(value => <option value={value} key={value}>{t(`assets.${key}Values.${value || "unknown"}`)}</option>)}</select></label>;
  const area = (key: "notes" | "accessories" | "transport_instructions") => <label className="equipment-field sm:col-span-2">{t(`assets.${key}`)}<textarea className="equipment-input" rows={2} value={form[key] ?? ""} onChange={event => patch({ [key]: event.target.value })} /></label>;
  const config = (index: number, values: Partial<TransportConfiguration>) => patch({ configurations: (form.configurations ?? []).map((item, i) => i === index ? { ...item, ...values } : item) });
  const format = (value: number | null | undefined) => value == null ? "—" : value.toLocaleString(i18n.language);
  return <form id={formId} onInvalidCapture={event => {
    // Native validation must be able to focus a field inside any closed section.
    let section = (event.target as HTMLElement).closest("details");
    while (section) { section.open = true; section = section.parentElement?.closest("details") ?? null; }
  }} onSubmit={event => { event.preventDefault(); void onSave(aliasDraft.trim() ? { ...form, aliases: aliasesWithDraft() } : form); }}>
    <fieldset disabled={busy} className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2">
        {select("kind", ["vehicle", "machine", "container", "other"])}
        {isContainer ? <ContainerTemplatePicker item={form} onTemplate={setTemplate} onApply={values => { patch(values); setEditDimensions(false); }} /> : text("specifications", "name", { required: true })}
        {isContainer ? <>{text("specifications", "name", { required: true })}{text("container_number")}</> : <>{text("asset_code")}{form.kind === "vehicle" ? text("registration") : text("model_name")}</>}
      </div>
      <section aria-label={t("assets.transport")}>
        {compactDimensions ? <div className="equipment-measurements">
          <div><span>{t("assets.dimensions")}</span><strong>{[form.length_cm, form.width_cm, form.height_cm].map(format).join(" × ")} cm</strong><span>{t("equipmentSimple.tare")} · {format(form.weight_kg)} kg</span></div>
          <button type="button" className="equipment-text-button" onClick={() => setEditDimensions(true)}>{t("equipmentSimple.adjust")}</button>
        </div> : <><h4 className="mb-3 text-sm font-semibold">{t("equipmentSimple.dimensionsWeight")}</h4><div className="grid grid-cols-2 gap-3">
          {number("length_cm")}{number("width_cm")}{number("height_cm")}{number("weight_kg", isContainer ? "tare_kg" : "weight_kg", true)}
        </div></>}
      </section>
      <div className="equipment-sections">
        <details className="equipment-section">
          <summary>{t("equipmentSimple.moreDetails")}</summary>
          <div className="equipment-section-body space-y-5">
            <div className="grid gap-3 sm:grid-cols-2">
              {isContainer && text("asset_code")}{text("brand")}
              {form.kind === "vehicle" && text("model_name")}
              {isContainer ? <>{text("container_type")}{select("container_use", containerUses)}</> : <>{text("serial_number")}{form.kind === "machine" && text("registration")}{select("propulsion", ["", "diesel", "petrol", "electric", "lpg", "hybrid", "other"])}</>}
              {initial.id ? <div className="equipment-field"><span>{t("assets.current_location")}</span><span>{form.current_location || t("assets.locationUnknown")}</span></div> : text("current_location")}{select("availability", ["unknown", "available", "planned", "in_transit", "maintenance"])}
              {select("condition", ["unknown", "good", "damaged", "unserviceable"])}
            </div>
            {isContainer && <section><h4 className="mb-3 text-sm font-semibold">{t("assets.facilities")}</h4><div className="grid grid-cols-2 gap-2">{facilities.map(value => <label key={value} className="equipment-check"><input type="checkbox" checked={(form.facilities ?? []).includes(value)} onChange={event => patch({ facilities: event.target.checked ? [...(form.facilities ?? []), value] : (form.facilities ?? []).filter(key => key !== value) })} />{t(`assets.facilityValues.${value}`)}</label>)}</div></section>}
            <div className="grid gap-3 sm:grid-cols-2">
              {isContainer && <>{number("inner_length_cm")}{number("inner_width_cm")}{number("inner_height_cm")}{number("max_payload_kg")}{number("max_gross_kg")}</>}
              {form.kind === "other" && number("wall_thickness_mm")}
              {area("transport_instructions")}{area("accessories")}{area("notes")}
              {text("planned_reference")}{text("planned_date", "planned_date", { date: true })}
              <div className="sm:col-span-2 space-y-2">
                <div className="flex items-end gap-2"><label className="equipment-field min-w-0 flex-1">{t("materieel.aliases")}<input className="equipment-input" value={aliasDraft} onChange={event => setAliasDraft(event.target.value)} onKeyDown={event => { if (event.key === "Enter") { event.preventDefault(); addAlias(); } }} /></label><button className="action-secondary" type="button" disabled={!aliasDraft.trim()} onClick={addAlias}>{t("articles.create")}</button></div>
                {!!form.aliases?.filter(Boolean).length && <ul className="flex flex-wrap gap-2">{form.aliases.map((alias, index) => alias ? <li key={`${index}-${alias}`}><button type="button" className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-slate-200 px-3 text-sm dark:border-slate-700" aria-label={`${t("materieel.delete")}: ${alias}`} onClick={() => patch({ aliases: form.aliases?.filter((_, current) => current !== index) })}><span>{alias}</span><CloseIcon className="h-4 w-4" /></button></li> : null)}</ul>}
              </div>
            </div>
            <details className="equipment-section">
              <summary>{t("assets.configurations")}{!!form.configurations?.length && <span className="equipment-count">{form.configurations.length}</span>}</summary>
              <div className="equipment-section-body space-y-3">
                {(form.configurations ?? []).map((item, index) => <div key={index} className="grid gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700 sm:grid-cols-2">
                  <label className="equipment-field sm:col-span-2">{t("assets.configurationName")}<input className="equipment-input" required value={item.name} onChange={event => config(index, { name: event.target.value })} /></label>
                  {(["length_cm", "width_cm", "height_cm", "weight_kg"] as const).map(key => <label className="equipment-field" key={key}>{t(`assets.${key}`)}<NumberInput className="equipment-input" required={key === "weight_kg"} min="0.001" step="any" value={item[key] ?? ""} onChange={event => config(index, { [key]: event.target.value ? Number(event.target.value) : null })} /></label>)}
                  <label className="equipment-field sm:col-span-2">{t("assets.transport_instructions")}<textarea className="equipment-input" value={item.instructions ?? ""} onChange={event => config(index, { instructions: event.target.value })} /></label>
                  <button type="button" className="equipment-text-button justify-self-start" onClick={() => patch({ configurations: form.configurations?.filter((_, i) => i !== index) })}>{t("assets.removeConfiguration")}</button>
                </div>)}
                <button type="button" className="action-secondary" disabled={(form.configurations?.length ?? 0) >= 20} onClick={() => patch({ configurations: [...(form.configurations ?? []), { name: "", weight_kg: form.weight_kg, length_cm: form.length_cm, width_cm: form.width_cm, height_cm: form.height_cm }] })}>{t("assets.addConfiguration")}</button>
              </div>
            </details>
            {isContainer && template && <div className="text-xs leading-relaxed text-slate-500 dark:text-slate-400"><p>{t(`containerCatalog.basis.${template.basis}`)}</p><a className="underline" href={template.source_url} target="_blank" rel="noopener noreferrer">{t("containerCatalog.source", { supplier: template.supplier })}</a> · {t("containerCatalog.checked", { date: template.checked_on })}</div>}
          </div>
        </details>
        <details className="equipment-section">
          <summary>{t("inspections.filter")}<InspectionSummary items={form.inspections} /></summary>
          <div className="equipment-section-body"><EquipmentInspections items={form.inspections} onChange={inspections => patch({ inspections, inspection_due: null })} /></div>
        </details>
      </div>
    </fieldset>
  </form>;
}
