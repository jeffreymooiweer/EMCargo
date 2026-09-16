import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, ContainerTemplate, EquipmentItem } from "../api/client";
import { templatePatch } from "../utils/inspections";

export default function ContainerTemplatePicker({ item, onApply }: {
  item: EquipmentItem; onApply: (patch: Partial<EquipmentItem>) => void;
}) {
  const { t, i18n } = useTranslation();
  const [templates, setTemplates] = useState<ContainerTemplate[]>([]);
  const [chosen, setChosen] = useState(item.container_template_id ?? "");
  const [query, setQuery] = useState("");
  const [family, setFamily] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => { let live = true; api.containerTemplates().then(data => { if (live) setTemplates(data); })
    .catch(e => { if (live) setError(String(e)); }).finally(() => { if (live) setLoading(false); }); return () => { live = false; }; }, []);
  const language = i18n.language.split("-")[0];
  const name = (model: ContainerTemplate) => model.language_labels[language] || model.name;
  const filtered = templates.filter(model => (!family || model.family === family) &&
    `${name(model)} ${model.name} ${model.size_ft}ft ${model.supplier}`.toLowerCase().includes(query.toLowerCase().trim()));
  const selected = templates.find(model => model.id === chosen);
  const cls = "min-h-[44px] min-w-0 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950";
  return <section className="rounded-xl border border-blue-200 bg-blue-50/50 p-4 dark:border-blue-900 dark:bg-blue-950/20">
    <h4 className="font-semibold">{t("containerCatalog.title")}</h4>
    <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{t("containerCatalog.hint")}</p>
    {error ? <p role="alert" className="mt-3 text-red-600">{error}</p> : loading ? <p role="status">{t("assets.loading")}</p> : <>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <label className="equipment-field">{t("containerCatalog.search")}<input type="search" className={cls} value={query} onChange={e => setQuery(e.target.value)} /></label>
        <label className="equipment-field">{t("containerCatalog.family")}<select className={cls} value={family} onChange={e => setFamily(e.target.value)}><option value="">{t("assets.filters.all")}</option>{[...new Set(templates.map(model => model.family))].sort().map(key => <option value={key} key={key}>{t(`containerCatalog.families.${key}`)}</option>)}</select></label>
        <label className="equipment-field md:col-span-2">{t("containerCatalog.model")}<select className={cls} value={chosen} onChange={e => setChosen(e.target.value)}><option value="">{t("containerCatalog.select")}</option>
          {selected && !filtered.some(model => model.id === selected.id) && <option value={selected.id}>{name(selected)} — {selected.supplier}</option>}
          {filtered.map(model => <option key={model.id} value={model.id}>{name(model)} — {model.supplier}</option>)}
        </select></label>
      </div>
      <p className="mt-2 text-xs text-slate-500">{t("containerCatalog.count", { count: filtered.length })}</p>
      {selected && <div className="mt-3 space-y-3 text-sm">
        <p className="font-semibold">{[selected.length_cm, selected.width_cm, selected.height_cm].map(value => value.toLocaleString(i18n.language)).join(" × ")} cm · {selected.weight_kg ? `${selected.weight_kg.toLocaleString(i18n.language)} kg` : t("containerCatalog.weightUnknown")}</p>
        <p>{t(`containerCatalog.basis.${selected.basis}`)}</p>
        <p><a className="underline" href={selected.source_url} target="_blank" rel="noopener noreferrer">{t("containerCatalog.source", { supplier: selected.supplier })}</a> · {t("containerCatalog.checked", { date: selected.checked_on })}</p>
        <button type="button" className="action-secondary" onClick={() => onApply(templatePatch(selected, item, i18n.language))}>{t("containerCatalog.apply")}</button>
        <p className="text-xs text-slate-500">{t("containerCatalog.applyHint")}</p>
      </div>}
    </>}
  </section>;
}
