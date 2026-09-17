import { useTranslation } from "react-i18next";
import type { LineItem } from "../api/client";
import type { DraftLine } from "./ReviewLinesPanel";

/** Choices belong to this shipment; changing one never updates the library. */
export default function EquipmentLineFields({ line, lines, result, onChange, cargoManaged = false }: {
  cargoManaged?: boolean;
  line: DraftLine; lines: DraftLine[]; result: LineItem | null; onChange: (patch: Partial<DraftLine>) => void;
}) {
  const { t, i18n } = useTranslation();
  const equipment = line.equipment;
  const containers = lines.filter(candidate => candidate.id !== line.id && candidate.equipment?.kind === "container" && candidate.equipment_role === "container");
  if (!equipment && (cargoManaged || (!containers.length && line.container_line_id == null))) return null;
  const input = "min-h-[44px] rounded-lg border border-slate-200 bg-transparent px-3 py-2 text-sm dark:border-slate-700";
  const number = new Intl.NumberFormat(i18n.language, { maximumFractionDigits: 2 });
  return <div className="equipment-line">
    {equipment && <>
      <span className="text-xs text-slate-500 dark:text-slate-400">{t("assets.selected", { name: equipment.asset_code || equipment.container_number || equipment.registration || equipment.specifications })}</span>
      {!!equipment.configurations?.length && <label>{t("assets.configuration")}<select className={input} value={equipment.configuration || ""} onChange={event => {
        const configuration = equipment.configurations?.find(item => item.name === event.target.value);
        onChange({ equipment: { ...equipment, configuration: configuration?.name ?? "" },
          length_cm: (configuration ?? equipment).length_cm ?? undefined,
          width_cm: (configuration ?? equipment).width_cm ?? undefined,
          height_cm: (configuration ?? equipment).height_cm ?? undefined,
          weight_each_kg: (configuration ?? equipment).weight_kg, weight_total_kg: undefined });
      }}><option value="">{t("assets.standardConfiguration")}</option>{equipment.configurations.map(item => <option key={item.name}>{item.name}</option>)}</select></label>}
      {!cargoManaged && equipment.kind === "container" && <label>{t("assets.useAs")}<select className={input} value={line.equipment_role ?? "cargo"} onChange={event => onChange({ equipment_role: event.target.value as "cargo" | "container", container_line_id: undefined })}>
        <option value="cargo">{t("assets.emptyCargo")}</option><option value="container">{t("assets.loadedContainer")}</option>
      </select></label>}
      {(equipment.accessories || equipment.transport_instructions || equipment.configuration) && <details className="text-sm"><summary>{t("assets.transportInstructions")}</summary>
        <p className="whitespace-pre-wrap">{equipment.configurations?.find(item => item.name === equipment.configuration)?.instructions || equipment.transport_instructions}</p>
        {equipment.accessories && <p>{equipment.accessories}</p>}
      </details>}
    </>}
    {!cargoManaged && line.equipment_role !== "container" && (containers.length > 0 || line.container_line_id != null) && <label>{t("assets.inContainer")}<select className={input} value={line.container_line_id ?? ""} onChange={event => onChange({ container_line_id: event.target.value ? Number(event.target.value) : undefined })}>
      <option value="">{t("assets.looseCargo")}</option>
      {line.container_line_id != null && !containers.some(item => item.id === line.container_line_id) && <option value={line.container_line_id}>{t("assets.missingContainer")}</option>}
      {containers.map(item => <option key={item.id} value={item.id}>{item.equipment?.container_number || item.equipment?.asset_code || item.description}</option>)}
    </select></label>}
    {result?.container_load && <p className="text-sm">{t("assets.loadSummary", {
      tare: number.format(result.container_load.tare_kg ?? 0), cargo: number.format(result.container_load.cargo_kg),
      gross: result.container_load.complete ? number.format(result.container_load.gross_kg ?? 0) : "—",
    })}</p>}
  </div>;
}
