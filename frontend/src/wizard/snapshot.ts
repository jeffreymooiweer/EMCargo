/**
 * The wizard's state as one document, so a kept shipment can be reopened.
 *
 * The server stores this without reading it — it is the interface's own
 * shape, versioned by the interface. What goes in is the *source* state:
 * the lines as typed, the calculated result, the declared dangerous goods,
 * the document fields, the selection and the signature. Everything the
 * wizard derives from those (the advice, the profiles, the warnings) is
 * recomputed on open, so a snapshot never carries a stale judgement.
 *
 * Reading is defensive on purpose. A snapshot written by a later version
 * with a shape this one does not know, or a row somebody edited by hand,
 * must open as far as it can rather than crash the wizard: every field has
 * a fallback and the version is checked for a major break only.
 */
import type { CalcResult, DgEntry, DocumentEvidence } from "../api/client";
import type { DraftLine } from "../components/ReviewLinesPanel";

export const SNAPSHOT_VERSION = 1;

export interface WizardSnapshot {
  version: number;
  modality: string;
  stepKey: "lines" | "dg" | "details" | "export";
  /** The language the documents are drawn up in; null means the screen's. */
  docLang: string | null;
  /** null means "the advice decides". */
  selectedDocs: string[] | null;
  docValues: Record<string, string>;
  skippedQuestions: string[];
  draftLines: DraftLine[];
  nextId: number;
  result: CalcResult | null;
  dgEntries: DgEntry[];
  signature: string | null;
  documentEvidence?: DocumentEvidence[];
}

const STEPS = new Set(["lines", "dg", "details", "export"]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : [];
}

/** A snapshot from whatever was stored, or null when it is not one at all. */
export function readSnapshot(raw: unknown): WizardSnapshot | null {
  if (!isRecord(raw)) return null;
  const version = typeof raw.version === "number" ? raw.version : 0;
  if (version < 1 || version > SNAPSHOT_VERSION) return null;

  const draftLines = Array.isArray(raw.draftLines)
    ? (raw.draftLines.filter(isRecord) as unknown as DraftLine[])
    : [];
  const values: Record<string, string> = {};
  if (isRecord(raw.docValues)) {
    for (const [key, value] of Object.entries(raw.docValues)) {
      if (typeof value === "string") values[key] = value;
    }
  }
  const stepKey = typeof raw.stepKey === "string" && STEPS.has(raw.stepKey)
    ? (raw.stepKey as WizardSnapshot["stepKey"])
    : "lines";
  const lines: DraftLine[] = draftLines.length > 0
    ? draftLines
    : [{ id: 1, description: "", quantity: 1, unit: "pcs" }];
  // The next id must clear every line there is, including the blank one a
  // missing list falls back to — a duplicate id is two rows editing as one.
  const nextId = typeof raw.nextId === "number" && raw.nextId > 0
    ? raw.nextId
    : Math.max(0, ...lines.map((line) => Number(line.id) || 0)) + 1;

  return {
    version,
    modality: typeof raw.modality === "string" ? raw.modality : "",
    stepKey,
    docLang: typeof raw.docLang === "string" ? raw.docLang : null,
    selectedDocs: Array.isArray(raw.selectedDocs) ? strings(raw.selectedDocs) : null,
    docValues: values,
    skippedQuestions: strings(raw.skippedQuestions),
    draftLines: lines,
    nextId,
    result: isRecord(raw.result) && Array.isArray(raw.result.lines) ? (raw.result as unknown as CalcResult) : null,
    dgEntries: Array.isArray(raw.dgEntries) ? (raw.dgEntries.filter(isRecord) as unknown as DgEntry[]) : [],
    signature: typeof raw.signature === "string" && raw.signature ? raw.signature : null,
    ...(Array.isArray(raw.documentEvidence) ? { documentEvidence: raw.documentEvidence.filter((item): item is DocumentEvidence =>
      isRecord(item) && typeof item.name === "string" && typeof item.sha256 === "string" && typeof item.target === "string"
      && typeof item.value === "string" && typeof item.excerpt === "string" && item.excerpt.length <= 6000
      && ["text", "ocr", "corrected"].includes(String(item.method)) && Array.isArray(item.pages)
      && item.pages.every(page => typeof page === "number" && Number.isInteger(page) && page > 0 && page <= 10)).slice(0, 500) } : {}),
  };
}

/** The reference fields a new shipment must not inherit from the one it is
 *  made from: the wizard's own reference, and the carrier's numbers that
 *  belong to one booking. Everything else — parties, route, remarks — is
 *  exactly what a template is for. */
export const TEMPLATE_CLEARED_KEYS = new Set([
  "shipment_reference",
  "reference",
  "booking_number",
  "awb_number",
  "transport_document_number",
  "ens_mrn",
  "ens_ics2_reference",
  "aes_itn",
  "customs_mrn",
  "container_number",
  "container_uti_number",
  "seal_numbers",
  "vgm_reference",
  "vehicle_registration",
  "wagon_number",
]);

/** The details of a kept shipment as a new shipment starts with them: the
 *  identifying references and every date cleared, the rest kept. Dates are
 *  recognised by their key — they all end in `_date` — because the values
 *  are the only thing here, not the registry.
 *
 *  `confirmations` are the keys the registry marks as a declaration somebody
 *  signs for. They are cleared too, and that is not tidiness: a copy that
 *  arrives with last week's confirmation already ticked is a form declaring
 *  something about goods nobody has looked at. The caller passes them because
 *  only it has the registry. */
export function templateValues(
  values: Record<string, string>,
  confirmations: Iterable<string> = [],
): Record<string, string> {
  const signed = new Set(confirmations);
  const fresh: Record<string, string> = {};
  for (const [key, value] of Object.entries(values)) {
    if (TEMPLATE_CLEARED_KEYS.has(key) || key.endsWith("_date") || signed.has(key)) continue;
    fresh[key] = value;
  }
  return fresh;
}
