import { useState } from "react";
import { useTranslation } from "react-i18next";
import { EquipmentItem, TransportConfiguration } from "../api/client";
import NumberInput from "./NumberInput";
import ContainerTemplatePicker from "./ContainerTemplatePicker";
import EquipmentInspections from "./EquipmentInspections";
import { containerUses, facilities } from "../utils/inspections";

const fieldClass = "min-h-[44px] w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950";
export default function EquipmentForm({ initial, onSave, onClose, busy }: {
  initial: EquipmentItem; onSave: (item: EquipmentItem) => Promise<void>; onClose: () => void; busy: boolean;
}) {
  const { t } = useTranslation();
  const [form, setForm] = useState<EquipmentItem>(() => structuredClone(initial));
  const patch = (values: Partial<EquipmentItem>) => setForm(previous => ({ ...previous, ...values }));
  const text = (key: keyof EquipmentItem, label = key as string, options: { required?: boolean; date?: boolean; disabled?: boolean } = {}) => <label className="equipment-field" key={key}>{t(`assets.${label}`)}<input className={fieldClass} required={options.required} disabled={options.disabled} type={options.date ? "date" : "text"} value={String(form[key] ?? "")} onChange={event => patch({ [key]: options.date ? event.target.value || null : event.target.value })} /></label>;
  const number = (key: keyof EquipmentItem, label = key as string, required = false) => <label className="equipment-field" key={key}>{t(`assets.${label}`)}<NumberInput className={fieldClass} min="0.001" step="any" required={required} value={form[key] as number ?? ""} onChange={event => patch({ [key]: event.target.value ? Number(event.target.value) : null })} /></label>;
  const select = (key: keyof EquipmentItem, options: string[]) => <label className="equipment-field" key={key}>{t(`assets.${key}`)}<select className={fieldClass} value={String(form[key] ?? options[0])} onChange={event => patch({ [key]: event.target.value })}>{options.map(value => <option value={value} key={value}>{t(`assets.${key}Values.${value || "unknown"}`)}</option>)}</select></label>;
  const area = (key: "notes" | "accessories" | "transport_instructions") => <label className="equipment-field md:col-span-2">{t(`assets.${key}`)}<textarea className={fieldClass} rows={3} value={form[key] ?? ""} onChange={event => patch({ [key]: event.target.value })} /></label>;
  const config = (index: number, values: Partial<TransportConfiguration>) => patch({ configurations: (form.configurations ?? []).map((item, i) => i === index ? { ...item, ...values } : item) });
  return <form onInvalidCapture={event => { const row = (event.target as HTMLElement).closest("details"); if (row) row.open = true; }} onSubmit={event => { event.preventDefault(); void onSave(form); }} className="space-y-6">
    <fieldset disabled={busy} className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        {select("kind", ["vehicle", "machine", "container", "other"])}{text("asset_code")}
        {text("specifications", "name", { required: true })}{text("brand")}{text("model_name")}
        {(form.kind === "vehicle" || form.kind === "machine") && <>{text("registration")}{text("serial_number")}{select("propulsion", ["", "diesel", "petrol", "electric", "lpg", "hybrid", "other"])}</>}
        {form.kind === "container" && <>{text("container_number")}{text("container_type")}{select("container_use", containerUses)}</>}
      </div>
      {form.kind === "container" && <><ContainerTemplatePicker item={form} onApply={patch} />
        <div><h4 className="mb-2 font-semibold">{t("assets.facilities")}</h4><div className="flex flex-wrap gap-4">{facilities.map(value => <label key={value} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={(form.facilities ?? []).includes(value)} onChange={event => patch({ facilities: event.target.checked ? [...(form.facilities ?? []), value] : form.facilities?.filter(key => key !== value) })} />{t(`assets.facilityValues.${value}`)}</label>)}</div></div>
      </>}
      <section><h4 className="font-semibold">{t("assets.transport")}</h4><p className="mb-4 text-sm text-slate-500 dark:text-slate-400">{t("assets.transportHint")}</p>
        <div className="grid gap-4 md:grid-cols-2">{number("length_cm")}{number("width_cm")}{number("height_cm")}{number("weight_kg", form.kind === "container" ? "tare_kg" : "weight_kg", true)}
          {form.kind === "other" && number("wall_thickness_mm")}
          {form.kind === "container" && <>{number("inner_length_cm")}{number("inner_width_cm")}{number("inner_height_cm")}{number("max_payload_kg")}{number("max_gross_kg")}</>}
          {area("transport_instructions")}{area("accessories")}
        </div>
      </section>
      <section><h4 className="mb-3 font-semibold">{t("assets.configurations")}</h4>
        {(form.configurations ?? []).map((item, index) => <div key={index} className="mb-3 grid gap-3 rounded-xl border border-slate-200 p-4 dark:border-slate-700 md:grid-cols-2">
          <label className="equipment-field">{t("assets.configurationName")}<input className={fieldClass} required value={item.name} onChange={event => config(index, { name: event.target.value })} /></label>
          {(["length_cm", "width_cm", "height_cm", "weight_kg"] as const).map(key => <label className="equipment-field" key={key}>{t(`assets.${key}`)}<NumberInput className={fieldClass} required={key === "weight_kg"} min="0.001" step="any" value={item[key] ?? ""} onChange={event => config(index, { [key]: event.target.value ? Number(event.target.value) : null })} /></label>)}
          <label className="equipment-field">{t("assets.transport_instructions")}<textarea className={fieldClass} value={item.instructions ?? ""} onChange={event => config(index, { instructions: event.target.value })} /></label>
          <button type="button" className="action-secondary justify-self-start" onClick={() => patch({ configurations: form.configurations?.filter((_, i) => i !== index) })}>{t("assets.removeConfiguration")}</button>
        </div>)}
        <button type="button" className="action-secondary" disabled={(form.configurations?.length ?? 0) >= 20} onClick={() => patch({ configurations: [...(form.configurations ?? []), { name: "", weight_kg: form.weight_kg, length_cm: form.length_cm, width_cm: form.width_cm, height_cm: form.height_cm }] })}>{t("assets.addConfiguration")}</button>
      </section>
      <EquipmentInspections items={form.inspections} onChange={inspections => patch({ inspections, inspection_due: null })} />
      <section><h4 className="mb-3 font-semibold">{t("assets.management")}</h4><div className="grid gap-4 md:grid-cols-2">
        {text("current_location", "current_location", { disabled: !!initial.id })}{select("availability", ["unknown", "available", "planned", "in_transit", "maintenance"])}
        {!!initial.id && <p className="text-xs text-slate-500 md:col-span-2">{t("assets.moveHint")}</p>}
        {select("condition", ["unknown", "good", "damaged", "unserviceable"])}{text("planned_reference")}{text("planned_date", "planned_date", { date: true })}
        <label className="equipment-field">{t("materieel.aliases")}<input className={fieldClass} value={(form.aliases ?? []).join(", ")} onChange={event => patch({ aliases: event.target.value.split(",").map(value => value.trim()) })} /></label>
        {area("notes")}
      </div></section>
      <div className="flex flex-wrap gap-2"><button type="submit" className="action-primary">{t("materieel.save")}</button><button type="button" className="action-secondary" onClick={onClose}>{t("materieel.cancel")}</button></div>
    </fieldset>
  </form>;
}
