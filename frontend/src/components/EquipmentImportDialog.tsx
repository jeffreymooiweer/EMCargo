import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, EquipmentImportResult, translateMessage } from "../api/client";
import { useToast } from "../toast/ToastProvider";
import EquipmentDialog from "./EquipmentDialog";
import { DownloadIcon, ImportIcon } from "./icons";

interface Props {
  open: boolean;
  onClose: () => void;
  onComplete: () => void;
}

export default function EquipmentImportDialog({ open, onClose, onComplete }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<EquipmentImportResult | null>(null);
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!open) return null;

  const handleClose = () => {
    if (loading) return;
    setResult(null);
    setError("");
    if (fileInputRef.current) fileInputRef.current.value = "";
    onClose();
  };

  const handleFile = async (file: File | null) => {
    if (!file || loading) return;
    setLoading(true);
    setResult(null);
    setError("");
    try {
      const imported = await api.importEquipmentFile(file);
      onComplete();
      if (imported.errors.length === 0 && imported.skipped === 0) {
        toast.success(`${t("materieel.importCreated", { count: imported.created })}, ${t("materieel.importUpdated", { count: imported.updated })}`);
        onClose();
      } else {
        setResult(imported);
      }
    } catch (cause) {
      setError(String(cause));
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return <EquipmentDialog title={t("materieel.importTitle")} onClose={handleClose} busy={loading}>
    <div className="space-y-4" aria-busy={loading}>
      <div className="flex flex-wrap gap-2">
        <button type="button" className="action-primary" disabled={loading} onClick={() => fileInputRef.current?.click()}><ImportIcon />{t(loading ? "import.importingFile" : "import.chooseFile")}</button>
        <button type="button" className="action-secondary" disabled={loading} onClick={() => { void api.downloadEquipmentTemplate().catch(cause => setError(String(cause))); }}><DownloadIcon />{t("import.downloadTemplate")}</button>
        <input ref={fileInputRef} type="file" accept=".xlsx,.csv,.txt" className="sr-only" tabIndex={-1} aria-label={t("import.chooseFile")} disabled={loading} onChange={event => { void handleFile(event.target.files?.[0] ?? null); }} />
      </div>
      <p className="text-xs text-slate-500 dark:text-slate-400">XLSX · CSV · TXT</p>
      {error && <p role="alert" className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      {result && <section className="rounded-xl border border-slate-200 p-4 text-sm dark:border-slate-700" aria-label={t("materieel.importDone")}>
        <p role="status" className="font-medium">{t("materieel.importCreated", { count: result.created })} · {t("materieel.importUpdated", { count: result.updated })}{result.skipped > 0 && ` · ${t("materieel.importSkipped", { count: result.skipped })}`}</p>
        {result.errors.length > 0 && <ul role="alert" className="mt-3 space-y-2 text-amber-700 dark:text-amber-300">{result.errors.map((item, index) => <li key={`${index}-${item.code}`}>{translateMessage(item)}</li>)}</ul>}
      </section>}
    </div>
  </EquipmentDialog>;
}
