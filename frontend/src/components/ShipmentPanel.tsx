/**
 * What the shipment adds up to, standing beside the work instead of waiting
 * at the end of it.
 *
 * Two things were true before this and neither was good. The counts — lines,
 * weight, volume, warnings — were four cards on the goods step and nowhere
 * else, so the moment you moved to the questions the totals you were entering
 * against went off the screen. And the documents being prepared were only
 * visible on the step that asks their questions, so on the goods step nobody
 * could see what all this typing was *for*.
 *
 * Both live here now, on every step: the four numbers, and the document set
 * with what each one is still waiting for. A document that is short of an
 * answer says how many and takes you to the first of them — the same jump
 * release 111 built for the export step's chips, from a place you pass much
 * earlier.
 *
 * **Where it stands.** A right-hand column from `xl` up, sticky so it stays
 * with you; below that, a card above the work. The goods list is a row of
 * fields that wraps rather than a fixed table, so taking 18rem off it on a
 * wide screen costs nothing — measured at 1440, where the row is still one
 * line. Under `xl` there is not that much to spare, and the panel goes back to
 * being what it always was: a strip above the list.
 */
import { useTranslation } from "react-i18next";

/** How ready one document is. `not_applicable` never reaches this panel: a
 *  document that does not apply to this shipment is not being prepared. */
export type PanelDocState = "ready" | "draft" | "blocked";

export interface PanelDocument {
  key: string;
  label: string;
  state: PanelDocState;
  /** How many answers it is still short, and the first of them. */
  missing: number;
  firstMissing: string | null;
  /** A cargo failure has its own explanation and a place to resolve it. */
  blockedReason?: string;
}

interface Props {
  lines: number;
  weightKg: number | null;
  volumeM3: number | null;
  /** Warnings on the goods plus substance questions nobody has answered. */
  attention: number;
  documents: PanelDocument[];
  /** Take the user to one missing answer. */
  onMissing?: (fieldKey: string) => void;
}

const dotColour: Record<PanelDocState, string> = {
  ready: "bg-emerald-500",
  draft: "bg-amber-500",
  blocked: "bg-red-500",
};

function Count({ label, value, tone }: { label: string; value: string; tone?: "attention" }) {
  return (
    <div className="min-w-0">
      {/* Wrapping, not truncating. In an 18rem column "Total transport
          volume" does not fit on one line in any of the four languages, and
          a label cut to "Total transpo…" has stopped being a label. */}
      <p className="text-[11px] uppercase leading-tight tracking-wide text-slate-500 dark:text-slate-400">
        {label}
      </p>
      <p
        className={`mt-0.5 text-base font-semibold tabular-nums sm:text-lg ${
          tone === "attention"
            ? "text-amber-700 dark:text-amber-300"
            : "text-slate-900 dark:text-slate-100"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

/** How many answers a document is short. A button when there is somewhere to
 *  go and the caller can take you there; the same words as plain text when
 *  there is not, because the count is worth knowing either way. */
function MissingCount({ label, field, onMissing }: {
  label: string;
  field: string | null;
  onMissing?: (fieldKey: string) => void;
}) {
  if (!field || !onMissing) {
    return <span className="text-xs text-amber-700 dark:text-amber-300">{label}</span>;
  }
  return (
    <button
      type="button"
      onClick={() => onMissing(field)}
      className="text-xs font-medium text-brand-700 underline-offset-2 hover:underline dark:text-brand-300"
    >
      {label}
    </button>
  );
}

export default function ShipmentPanel({
  lines, weightKg, volumeM3, attention, documents, onMissing,
}: Props) {
  const { t } = useTranslation();

  return (
    <div className="shipment-panel rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <h3 className="px-4 pt-4 text-base font-semibold">{t("panel.title")}</h3>
      <div className="grid grid-cols-2 gap-x-4 gap-y-3 px-4 py-3 sm:grid-cols-4 xl:grid-cols-2">
        <Count label={t("wizard.lines")} value={String(lines)} />
        <Count label={t("wizard.totalWeight")} value={weightKg != null ? `${weightKg} kg` : "—"} />
        <Count label={t("wizard.totalVolume")} value={volumeM3 != null ? `${volumeM3} m³` : "—"} />
        <Count
          label={t("wizard.warnings")}
          value={String(attention)}
          tone={attention > 0 ? "attention" : undefined}
        />
      </div>

      {documents.length > 0 && (
        <details className="shipment-documents border-t border-slate-200 px-4 py-3 dark:border-slate-800" open>
          <summary className="cursor-pointer text-sm font-semibold text-slate-700 dark:text-slate-200">{t("panel.preparing")}</summary>
          <ul className="mt-2 space-y-1.5">
            {documents.map((doc) => (
              <li key={doc.key} className="grid grid-cols-[8px_minmax(0,1fr)] items-start gap-x-2 gap-y-0.5">
                <span
                  className={`mt-1.5 h-2 w-2 shrink-0 self-start rounded-full ${dotColour[doc.state]}`}
                  aria-hidden
                />
                <span className="min-w-0 break-words text-sm text-slate-700 dark:text-slate-200">
                  {doc.label}
                </span>
                <div className="col-start-2 min-w-0 break-words">
                {doc.state === "ready" ? (
                  <span className="text-xs text-emerald-700 dark:text-emerald-300">
                    {t("panel.ready")}
                  </span>
                ) : doc.state === "blocked" && doc.blockedReason ? (
                  <MissingCount label={doc.blockedReason} field={doc.firstMissing} onMissing={onMissing} />
                ) : doc.state === "blocked" ? (
                  // Blocked means the substance itself is not established.
                  // There is no one field to send somebody to, and offering a
                  // jump would send them nowhere.
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    {t("panel.blocked")}
                  </span>
                ) : doc.missing > 0 ? (
                  // The count is the way in. Naming a number of missing
                  // answers and then leaving somebody to find them is how the
                  // export step used to end.
                  <MissingCount
                    label={t("panel.missing", { count: doc.missing })}
                    field={doc.firstMissing}
                    onMissing={onMissing}
                  />
                ) : (
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    {t("panel.missingUnknown")}
                  </span>
                )}
                </div>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
