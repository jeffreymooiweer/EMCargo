/** Import is a separate task surface; everyday goods editing has one entry.
 * Column mapping and append/replace decisions still happen before changing a
 * populated shipment. Closing an in-flight import invalidates its response.
 */
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, ImportAnalysis, ImportMapping } from "../api/client";
import { useToast } from "../toast/ToastProvider";
import ImportColumnMapping from "./ImportColumnMapping";
import { ImportIcon, PasteIcon, CloseIcon } from "./icons";

const buttonClass =
  "inline-flex min-h-[44px] shrink-0 items-center gap-2 rounded-lg border border-slate-200 dark:border-slate-700 px-3 text-sm font-medium " +
  "text-slate-700 transition-colors hover:bg-slate-50 disabled:opacity-50 " +
  "dark:text-slate-200 dark:hover:bg-slate-800";
const textareaClass =
  "w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-mono text-sm " +
  "text-slate-900 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 " +
  "dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 min-h-[9rem]";
const primaryClass =
  "rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50";
const secondaryClass =
  "rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 dark:border-slate-700 dark:text-slate-200";

interface Props {
  /** Whether the shipment already holds a line worth replacing. */
  hasLines: boolean;
  initialPaste?: boolean;
  onImport: (text: string, mode: "append" | "replace") => void;
  /** A file dropped on the goods panel, handed over to be parsed here. */
  dropped?: File | null;
  onDroppedHandled?: () => void;
}

export default function GoodsImport({ hasLines, onImport, dropped, onDroppedHandled, initialPaste = false }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const [open, setOpen] = useState(initialPaste);
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const operation = useRef(0);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [analysis, setAnalysis] = useState<ImportAnalysis | null>(null);
  const [rows, setRows] = useState<string[][]>([]);
  const area = useRef<HTMLTextAreaElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const lineCount = text.split(/\r?\n/).filter((line) => line.trim()).length;
  const readRows = rows.length - (analysis?.has_header ? 1 : 0);
  const skipped = rows.length > 0 ? Math.max(0, readRows - lineCount) : 0;

  const close = () => {
    operation.current += 1;
    setBusy(false);
    setOpen(false);
    setText("");
    setAnalysis(null);
    setRows([]);
  };

  const takeFile = async (file: File | null) => {
    if (!file) return;
    setOpen(true);
    const request = ++operation.current;
    setBusy(true);
    try {
      const result = await api.parseWizardImportFile(file);
      if (request !== operation.current) return;
      setText(result.text);
      setAnalysis(result.analysis);
      setRows(result.rows);
      // A recognised header leaves nothing to ask about: an empty shipment
      // takes the lines straight away. With lines already in it the choice
      // between adding and replacing is still the user's.
      if (result.analysis.source === "header" && !hasLines && result.text.trim()) {
        onImport(result.text, "replace");
        close();
        return;
      }
      setOpen(true);
    } catch (e) {
      if (request === operation.current) toast.error(String(e));
    } finally {
      if (request === operation.current) setBusy(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  useEffect(() => {
    if (!dropped) return;
    void takeFile(dropped);
    onDroppedHandled?.();
    // takeFile is recreated every render; the file is what decides.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dropped]);

  const remap = async (mapping: ImportMapping, hasHeader: boolean) => {
    if (rows.length === 0) return;
    const request = ++operation.current;
    setBusy(true);
    try {
      const result = await api.remapWizardImport(rows, mapping, hasHeader);
      if (request !== operation.current) return;
      setText(result.text);
      setAnalysis(result.analysis);
    } catch (e) {
      if (request === operation.current) toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      if (request === operation.current) setBusy(false);
    }
  };

  useEffect(() => {
    if (open && !dialog.current?.open) {
      dialog.current?.showModal();
      // A named heading avoids opening the phone keyboard when the user wants
      // a file. A direct paste shortcut intentionally focuses the paste area.
      if (initialPaste) area.current?.focus();
      else heading.current?.focus();
    } else if (!open && dialog.current?.open) {
      dialog.current.close();
      trigger.current?.focus();
    }
  }, [open, initialPaste]);
  useEffect(() => () => { operation.current += 1; }, []);

  const run = async (mode: "append" | "replace") => {
    if (!text.trim()) return;
    // Excel clipboard data deserves the same header detection and column
    // mapping as an uploaded spreadsheet, including reordered columns.
    if (text.includes("\t")) {
      const request = ++operation.current;
      setBusy(true);
      try {
        const result = await api.parseWizardImportFile(new File([text], "clipboard.txt", { type: "text/plain" }));
        if (request !== operation.current) return;
        setText(result.text);
        setAnalysis(result.analysis);
        setRows(result.rows);
        if (result.analysis.source !== "header" || !result.text.trim()) return;
        onImport(result.text, mode);
        close();
      } catch (e) {
        if (request === operation.current) toast.error(e instanceof Error ? e.message : String(e));
      } finally {
        if (request === operation.current) setBusy(false);
      }
      return;
    }
    onImport(text, mode);
    close();
  };

  return (
    <>
      <button ref={trigger} type="button" onClick={() => setOpen(true)} className="goods-import-trigger" aria-haspopup="dialog">
        <ImportIcon />{t("review.importAction")}
      </button>
      <dialog ref={dialog} className="goods-import-dialog" aria-labelledby="goods-import-title"
        onCancel={(event) => { event.preventDefault(); close(); }}>
        {open && <div className="goods-import-content" aria-busy={busy}>
          <header className="goods-import-heading">
            <h3 ref={heading} id="goods-import-title" tabIndex={-1}>{t("review.importTitle")}</h3>
            <button type="button" onClick={close} className="goods-import-close" aria-label={t("review.cancel")}><CloseIcon className="h-5 w-5" /></button>
          </header>
          <label className={buttonClass + " goods-file-button"}>
            <ImportIcon />{busy ? t("import.parsingFile") : t("review.importFile")}
            <input ref={fileInput} type="file" accept=".xlsx,.csv,.txt" className="sr-only" disabled={busy}
              onChange={(event) => void takeFile(event.target.files?.[0] ?? null)} />
          </label>
          <span className="goods-file-formats">XLSX · CSV · TXT</span>
          {analysis && <ImportColumnMapping analysis={analysis} onChange={remap} busy={busy} />}
          <label htmlFor="goods-paste-area" className="goods-paste-label"><PasteIcon />{t("review.importPaste")}</label>
          <textarea id="goods-paste-area" ref={area} className={textareaClass} value={text}
            onChange={(event) => setText(event.target.value)} placeholder={t("wizard.paste")} disabled={busy} />
          {text.trim() && <p className="goods-import-count">
            {t("review.importRead", { count: lineCount })}
            {skipped > 0 && ` · ${t("review.importSkipped", { count: skipped })}`}
          </p>}
          <button type="button" className="goods-template-link"
            onClick={() => void api.downloadWizardTemplate().catch((e) => toast.error(String(e)))}>
            {t("import.downloadTemplate")}
          </button>
          <footer className="goods-import-actions">
            {hasLines ? <>
              <button type="button" onClick={() => run("replace")} disabled={!text.trim() || busy} className={secondaryClass}>{t("review.importReplace")}</button>
              <button type="button" onClick={() => run("append")} disabled={!text.trim() || busy} className={primaryClass}>{t("review.importAppend")}</button>
            </> : <button type="button" onClick={() => run("replace")} disabled={!text.trim() || busy} className={primaryClass}>{t("review.importConfirm")}</button>}
          </footer>
        </div>}
      </dialog>
    </>
  );
}
