import { useEffect, useState } from "react";
import { Link } from "react-router";
import { useTranslation } from "react-i18next";
import { api, type DgReview, type ShipmentIn } from "../api/client";
import { ShieldIcon } from "../components/icons";

/** Save revisions are concurrency bookkeeping, not a different load to approve. */
export function reviewInputKey(payload: ShipmentIn): string {
  return JSON.stringify({ ...payload, snapshot: undefined, draft: undefined, expected_cargo_revision: undefined }, function(key, value) {
    if (key === "cargo") return value == null ? undefined : { ...value, revision: undefined };
    return value;
  });
}

export function useDgReview(payload: ShipmentIn, enabled: boolean, active: boolean, sourceReviewId?: string | null) {
  // The source state is for reopening only. Approval covers the actual
  // shipment/document inputs; changing tabs must not invalidate a decision.
  const key = reviewInputKey(payload);
  const [state, setState] = useState<{ key: string; review: DgReview | null } | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");
  const [refresh, setRefresh] = useState(0);
  const review = state?.key === key ? state.review : null;
  useEffect(() => {
    if (!enabled || !active) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const check = async () => {
      try {
        const result = await api.dgReviewStatus(payload);
        if (!cancelled) { setState({ key, review: result }); setFailure(""); }
      } catch (e) { if (!cancelled) { setState(null); setFailure(String(e)); } }
      if (!cancelled) timer = setTimeout(() => void check(), 15000);
    };
    timer = setTimeout(() => void check(), 400);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [key, enabled, active, refresh]);
  const submit = async () => {
    setBusy(true); setFailure("");
    const previous = sourceReviewId || review?.id;
    try { const result = await api.submitDgReview(previous ? { ...payload, dg_review_id: previous } : payload); setState({ key, review: result }); }
    catch (e) { setFailure(String(e)); }
    finally { setBusy(false); }
  };
  return { review, busy, failure, submit, refresh: () => setRefresh(n => n + 1),
    blocked: enabled && review?.status !== "approved", id: review?.status === "approved" ? review.id : undefined };
}

export function DgReviewGate({ control, ready }: { control: ReturnType<typeof useDgReview>; ready: boolean }) {
  const { t } = useTranslation();
  return <section className="surface review-gate" aria-label={t("dgReview.title")}><ShieldIcon className="h-8 w-8" /><div className="min-w-0 flex-1"><h3>{t("dgReview.title")}</h3><p role="status">{t(control.review ? `dgReview.${control.review.status}` : "dgReview.requiredHint")}</p>{!control.review && <p className="review-storage-hint">{t("dgReview.storageHint")}</p>}{control.review?.comment && <blockquote className="review-comment">{control.review.comment}</blockquote>}{control.failure && <p role="alert" className="text-red-700 dark:text-red-300">{control.failure}</p>}<div className="mt-3 flex flex-wrap gap-2">
    {(!control.review || control.review.status === "changes_requested") && <button type="button" className="action-primary" disabled={control.busy || !ready} onClick={() => void control.submit()}>{t(control.busy ? "dgReview.submitting" : "dgReview.submit")}</button>}
    {control.review && <Link className="action-secondary" to={`/dg-reviews/${control.review.id}`}>{t("dgReview.view")}</Link>}
    {control.review?.status === "pending" && <button type="button" className="action-secondary" onClick={control.refresh}>{t("dgReview.refresh")}</button>}
    {!ready && <p>{t("dgReview.finishFirst")}</p>}
  </div></div></section>;
}
