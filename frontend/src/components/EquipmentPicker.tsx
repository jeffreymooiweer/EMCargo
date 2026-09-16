import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, EquipmentItem, EquipmentSnapshot } from "../api/client";
import { equipmentSnapshot } from "../utils/equipment";
import EquipmentDialog from "./EquipmentDialog";

export default function EquipmentPicker({ onPick, onClose }: { onPick: (item: EquipmentSnapshot) => void; onClose: () => void }) {
  const { t, i18n } = useTranslation();
  const [items, setItems] = useState<EquipmentItem[]>([]);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => { let alive = true; api.listEquipment().then(data => { if (alive) setItems(data); }).catch(e => { if (alive) setError(String(e)); }).finally(() => { if (alive) setLoading(false); }); return () => { alive = false; }; }, []);
  const filtered = items.filter(item => item.active !== false && [item.specifications, item.asset_code, item.container_number, item.registration, item.serial_number, item.current_location, item.brand, item.model_name].join(" ").toLowerCase().includes(search.toLowerCase().trim()));
  return <EquipmentDialog title={t("assets.choose")} onClose={onClose}>
    <p className="mb-4 text-sm text-slate-500">{t("assets.chooseHint")}</p>
    <input autoFocus type="search" className="mb-4 min-h-[44px] w-full rounded-lg border border-slate-300 bg-transparent px-3 dark:border-slate-600" aria-label={t("assets.search")} placeholder={t("assets.search")} value={search} onChange={event => setSearch(event.target.value)} />
    {error && <p role="alert">{error}</p>}
    {loading ? <p role="status">{t("assets.loading")}</p> : !filtered.length ? <p>{t("assets.noResults")}</p> : <ul className="space-y-2">{filtered.map(item => <li key={item.id}><button className="flex w-full items-center gap-3 rounded-xl border border-slate-200 p-3 text-left hover:border-brand-500 dark:border-slate-700" onClick={() => onPick(equipmentSnapshot(item))}>
      {item.photo_url && <img className="h-14 w-14 rounded-lg object-cover" alt="" src={item.photo_url} />}
      <span className="min-w-0"><strong className="block break-words">{item.specifications}</strong><span className="block text-xs text-slate-500 dark:text-slate-400">{[item.asset_code, item.container_number || item.registration, item.current_location].filter(Boolean).join(" · ")}</span><span className="block text-sm">{[item.length_cm ?? "—", item.width_cm ?? "—", item.height_cm ?? "—"].join(" × ")} cm · {new Intl.NumberFormat(i18n.language).format(item.weight_kg)} kg · {t(`assets.availabilityValues.${item.availability || "unknown"}`)}</span></span>
    </button></li>)}</ul>}
  </EquipmentDialog>;
}
