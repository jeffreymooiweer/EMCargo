import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";
import { api, AssistantEvent, AssistantPending, AssistantReview, AssistantState } from "../api/client";
import { documentLanguage, localised } from "../i18n/language";
import { ArrowRightIcon, CheckIcon, CloseIcon } from "./icons";
import AiIcon from "./AiIcon";
import BusinessSuggestions from "./BusinessSuggestions";
import DocumentIntake from "./DocumentIntake";
import { AddressTextarea, LOCATION_FIELD_KEYS, LocationInput, MODALITY_LOCATION_TYPES } from "./GeoInputs";
import "./AssistantModal.css";

type Screen = "describe" | "question" | "ready";
type Action = "answer" | "revise" | "optional" | "add_goods";
interface Snapshot { state: AssistantState; pending: AssistantPending | null; review?: AssistantReview; screen: Screen; answer: string }
interface Props {
  open: boolean;
  onClose: () => void;
  buildState: () => AssistantState;
  onApplyState: (state: AssistantState) => void;
  onReview?: () => void;
  modality?: string;
  initialDocument?: boolean;
}
const copy = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T;
const PLAIN_QUESTIONS = new Set(["consignor_name", "consignor_address", "consignee_name", "consignee_address", "carrier_name", "loading_point", "discharge_point", "loading_date", "freight_payment", "payment_instruction", "established_place", "established_date"]);

/** A focused shipment interview, with an inspectable working draft.
 * Successful turns are saved in the ordinary wizard. Failed interpretations
 * keep the original answer. Every history entry is a complete snapshot, and
 * late responses cannot overwrite the wizard after the panel closes.
 */
export default function AssistantModal({ open, onClose, buildState, onApplyState, onReview, modality, initialDocument = false }: Props) {
  const { t, i18n } = useTranslation();
  const lang = documentLanguage(i18n.language);
  const [pending, setPending] = useState<AssistantPending | null>(null);
  const [working, setWorking] = useState<AssistantState>({});
  const [review, setReview] = useState<AssistantReview>();
  const [history, setHistory] = useState<Snapshot[]>([]);
  const [screen, setScreen] = useState<Screen>("describe");
  const [input, setInput] = useState("");
  const [choice, setChoice] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [documentOpen, setDocumentOpen] = useState(false);
  const [modelBlocked, setModelBlocked] = useState(false);
  const [showInfo, setShowInfo] = useState(false);
  const [availability, setAvailability] = useState<"checking" | "ready" | "missing" | "error">("checking");
  const [statusAttempt, setStatusAttempt] = useState(0);
  const dialog = useRef<HTMLDivElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const sequence = useRef(0);
  const inFlight = useRef(false);
  const callbacks = useRef({ buildState, onApplyState, onClose });
  callbacks.current = { buildState, onApplyState, onClose };
  const current = useRef({ working, pending, review, screen, input, choice });
  current.current = { working, pending, review, screen, input, choice };

  const L = (value: unknown) => typeof value === "string" ? value : localised(value as Record<string, string> | undefined, lang);
  const unitLabel = (value: unknown) => t(`units.name.${String(value ?? "pcs")}`, { defaultValue: String(value ?? "pcs") });
  const factValue = (fact: AssistantPending) => L(fact.option_labels?.[String(fact.value)]) || String(fact.value ?? "");
  const errorFor = (event: AssistantEvent) => {
    if (event.reason) return t(`assistant.problem.${String(event.reason)}`, { choice: L(event.option_label) || String(event.suggested_choice ?? "") });
    if (event.kind === "not_understood") return t("assistant.notUnderstood");
    return event.example ? t("assistant.clarify", { example: String(event.example) })
      : t("assistant.corrected", { attempt: String(event.attempt ?? "") });
  };

  async function send(message: string, action: Action = "answer", target?: AssistantPending, initial?: AssistantState, previous?: Snapshot): Promise<boolean> {
    if (inFlight.current || modelBlocked) return false;
    inFlight.current = true;
    const request = ++sequence.current;
    const view = current.current;
    const state = copy(initial ?? view.working);
    const question = initial ? null : target ?? (view.screen === "describe" ? null : view.pending);
    const snapshot: Snapshot = { state, pending: view.pending, review: view.review, screen: view.screen, answer: message };
    setBusy(true);
    setError("");
    try {
      const result = await api.assistantStep({ message, state, pending: question, language: lang, ...(action === "answer" ? {} : { action }) });
      if (sequence.current !== request) return false;
      const failure = result.events.find(event => event.kind === "clarify" || event.kind === "not_understood");
      if (failure) {
        setError(errorFor(failure));
        if (failure.reason === "unknown") setShowInfo(true);
        // A stale question is the only failure that requires a new question.
        if (failure.reason === "stale") { setPending(result.pending); setScreen(result.pending?.scope === "goods_intake" ? "describe" : result.pending ? "question" : "ready"); }
        return false;
      }
      if (previous || !initial) setHistory(stack => [...stack, previous ?? snapshot]);
      setWorking(copy(result.state));
      setReview(result.review);
      setPending(result.pending);
      setScreen(result.pending?.scope === "goods_intake" ? "describe" : result.pending ? "question" : "ready");
      if (action !== "revise") callbacks.current.onApplyState(copy(result.state));
      const revisingChoice = action === "revise" && target?.options?.includes(String(target.value));
      setInput(action === "revise" && !revisingChoice ? String(target?.value ?? "") : "");
      setChoice(revisingChoice ? String(target?.value) : "");
      setShowInfo(false);
      const answered = result.events.filter(event => event.kind === "answered");
      const added = result.events.find(event => event.kind === "lines_added");
      setNotice(added ? t("assistant.linesAdded", { count: Number(added.count) })
        : answered.length ? t("assistant.factsUpdated", { count: answered.length })
        : result.events.some(event => event.kind === "un_confirmed") ? t("assistant.unConfirmed", { un: String(result.events.find(e => e.kind === "un_confirmed")?.un) })
        : result.events.some(event => event.kind === "un_dismissed") ? t("assistant.unDismissed") : "");

      return true;
    } catch (cause) {
      if (sequence.current === request) {
        const removed = !!(cause && typeof cause === "object" && "code" in cause && cause.code === "assistant.model_required");
        if (removed) setModelBlocked(true);
        setError(t(removed ? "assistant.modelRequired" : "assistant.problem.connection"));
      }
      return false;
    } finally {
      if (sequence.current === request) { inFlight.current = false; setBusy(false); }
    }
  }

  async function pickBusiness(party: string, candidate: { name: string; address: string }) {
    if (busy || modelBlocked || inFlight.current) return;
    const view = current.current;
    const next = copy(view.working);
    if (next.doc_values?.[`${party}_address`]) return;
    next.doc_values = { ...next.doc_values, [`${party}_name`]: candidate.name, [`${party}_address`]: candidate.address };
    await send("", "answer", undefined, next, { state: copy(view.working), pending: view.pending, review: view.review, screen: view.screen, answer: view.input });
  }

  async function recheckModel() {
    if (inFlight.current) return;
    inFlight.current = true;
    const request = ++sequence.current;
    setBusy(true);
    try {
      const status = await api.assistantStatus();
      if (sequence.current !== request) return;
      if (status.installed && status.available) {
        setModelBlocked(false);
        setError("");
      } else setError(t("assistant.modelRequired"));
    } catch {
      if (sequence.current === request) setError(t("assistant.problem.connection"));
    } finally {
      if (sequence.current === request) { inFlight.current = false; setBusy(false); }
    }
  }

  useLayoutEffect(() => {
    if (!open) return;
    const trigger = document.activeElement as HTMLElement | null;
    return () => trigger?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const before = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const initial = copy(callbacks.current.buildState());
    setWorking(initial); setHistory([]); setPending(null); setReview(undefined);
    setDocumentOpen(initialDocument);
    setInput(""); setChoice(""); setError(""); setNotice(""); setShowInfo(false); setScreen("describe");
    setAvailability("checking"); setModelBlocked(false);
    const statusRequest = ++sequence.current;
    void api.assistantStatus().then(status => {
      if (sequence.current !== statusRequest) return;
      if (!status.installed || !status.available) { setAvailability("missing"); return; }
      setAvailability("ready");
      if (initial.draft_lines?.length && !initialDocument) void send("", "answer", undefined, initial);
    }).catch(() => {
      if (sequence.current === statusRequest) setAvailability("error");
    });

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); callbacks.current.onClose(); }
      if (event.key !== "Tab") return;
      const items = Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), textarea:not(:disabled), select:not(:disabled), summary, [tabindex="0"]') ?? [])
        .filter(el => {
          for (let node: HTMLElement | null = el; node; node = node.parentElement) {
            if (node.tagName === "DETAILS" && !node.hasAttribute("open") && !node.querySelector(":scope > summary")?.contains(el)) return false;
            const style = window.getComputedStyle(node);
            if (node.hidden || style.display === "none" || style.visibility === "hidden") return false;
          }
          return true;
        });
      const first = items[0], last = items[items.length - 1];
      if (event.shiftKey && (document.activeElement === first || !items.includes(document.activeElement as HTMLElement))) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && (document.activeElement === last || !dialog.current?.contains(document.activeElement))) { event.preventDefault(); first?.focus(); }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      ++sequence.current; inFlight.current = false; setBusy(false);
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = before;
    };
    // A fresh opening deliberately reads the latest manual wizard edits.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, statusAttempt]);

  useLayoutEffect(() => {
    if (!open) return;
    // Focus before paint: a delayed focus callback could interrupt someone
    // already typing in the address suggestions of the next question.
    if (screen === "describe" && availability === "ready") dialog.current?.querySelector<HTMLTextAreaElement>("textarea")?.focus();
    else heading.current?.focus();
  }, [open, availability, screen, pending?.scope, pending?.field, pending?.line_id]);

  useLayoutEffect(() => {
    // Long mobile questions can push the error and recovery buttons below
    // the fixed footer. Reveal the message without stealing keyboard focus.
    if (open && error) dialog.current?.querySelector<HTMLElement>("#assistant-error")?.scrollIntoView?.({ block: "nearest" });
  }, [open, error]);

  function goBack() {
    const snapshot = history[history.length - 1];
    if (!snapshot || busy) return;
    setHistory(stack => stack.slice(0, -1)); setWorking(copy(snapshot.state));
    callbacks.current.onApplyState(copy(snapshot.state)); setPending(snapshot.pending);
    setScreen(snapshot.screen); setReview(snapshot.review); setInput(snapshot.answer);
    setChoice(""); setError(""); setNotice(""); setShowInfo(false);

  }

  if (!open) return null;
  const candidates = (pending?.candidates ?? []) as { un: string; name: string; class: string }[];
  const title = pending?.scope === "un_confirm"
    ? candidates.length === 1 ? t("assistant.unConfirmOne", candidates[0]) : t("assistant.unConfirmMany")
    : pending?.scope === "goods_weight_basis" ? t("assistant.weightBasisQuestion", { weight: pending.weight })
    : pending?.scope === "goods_quantity" ? t("assistant.quantityQuestion", { unit: unitLabel(pending.unit) })
    : pending?.scope === "doc_question" && PLAIN_QUESTIONS.has(String(pending.field)) ? t(`assistant.questionFor.${pending.field}`)
    : L(pending?.simple) || t("assistant.question", { label: L(pending?.label) || pending?.field });
  const options = pending?.scope === "un_confirm"
    ? candidates.length === 1 ? [{ value: "ja", label: t("assistant.yes") }, { value: "nee", label: t("assistant.no") }]
      : [...candidates.map(c => ({ value: `UN ${c.un}`, label: `UN ${c.un} · ${c.name}` })), { value: "nee", label: t("assistant.noneOfThese") }]
    : pending?.scope === "goods_weight_basis" ? [{ value: "total", label: t("assistant.weightTotal") }, { value: "each", label: t("assistant.weightEach") }]
    : (pending?.options ?? []).map(value => ({ value, label: L(pending?.option_labels?.[value]) || value }));
  const answer = input.trim() || choice;
  const field = String(pending?.field ?? "");
  const isAddress = pending?.scope === "doc_question" && field.endsWith("_address");
  const isLocation = pending?.scope === "doc_question" && LOCATION_FIELD_KEYS.has(field);
  const goods = working.draft_lines ?? [];
  const description = goods.map(line => `${line.quantity_unconfirmed ? "?" : line.quantity ?? "?"} ${unitLabel(line.unit)} ${line.description ?? ""}`).join(" · ");
  const info = [L(pending?.label), L(pending?.help)].filter(Boolean).join(" — ");
  const section = screen === "describe" ? 0 : screen === "ready" ? 3 : pending?.scope === "doc_question" ? 2 : 1;
  const facts = review?.facts ?? [];
  const documentFacts = facts.filter(f => f.scope === "doc_question");
  const dgFacts = facts.filter(f => f.scope === "dg_question");
  const edit = (target: AssistantPending) => { void send("", "revise", target); };
  const summary = <div className="assistant-summary-content">
    <p className="assistant-eyebrow">{t("assistant.recorded")}</p>
    {!goods.length && <p className="assistant-empty">{t("assistant.summaryEmpty")}</p>}
    {goods.map(line => <div className="assistant-cargo" key={String(line.id)}>
      <div className="assistant-cargo-title"><span>{String(line.description ?? "")}</span>
        <button type="button" disabled={busy || modelBlocked} className="assistant-edit" onClick={() => edit({ scope: "goods_quantity", field: "quantity", line_id: line.id, value: line.quantity_unconfirmed ? "" : line.quantity })} aria-label={t("assistant.editQuantity", { goods: String(line.description ?? "") })}>{t("assistant.edit")}</button></div>
      <p>{line.quantity_unconfirmed ? t("assistant.quantityMissing") : `${line.quantity} ${unitLabel(line.unit)}`}</p>
      {line.unconfirmed_weight_kg != null ? <p className="assistant-measure">{t("assistant.weightAwaitingBasis", { weight: Number(line.unconfirmed_weight_kg).toLocaleString(i18n.language) })}</p>
        : line.weight_total_kg != null && <p className="assistant-measure">{Number(line.weight_total_kg).toLocaleString(i18n.language, { maximumFractionDigits: 3 })} kg <span>· {t(line.weight_each_kg != null ? "assistant.statedWeight" : "assistant.calculatedWeight")}</span></p>}
      <details className="assistant-cargo-actions"><summary>{t("assistant.measurements")}</summary>
        {line.length_cm != null && line.width_cm != null && line.height_cm != null && <p>{[line.length_cm, line.width_cm, line.height_cm].map(value => Number(value).toLocaleString(i18n.language)).join(" × ")} cm</p>}
        <button type="button" disabled={busy || modelBlocked} className="assistant-edit" aria-label={`${t("assistant.editWeight")} · ${line.description}`} onClick={() => edit({ scope: "goods_question", field: "goods_weight_each", line_id: line.id })}>{t("assistant.editWeight")}</button>
        <button type="button" disabled={busy || modelBlocked} className="assistant-edit" aria-label={`${t("assistant.editDimensions")} · ${line.description}`} onClick={() => edit({ scope: "goods_question", field: "goods_dimensions", line_id: line.id })}>{t("assistant.editDimensions")}</button>
      </details>
      {line.confirmed_un ? <span className="assistant-un">UN {String(line.confirmed_un)}</span> : null}
    </div>)}
    {documentFacts.length > 0 && <dl className="assistant-facts">{documentFacts.map(fact => <div key={fact.field}>
      <dt>{L(fact.label) || fact.field}</dt><dd><span>{factValue(fact)}</span><button type="button" disabled={busy || modelBlocked} className="assistant-edit" aria-label={t("assistant.editField", { field: L(fact.label) || fact.field })} onClick={() => edit(fact)}>{t("assistant.edit")}</button></dd>
    </div>)}</dl>}
    {dgFacts.length > 0 && <details className="assistant-dg-facts"><summary>{t("assistant.dgDetails")}</summary><dl className="assistant-facts">{dgFacts.map((fact, i) => <div key={i}><dt>{L(fact.label) || fact.field}</dt><dd>{factValue(fact)}</dd></div>)}</dl></details>}
    {Boolean(review?.deferred_count) && <p className="assistant-deferred">{t("assistant.deferred", { count: review!.deferred_count })}</p>}
    {!!goods.length && <p className="assistant-saved"><CheckIcon className="h-3.5 w-3.5" />{t("assistant.savedInWizard")}</p>}
  </div>;

  return createPortal(<div className="assistant-backdrop" data-testid="assistant-backdrop" onClick={onClose}>
    <div ref={dialog} role="dialog" aria-modal="true" aria-labelledby="assistant-title" className="assistant-dialog" data-busy={busy} onClick={event => event.stopPropagation()}>
      <header className="assistant-header"><div className="assistant-mark"><AiIcon className="h-7 w-7" /></div><div><h2 id="assistant-title">{t("assistant.title")}</h2></div><button type="button" className="assistant-close" aria-label={t("assistant.close")} onClick={onClose}><CloseIcon className="h-5 w-5" /></button></header>
      {availability !== "ready" ? <div className="assistant-availability">
        <h3 ref={heading} tabIndex={-1}>{t(availability === "checking" ? "assistant.checkingModel" : availability === "missing" ? "assistant.modelTitle" : "assistant.statusFailed")}</h3>
        <p role="status">{t(availability === "checking" ? "assistant.checkingModelHint" : availability === "missing" ? "assistant.modelRequired" : "assistant.problem.connection")}</p>
        <div className="assistant-availability-actions">
          <button type="button" className="assistant-primary" onClick={onClose}>{t("assistant.continueManually")}</button>
          {availability !== "checking" && <button type="button" className="assistant-secondary" onClick={() => setStatusAttempt(attempt => attempt + 1)}>{t("assistant.retryStatus")}</button>}
        </div>
      </div> : <>
      <ol className="assistant-stages" aria-label={t("assistant.progress")}>{["brief", "cargo", "details", "review"].map((key, i) => <li key={key} data-active={i === section} data-complete={i < section} aria-current={i === section ? "step" : undefined}><span>{i < section ? <CheckIcon className="h-3 w-3" /> : i + 1}</span>{t(`assistant.stage.${key}`)}</li>)}</ol>
      {documentOpen ? <DocumentIntake state={working} language={lang} onCancel={() => setDocumentOpen(false)} onAccept={async next => {
        const before = current.current;
        const ok = await send("", "add_goods", undefined, next, { state: copy(before.working), pending: before.pending,
          review: before.review, screen: before.screen, answer: before.input });
        if (ok) setDocumentOpen(false);
        return ok;
      }} /> : <><div className="assistant-layout">
        <div className="assistant-main">
          <details className="assistant-mobile-summary"><summary>{t("assistant.summary")}<span>{description || t("assistant.summaryEmptyShort")}</span></summary>{summary}</details>
          <div className="assistant-question">
            {screen !== "describe" && availability === "ready" && !modelBlocked && ([
              ["consignor", "loading_point"], ["consignee", "discharge_point"],
            ] as const).map(([party, location]) => {
              const name = working.doc_values?.[`${party}_name`];
              const city = working.doc_values?.[location];
              return name && city && !working.doc_values?.[`${party}_address`] ?
                <BusinessSuggestions key={`${party}:${name}:${city}`} name={name} city={city} language={lang}
                  disabled={busy || !!input.trim()} onPick={candidate => void pickBusiness(party, candidate)} /> : null;
            })}
            {screen === "describe" ? <>
              <h3 ref={heading} tabIndex={-1}>{t("assistant.describeLabel")}</h3>
              <button type="button" className="assistant-secondary mb-4" disabled={busy || modelBlocked} onClick={() => setDocumentOpen(true)}>{t("intake.open")}</button>
              <label className="sr-only" htmlFor="assistant-description">{t("assistant.describeLabel")}</label>
              <textarea id="assistant-description" className="assistant-input assistant-description" value={input} onChange={e => setInput(e.target.value)} maxLength={4000} placeholder={t("assistant.describePlaceholder")} disabled={busy || modelBlocked} aria-describedby={error ? "assistant-error" : undefined} />
            </> : screen === "ready" ? <>
              <div className="assistant-ready-mark"><CheckIcon className="h-7 w-7" /></div>
              <h3 ref={heading} tabIndex={-1}>{t("assistant.readyTitle")}</h3>
              {review?.has_dangerous_goods && <p className="assistant-release-note">{t("assistant.dgReviewNotice")}</p>}
              {!!review?.optional_count && !working.include_optional && <button type="button" disabled={busy || modelBlocked} className="assistant-optional" onClick={() => void send("", "optional")}>{t("assistant.optionalDetails", { count: review.optional_count })}<ArrowRightIcon className="h-4 w-4" /></button>}
              <button type="button" disabled={busy || modelBlocked} className="assistant-text-button" onClick={() => { setScreen("describe"); setPending(null); setInput(""); setError(""); }}>{t("assistant.addGoods")}</button>
            </> : <>
              <div className="assistant-question-meta"><p className="assistant-eyebrow">{t(pending?.scope === "doc_question" ? "assistant.shipmentDetails" : "assistant.yourGoods")}</p><span>{t(pending?.required ? "assistant.required" : "assistant.optional")}</span></div>
              <h3 ref={heading} tabIndex={-1} id="assistant-question-title">{title}</h3>
              {pending?.goods ? <p className="assistant-for-goods">{String(pending.goods)}</p> : null}
              {options.length > 0 && <div className="assistant-options" role="radiogroup" aria-labelledby="assistant-question-title">{options.map(option => <label key={option.value} data-selected={choice === option.value && !input}>
                <input type="radio" name="assistant-choice" value={option.value} checked={choice === option.value && !input} disabled={busy || modelBlocked} onChange={() => { setChoice(option.value); setInput(""); }} /><span>{option.label}</span><CheckIcon className="assistant-option-check h-4 w-4" />
              </label>)}</div>}
              <label className="assistant-answer-label" htmlFor="assistant-answer">{t(options.length ? "assistant.orDescribe" : "assistant.yourAnswer")}</label>
              <fieldset disabled={busy || modelBlocked} className="assistant-answer-field">
                {isAddress ? <AddressTextarea value={input} onChange={setInput} textareaId="assistant-answer" rows={4} textareaClassName="assistant-input" />
                  : isLocation ? <LocationInput id="assistant-answer" value={input} onChange={setInput} types={MODALITY_LOCATION_TYPES[modality ?? ""] ?? ["airport", "port", "station"]} className="assistant-input" />
                  : <input id="assistant-answer" className="assistant-input" type="text" inputMode={pending?.scope === "goods_quantity" ? "numeric" : "text"} value={input} onChange={e => { setInput(e.target.value); setChoice(""); }} placeholder={t(pending?.type === "date" ? "assistant.dateExample" : "assistant.answerPlaceholder")} maxLength={4000} aria-invalid={!!error} aria-describedby={error ? "assistant-error" : undefined} onKeyDown={event => { if (event.key === "Enter" && answer) { event.preventDefault(); void send(answer); } }} />}
                {pending?.type === "date" && <input className="assistant-date-picker" type="date" aria-label={t("assistant.chooseDate")} value={/^\d{4}-\d{2}-\d{2}$/.test(input) ? input : ""} onChange={e => setInput(e.target.value)} />}
              </fieldset>
              {info && <button type="button" className="assistant-text-button" onClick={() => setShowInfo(!showInfo)} aria-expanded={showInfo}>{t("assistant.info")}</button>}
              {showInfo && <p className="assistant-help">{info}</p>}
            </>}
            {error && <div id="assistant-error" role="alert" className="assistant-error"><strong>{t(modelBlocked ? "assistant.modelTitle" : "assistant.needsClarification")}</strong><p>{error}</p>{modelBlocked && <div className="assistant-availability-actions"><button type="button" disabled={busy} className="assistant-secondary" onClick={() => void recheckModel()}>{t("assistant.retryStatus")}</button><button type="button" className="assistant-secondary" onClick={onClose}>{t("assistant.continueManually")}</button></div>}</div>}
            <div className="assistant-status" role="status" aria-live="polite">{busy ? <span className="assistant-thinking"><AiIcon className="h-4 w-4" />{t("assistant.thinking")}</span> : !error && notice ? <span><CheckIcon className="h-4 w-4" />{notice}</span> : null}</div>
          </div>
        </div>
        <aside className="assistant-summary" aria-label={t("assistant.summary")}><h3>{t("assistant.summary")}</h3>{summary}</aside>
      </div>
      <footer className="assistant-footer"><div className="assistant-footer-left"><button type="button" disabled={busy || modelBlocked || !history.length} className="assistant-secondary" onClick={goBack}>{t("assistant.previous")}</button>{screen === "question" && pending?.required === false && <button type="button" disabled={busy || modelBlocked} className="assistant-text-button" onClick={() => void send("overslaan")}>{t("assistant.skip")}</button>}</div>
        {screen === "ready" ? <button type="button" disabled={busy || modelBlocked} className="assistant-primary" onClick={() => { onClose(); onReview?.(); }}>{t("assistant.done")}<ArrowRightIcon className="h-4 w-4" /></button>
          : <button type="button" disabled={busy || modelBlocked || !answer} className="assistant-primary" onClick={() => void send(answer)}>{t(screen === "describe" ? "assistant.start" : "assistant.next")}<ArrowRightIcon className="h-4 w-4" /></button>}
      </footer>
      </>}
      </>}
    </div>
  </div>, document.body);
}
