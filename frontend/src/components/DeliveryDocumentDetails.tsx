import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type DocumentRegistry } from "../api/client";
import { deliveries, inputOf, type Delivery, type Leg } from "../api/deliveries";
import DocumentFieldsStep from "./DocumentFieldsStep";

const planningFields = ["carrier_name", "loading_point", "place_of_receipt", "discharge_point", "place_of_delivery", "vehicle_registration", "loading_date", "booking_number"];

/** Document inputs share the leg revision, so any edit invalidates release. */
export default function DeliveryDocumentDetails({ record, part, shipmentId, documentKey, allocationIds = [], busy, accept, run, onDirtyChange }: {
  record: Delivery; part: Leg; shipmentId: string; documentKey: string; allocationIds?: string[]; busy: boolean;
  onDirtyChange: (dirty: boolean) => void;
  accept: (record: Delivery) => void; run: (action: () => Promise<void>) => Promise<void>;
}) {
  const { t } = useTranslation();
  const [registry, setRegistry] = useState<DocumentRegistry | null>(null);
  const [failure, setFailure] = useState("");
  const derived: Record<string, string> = {};
  const routing = record.sources[shipmentId]?.export?.routing;
  const allocation = record.allocations.find(a => allocationIds.includes(a.id));
  const distribution = routing?.distributions.find(d => d.id === allocation?.source_distribution_id);
  if (distribution) for (const [kind, prefix] of [["pickup", "consignor"], ["delivery", "consignee"]] as const) {
    const sourceKind = record.followup?.kind === "return" ? (kind === "pickup" ? "delivery" : "pickup") : kind;
    const point = routing?.locations.find(p => p.id === distribution[`${sourceKind}_id`]);
    if (point) for (const key of ["name", "address", "country", "contact"] as const) derived[`${prefix}_${key}`] = point.party[key];
  }
  const valuesKey = distribution ? `route:${JSON.stringify([shipmentId, distribution.pickup_id, distribution.delivery_id])}` : shipmentId;
  const original = { ...record.sources[shipmentId]?.export?.consignment, ...part.document_values?.[valuesKey], ...derived };
  const [values, setValues] = useState<Record<string, string>>(original);
  useEffect(() => { setValues(original); }, [record.version, part.id, shipmentId, allocationIds.join(",")]);
  useEffect(() => {
    let active = true;
    api.documentsRegistry().then(value => { if (active) setRegistry(value); }).catch(error => { if (active) setFailure(String(error)); });
    return () => { active = false; };
  }, []);
  const definition = registry?.documents.find(doc => doc.key === documentKey);
  const editable = record.can_plan && part.status === "draft";
  const dirty = editable && JSON.stringify(values) !== JSON.stringify(original);
  useEffect(() => { onDirtyChange(dirty); }, [dirty, onDirtyChange]);
  useEffect(() => () => onDirtyChange(false), [onDirtyChange]);
  return <details className="delivery-document-details">
    <summary>{t("deliveries.documentDetails")}</summary>
    <p>{t(editable ? "deliveries.documentDetailsHint" : "deliveries.documentDetailsLocked")}</p>
    {failure && <p role="alert">{failure}</p>}
    {registry && definition && <fieldset disabled={busy || !editable}>
      <DocumentFieldsStep registry={registry} documents={[definition]} values={values} onChange={setValues}
        modality={part.mode} excludedFields={routing ? [...planningFields, ...Object.keys(derived)] : planningFields} hideActions />
      {editable && <button type="button" className="action-primary" disabled={busy || JSON.stringify(values) === JSON.stringify(original)} onClick={() => run(async () => {
        const input = inputOf(record);
        input.legs = input.legs.map(leg => leg.id === part.id ? { ...leg, document_values: { ...leg.document_values, [valuesKey]: values } } : leg);
        accept(await deliveries.save(record.id, input));
      })}>{t("deliveries.save")}</button>}
    </fieldset>}
  </details>;
}
