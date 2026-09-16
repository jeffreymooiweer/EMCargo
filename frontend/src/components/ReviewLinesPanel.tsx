import { PlusIcon, CopyIcon, TrashIcon, MoreIcon, ChevronDownIcon } from "./icons";
/**
 * A goods list with direct quantity editing and details on demand.
 * Successful lines show their result once; only exceptions and unanswered
 * substance questions add explanation. A compact row must never hide a safety
 * question, label an unanswered substance safe, or display a stale calculation
 * as current. Import has its own surface so it does not dominate every edit.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { LineItem, UnitCatalogue, api, ArticleRef, EquipmentSnapshot } from "../api/client";
import EquipmentCombobox from "./EquipmentCombobox";
import { equipmentPatch } from "../utils/equipment";
import EquipmentPicker from "./EquipmentPicker";
import EquipmentLineFields from "./EquipmentLineFields";
import GoodsImport from "./GoodsImport";
import LineDetails, { ROUND_TYPES, WALL_PROFILE_TYPES, isDangerous } from "./LineDetails";
import NumberInput from "./NumberInput";
import UnitSelect from "./UnitSelect";

export interface DraftLine {
  equipment?: EquipmentSnapshot;
  equipment_role?: "cargo" | "container";
  container_line_id?: number;
  id: number;
  description: string;
  quantity: number | "";
  /** The assistant must ask when the description omitted the count. */
  quantity_unconfirmed?: boolean;
  weight_basis?: "each" | "total";
  stated_weight_kg?: number;
  weight_total_kg?: number | "";
  unconfirmed_weight_kg?: number;
  unit: string;
  /** The form this commodity travels in: solid, stacked, loose bulk. Determines
   *  how much of a cubic metre is actually material. */
  cargo_form?: string;
  /** Wall thickness in millimetres. Only meaningful with a cross-section that
   *  has a wall — an angle or a hollow section. For a plate or a beam the three
   *  outside measurements already describe the material completely. */
  wall_thickness_mm?: number | "";
  /** Dimensions the user fills in themselves, in centimetres. They no longer
   *  have to be hidden in the description to count. */
  length_cm?: number | "";
  width_cm?: number | "";
  height_cm?: number | "";
  dangerous_goods?: boolean;
  /** UN number the user confirmed from a name suggestion. Carries through to
   *  the DG step so nothing recognised has to be typed again. */
  confirmed_un?: string;
  /** The suggestion was rejected for this line; it must not come back. Kept
   *  because the assistant and older saved shipments speak it; what the screen
   *  reads is ``dg_decision``, which this maps onto. */
  dg_dismissed?: boolean;
  /** What the user answered to the substance recognition: they took the
   *  suggested UN number, they said it is a different substance, or they said
   *  the suggestion is wrong. Undefined means nobody has answered yet — which
   *  is not the same as "no", and is why closing something cannot set it. */
  dg_decision?: "confirmed" | "other" | "rejected";
  /** Net content of one package as the description said it ("25 L"); the DG
   *  derivation fills the per-package quantity from it. */
  package_content?: string;
  /**
   * The substance's identity, stated on the line it is about.
   *
   * Until v1.203.0 these lived only on the dangerous-goods step, which meant
   * the goods step recognised UN 1203 on a line and then the next step asked
   * what the substance was — the same question, one step further on. They are
   * answered here now and seeded into the step's product, so the step is left
   * with what it is actually for: the assessment.
   *
   * The class is deliberately not among them. It follows from the UN number
   * through Table A, and a field for it is an invitation to state something
   * the tables will contradict.
   */
  proper_shipping_name?: string;
  packing_group?: string;
  type_of_package?: string;
  /** The library article this line was picked from, if any. Its UN number
   *  travels as `confirmed_un`; the rest seeds the DG product. */
  article?: ArticleRef;
  /** Weight of one item or package the consignor stated themselves, for goods
   *  the catalogue cannot weigh. Never a computed value. */
  weight_each_kg?: number | "";
}

interface Props {
  draftLines: DraftLine[];
  resultLines?: LineItem[];
  onDraftChange: (lines: DraftLine[]) => void;
  onRemoveLine: (id: number) => void;
  onDuplicateLine: (id: number) => void;
  onAddLine: () => void;
  onChooseEquipment?: (item: EquipmentSnapshot) => void;
  onImport?: (text: string, mode: "append" | "replace") => void;
  onLineWeightChange?: (lineId: number, field: "weight_each_kg" | "weight_total_kg", value: number | null) => void;
  initialPaste?: boolean;
  translateMessage: (msg: string) => string;
}

/** What was answered to a line's substance question, if anything.
 *
 *  ``dg_decision`` is what the screen writes. The two older fields are read as
 *  well, so a shipment saved before v1.195.0 — or one the assistant filled in —
 *  opens with its answers intact rather than asking everything again. */
function decisionOf(line: DraftLine): DraftLine["dg_decision"] | undefined {
  if (line.dg_decision) return line.dg_decision;
  if (line.confirmed_un) return "confirmed";
  if (line.dg_dismissed) return "rejected";
  return undefined;
}

/** Whether this line is still waiting for an answer about its substance. */
export function hasOpenQuestion(line: DraftLine, item: LineItem | null | undefined): boolean {
  return !!item && (item.dg_name_candidates?.length ?? 0) > 0 && !decisionOf(line);
}

/** How many lines are still waiting, for whoever has to say so elsewhere. */
export function openQuestions(lines: DraftLine[], items?: LineItem[]): number {
  return lines.filter((line, index) => hasOpenQuestion(line, items?.[index])).length;
}

/** A line the calculation could not settle: no weight came out, or it wants
 *  looking at. These are what the filter above the list narrows to. */
function needsAttention(item: LineItem | null): boolean {
  return !!item && item.status !== "ok";
}

/** What a line's derived figures were computed from. Two lines with the same
 *  signature have the same answer; a line whose signature moved has none yet. */
function signatureOf(line: DraftLine): string {
  return JSON.stringify([
    line.equipment, line.equipment_role, line.container_line_id,
    line.description.trim(), line.quantity, line.unit, line.cargo_form ?? "",
    line.length_cm ?? "", line.width_cm ?? "", line.height_cm ?? "", line.wall_thickness_mm ?? "",
  ]);
}

function DetailsIcon({ open }: { open: boolean }) {
  return <ChevronDownIcon className={`h-4 w-4 transition-transform motion-reduce:transition-none ${open ? "rotate-180" : ""}`} />;
}

export default function ReviewLinesPanel({
  draftLines,
  resultLines,
  onDraftChange,
  onRemoveLine,
  onDuplicateLine,
  onAddLine,
  onImport,
  onChooseEquipment,
  onLineWeightChange,
  translateMessage,
  initialPaste,
}: Props) {
  const { t, i18n } = useTranslation();
  const [pickerOpen, setPickerOpen] = useState(false);
  const number = new Intl.NumberFormat(i18n.language, { maximumFractionDigits: 3 });
  const canRemove = draftLines.length > 1;

  // Which line is open, by id rather than by index: a line can be removed or
  // duplicated while it stands open, and an index would then quietly point at
  // another line.
  //
  // One at a time. The panel is a screenful of fields, and two of them open
  // means the row you are comparing against has scrolled off — which is the
  // problem the dialog had, in a different shape.
  const [openId, setOpenId] = useState<number | null>(null);
  // A file dropped on the panel, handed to the import; and whether something is
  // being dragged over it, so the panel can say it will take it.
  const [dropped, setDropped] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  // Fifty imported lines with one that needs looking at is fifty cards of
  // scrolling to find it. This narrows the list to those, and says how many.
  const [onlyAttention, setOnlyAttention] = useState(false);
  const hasLines = draftLines.some((line) => line.description.trim());

  const updateDraft = (id: number, patch: Partial<DraftLine>) => {
    onDraftChange(draftLines.map((line) => (line.id === id ? { ...line, ...patch } : line)));
  };

  /**
   * The name recognition, answered on the line it is about.
   *
   * It used to be a snackbar: a question that floated at the bottom right of
   * the screen, away from the line it was about, and whose close button was an
   * answer. That last part is what made it wrong. Closing something is not a
   * decision — but the × set ``dg_dismissed``, so "not now" was stored as "not
   * this substance", and the line then showed no trace of the question at all.
   * The decision could not be found again, let alone revised, which the
   * baseline recorded as a task that cannot be completed.
   *
   * Here the question sits under its own line, with three answers spelled out:
   * take the UN number, say it is a different substance, or say the suggestion
   * is wrong. Rejecting one candidate says nothing about whether the goods are
   * dangerous — it says this suggestion is not them — so it touches neither the
   * dangerous-goods tick nor anything the compliance check reads. An answer can
   * be changed afterwards, because the line keeps saying what was answered.
   */
  const answer = (line: DraftLine, patch: Partial<DraftLine>) => updateDraft(line.id, patch);

  // The unit catalogue comes from the backend, so the list is maintained in one
  // place. If that fails, UnitSelect falls back to a text field and the step
  // stays usable.
  const [catalogue, setCatalogue] = useState<UnitCatalogue | null>(null);
  useEffect(() => {
    let alive = true;
    api.unitCatalogue()
      .then((result) => alive && setCatalogue(result))
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, []);

  // What was last worked out per line, and for which text. Kept so that the
  // figures do not blink away on every keystroke; only shown for a line whose
  // own signature has not moved since.
  const computed = useRef(new Map<number, { signature: string; item: LineItem }>());
  if (resultLines && resultLines.length > 0) {
    const next = new Map<number, { signature: string; item: LineItem }>();
    draftLines.forEach((line, index) => {
      const item = resultLines[index];
      if (item) next.set(line.id, { signature: signatureOf(line), item });
    });
    computed.current = next;
  }

  function outcomeFor(line: DraftLine, index: number): { item: LineItem | null; stale: boolean } {
    const fresh = resultLines?.[index];
    if (fresh) return { item: fresh, stale: false };
    const remembered = computed.current.get(line.id);
    if (remembered && remembered.signature === signatureOf(line)) {
      return { item: remembered.item, stale: true };
    }
    return { item: null, stale: true };
  }

  // A new line gets the cursor. Detected here rather than passed in, because
  // adding is the wizard's action and focusing is this panel's business: the
  // one id that was not there a render ago is the one to type in.
  const seen = useRef<number[]>(draftLines.map((line) => line.id));
  const inputs = useRef(new Map<number, HTMLInputElement>());
  useEffect(() => {
    const ids = draftLines.map((line) => line.id);
    const added = ids.filter((id) => !seen.current.includes(id));
    seen.current = ids;
    // Exactly one new line is somebody adding or duplicating one. A handful at
    // once is an import, and an import should not drag the page to its last row.
    if (added.length === 1 && !draftLines.find(line => line.id === added[0])?.equipment) {
      const input = inputs.current.get(added[0]);
      input?.focus();
      // jsdom has no layout, so it has no scrollIntoView either.
      input?.scrollIntoView?.({ block: "nearest" });
    }
  }, [draftLines]);

  function onFieldKeyDown(event: React.KeyboardEvent, index: number) {
    if (event.key !== "Enter") return;
    event.preventDefault();
    if (index === draftLines.length - 1) {
      onAddLine();
      return;
    }
    inputs.current.get(draftLines[index + 1].id)?.focus();
  }

  // How the calculation judged the lines, for the summary above the list. A
  // line still being rechecked is neither settled nor a problem yet.
  const { settled, attention, unanswered } = useMemo(() => {
    let settledCount = 0;
    let attentionCount = 0;
    let unansweredCount = 0;
    draftLines.forEach((line, index) => {
      const { item, stale } = outcomeFor(line, index);
      if (!item || stale) return;
      settledCount += 1;
      if (needsAttention(item)) attentionCount += 1;
      if (hasOpenQuestion(line, item)) unansweredCount += 1;
    });
    return { settled: settledCount, attention: attentionCount, unanswered: unansweredCount };
    // outcomeFor reads the refs, which change with the results.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftLines, resultLines]);

  // Nothing to narrow to any more: leaving the filter on would show an empty
  // list and look like the lines had gone.
  useEffect(() => {
    if (attention + unanswered === 0 && onlyAttention) setOnlyAttention(false);
  }, [attention, unanswered, onlyAttention]);


  return (
    <section
      aria-label={t("review.linesTitle")}
      className={"goods-panel" + (dragging ? " goods-dragging" : "")}
      onDragOver={onImport ? (event) => {
        if (!event.dataTransfer.types.includes("Files")) return;
        event.preventDefault(); setDragging(true);
      } : undefined}
      onDragLeave={onImport ? (event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node)) setDragging(false);
      } : undefined}
      onDrop={onImport ? (event) => {
        const file = event.dataTransfer.files?.[0];
        if (!file) return;
        event.preventDefault(); setDragging(false); setDropped(file);
      } : undefined}
    >
      <div className="goods-heading">
        <h3>{t("review.linesTitle")}</h3>
        {onChooseEquipment && <button type="button" className="action-secondary" onClick={() => setPickerOpen(true)}>{t("assets.choose")}</button>}
        {pickerOpen && onChooseEquipment && <EquipmentPicker onClose={() => setPickerOpen(false)} onPick={item => { onChooseEquipment(item); setPickerOpen(false); }} />}
        {onImport && <GoodsImport initialPaste={initialPaste} hasLines={hasLines} onImport={onImport}
          dropped={dropped} onDroppedHandled={() => setDropped(null)} />}
      </div>
      {!hasLines && <p className="goods-empty-hint">{t("review.simpleIntro")}</p>}
      {dragging && <p className="goods-drop-hint">{t("review.importDrop")}</p>}
      {draftLines.length > 1 && attention + unanswered > 0 && (
        <div className="goods-attention">
          <span>{t("review.attentionSummary", { ok: settled - attention, attention })}
            {unanswered > 0 && ` · ${t("review.unansweredSummary", { count: unanswered })}`}</span>
          <button type="button" onClick={() => setOnlyAttention((on) => !on)}>
            {onlyAttention ? t("review.showAllLines") : t("review.onlyAttention")}
          </button>
        </div>
      )}
      <ul className="goods-list">
        {draftLines.map((line, index) => {
          const { item, stale } = outcomeFor(line, index);
          if (onlyAttention && !needsAttention(item) && !hasOpenQuestion(line, item)) return null;
          const open = openId === line.id;
          const panelId = `line-panel-${line.id}`;
          const decision = decisionOf(line);
          const dgLabel = line.confirmed_un ? `UN ${line.confirmed_un}`
            : decision === "other" ? t("review.dgIdentityNeeded")
            : decision === "rejected" ? [isDangerous(line, item) ? t("review.dgMarked") : "", t("review.dgCandidateRejected")].filter(Boolean).join(" · ")
            : isDangerous(line, item) && !hasOpenQuestion(line, item) ? t("review.dgMarked") : null;
          return (
            <li key={line.id} className={"goods-row" + (open ? " goods-row-open" : "")}
              data-empty={!line.description.trim()}>
              <div className="goods-fields">
                <div className="goods-description">
                  <label className="goods-field-label" htmlFor={`goods-description-${line.id}`}>{t("wizard.stageGoods")}</label>
                  <EquipmentCombobox id={`goods-description-${line.id}`} value={line.description}
                    placeholder={t("review.simplePlaceholder")}
                    onChange={(value, selected) => updateDraft(line.id, selected ? equipmentPatch(selected) : { description: value, ...(line.equipment ? { equipment: undefined, equipment_role: undefined, length_cm: undefined, width_cm: undefined, height_cm: undefined, weight_each_kg: undefined, weight_total_kg: undefined } : {}) })}
                    inputRef={(element) => {
                      if (element) inputs.current.set(line.id, element);
                      else inputs.current.delete(line.id);
                    }}
                    onKeyDown={(event) => onFieldKeyDown(event, index)}
                    aria-label={t("review.descriptionOfLine", { number: index + 1 })} />
                </div>
                <label className="goods-quantity-field">
                  <span className="goods-field-label">{t("review.quantity")}</span>
                  <NumberInput className="goods-number" inputMode="decimal" value={line.quantity}
                    aria-label={t("review.quantityOfLine", { number: index + 1 })}
                    onKeyDown={(event) => onFieldKeyDown(event, index)}
                    onChange={(event) => updateDraft(line.id, {
                      quantity: event.target.value === "" ? "" : Number(event.target.value),
                    })} />
                </label>
                <div className="goods-unit-field">
                  <label className="goods-field-label" htmlFor={`goods-unit-${line.id}`}>{t("review.unit")}</label>
                  <UnitSelect id={`goods-unit-${line.id}`} value={line.unit}
                    onChange={(unit) => updateDraft(line.id, { unit })}
                    category={item?.material_category} catalogue={catalogue} className="goods-unit-input"
                    aria-label={t("review.unitOfLine", { number: index + 1 })} />
                </div>
                <div className={"goods-weight" + (stale ? " goods-weight-pending" : "")}>
                  <span className="goods-field-label">{t("review.weightTotal")}</span>
                  <div>{item?.weight_total_kg != null
                    ? <><span>{number.format(item.weight_total_kg)}</span><span className="goods-weight-unit"> kg</span></>
                    : <span>—</span>}</div>
                </div>
                <details className="goods-menu" onKeyDown={(event) => {
                  if (event.key === "Escape") { event.currentTarget.open = false; event.currentTarget.querySelector("summary")?.focus(); }
                }}>
                  <summary aria-label={t("review.moreActions")}><MoreIcon /></summary>
                  <div className="goods-menu-options">
                    <button type="button" onClick={(event) => { event.currentTarget.closest("details")?.removeAttribute("open"); onDuplicateLine(line.id); }}><CopyIcon />{t("review.duplicateLine")}</button>
                    <button type="button" disabled={!canRemove} onClick={(event) => { event.currentTarget.closest("details")?.removeAttribute("open"); onRemoveLine(line.id); }}><TrashIcon />{t("review.removeLine")}</button>
                  </div>
                </details>
              </div>
              <div className="goods-row-meta">
                <div className="goods-row-state">
                  {stale && line.description.trim() && <span className="goods-pending">{t("review.toBeRechecked")}</span>}
                  {!stale && item && item.status !== "ok" && <span className="goods-problem">{t(`status.${item.status}` as "status.ok")}</span>}
                  {dgLabel && <span className={isDangerous(line, item) ? "goods-substance" : "goods-decision"}>{dgLabel}</span>}
                </div>
                <button type="button" className="goods-details" onClick={() => setOpenId(open ? null : line.id)}
                  aria-expanded={open} aria-controls={panelId}
                  aria-label={open ? t("review.closeDetails") : isDangerous(line, item) ? t("review.lineDetailsDg") : t("review.lineDetails")}>
                  {t("review.lineDetails")}<DetailsIcon open={open} />
                </button>
              </div>
              <EquipmentLineFields line={line} lines={draftLines} result={item} onChange={(patch) => updateDraft(line.id, patch)} />
              <Derived line={line} item={item} stale={stale} expanded={open} translateMessage={translateMessage} />
              <SubstanceQuestion line={line} item={item} expanded={open} onAnswer={(patch) => answer(line, patch)} />
              {open && <LineDetails line={line} result={item} position={index + 1} catalogue={catalogue} id={panelId}
                onChange={(patch) => updateDraft(line.id, patch)}
                onWeightChange={onLineWeightChange && item
                  ? (weightField, value) => onLineWeightChange(item.line_id, weightField, value) : undefined} />}
            </li>
          );
        })}
      </ul>
      <button type="button" onClick={onAddLine} className="goods-add"><PlusIcon />{t("review.addLine")}</button>
    </section>
  );
}

/**
 * The substance question, on the line it is about.
 *
 * Three answers, each said in words. **Take UN 1203** ticks the line as
 * dangerous goods and carries the number to the dangerous goods step. **A
 * different substance** ticks it too but leaves the number to that step, where
 * a substance is actually established. **The suggestion is wrong** rejects the
 * candidate and nothing else: it does not say the goods are safe, and it leaves
 * the dangerous-goods tick exactly as the user left it.
 *
 * An answered line says what was answered, with a way back to the question. A
 * decision you cannot find again is a decision you cannot check.
 */
function SubstanceQuestion({ line, item, expanded, onAnswer }: {
  expanded: boolean;
  line: DraftLine;
  item: LineItem | null;
  onAnswer: (patch: Partial<DraftLine>) => void;
}) {
  const { t } = useTranslation();
  const candidates = item?.dg_name_candidates ?? [];
  if (candidates.length === 0) return null;
  const decision = decisionOf(line);

  const chip = "min-h-[44px] rounded-lg border px-2.5 py-2 text-xs font-medium transition-colors";

  if (decision) {
    if (!expanded) return null;
    const said = decision === "confirmed"
      ? t("review.dgAnsweredConfirmed", { un: line.confirmed_un ?? candidates[0].un })
      : decision === "other"
        ? t("review.dgAnsweredOther")
        : t("review.dgAnsweredRejected");
    return (
      <div className="goods-answer">
        <span className="text-xs text-slate-500 dark:text-slate-400">{said}</span>
        <button
          type="button"
          onClick={() => onAnswer({ dg_decision: undefined, dg_dismissed: undefined, confirmed_un: undefined })}
          className="text-xs font-medium text-brand-700 underline-offset-2 hover:underline dark:text-brand-300"
        >
          {t("review.dgChangeAnswer")}
        </button>
      </div>
    );
  }

  return (
    <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 dark:border-amber-900/50 dark:bg-amber-950/30">
      <p className="text-xs text-amber-900 dark:text-amber-200">
        {candidates.length === 1
          ? t("review.dgAskOne", {
              un: candidates[0].un, class: candidates[0].class, name: candidates[0].name,
            })
          : t("review.dgAskMany")}
      </p>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {candidates.slice(0, 3).map((candidate) => (
          <button
            key={candidate.un}
            type="button"
            onClick={() => onAnswer({
              dangerous_goods: true, confirmed_un: candidate.un, dg_decision: "confirmed",
              dg_dismissed: undefined,
            })}
            className={`${chip} border-amber-300 bg-white text-amber-900 hover:bg-amber-100 dark:border-amber-800 dark:bg-slate-900 dark:text-amber-200`}
            title={candidates.length > 1 ? candidate.name : undefined}
          >
            {t("review.dgTake", { un: candidate.un })}
            {candidates.length > 1 && <span className="block text-left font-normal">{candidate.name}</span>}
          </button>
        ))}
        <button
          type="button"
          onClick={() => onAnswer({ dangerous_goods: true, dg_decision: "other", dg_dismissed: undefined })}
          className={`${chip} border-amber-300 text-amber-900 hover:bg-amber-100 dark:border-amber-800 dark:text-amber-200`}
        >
          {t("review.dgOther")}
        </button>
        <button
          type="button"
          onClick={() => onAnswer({ dg_decision: "rejected", dg_dismissed: true })}
          className={`${chip} border-amber-300 text-amber-900 hover:bg-amber-100 dark:border-amber-800 dark:text-amber-200`}
        >
          {t("review.dgWrong")}
        </button>
      </div>
      <p className="mt-1.5 text-[11px] text-amber-800 dark:text-amber-300">{t("review.dgWrongHint")}</p>
    </div>
  );
}

/**
 * Under the row: what was worked out and what is worth knowing about the line,
 * as text rather than as fields. Supporting dimensions and per-item figures
 * belong with Details; actionable messages stay on the collapsed line.
 */
function Derived({ line, item, stale, expanded, translateMessage }: {
  expanded: boolean;
  line: DraftLine;
  item: LineItem | null;
  stale: boolean;
  initialPaste?: boolean;
  translateMessage: (msg: string) => string;
}) {
  const { t } = useTranslation();
  const parts: string[] = [];

  const measure = (field: "length_cm" | "width_cm" | "height_cm") => {
    const own = line[field];
    if (own !== undefined && own !== "") return own;
    return item?.[field] ?? null;
  };
  const round = ROUND_TYPES.has(item?.product_type ?? "");
  const length = measure("length_cm");
  const width = measure("width_cm");
  const height = round ? null : measure("height_cm");
  if (length != null || width != null || height != null) {
    const show = (value: number | null) => (value == null ? "?" : String(value));
    parts.push(round
      ? `${show(length)} × ⌀ ${show(width)} cm`
      : `${[length, width, height].map(show).join(" × ")} cm`);
  }
  if (item?.weight_each_kg != null) parts.push(`${item.weight_each_kg} kg/${t("review.each")}`);
  if (item?.transport_volume_m3 != null) parts.push(`${item.transport_volume_m3.toFixed(3)} m³`);
  const form = line.cargo_form ?? item?.cargo_form;
  if (form) parts.push(t(`forms.${form}`, form));
  const type = item?.product_type;
  if (type && WALL_PROFILE_TYPES.has(type) && line.wall_thickness_mm !== undefined && line.wall_thickness_mm !== "") {
    parts.push(`${line.wall_thickness_mm} mm`);
  }

  const messages = item?.messages ?? [];
  if (!expanded && messages.length === 0) return null;
  return (
    <div className="goods-derived">
      {expanded && parts.length > 0 && <span className={stale ? "goods-pending" : undefined}>{parts.join(" · ")}</span>}
      {expanded && line.article?.code && <span>{line.article.code}</span>}
      {messages.length > 0 && <span className="goods-problem">{messages.map(translateMessage).join(", ")}</span>}
    </div>
  );
}

export function draftToText(lines: DraftLine[]): string {
  return lines
    .filter((l) => l.description.trim())
    .map((l) => `${l.description.trim()} | ${l.quantity || 1} | ${l.unit || "stuks"}`)
    .join("\n");
}

export function textToDraftLines(text: string, startId = 1): DraftLine[] {
  const rows = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (rows.length === 0) return [{ id: startId, description: "", quantity: 1, unit: "stuks" }];
  return rows.map((row, i) => {
    const parts = row.split(/[|\t]/).map((p) => p.trim());
    return {
      id: startId + i,
      description: parts[0] || row,
      quantity: parts[1] ? Number(parts[1]) || 1 : 1,
      unit: parts[2] || "stuks",
    };
  });
}
