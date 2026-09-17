/**
 * Paste the carrier's booking confirmation; the references find their fields.
 *
 * The AWB number, the booking reference and the customs references arrive in
 * a confirmation e-mail *after* the booking — which is exactly when the
 * wizard's fields for them are still empty. Pasting the e-mail here saves
 * the retyping. Two rules keep it honest: the server only reads formats it
 * can verify (nothing is invented), and this component fills only fields
 * that are still empty — what a user typed is never overwritten.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../api/client";

const FIELD_LABEL_KEYS: Record<string, string> = {
  awb_number: "carrier.awb",
  booking_number: "carrier.booking",
  ens_mrn: "carrier.ens",
  aes_itn: "carrier.itn",
};

interface Props {
  values: Record<string, string>;
  onChange: (values: Record<string, string>) => void;
}

export default function CarrierConfirmationBox({ values, onChange }: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [summary, setSummary] = useState<string | null>(null);

  const read = async () => {
    setBusy(true);
    setSummary(null);
    try {
      const { found } = await api.parseCarrierConfirmation(text);
      const filled: string[] = [];
      const kept: string[] = [];
      const next = { ...values };
      for (const [key, value] of Object.entries(found)) {
        const label = t(FIELD_LABEL_KEYS[key] ?? key);
        if ((values[key] ?? "").trim()) {
          kept.push(label);
        } else {
          next[key] = value;
          filled.push(label);
        }
      }
      if (filled.length > 0) onChange(next);
      if (filled.length === 0 && kept.length === 0) {
        setSummary(t("carrier.foundNone"));
      } else {
        const parts = [];
        if (filled.length > 0) parts.push(t("carrier.filled", { fields: filled.join(", ") }));
        if (kept.length > 0) parts.push(t("carrier.kept", { fields: kept.join(", ") }));
        setSummary(parts.join(" "));
      }
    } catch (error) {
      setSummary(String(error));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-xl border border-dashed border-slate-300 p-3 dark:border-slate-700">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between text-left text-sm font-medium text-slate-800 dark:text-slate-200"
        aria-expanded={open}
      >
        <span>{t("carrier.title")}</span>
        <span aria-hidden>{open ? "−" : "+"}</span>
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          <textarea
            aria-label={t("carrier.title")}
            disabled={busy}
            className="min-h-[96px] w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            placeholder={t("carrier.placeholder")}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => void read()}
              disabled={busy || !text.trim()}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
            >
              {t("carrier.read")}
            </button>
            {summary && <p role="status" className="text-xs text-slate-600 dark:text-slate-300">{summary}</p>}
          </div>
        </div>
      )}
    </div>
  );
}
