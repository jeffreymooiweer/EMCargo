import { AssistantState, DgEntry, LineItem, type DocumentEvidence } from "../api/client";
import { DraftLine } from "../components/ReviewLinesPanel";

/**
 * The wizard state as the assistant exchanges it — and back.
 *
 * The server is stateless: every turn the modal rebuilds the state from the
 * wizard, and everything the assistant wrote must land back in the wizard.
 * Whatever these two functions do not carry is silently forgotten between
 * turns. That is not theoretical: the skipped questions were not carried,
 * so every "skip" was forgotten the moment the next answer was sent — and
 * the same optional question came back after every turn, swallowing whatever
 * was typed as an answer to it.
 */
export function buildAssistantState(args: {
  modality: string;
  draftLines: DraftLine[];
  resultLines?: LineItem[];
  dgEntries: DgEntry[];
  docValues: Record<string, string>;
  selectedDocs: string[] | null;
  skippedQuestions: string[];
  documentEvidence?: DocumentEvidence[];
}): AssistantState {
  return {
    modality: args.modality,
    draft_lines: args.draftLines
      .filter((line) => line.description.trim())
      .map((line, index) => {
        const resultLine = args.resultLines?.find((r) => r.line_id === index + 1);
        return {
          id: line.id,
          description: line.description,
          quantity: line.quantity || 1,
          quantity_unconfirmed: line.quantity_unconfirmed,
          weight_basis: line.weight_basis,
          stated_weight_kg: line.stated_weight_kg,
          unconfirmed_weight_kg: line.unconfirmed_weight_kg,
          unit: line.unit,
          dangerous_goods: Boolean(line.dangerous_goods),
          dg_decision: line.dg_decision,
          confirmed_un: line.confirmed_un,
          dg_dismissed: line.dg_dismissed,
          detected_un_numbers: resultLine?.detected_un_numbers ?? [],
          dg_name_candidates: resultLine?.dg_name_candidates ?? [],
          // What the consignor stated themselves travels as their answer; the
          // computed weight travels beside it, never as an override.
          weight_each_kg: line.weight_each_kg === "" ? undefined : line.weight_each_kg,
          computed_weight_each_kg: resultLine?.weight_each_kg ?? undefined,
          length_cm: line.length_cm === "" ? undefined : line.length_cm,
          width_cm: line.width_cm === "" ? undefined : line.width_cm,
          height_cm: line.height_cm === "" ? undefined : line.height_cm,
          package_content: line.package_content ?? resultLine?.package_content ?? undefined,
        };
      }),
    // Draft ids survive deletions; calculation/DG ids are positions. Map
    // explicitly at this boundary so answers stay on the right goods.
    dg_entries: args.dgEntries.map(entry => ({ ...entry,
      line_id: args.draftLines.filter(line => line.description.trim())[entry.line_id - 1]?.id ?? entry.line_id,
    })),
    doc_values: args.docValues,
    selected_docs: args.selectedDocs,
    skipped_questions: args.skippedQuestions,
    ...(args.documentEvidence ? { document_evidence: args.documentEvidence } : {}),
  };
}

/** The assistant's draft lines mapped onto the wizard's own, merged by id so
 *  nothing the wizard holds beyond these fields is lost. */
export function draftLinesFromAssistant(
  state: AssistantState,
  current: DraftLine[],
): DraftLine[] | null {
  if (!Array.isArray(state.draft_lines)) return null;
  const byId = new Map(current.map((line) => [line.id, line]));
  return state.draft_lines.map((line) => ({
    ...(byId.get(Number(line.id)) ?? {}),
    id: Number(line.id),
    description: String(line.description ?? ""),
    quantity: line.quantity_unconfirmed ? "" : (line.quantity as number) ?? 1,
    quantity_unconfirmed: Boolean(line.quantity_unconfirmed),
    weight_basis: line.weight_basis as "each" | "total" | undefined,
    stated_weight_kg: line.stated_weight_kg as number | undefined,
    unconfirmed_weight_kg: line.unconfirmed_weight_kg as number | undefined,
    unit: String(line.unit ?? "pcs"),
    dangerous_goods: Boolean(line.dangerous_goods),
    confirmed_un: (line.confirmed_un as string) || undefined,
    dg_dismissed: Boolean(line.dg_dismissed) || undefined,
    // New assistant decisions take precedence; preserve an explicit manual
    // "other goods" answer when neither confirmation nor rejection replaced it.
    dg_decision: line.confirmed_un ? "confirmed" : line.dg_dismissed ? "rejected" : line.dg_decision === "other" ? "other" : undefined,
    package_content: (line.package_content as string) || undefined,
    // Measurements the assistant asked for land in the same columns the
    // lines table writes, so the classic wizard computes with them too.
    length_cm: (line.length_cm as number) ?? undefined,
    width_cm: (line.width_cm as number) ?? undefined,
    height_cm: (line.height_cm as number) ?? undefined,
    weight_each_kg: (line.weight_each_kg as number) ?? undefined,
  }));
}

/** Map assistant draft ids back to the calculation's non-empty positions. */
export function wizardDgEntriesFromAssistant(state: AssistantState): DgEntry[] {
  const lines = (state.draft_lines ?? []).filter(line => String(line.description ?? "").trim());
  return (state.dg_entries ?? []).flatMap(entry => {
    const index = lines.findIndex(line => Number(line.id) === entry.line_id);
    return index < 0 ? [] : [{ ...entry, line_id: index + 1 }];
  });
}

/** Preserve interview answers while rebuilding the wizard's DG step. */
export function retainAssistantDgAnswers(prepared: DgEntry[], answered: DgEntry[]): DgEntry[] {
  return prepared.map(entry => {
    const existing = answered.find(old => old.line_id === entry.line_id);
    if (!existing || existing.products[0]?.un_number !== entry.products[0]?.un_number) return entry;
    return { ...entry, ...existing, vehicle: entry.vehicle };
  });
}
