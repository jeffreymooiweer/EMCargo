/** The adviser's half of the annual report, in the DVSA's shape.
 *
 *  Drawn from the definition the server sends — sections and questions in
 *  the reader's language — so the form and the paper cannot disagree about
 *  what is asked. What the history can propose (the transport table, the
 *  method of carriage, the high consequence goods, the tonnage) is offered
 *  under a button and never written into an answer by itself: the adviser
 *  takes it over, or does not.
 */
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  api,
  DgsaAnswers,
  DgsaFormResponse,
  DgsaIncident,
  DgsaQuestion,
  DgsaTransportRow,
  DgsaYesNo,
} from "../api/client";
import { useToast } from "../toast/ToastProvider";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm min-h-[40px]";
const buttonPrimary =
  "bg-brand-600 text-white px-4 py-2.5 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50 min-h-[44px] text-sm";
const buttonSecondary =
  "px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 text-xs";

type Props = {
  year: number;
  department: string;
  language: string;
  form: DgsaFormResponse;
  onSaved: (savedAt: string) => void;
};

function yesNo(value: unknown): DgsaYesNo {
  const v = (value ?? {}) as Partial<DgsaYesNo>;
  return { answer: (v.answer as DgsaYesNo["answer"]) ?? "", details: v.details ?? "" };
}

export default function DgsaReportForm({ year, department, language, form, onSaved }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const [answers, setAnswers] = useState<DgsaAnswers>(form.answers);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setAnswers(form.answers);
    setDirty(false);
  }, [form]);

  const { definition, prefill, report } = form;
  const questionsBySection = useMemo(() => {
    const map: Record<string, DgsaQuestion[]> = {};
    for (const q of definition.questions) (map[q.section] ??= []).push(q);
    return map;
  }, [definition]);
  const classesPresent = useMemo(
    () => new Set((report.by_class ?? []).map((c) => String(c.class).split(".")[0])),
    [report],
  );

  const set = (key: string, value: DgsaAnswers[string]) => {
    setAnswers((current) => ({ ...current, [key]: value }));
    setDirty(true);
  };

  const takeOver = (q: DgsaQuestion) => {
    const proposed = prefill[q.key];
    if (proposed === undefined) return;
    if (q.kind === "transport_table") {
      // Merge: the operations and band per class the history saw, on top of
      // what the adviser already ticked for other classes.
      const current = (answers[q.key] ?? {}) as Record<string, DgsaTransportRow>;
      const merged: Record<string, DgsaTransportRow> = { ...current };
      for (const [cls, row] of Object.entries(proposed as Record<string, DgsaTransportRow>)) {
        merged[cls] = { ...(current[cls] ?? { operations: [], band: "" }), operations: row.operations, band: row.band || current[cls]?.band || "" };
      }
      set(q.key, merged);
    } else {
      set(q.key, proposed);
    }
  };

  const save = async () => {
    setSaving(true);
    try {
      const result = await api.saveDgsaAnswers(year, department, answers);
      setAnswers(result.answers);
      setDirty(false);
      onSaved(result.saved_at);
      toast.success(t("dgsa.saved"));
    } catch (e) {
      toast.error(String(e));
    } finally {
      setSaving(false);
    }
  };

  const labels = definition.answer_labels;

  const renderYesNo = (q: DgsaQuestion) => {
    const value = yesNo(answers[q.key]);
    const choices: DgsaYesNo["answer"][] = q.kind === "yesnona" ? ["yes", "no", "na"] : ["yes", "no"];
    return (
      <div key={q.key} className="rounded-xl border border-slate-200 dark:border-slate-800 p-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <p className="text-sm text-slate-800 dark:text-slate-200 max-w-3xl">
            {q.text}
            {q.checklist && <span className="ml-2 text-xs text-slate-400">{q.checklist}</span>}
          </p>
          <div className="flex gap-3" role="radiogroup" aria-label={q.text}>
            {choices.map((choice) => (
              <label key={choice} className="flex items-center gap-1 text-sm text-slate-700 dark:text-slate-300">
                <input
                  type="radio"
                  name={q.key}
                  checked={value.answer === choice}
                  onChange={() => set(q.key, { ...value, answer: choice })}
                  className="h-4 w-4 text-brand-600"
                />
                {labels[choice]}
              </label>
            ))}
          </div>
        </div>
        <textarea
          className={`${inputClass} mt-2 min-h-[56px]`}
          placeholder={labels.details}
          aria-label={`${q.text} — ${labels.details}`}
          value={value.details}
          onChange={(e) => set(q.key, { ...value, details: e.target.value })}
        />
        {prefill[q.key] !== undefined && q.prefill && (
          <button type="button" className={`${buttonSecondary} mt-2`} onClick={() => takeOver(q)}>
            {t("dgsa.takeOver")}
          </button>
        )}
      </div>
    );
  };

  const renderText = (q: DgsaQuestion) => {
    const value = String(answers[q.key] ?? "");
    const proposed = prefill[q.key];
    return (
      <label key={q.key} className="block text-sm text-slate-800 dark:text-slate-200">
        {q.text}
        {q.checklist && <span className="ml-2 text-xs text-slate-400">{q.checklist}</span>}
        {q.kind === "textarea" ? (
          <textarea className={`${inputClass} mt-1 min-h-[88px]`} value={value} onChange={(e) => set(q.key, e.target.value)} />
        ) : (
          <input
            type={q.kind === "date" ? "date" : "text"}
            className={`${inputClass} mt-1`}
            value={value}
            onChange={(e) => set(q.key, e.target.value)}
          />
        )}
        {typeof proposed === "string" && proposed && proposed !== value && (
          <button type="button" className={`${buttonSecondary} mt-1`} onClick={() => takeOver(q)}>
            {t("dgsa.takeOverValue", { value: proposed })}
          </button>
        )}
      </label>
    );
  };

  const renderChoice = (q: DgsaQuestion) => {
    const value = String(answers[q.key] ?? "");
    return (
      <fieldset key={q.key} className="space-y-2">
        <legend className="text-sm font-medium text-slate-800 dark:text-slate-200">{q.text}</legend>
        {(q.options ?? []).map((option) => (
          <label key={option} className="flex items-start gap-2 text-sm text-slate-700 dark:text-slate-300">
            <input type="radio" name={q.key} checked={value === option} onChange={() => set(q.key, option)} className="mt-1 h-4 w-4 text-brand-600" />
            <span>{q.option_labels?.[option] ?? option}</span>
          </label>
        ))}
      </fieldset>
    );
  };

  const renderMulti = (q: DgsaQuestion) => {
    const value = (answers[q.key] as string[] | undefined) ?? [];
    const proposed = prefill[q.key] as string[] | undefined;
    return (
      <fieldset key={q.key} className="space-y-1">
        <legend className="text-sm font-medium text-slate-800 dark:text-slate-200">{q.text}</legend>
        <div className="flex flex-wrap gap-4">
          {(q.options ?? []).map((option) => (
            <label key={option} className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={value.includes(option)}
                onChange={(e) => set(q.key, e.target.checked ? [...value, option] : value.filter((v) => v !== option))}
                className="h-4 w-4 rounded text-brand-600"
              />
              {q.option_labels?.[option] ?? option}
            </label>
          ))}
        </div>
        {proposed && proposed.length > 0 && q.prefill && (
          <button type="button" className={buttonSecondary} onClick={() => takeOver(q)}>
            {t("dgsa.takeOverValue", { value: proposed.map((p) => q.option_labels?.[p] ?? p).join(", ") })}
          </button>
        )}
      </fieldset>
    );
  };

  const renderIncidents = (q: DgsaQuestion) => {
    const rows = (answers[q.key] as DgsaIncident[] | undefined) ?? [];
    const update = (index: number, patch: Partial<DgsaIncident>) =>
      set(q.key, rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
    return (
      <div key={q.key} className="space-y-2">
        <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{q.text}</p>
        {rows.map((row, index) => (
          <div key={index} className="grid gap-2 sm:grid-cols-[9rem_1fr_2fr_auto]">
            <input type="date" className={inputClass} value={row.date} aria-label={q.columns?.date} onChange={(e) => update(index, { date: e.target.value })} />
            <input className={inputClass} value={row.place} placeholder={q.columns?.place} aria-label={q.columns?.place} onChange={(e) => update(index, { place: e.target.value })} />
            <input className={inputClass} value={row.description} placeholder={q.columns?.description} aria-label={q.columns?.description} onChange={(e) => update(index, { description: e.target.value })} />
            <button type="button" className={buttonSecondary} onClick={() => set(q.key, rows.filter((_, i) => i !== index))}>
              {t("dgsa.removeRow")}
            </button>
          </div>
        ))}
        <button type="button" className={buttonSecondary} onClick={() => set(q.key, [...rows, { date: "", place: "", description: "" }])}>
          {t("dgsa.addIncident")}
        </button>
      </div>
    );
  };

  const renderTransportTable = (q: DgsaQuestion) => {
    const table = (answers[q.key] as Record<string, DgsaTransportRow> | undefined) ?? {};
    const proposed = (prefill[q.key] as Record<string, DgsaTransportRow> | undefined) ?? {};
    const rowOf = (cls: string): DgsaTransportRow => table[cls] ?? { operations: [], band: "" };
    const setRow = (cls: string, patch: Partial<DgsaTransportRow>) => set(q.key, { ...table, [cls]: { ...rowOf(cls), ...patch } });
    const counted = (cls: string) => {
      const p = proposed[cls];
      if (!p) return "";
      const parts: string[] = [];
      if (p.quantity_kg) parts.push(`${p.quantity_kg.toLocaleString(undefined, { maximumFractionDigits: 1 })} kg`);
      if (p.quantity_l) parts.push(`${p.quantity_l.toLocaleString(undefined, { maximumFractionDigits: 1 })} L`);
      if (p.packages) parts.push(`${p.packages} ${t("dgsa.packages")}`);
      if (p.shipments) parts.push(`${p.shipments}×`);
      return parts.join(" · ");
    };
    return (
      <div key={q.key} className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{q.text}</p>
          {Object.keys(proposed).length > 0 && (
            <button type="button" className={buttonSecondary} onClick={() => takeOver(q)}>
              {t("dgsa.takeOverTable")}
            </button>
          )}
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400">{q.band_note}</p>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="px-2 py-1">{t("dgsa.class")}</th>
                <th className="px-2 py-1">{t("dgsa.operations")}</th>
                <th className="px-2 py-1">{t("dgsa.band")}</th>
                <th className="px-2 py-1">{t("dgsa.counted")}</th>
              </tr>
            </thead>
            <tbody>
              {(q.classes ?? []).map((cls) => {
                const row = rowOf(cls);
                return (
                  <tr key={cls} className="border-b border-slate-100 dark:border-slate-800/60 align-top">
                    <td className="px-2 py-2 font-medium text-slate-800 dark:text-slate-200">{cls}</td>
                    <td className="px-2 py-2">
                      <div className="flex flex-wrap gap-x-3 gap-y-1">
                        {(q.operations ?? []).map((op) => (
                          <label key={op} className="flex items-center gap-1 text-xs text-slate-700 dark:text-slate-300">
                            <input
                              type="checkbox"
                              checked={row.operations.includes(op)}
                              aria-label={`${cls} ${q.operation_labels?.[op] ?? op}`}
                              onChange={(e) =>
                                setRow(cls, { operations: e.target.checked ? [...row.operations, op] : row.operations.filter((o) => o !== op) })
                              }
                              className="h-3.5 w-3.5 rounded text-brand-600"
                            />
                            {q.operation_labels?.[op] ?? op}
                          </label>
                        ))}
                      </div>
                    </td>
                    <td className="px-2 py-2">
                      <select className={`${inputClass} min-w-[7rem]`} value={row.band} aria-label={`${cls} ${t("dgsa.band")}`} onChange={(e) => setRow(cls, { band: e.target.value })}>
                        <option value="">—</option>
                        {(q.bands ?? []).map((band) => (
                          <option key={band} value={band}>{band}</option>
                        ))}
                      </select>
                      {cls === "7" && (
                        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
                          {(q.package_designs ?? []).map((design) => (
                            <label key={design} className="flex items-center gap-1 text-xs text-slate-700 dark:text-slate-300">
                              <input
                                type="checkbox"
                                checked={(row.designs ?? []).includes(design)}
                                onChange={(e) =>
                                  setRow(cls, { designs: e.target.checked ? [...(row.designs ?? []), design] : (row.designs ?? []).filter((d) => d !== design) })
                                }
                                className="h-3.5 w-3.5 rounded text-brand-600"
                              />
                              {q.package_design_labels?.[design] ?? design}
                            </label>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="px-2 py-2 text-xs text-slate-600 dark:text-slate-400 whitespace-nowrap">{counted(cls)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderQuestion = (q: DgsaQuestion) => {
    switch (q.kind) {
      case "yesno":
      case "yesnona":
        return renderYesNo(q);
      case "choice":
        return renderChoice(q);
      case "multi":
        return renderMulti(q);
      case "incidents":
        return renderIncidents(q);
      case "transport_table":
        return renderTransportTable(q);
      default:
        return renderText(q);
    }
  };

  return (
    <div className="space-y-4">
      {definition.sections.map((section) => {
        const questions = questionsBySection[section.key] ?? [];
        const answeredHere = questions.some((q) => yesNo(answers[q.key]).answer);
        if (section.only_with_class && !classesPresent.has(section.only_with_class) && !answeredHere) return null;
        return (
          <section key={section.key} className={`${panelClass} p-4 sm:p-6 space-y-3`}>
            <h3 className="font-semibold text-slate-900 dark:text-slate-100">{section.title}</h3>
            {questions.map(renderQuestion)}
            {section.key === "prepared" && (
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {form.has_signature ? t("dgsa.signatureSaved") : t("dgsa.signatureMissing")}
              </p>
            )}
          </section>
        );
      })}
      <div className="sticky bottom-3 flex flex-wrap items-center justify-end gap-3">
        {dirty && <span className="text-xs text-amber-700 dark:text-amber-300">{t("dgsa.unsaved")}</span>}
        <button type="button" className={buttonPrimary} disabled={saving || !dirty} onClick={() => void save()}>
          {saving ? t("dgsa.saving") : t("dgsa.save")}
        </button>
      </div>
    </div>
  );
}
