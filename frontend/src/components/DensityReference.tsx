import { useTranslation } from "react-i18next";
import type { DensityReferenceData } from "../api/client";

/** The source describes a particular state of the goods, not every shipment. */
export default function DensityReference({ value }: { value: DensityReferenceData }) {
  const { t, i18n } = useTranslation();
  const format = (number: number) => number.toLocaleString(i18n.language, { maximumFractionDigits: 6 });
  const minimum = value.density_min_kg_m3;
  const maximum = value.density_max_kg_m3;
  return <div className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
    <p>{t(`densities.kinds.${value.kind}`)}</p>
    {value.condition_key && <p>{t(`densities.conditions.${value.condition_key}`)}</p>}
    {value.temperature_c != null && <p>{t("densities.temperature")}: {format(value.temperature_c)} °C</p>}
    {value.pressure_kpa != null && <p>{t("densities.pressure")}: {format(value.pressure_kpa)} kPa</p>}
    {value.method && <p>{t("densities.method")}: {value.method}</p>}
    {value.expanded_uncertainty_kg_m3 != null && <p>{t("densities.uncertainty")}: ±{format(value.expanded_uncertainty_kg_m3)} kg/m³</p>}
    {value.manufacturer && <p>{t("densities.manufacturer")}: {value.manufacturer}</p>}
    {value.original_value != null && value.original_unit && <p>{t("densities.originalValue")}: {format(value.original_value)} {value.original_unit}</p>}
    {minimum != null && maximum != null && minimum !== maximum && <p>{t("densities.range")}: {format(minimum)}–{format(maximum)} kg/m³</p>}
    {value.record_count != null && <p>{t("densities.records", { count: value.record_count })}</p>}
    {value.source_url && /^https:\/\//.test(value.source_url) && <a className="inline-block text-brand-700 underline underline-offset-4 dark:text-brand-300" href={value.source_url} target="_blank" rel="noreferrer">{value.source_name}</a>}
  </div>;
}
