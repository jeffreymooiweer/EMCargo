import { localised, documentLanguage } from "../i18n/language";
import DocumentWarnings, { useDocumentValidation } from "../components/DocumentWarnings";
import { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { api, type DgReview, type ShipmentIn, type User, type DocumentRegistry } from "../api/client";
import { canUseDgsa } from "../permissions";
import { usePreferences } from "../settings/preferences";
import { useToast } from "../toast/ToastProvider";
import ConfirmDialog from "../toast/ConfirmDialog";
import { ArrowRightIcon, CheckIcon, RefreshIcon, ShieldIcon } from "../components/icons";
import DgCompliancePanel from "../components/DgCompliancePanel";
import CargoSummary from "../components/cargo/CargoSummary";
import { cargoGoods } from "../wizard/cargoState";

const when = (value: string, language: string) => new Date(value.endsWith("Z") ? value : `${value}Z`).toLocaleString(language, { dateStyle: "medium", timeStyle: "short" });

export default function DgReviewsPage({ user }: { user: User }) {
  const { id } = useParams();
  const { t, i18n } = useTranslation();
  const { publicSettings } = usePreferences();
  const toast = useToast();
  const navigate = useNavigate();
  const specialist = user.role === "dg_specialist";
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [rows, setRows] = useState<DgReview[]>([]);
  const [total, setTotal] = useState(0);
  const [detail, setDetail] = useState<(DgReview & { shipment: ShipmentIn }) | null>(null);
  const [loading, setLoading] = useState(true);
  const [failure, setFailure] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [forget, setForget] = useState(false);
  const [registry, setRegistry] = useState<DocumentRegistry | null>(null);
  const language = documentLanguage(i18n.language);
  const labelFor = (key: string) => localised(registry?.documents.find(doc => doc.key === key)?.label, language) || key;
  const fieldLabels = Object.fromEntries([...(registry?.shared_sections || []), ...(registry?.documents.flatMap(doc => doc.sections) || [])].flatMap(section => section.fields || []).map(field => [field.key, localised(field.label, language)]));
  const warnings = useDocumentValidation(detail?.shipment.bundle?.documents || [], !!detail, t("exportFocus.validationFailed"));
  useEffect(() => { api.documentsRegistry().then(setRegistry).catch(() => {}); }, []);
  useEffect(() => {
    let cancelled = false;
    setLoading(true); setFailure(""); setDetail(null); setComment("");
    const load = async () => {
      if (id) {
        const value = await api.dgReview(id);
        if (!cancelled) setDetail(value);
      } else {
        const value = await api.dgReviews(status, page);
        if (!cancelled) { setRows(value.items); setTotal(value.total); }
      }
    };
    void load().catch(e => { if (!cancelled) setFailure(String(e)); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [id, status, page, refresh]);
  async function decide(next: "approved" | "changes_requested") {
    if (!detail) return;
    setBusy(true);
    try {
      const decision = await api.decideDgReview(detail.id, next, comment);
      setDetail({ ...detail, ...decision });
      toast.success(t(`dgReview.${next}`));
    } catch (e) { toast.error(String(e)); }
    finally { setBusy(false); }
  }
  async function remove() {
    if (!detail) return;
    setBusy(true);
    try { await api.forgetDgReview(detail.id); setForget(false); navigate("/dg-reviews"); }
    catch (e) { toast.error(String(e)); }
    finally { setBusy(false); }
  }
  const shipment = detail?.shipment;
  return <div className="collection-page page-enter dg-review-workspace">
    <header className="page-heading"><div><p className="eyebrow">{t("dgReview.eyebrow")}</p><h2>{detail?.reference || t("dgReview.title")}</h2></div>
      <div className="flex flex-wrap gap-2">{id && <Link className="action-secondary" to="/dg-reviews">{t("dgReview.back")}</Link>}
        {canUseDgsa(user, publicSettings) && <Link className="action-secondary" to="/shipments/report">{t("dgsa.title")}</Link>}
        <button className="action-secondary" disabled={loading || busy} onClick={() => setRefresh(n => n + 1)}><RefreshIcon />{t("dgReview.refresh")}</button></div>
    </header>
    {publicSettings?.dg_review_enabled === false && <p className="review-policy-note">{t("dgReview.disabledHint")}</p>}
    {failure && <p className="editor-feedback" data-kind="error" role="alert">{failure}</p>}
    {loading ? <p role="status">{t("wizard.loading")}</p> : !failure && !id ? <section className="surface">
      <div className="review-filter"><label>{t("dgReview.filter")}<select className="directory-input" value={status} onChange={e => { setStatus(e.target.value); setPage(1); }}><option value="">{t("directory.allStatuses")}</option>{["pending", "approved", "changes_requested"].map(value => <option key={value} value={value}>{t(`dgReview.${value}`)}</option>)}</select></label><span>{t("dgReview.count", { count: total })}</span></div>
      {rows.length === 0 ? <div className="directory-empty"><ShieldIcon className="h-9 w-9" /><h3>{t("dgReview.empty")}</h3>{status ? <button className="action-secondary" onClick={() => { setStatus(""); setPage(1); }}>{t("history.clearFilters")}</button> : <Link className="action-secondary" to="/shipments">{t("nav.shipments")}</Link>}</div> : <ul className="review-list">{rows.map(row => <li key={row.id}><Link to={`/dg-reviews/${row.id}`}><div><strong>{row.reference || t("history.noReference")}</strong><p>{row.created_by} · {t(`modality.${row.modality}`)} · {when(row.created_at, i18n.language)}</p></div><span className="review-status" data-status={row.status}>{t(`dgReview.${row.status}`)}</span><ArrowRightIcon className="h-5 w-5" /></Link></li>)}</ul>}
      {total > 25 && <div className="review-filter"><button className="action-secondary" disabled={page === 1} onClick={() => setPage(n => n - 1)}>{t("wizard.back")}</button><span>{page} / {Math.ceil(total / 25)}</span><button className="action-secondary" disabled={page * 25 >= total} onClick={() => setPage(n => n + 1)}>{t("wizard.next")}</button></div>}
    </section> : !failure && detail && shipment && <>
      <section className="surface review-summary"><ShieldIcon className="h-8 w-8" /><div><span className="review-status" data-status={detail.status}>{t(`dgReview.${detail.status}`)}</span><p>{t("dgReview.submittedBy", { name: detail.created_by, date: when(detail.created_at, i18n.language) })}</p>{detail.reviewed_by && <p>{t("dgReview.reviewedBy", { name: detail.reviewed_by, date: detail.reviewed_at ? when(detail.reviewed_at, i18n.language) : "" })}</p>}{detail.comment && <blockquote className="review-comment">{detail.comment}</blockquote>}</div></section>
      <section className="surface p-5 sm:p-6"><h3 className="mb-4 font-semibold">{t("dgReview.submittedShipment")}</h3><p className="mb-4 text-sm text-slate-500">{t("dgReview.snapshotHint")}</p><ShipmentFields values={shipment.values} labels={fieldLabels} />
        {shipment.cargo ? <CargoSummary value={shipment.cargo} goods={cargoGoods(shipment.lines, shipment.cargo)} /> : <><h4 className="mb-3 mt-6 font-semibold">{t("wizard.lines")}</h4><ul className="review-goods">{shipment.lines.map((line, index) => <li key={index}><strong>{line.output_description || line.description}</strong><span>{line.quantity} {line.unit} · {line.weight_total_kg ?? "—"} kg</span></li>)}</ul></>}
      </section>
      <DgCompliancePanel entries={shipment.dangerous_goods || []} profiles={shipment.profiles} />
      <section className="surface p-5 sm:p-6"><h3 className="mb-4 font-semibold">{t("dgReview.declaration")}</h3>{shipment.dangerous_goods?.map((entry, index) => <div key={index} className="review-declaration">{entry.products.map((product, productIndex) => <details key={productIndex} open><summary>UN {String(product.un_number || "—")} · {String(product.proper_shipping_name || "")}</summary><DataFields value={product} /></details>)}<details><summary>{t("dgReview.packaging")}</summary><DataFields value={{ ...entry, products: undefined }} /></details></div>)}</section>
      <section className="surface p-5 sm:p-6"><h3 className="mb-3 font-semibold">{t("wizardDocs.title")}</h3>{shipment.bundle?.documents.map((document, index) => <details className="review-declaration" key={index}><summary>{labelFor(document.document_key)}</summary><DocumentWarnings heading={t("exportFocus.checks")} warnings={warnings[document.document_key] || []} /><ShipmentFields values={document.values} labels={fieldLabels} /></details>)}</section>
      {shipment.bundle?.signature_image && <section className="surface p-5"><h3 className="mb-3 font-semibold">{t("dgReview.signature")}</h3><img src={shipment.bundle.signature_image} className="max-h-32 max-w-full rounded bg-white p-3" alt={t("dgReview.signatureAlt")} /></section>}
      {specialist && detail.status === "pending" && <section className="surface review-decision"><div><h3>{t("dgReview.decision")}</h3><p>{t("dgReview.decisionHint")}</p></div><label htmlFor="review-comment">{t("dgReview.comment")}</label><textarea id="review-comment" className="directory-input" rows={4} maxLength={4000} value={comment} disabled={busy} onChange={e => setComment(e.target.value)} /><div className="flex flex-wrap gap-3"><button className="action-primary" disabled={busy} onClick={() => void decide("approved")}><CheckIcon />{t("dgReview.approve")}</button><button className="action-secondary" disabled={busy || !comment.trim()} onClick={() => void decide("changes_requested")}>{t("dgReview.requestChanges")}</button></div></section>}
      <footer className="review-footer">{detail.created_by === user.username && <Link className="action-secondary" to={`/wizard/${shipment.modality}?review=${detail.id}`}>{t("dgReview.openWizard")}<ArrowRightIcon /></Link>}
        {(detail.created_by === user.username || user.role === "admin") && <button className="action-secondary" disabled={busy} onClick={() => setForget(true)}>{t("dgReview.forget")}</button>}</footer>
      <ConfirmDialog open={forget} title={t("dgReview.forget")} body={t("dgReview.forgetHint")} confirmLabel={t("dgReview.forget")} onConfirm={() => void remove()} onCancel={() => setForget(false)} />
    </>}
  </div>;
}

/** Review every submitted field; no mutable controls can change the snapshot. */
function ShipmentFields({ values, labels }: { values: Record<string, string>; labels: Record<string, string> }) { return <DataFields value={values} labels={labels} />; }
function DataFields({ value, labels = {} }: { value: object; labels?: Record<string, string> }) {
  const { t } = useTranslation();
  return <dl className="review-fields">{Object.entries(value).filter(([, item]) => item !== undefined && item !== null && item !== "" && (!Array.isArray(item) || item.length > 0)).map(([key, item]) => <div key={key}><dt>{labels[key] || t(`dgReview.fields.${key}`, { defaultValue: key.replace(/_/g, " ") })}</dt><dd>{typeof item === "object" ? <DataFields value={item} /> : typeof item === "boolean" ? t(item ? "dgReview.yes" : "dgReview.no") : String(item)}</dd></div>)}</dl>;
}
