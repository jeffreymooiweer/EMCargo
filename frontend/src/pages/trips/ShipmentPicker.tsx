import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type ShipmentSummary, type TripConsignment } from "../../api/client";
import { CheckIcon, PlusIcon, SearchIcon } from "../../components/icons";

export default function ShipmentPicker({ selected, busyIds, onAdd, onClose }: {
  selected: TripConsignment[]; busyIds: Set<number>; onAdd: (shipment: ShipmentSummary) => void; onClose: () => void;
}) {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [rows, setRows] = useState<ShipmentSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  const search = useRef<HTMLInputElement>(null);
  useEffect(() => { search.current?.focus(); }, []);
  useEffect(() => {
    let cancelled = false;
    setLoading(true); setFailed(false);
    const timer = setTimeout(() => {
      api.shipments({ q: query, page, per_page: 10 }).then(answer => {
        if (!cancelled) { setRows(answer.items); setTotal(answer.total); }
      }).catch(() => { if (!cancelled) setFailed(true); }).finally(() => { if (!cancelled) setLoading(false); });
    }, query ? 250 : 0);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [query, page, retry]);
  return <section className="trip-picker" aria-label={t("tripWorkspace.add")}>
    <div className="trip-picker-heading"><h3>{t("tripWorkspace.choose")}</h3><button className="trip-text-button" type="button" onClick={onClose}>{t("tripWorkspace.done")}</button></div>
    <div className="trip-search"><SearchIcon /><input ref={search} type="search" aria-label={t("groupage.searchHistory")} placeholder={t("groupage.searchHistory")} value={query} maxLength={120} onChange={event => { setQuery(event.target.value); setPage(1); }} /></div>
    {failed ? <div role="alert" className="trip-inline-error">{t("tripWorkspace.shipmentsFailed")}<button type="button" className="trip-text-button" onClick={() => setRetry(v => v + 1)}>{t("tripWorkspace.retry")}</button></div>
      : loading ? <p role="status" className="trip-muted trip-picker-message">{t("trips.loading")}</p>
      : !rows.length ? <p className="trip-muted trip-picker-message">{t("tripWorkspace.noShipments")}</p>
      : <ul className="trip-picker-list">{rows.map(shipment => {
        const added = selected.some(c => c.shipment_id === shipment.id);
        const busy = busyIds.has(shipment.id);
        return <li key={shipment.id}><button type="button" disabled={added || busy} onClick={() => onAdd(shipment)} aria-label={`${t(added ? "tripWorkspace.added" : "tripWorkspace.add")} ${shipment.reference || `#${shipment.id}`}`}>
          <span className={`trip-picker-check ${added ? "is-added" : ""}`}>{added ? <CheckIcon /> : <PlusIcon />}</span>
          <span className="trip-picker-copy"><strong>{shipment.reference || `#${shipment.id}`}</strong><span>{[shipment.consignor_name, shipment.consignee_name].filter(Boolean).join(" → ") || t(`modality.${shipment.modality || "preparation"}`)}</span></span>
          <span className="trip-picker-tag">{busy ? t("tripWorkspace.adding") : added ? t("tripWorkspace.added") : shipment.has_dangerous_goods ? "DG" : ""}</span>
        </button></li>;
      })}</ul>}
    {total > 10 && <div className="trip-pagination"><button type="button" disabled={page === 1 || loading} onClick={() => setPage(p => p - 1)}>{t("history.previous")}</button><span>{page} / {Math.ceil(total / 10)}</span><button type="button" disabled={page * 10 >= total || loading} onClick={() => setPage(p => p + 1)}>{t("history.next")}</button></div>}
  </section>;
}
