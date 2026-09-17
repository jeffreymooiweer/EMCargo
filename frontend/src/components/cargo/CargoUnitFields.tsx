import { useTranslation } from "react-i18next";
import type { CargoDimensions, CargoUnit, PackagingTemplate } from "../../api/cargo";
import NumberInput from "../NumberInput";

export const PACKAGING_CATEGORIES = ["box", "crate", "case", "bag", "big_bag", "drum", "jerrycan", "ibc", "bundle", "roll", "reel", "pallet", "roll_cage", "stillage", "mesh_box", "custom"];
export const blankTemplate = (): PackagingTemplate => ({ id: "", name: "", category: "box", reusable: false });
const blankDimensions = (): CargoDimensions => ({ length: null, width: null, height: null });

export default function CargoUnitFields({ value, onChange, unit = false }: {
  value: PackagingTemplate | CargoUnit; onChange: (value: PackagingTemplate | CargoUnit) => void; unit?: boolean;
}) {
  const { t } = useTranslation();
  const patch = (next: Partial<CargoUnit>) => onChange({ ...value, ...next });
  const numeric = (key: "tare_kg" | "max_payload_kg" | "max_gross_kg" | "max_stack_load_kg" | "measured_gross_kg") => <label key={key}>{t(`cargo.${key}`)}
    <NumberInput min={key === "max_payload_kg" || key === "max_gross_kg" ? "0.001" : "0"} step="any" value={(value as CargoUnit)[key] ?? ""} onChange={event => patch({ [key]: event.target.value === "" ? null : Number(event.target.value) })} />
  </label>;
  const dimensions = (key: "dimensions_mm" | "inner_dimensions_mm" | "loaded_dimensions_mm") => <fieldset className="cargo-dimensions"><legend>{t(`cargo.${key}`)}</legend><div>
    {(["length", "width", "height"] as const).map(axis => <label key={axis}>{t(`cargo.${axis}`)}<NumberInput min="0.001" step="any" value={(value as CargoUnit)[key]?.[axis] ?? ""}
      onChange={event => patch({ [key]: { ...blankDimensions(), ...(value as CargoUnit)[key], [axis]: event.target.value === "" ? null : Number(event.target.value) } })} /></label>)}
  </div></fieldset>;
  return <div className="cargo-fields">
    <div className="cargo-field-pair">
      <label>{t("cargo.name")}<input required maxLength={160} value={value.name} onChange={event => patch({ name: event.target.value })} /></label>
      {!(value as CargoUnit).kind || (value as CargoUnit).kind === "package" ? <label>{t("cargo.category")}<select value={value.category} onChange={event => patch({ category: event.target.value })}>
        {!PACKAGING_CATEGORIES.includes(value.category) && <option value={value.category}>{t(`cargo.categories.${value.category}`, { defaultValue: value.category })}</option>}
        {PACKAGING_CATEGORIES.map(category => <option key={category} value={category}>{t(`cargo.categories.${category}`)}</option>)}
      </select></label> : <label>{t("cargo.reference")}<input maxLength={120} value={(value as CargoUnit).external_reference ?? ""} onChange={event => patch({ external_reference: event.target.value })} /></label>}
    </div>
    <details className="cargo-details"><summary>{t("cargo.dimensionsAndWeight")}</summary>
      {dimensions("dimensions_mm")}{numeric("tare_kg")}
      {unit && <>{dimensions("loaded_dimensions_mm")}{numeric("measured_gross_kg")}</>}
      {dimensions("inner_dimensions_mm")}
    </details>
    <details className="cargo-details"><summary>{t("cargo.properties")}</summary>
      <div className="cargo-field-pair">{numeric("max_payload_kg")}{numeric("max_gross_kg")}{numeric("max_stack_load_kg")}</div>
      <div className="cargo-field-pair">{(["stackable", "keep_upright", "can_rotate"] as const).map(key => <label key={key}>{t(`cargo.${key}`)}<select value={value[key] == null ? "" : String(value[key])} onChange={event => patch({ [key]: event.target.value === "" ? null : event.target.value === "true" })}>
        <option value="">{t("cargo.unknown")}</option><option value="true">{t("cargo.yes")}</option><option value="false">{t("cargo.no")}</option>
      </select></label>)}</div>
      <label className="cargo-checkbox"><input type="checkbox" checked={!!value.reusable} onChange={event => patch({ reusable: event.target.checked })} />{t("cargo.reusable")}</label>
    </details>
  </div>;
}
