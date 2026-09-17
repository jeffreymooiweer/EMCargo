import { useTranslation } from "react-i18next";
import { DocumentDefinition, DocumentRegistry, LocalizedText } from "../api/client";
import { documentLanguage, localised } from "../i18n/language";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";

/** Why a document is on the list. Each of these is read off the registry —
 *  which document a modality names for 5.4.1, which papers are dangerous-goods
 *  only, which document a modality customarily uses, and which entries carry
 *  data rather than a document. None of them is a rule invented for a label. */
export type AdviceReason =
  | "dgTransport"
  | "dgSupport"
  | "modalityDefault"
  | "commercial"
  | "dataExchange";

export interface Advice {
  required: string[];
  recommended: string[];
  possible: string[];
  /** Not documents: the JSON export and the EDI notification, which are read
   *  by another system rather than carried on the vehicle. */
  integration: string[];
  preselected: string[];
  reasons: Record<string, AdviceReason>;
}

/** Which documents this shipment calls for, in honest groups.
 *
 * *Required* is reserved for what a read provision carries: with dangerous
 * goods on board, 5.4.1 requires a transport document with the prescribed
 * particulars, and the registry names which document that is per modality.
 * Everything else the app can make is *recommended* (the DG support papers,
 * or the modality's customary transport document) or *possible* — a
 * commercial document is the consignor's choice, and calling it required
 * would be claiming a provision nobody read.
 */
export function buildAdvice(registry: DocumentRegistry, modality: string, needsDg: boolean): Advice {
  const modalityDef = registry.modalities.find((m) => m.key === modality);
  const docs = modalityDef?.documents ?? [];
  const dgDoc = registry.dg_transport_documents?.[modality];
  const fallback = registry.modality_defaults?.[modality];
  const definition = (key: string) => registry.documents.find((d) => d.key === key);

  const reasons: Record<string, AdviceReason> = {};
  const required: string[] = [];
  const recommended: string[] = [];
  const possible: string[] = [];
  const integration: string[] = [];

  for (const key of docs) {
    const doc = definition(key);
    if (!doc) continue;
    if (doc.data_exchange) {
      reasons[key] = "dataExchange";
      integration.push(key);
    } else if (needsDg && key === dgDoc) {
      reasons[key] = "dgTransport";
      required.push(key);
    } else if (needsDg && doc.dg_only) {
      reasons[key] = "dgSupport";
      recommended.push(key);
    } else if (key === fallback) {
      reasons[key] = "modalityDefault";
      recommended.push(key);
    } else {
      reasons[key] = "commercial";
      possible.push(key);
    }
  }

  return { required, recommended, possible, integration, preselected: [...required, ...recommended], reasons };
}

interface Props {
  registry: DocumentRegistry;
  modality: string;
  needsDg: boolean;
  selected: string[];
  onChange: (selected: string[]) => void;
}

export default function DocumentAdvicePanel({ registry, modality, needsDg, selected, onChange }: Props) {
  const { t, i18n } = useTranslation();
  const lang = documentLanguage(i18n.language);
  const L = (text?: LocalizedText) => localised(text, lang);
  const advice = buildAdvice(registry, modality, needsDg);

  const toggle = (key: string) => {
    onChange(selected.includes(key) ? selected.filter((k) => k !== key) : [...selected, key]);
  };

  const groups: { keys: string[]; label: string; note?: string; optional?: boolean }[] = [
    { keys: advice.required, label: t("advice.required"), note: t("advice.requiredNote") },
    { keys: advice.recommended, label: t("advice.recommended") },
    { keys: advice.possible, label: t("advice.possible"), optional: true },
    // Not documents: read by another system, not carried on the vehicle.
    { keys: advice.integration, label: t("advice.integration"), optional: true },
  ];

  /** The reason a whole group shares, if its documents are all on the list for
   *  the same reason. Said once above them rather than repeated on every card;
   *  where the reasons differ — a DG paper beside the customary transport
   *  document — each card says its own. */
  const sharedReason = (keys: string[]): string | null => {
    const kinds = new Set(keys.map((key) => advice.reasons[key]));
    const kind = [...kinds][0];
    return kinds.size === 1 && (kind === "dgTransport" || kind === "dgSupport") ? t(`advice.reason.${kind}`) : null;
  };

  const docFor = (key: string): DocumentDefinition | undefined =>
    registry.documents.find((d) => d.key === key);

  return (
    <div className={`${panelClass} space-y-3 p-4 sm:p-6`}>
      <div>
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{t("advice.title")}</h3>
      </div>
      {groups.map((group) => {
        if (group.keys.length === 0) return null;
        const shared = sharedReason(group.keys);
        const choices = (
            <div key={group.label}>
              {!group.optional && <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                {group.label}
              </p>}
              {(group.note ?? shared) && (
                <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{group.note ?? shared}</p>
              )}
              <div className="mt-1.5 grid gap-1.5">
                {group.keys.map((key) => {
                  const doc = docFor(key);
                  if (!doc) return null;
                  const checked = selected.includes(key);
                  return (
                    <label
                      key={key}
                      className={`flex cursor-pointer items-start gap-2.5 rounded-xl border p-2.5 transition ${
                        checked
                          ? "border-brand-500 ring-1 ring-brand-500 dark:border-brand-500"
                          : "border-slate-200 hover:border-slate-300 dark:border-slate-700 dark:hover:border-slate-600"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggle(key)}
                        className="mt-0.5 h-4 w-4 shrink-0 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                      />
                      <span className="min-w-0">
                        <span className="block text-sm font-medium text-slate-900 dark:text-slate-100">
                          {L(doc.label)}
                        </span>
                        {/* Why it is on the list, where that differs from the
                            document beside it; otherwise the group said it. */}
                        {!shared && (advice.reasons[key] === "dgTransport" || advice.reasons[key] === "dgSupport") && (
                          <span className="mt-0.5 block text-xs font-medium text-slate-700 dark:text-slate-300">
                            {t(`advice.reason.${advice.reasons[key]}`)}
                          </span>
                        )}
                        <span className="mt-0.5 block text-xs text-slate-500 dark:text-slate-400">
                          {L(doc.issue_status)}
                        </span>
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>
        );
        if (!group.optional) return choices;
        const chosen = group.keys.filter(key => selected.includes(key));
        return <details key={group.label} className="document-options">
          <summary><span>{group.label}</span><span>{chosen.length ? t("studio.documentsSelected", { count: chosen.length }) : t("studio.showOptions")}</span></summary>
          {chosen.length > 0 && <p className="document-selected">{chosen.map(key => L(docFor(key)?.label)).join(" · ")}</p>}
          {choices}
        </details>;
      })}
    </div>
  );
}
