import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  DocumentDefinition,
  DocumentField,
  DocumentRegistry,
  DocumentSection,
  FieldStatus,
  LocalizedText,
} from "../api/client";
import { documentLanguage, localised } from "../i18n/language";
import { FieldGroup, GroupKey, GroupedField, GroupedSection, groupFields } from "../wizard/documentGroups";
import AddressBookBar, { PARTIES } from "./AddressBookBar";
import CarrierConfirmationBox from "./CarrierConfirmationBox";
import CustomsRouteHint, { CUSTOMS_FIELD_KEYS, useCustomsRoute } from "./CustomsRouteHint";
import {
  AddressTextarea,
  LOCATION_FIELD_KEYS,
  LocationInput,
  MODALITY_LOCATION_TYPES,
} from "./GeoInputs";
import NhmCombobox from "./NhmCombobox";
import SignaturePad from "./SignaturePad";
import { WizardActions } from "./WizardShell";

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm min-h-[40px]";
const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const NO_EXCLUDED_FIELDS: readonly string[] = [];
const buttonSecondary =
  "px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 min-h-[44px] text-sm";
const buttonPrimary =
  "bg-brand-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50 min-h-[44px] text-sm";

const STATUS_BADGES: Partial<Record<FieldStatus, { key: string; className: string }>> = {
  CARRIER_PROVIDED: {
    key: "docfields.carrierProvided",
    className: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
  },
  SIGNATURE_REQUIRED: {
    key: "docfields.signatureRequired",
    className: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  },
};

export function conditionMet(condition: string | undefined, values: Record<string, string>): boolean {
  if (!condition) return true;
  const [field, expected] = condition.split("=");
  return (values[field?.trim() ?? ""] ?? "").trim() === (expected ?? "").trim();
}

export function resolveSections(doc: DocumentDefinition, registry: DocumentRegistry): DocumentSection[] {
  const shared = new Map(registry.shared_sections.map((s) => [s.key, s]));
  return doc.sections
    .map((section) => (section.ref ? shared.get(section.ref) : section))
    .filter((s): s is DocumentSection => !!s);
}

interface Props {
  hideActions?: boolean;
  registry: DocumentRegistry;
  documents: DocumentDefinition[];
  values: Record<string, string>;
  onChange: (values: Record<string, string>) => void;
  /** Fields already edited in the surrounding shipment header. */
  excludedFields?: readonly string[];
  autoValues?: Record<string, string>;
  modality?: string;
  onBack?: () => void;
  onDone?: () => void;
  signature?: string | null;
  onSignatureChange?: (dataUrl: string | null) => void;
  /** Draw the address book on the parties section. Only an installation
   *  that keeps its shipments has one. */
  addressBook?: boolean;
  /** A field to open at and put the cursor in: the export step's missing-field
   *  chips name one, and this step is where it lives. */
  focusField?: string | null;
  onFocusHandled?: () => void;
  /** Where the user came from, if they came to answer one thing. Shown as the
   *  primary action so they go back to it rather than walking the forms out. */
  returnLabel?: string;
  onReturn?: () => void;
}

/** The DOM id of a field's control, so a label can point at it and a caller
 *  can find it. One rule, so both ends agree without passing anything. */
export function fieldId(key: string): string {
  return `field-${key}`;
}

export default function DocumentFieldsStep({
  hideActions = false,
  registry,
  documents,
  values,
  onChange,
  excludedFields = NO_EXCLUDED_FIELDS,
  autoValues,
  modality,
  onBack,
  onDone,
  signature,
  onSignatureChange,
  addressBook,
  focusField,
  onFocusHandled,
  returnLabel,
  onReturn,
}: Props) {
  const { t, i18n } = useTranslation();
  const lang = documentLanguage(i18n.language);
  const L = (text?: LocalizedText) => localised(text, lang);
  // Which required fields were empty when the user last pressed Next. Nothing
  // is marked while somebody is still typing — that is the difference between
  // telling and nagging — and nothing is blocked either: the second press goes
  // on regardless, because a document EMCargo cannot finish is still the
  // user's to take further.
  const [flagged, setFlagged] = useState<string[]>([]);
  // Whether the customs references apply, read off the route as it is typed.
  const customsVerdicts = useCustomsRoute(values);

  const setValue = (key: string, value: string) => onChange({ ...values, [key]: value });

  const { groups } = useMemo(() => {
    const grouped = groupFields(registry, documents);
    if (!excludedFields.length) return grouped;
    const excluded = new Set(excludedFields);
    return { ...grouped, groups: grouped.groups.map(group => ({
      ...group,
      sections: group.sections.map(section => ({
        ...section, fields: section.fields.filter(field => !excluded.has(field.key)),
      })).filter(section => section.fields.length > 0),
    })).filter(group => group.sections.length > 0) };
  }, [registry, documents, excludedFields]);

  const valueOf = (field: DocumentField): string => {
    const autoValue = field.auto_from ? autoValues?.[field.auto_from] : undefined;
    return (values[field.key] ?? autoValue ?? "").trim();
  };

  const missingKeys = (sections: GroupedSection[]): string[] => {
    const keys: string[] = [];
    for (const section of sections) {
      for (const field of section.fields) {
        if (field.status !== "USER_REQUIRED") continue;
        if (field.condition && !conditionMet(field.condition, values)) continue;
        if (!valueOf(field)) keys.push(field.key);
      }
    }
    return keys;
  };

  // A group nobody still owes anything starts collapsed, showing what it says
  // rather than asking it again — a shipment reopened from the history or from
  // a template is three summaries and a way on. This is decided when the step
  // opens: a group must not fold itself away under the hands of somebody who
  // has just finished filling it in.
  const [openGroups, setOpenGroups] = useState<GroupKey[]>(() =>
    groups.filter((group) => missingKeys(group.sections).length > 0).map((group) => group.key),
  );
  // A group that appears later — a document chosen after the step was opened —
  // is opened if it wants something, and left alone otherwise.
  const known = useRef<GroupKey[]>(groups.map((group) => group.key));
  useEffect(() => {
    const fresh = groups.filter((group) => !known.current.includes(group.key));
    known.current = groups.map((group) => group.key);
    const wanting = fresh.filter((group) => missingKeys(group.sections).length > 0).map((group) => group.key);
    if (wanting.length > 0) setOpenGroups((current) => [...current, ...wanting]);
    // The values change on every keystroke; what matters here is the set of groups.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groups]);

  const isOpen = (key: GroupKey) => openGroups.includes(key);
  const toggle = (key: GroupKey) =>
    setOpenGroups((current) => (current.includes(key) ? current.filter((one) => one !== key) : [...current, key]));
  const open = (key: GroupKey) => setOpenGroups((current) => (current.includes(key) ? current : [...current, key]));

  const allSections = groups.flatMap((group) => group.sections);
  const empty = missingKeys(allSections);
  const warned = flagged.length > 0 && empty.some((key) => flagged.includes(key));

  const labelOf = (key: string): string => {
    for (const section of allSections) {
      const field = section.fields.find((one) => one.key === key);
      if (field) return L(field.label);
    }
    return key;
  };

  /** Which group holds a field, so a notice elsewhere can open it. */
  const groupOf = (key: string): GroupKey | undefined =>
    groups.find((group) => group.sections.some((section) => section.fields.some((field) => field.key === key)))?.key;

  const goToField = (key: string) => {
    const group = groupOf(key);
    if (group) open(group);
    window.setTimeout(() => {
      const element = document.getElementById(fieldId(key));
      element?.focus();
      element?.scrollIntoView?.({ block: "center", behavior: "smooth" });
    }, 60);
  };

  // Coming in to answer one named field: open the group it is in and put the
  // cursor in it. The element is not there until the group has rendered, which
  // is why the focus waits a frame rather than happening in the click.
  useEffect(() => {
    if (!focusField) return;
    const group = groupOf(focusField);
    if (group) open(group);
    const timer = window.setTimeout(() => {
      const element = document.getElementById(fieldId(focusField));
      element?.focus();
      element?.scrollIntoView?.({ block: "center", behavior: "smooth" });
      onFocusHandled?.();
    }, 60);
    return () => window.clearTimeout(timer);
    // The field is what decides; groupOf reads the memoised groups.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusField, groups]);

  // The party labels the address book names, as the form shows them: the
  // part of "Consignor — name" before the dash.
  const partyLabels = (section: GroupedSection): Record<string, string> => {
    const labels: Record<string, string> = {};
    for (const party of PARTIES) {
      const field = section.fields.find((f) => f.key === party.fields.name);
      if (field) labels[party.key] = L(field.label).split(" — ")[0];
    }
    return labels;
  };

  /** What a folded group says it holds: the answers themselves, shortened, so
   *  the summary is a check and not a promise that something was filled in. */
  const summaryOf = (group: FieldGroup): string => {
    const parts: string[] = [];
    for (const section of group.sections) {
      for (const field of section.fields) {
        const value = valueOf(field);
        if (!value) continue;
        const option = field.options?.find((item) => item.value === value);
        const display = option ? L(option.label) : field.type === "checkbox" && value === "true" ? t("docfields.yes") : value;
        const flat = display.replace(/\s+/g, " ").trim();
        parts.push(`${L(field.label)}: ${flat.length > 40 ? `${flat.slice(0, 40)}…` : flat}`);
        if (parts.length === 4) return parts.join(" · ");
      }
    }
    return parts.length > 0 ? parts.join(" · ") : t("docgroups.nothingFilled");
  };

  const goNext = () => {
    // First press with required fields still empty: say which, on the fields
    // themselves and in a summary above them, and open the groups they are in.
    // Second press goes on — the export step will keep saying what is missing,
    // and the server has the last word on what may be exported.
    if (empty.length > 0 && !warned) {
      setFlagged(empty);
      const wanting = groups
        .filter((group) => missingKeys(group.sections).length > 0)
        .map((group) => group.key);
      setOpenGroups((current) => [...current, ...wanting.filter((key) => !current.includes(key))]);
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    setFlagged([]);
    onDone?.();
  };

  const renderField = (field: GroupedField) => {
    if (field.status === "CONDITIONAL" && field.condition && !conditionMet(field.condition, values)) {
      return null;
    }
    const badge = STATUS_BADGES[field.status];
    const autoValue = field.auto_from ? autoValues?.[field.auto_from] : undefined;
    const value = values[field.key] ?? (autoValue !== undefined && values[field.key] === undefined ? autoValue : "");
    const required = field.status === "USER_REQUIRED";
    const isAddress = field.type === "textarea" && field.key.endsWith("_address");
    const isLocation = field.type === "text" && LOCATION_FIELD_KEYS.has(field.key);
    const locationTypes = MODALITY_LOCATION_TYPES[modality ?? ""] ?? ["airport", "port", "station"];

    const id = fieldId(field.key);
    // Marked only after a Next that found it empty, and unmarked the moment
    // something is typed into it.
    const missed = flagged.includes(field.key) && !(values[field.key] ?? "").trim();
    const ring = missed ? "ring-2 ring-red-400 border-red-400 dark:border-red-500" : "";

    return (
      <div key={field.key} className={field.type === "textarea" ? "md:col-span-2" : ""}>
        <div className="flex flex-wrap items-center gap-1.5">
          <label htmlFor={id} className="text-sm font-medium text-slate-800 dark:text-slate-200">
            {L(field.label)}
            {required && <span className="text-red-500"> *</span>}
          </label>
          {badge && (
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${badge.className}`}>
              {t(badge.key)}
            </span>
          )}
        </div>
        {isAddress ? (
          <div className="mt-1">
            <AddressTextarea
              value={value}
              onChange={(v) => setValue(field.key, v)}
              textareaId={id}
              textareaClassName={`${inputClass} min-h-[64px] ${ring}`}
            />
          </div>
        ) : field.type === "textarea" ? (
          <textarea
            id={id}
            className={`${inputClass} mt-1 min-h-[64px] ${ring}`}
            value={value}
            onChange={(e) => setValue(field.key, e.target.value)}
          />
        ) : isLocation ? (
          <div className="mt-1">
            <LocationInput
              id={id}
              value={value}
              onChange={(v) => setValue(field.key, v)}
              types={locationTypes}
              includeAddresses={modality === "road" || modality === "multimodal"}
            />
          </div>
        ) : field.key === "nhm_code" ? (
          <div className="mt-1">
            <NhmCombobox id={id} value={value} onChange={(v) => setValue(field.key, v)} />
          </div>
        ) : field.type === "select" ? (
          <select id={id} className={`${inputClass} mt-1 ${ring}`} value={value} onChange={(e) => setValue(field.key, e.target.value)}>
            <option value="">{t("docfields.choose")}</option>
            {(field.options ?? []).map((option) => (
              <option key={option.value} value={option.value}>
                {L(option.label)}
              </option>
            ))}
          </select>
        ) : field.type === "checkbox" ? (
          <label className="mt-1.5 flex min-h-[40px] items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <input
              id={id}
              type="checkbox"
              checked={value === "true"}
              onChange={(e) => setValue(field.key, e.target.checked ? "true" : "")}
              className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
            />
            {field.status === "SIGNATURE_REQUIRED" ? t("docfields.confirmExplicit") : t("docfields.yes")}
          </label>
        ) : (
          <input
            id={id}
            type={field.type === "number" ? "number" : field.type === "date" ? "date" : "text"}
            step={field.type === "number" ? "0.01" : undefined}
            className={`${inputClass} mt-1 ${ring}`}
            value={value}
            onChange={(e) => setValue(field.key, e.target.value)}
          />
        )}
        {missed && (
          <p className="mt-1 text-xs text-red-600 dark:text-red-400">{t("docfields.fieldMissing")}</p>
        )}
        {CUSTOMS_FIELD_KEYS.has(field.key) && <CustomsRouteHint verdict={customsVerdicts[field.key]} />}
      </div>
    );
  };

  const renderSection = (group: FieldGroup, section: GroupedSection) => (
    <div key={section.key} className="mt-4 first:mt-0">
      {/* One group, one meaning: the heading inside it says which document
          wanted these, and the group name says what they are about. */}
      {group.sections.length > 1 && section.label && (
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300">{L(section.label)}</h4>
      )}
      {addressBook && section.key === "parties" && (
        <AddressBookBar values={values} onChange={onChange} labels={partyLabels(section)} />
      )}
      {section.key === "references" && <CarrierConfirmationBox values={values} onChange={onChange} />}
      <div className="mt-3 grid gap-3 md:grid-cols-2">{section.fields.map(renderField)}</div>
    </div>
  );

  return (
    <div className="space-y-4">
      <div className={`${panelClass} p-4 sm:p-6`}>
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{t("docfields.sharedTitle")}</h3>
      </div>

      {warned && (
        <div
          role="alert"
          className="rounded-2xl border border-red-200 bg-red-50 p-4 dark:border-red-900/50 dark:bg-red-950/30"
        >
          <p className="text-sm font-medium text-red-800 dark:text-red-200">
            {t("docfields.stillEmpty", { count: empty.length })}
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {empty.map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => goToField(key)}
                className="rounded-lg border border-red-300 bg-white px-2.5 py-1 text-xs font-medium text-red-800 hover:bg-red-100 dark:border-red-800 dark:bg-slate-900 dark:text-red-200"
              >
                {labelOf(key)}
              </button>
            ))}
          </div>
        </div>
      )}

      {groups.map((group) => {
        const missing = missingKeys(group.sections).length;
        const opened = isOpen(group.key);
        return (
          <section key={group.key} className={`${panelClass} p-4 sm:p-6`}>
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="font-semibold text-slate-900 dark:text-slate-100">{t(`docgroups.${group.key}`)}</h4>
              {missing > 0 ? (
                <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                  {t("docgroups.stillNeeded", { count: missing })}
                </span>
              ) : (
                <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                  {t("docgroups.complete")}
                </span>
              )}
              <button
                type="button"
                onClick={() => toggle(group.key)}
                aria-expanded={opened}
                className="ml-auto rounded-lg border border-slate-200 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                {opened ? t("docgroups.hide") : t("docgroups.change")}
              </button>
            </div>
            {opened ? (
              <div className="mt-3">{group.sections.map((section) => renderSection(group, section))}</div>
            ) : (
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{summaryOf(group)}</p>
            )}
          </section>
        );
      })}

      {onSignatureChange && <SignaturePad value={signature ?? null} onChange={onSignatureChange} />}

      {/* In the wizard these land in the shell's action bar at the foot of the
          screen; on their own — as this component's own tests render it — they
          stay where they are written. */}
      {!hideActions && <WizardActions>
        <button type="button" onClick={onBack} className={buttonSecondary}>
          {t("wizard.back")}
        </button>
        {onReturn && returnLabel && (
          <button type="button" onClick={onReturn} className={buttonPrimary}>
            {returnLabel}
          </button>
        )}
        <button
          type="button"
          onClick={goNext}
          className={onReturn && returnLabel ? buttonSecondary : buttonPrimary}
        >
          {warned ? t("docfields.continueAnyway") : t("wizard.toExport")}
        </button>
      </WizardActions>}
    </div>
  );
}
