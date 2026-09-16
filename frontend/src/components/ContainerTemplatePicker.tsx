import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, ContainerTemplate, EquipmentItem } from "../api/client";
import { templatePatch } from "../utils/inspections";

/** A model is a single choice. Loading options never reapplies saved dimensions. */
export default function ContainerTemplatePicker({ item, onApply, onTemplate }: {
  item: EquipmentItem;
  onApply: (patch: Partial<EquipmentItem>) => void;
  onTemplate: (template: ContainerTemplate | undefined) => void;
}) {
  const { t, i18n } = useTranslation();
  const [templates, setTemplates] = useState<ContainerTemplate[]>([]);
  const [custom, setCustom] = useState(!item.container_template_id && !!(item.container_type || item.id));
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let live = true;
    setLoading(true); setError(false);
    api.containerTemplates().then(data => { if (live) setTemplates(data); })
      .catch(() => { if (live) setError(true); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [attempt]);
  const selected = templates.find(model => model.id === item.container_template_id);
  useEffect(() => { onTemplate(selected); }, [selected, onTemplate]);
  const name = (model: ContainerTemplate) => model.language_labels[i18n.language.split("-")[0]] || model.name;
  return <div className="min-w-0">
    <label className="equipment-field">{t("assets.model_name")}
      <select className="equipment-input" value={item.container_template_id || (custom ? "custom" : "")} onChange={event => {
        const model = templates.find(entry => entry.id === event.target.value);
        if (model) {
          setCustom(false);
          onApply(templatePatch(model, item, i18n.language, selected));
        } else if (event.target.value === "custom") {
          setCustom(true);
          onApply({ container_template_id: "" });
        }
      }}>
        <option value="" disabled>{t(loading ? "equipmentSimple.modelsLoading" : "containerCatalog.select")}</option>
        {item.container_template_id && !selected && <option value={item.container_template_id}>{item.container_type || item.model_name || item.specifications}</option>}
        {[...new Set(templates.map(model => model.size_ft))].sort((a, b) => a - b).map(size => <optgroup key={size} label={`${size} ft`}>
          {templates.filter(model => model.size_ft === size).map(model => <option key={model.id} value={model.id}>{name(model)}</option>)}
        </optgroup>)}
        <option value="custom">{t("equipmentSimple.customModel")}</option>
      </select>
    </label>
    {error && <p role="status" className="mt-2 text-xs text-slate-500">{t("equipmentSimple.modelsUnavailable")} <button type="button" className="underline" onClick={() => setAttempt(value => value + 1)}>{t("assets.reload")}</button></p>}
  </div>;
}
