/**
 * What happens to the entry while it is being made.
 *
 * The baseline reloaded the page halfway through a shipment and found the
 * wizard back at the goods step with nothing left of what had been typed, and
 * nothing had warned beforehand. Two honest answers, depending on what the
 * installation is allowed to keep:
 *
 * - Where the history is on, the running entry is kept as a draft and this
 *   says so — *Saved*, *Saving…*, or *Could not save*, never a claim that
 *   something was kept when the save failed.
 * - Where the history is switched off, this says that too, and offers the draft as a file the
 *   user keeps themselves. A promise not to store anything is not a licence
 *   to lose somebody's work silently.
 */
import { useRef } from "react";
import { useTranslation } from "react-i18next";

export type DraftStatus = "idle" | "saving" | "saved" | "failed";

interface Props {
  /** "kept": the installation keeps the draft. "file": it keeps nothing. */
  mode: "kept" | "file";
  status: DraftStatus;
  savedAt?: Date | null;
  /** Whether anything has been entered yet; an empty wizard says nothing. */
  active: boolean;
  onDiscard?: () => void;
  onDownload?: () => void;
  onOpenFile?: (file: File) => void;
  /** Inside the wizard's header this is a line in a box that already exists;
   *  a second border around it would be a box inside a box. */
  compact?: boolean;
}

const barBase = "flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-slate-600 dark:text-slate-300";
const barClass = `${barBase} rounded-xl border border-slate-200 bg-white px-3 py-2 dark:border-slate-800 dark:bg-slate-900`;
const linkClass =
  "font-medium text-brand-700 underline hover:text-brand-800 dark:text-brand-300";

export default function DraftBar({
  mode, status, savedAt, active, onDiscard, onDownload, onOpenFile, compact,
}: Props) {
  const { t, i18n } = useTranslation();
  const fileInput = useRef<HTMLInputElement | null>(null);
  if (!active) return null;

  const box = compact ? barBase : barClass;
  const time = savedAt ? savedAt.toLocaleTimeString(i18n.language, { timeStyle: "short" }) : "";

  if (mode === "file") {
    return (
      <div className={box}>
        <span>{t("draft.notKeptHere")}</span>
        {onDownload && (
          <button type="button" onClick={onDownload} className={linkClass}>
            {t("draft.download")}
          </button>
        )}
        {onOpenFile && (
          <>
            <button type="button" onClick={() => fileInput.current?.click()} className={linkClass}>
              {t("draft.open")}
            </button>
            <input
              ref={fileInput}
              type="file"
              accept="application/json,.json"
              className="hidden"
              aria-label={t("draft.open")}
              onChange={(e) => {
                const file = e.target.files?.[0];
                e.target.value = "";
                if (file) onOpenFile(file);
              }}
            />
          </>
        )}
      </div>
    );
  }

  return (
    <div className={box} role="status">
      <span
        className={
          status === "failed"
            ? "font-medium text-red-700 dark:text-red-300"
            : status === "saved"
              ? "font-medium text-emerald-700 dark:text-emerald-300"
              : ""
        }
      >
        {status === "saving" && t("draft.saving")}
        {status === "saved" && (time ? t("draft.savedAt", { time }) : t("draft.saved"))}
        {status === "failed" && t("draft.failed")}
        {status === "idle" && t("draft.kept")}
      </span>
      {onOpenFile && <label className={linkClass}>
        {t("routing.import")}
        <input type="file" accept="application/json,.json" aria-label={t("routing.import")} className="sr-only" onChange={e => {
          const file = e.target.files?.[0]; e.target.value = ""; if (file) onOpenFile(file);
        }} />
      </label>}
      {onDiscard && (
        <button type="button" onClick={onDiscard} className={linkClass}>
          {t("draft.discard")}
        </button>
      )}
    </div>
  );
}
