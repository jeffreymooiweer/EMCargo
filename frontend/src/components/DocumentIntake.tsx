import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type AssistantState, type DocumentEvidence, type PackingField, type PackingGood, type PackingSource } from "../api/client";
import { ArrowRightIcon, CheckIcon, ImportIcon } from "./icons";
import "./DocumentIntake.css";

type Good = PackingGood & { picked: boolean; count: string; mass: string; length: string; width: string; height: string };
type Fact = PackingField & { picked: boolean };
const numeric = (value: string) => /^\d+(?:[.,]\d+)?$/.test(value.trim()) ? Number(value.replace(",", ".")) : NaN;
const goodRow = (good: PackingGood): Good => ({ ...good, picked: true,
  count: good.quantity == null ? "" : String(good.quantity), mass: good.weight_kg == null ? "" : String(good.weight_kg),
  length: good.dimensions_cm ? String(good.dimensions_cm.length_cm) : "",
  width: good.dimensions_cm ? String(good.dimensions_cm.width_cm) : "",
  height: good.dimensions_cm ? String(good.dimensions_cm.height_cm) : "" });

export function documentChunks(source: PackingSource): { id: string; text: string }[][] {
  const chunks: { id: string; text: string }[][] = [];
  const lines = source.pages.flatMap(page => page.lines);
  if (lines.length > 1200 || lines.reduce((total, line) => total + line.text.length, 0) > 40000) throw new Error("intake.longLine");
  let chunk: { id: string; text: string }[] = [], size = 0;
  for (const page of source.pages) for (const line of page.lines) {
    if (!line.text.trim()) continue;
    const length = line.text.length + line.id.length;
    if (length > 2800) throw new Error("intake.longLine");
    if (chunk.length && (size + length > 2800 || chunk.length === 4)) { chunks.push(chunk); chunk = []; size = 0; }
    chunk.push({ id: line.id, text: line.text }); size += length;
  }
  if (chunk.length) chunks.push(chunk);
  return chunks;
}

function withColumnHeader(source: PackingSource, chunk: { id: string; text: string }[]) {
  const lines = source.pages.flatMap(page => page.lines);
  const start = lines.findIndex(line => line.id === chunk[0].id);
  const header = lines.slice(0, start).reverse().find(line => line.text.length <= 500
    && !/\d/.test(line.text)
    && /description|omschrijving|beschrijving|bezeichnung|désignation|artikel|article/i.test(line.text)
    && /quantity|qty|aantal|anzahl|quantité|gewicht|weight|poids|masse|\bkg\b/i.test(line.text));
  return header ? [{ id: header.id, text: header.text }, ...chunk] : chunk;
}

export function applyPackingProposal(base: AssistantState, source: PackingSource, goods: Good[], fields: Fact[]): AssistantState {
  const state = JSON.parse(JSON.stringify(base)) as AssistantState;
  const evidence = [...(state.document_evidence ?? [])];
  const proof = (item: PackingGood | PackingField, target: string, value: string): DocumentEvidence => {
    const pages = source.pages.filter(page => page.lines.some(line => item.source_ids.includes(line.id)));
    return { name: source.name, sha256: source.sha256, pages: pages.map(page => page.number), excerpt: item.excerpt,
      method: pages.some(page => page.corrected) ? "corrected" : pages.some(page => page.method === "ocr") ? "ocr" : "text", target, value };
  };
  const lines = [...(state.draft_lines ?? [])];
  let id = Math.max(0, ...lines.map(line => Number(line.id) || 0)) + 1;
  for (const row of goods.filter(item => item.picked)) {
    const quantity = row.count.trim() ? numeric(row.count) : undefined;
    const mass = row.mass.trim() ? numeric(row.mass) : undefined;
    const dimensions = [row.length, row.width, row.height];
    if (!row.description.trim() || !row.unit || (quantity !== undefined && (!Number.isFinite(quantity) || quantity <= 0))
        || (mass !== undefined && (!Number.isFinite(mass) || mass <= 0 || row.weight_basis === "unknown"))
        || (dimensions.some(Boolean) && !dimensions.every(value => Number.isFinite(numeric(value)) && numeric(value) > 0))) {
      throw new Error("intake.checkValues");
    }
    const line: Record<string, unknown> = { id, description: row.description.trim(), unit: row.unit,
      quantity, quantity_unconfirmed: quantity === undefined };
    if (mass !== undefined) {
      line.weight_basis = row.weight_basis;
      line.stated_weight_kg = mass;
      if (row.weight_basis === "each") line.weight_each_kg = mass;
      else if (quantity) { line.weight_each_kg = mass / quantity; line.weight_total_kg = mass; }
    }
    if (dimensions.every(Boolean)) {
      line.length_cm = numeric(row.length); line.width_cm = numeric(row.width); line.height_cm = numeric(row.height);
    }
    lines.push(line);
    evidence.push(proof(row, `goods:${id}`, [row.description, row.count, row.unit,
      mass === undefined ? "" : `${mass} kg (${row.weight_basis})`, dimensions.every(Boolean) ? `${dimensions.join(" × ")} cm` : ""].filter(Boolean).join(" · ")));
    id += 1;
  }
  state.draft_lines = lines;
  state.doc_values = { ...state.doc_values };
  for (const field of fields.filter(item => item.picked && item.value.trim())) {
    state.doc_values[field.key] = field.value.trim();
    evidence.push(proof(field, field.key, field.value.trim()));
  }
  if (evidence.length > 500) throw new Error("intake.tooManyFacts");
  state.document_evidence = evidence;
  return state;
}

export default function DocumentIntake({ state, language, onAccept, onCancel }: {
  state: AssistantState; language: string; onAccept: (state: AssistantState) => Promise<boolean>; onCancel: () => void;
}) {
  const { t } = useTranslation();
  const [source, setSource] = useState<PackingSource | null>(null);
  const [pageIndex, setPageIndex] = useState(0);
  const [goods, setGoods] = useState<Good[]>([]);
  const [fields, setFields] = useState<Fact[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [stage, setStage] = useState<"choose" | "source" | "proposal">("choose");
  const [busy, setBusy] = useState(false);
  const [applying, setApplying] = useState(false);
  const [progress, setProgress] = useState("");
  const [failure, setFailure] = useState("");
  const [units, setUnits] = useState<string[]>([]);
  const controller = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const fileInput = useRef<HTMLInputElement>(null);
  useEffect(() => {
    let alive = true;
    void api.unitCatalogue().then(result => { if (alive) setUnits(result.units.map(unit => unit.code)); }).catch(() => {});
    return () => { alive = false; ++generation.current; controller.current?.abort(); };
  }, []);

  const message = (cause: unknown) => cause instanceof Error && cause.message.startsWith("intake.")
    ? t(cause.message) : String(cause);
  async function prepare(value: PackingSource, current: number, signal: AbortSignal) {
    const chunks = documentChunks(value);
    if (!chunks.length) throw new Error("intake.noReadableText");
    const nextGoods: PackingGood[] = [], nextFields: PackingField[] = [], notices: string[] = [];
    for (let index = 0; index < chunks.length; index++) {
      if (generation.current !== current) return;
      setProgress(t("intake.proposing", { current: index + 1, total: chunks.length }));
      const result = await api.proposePackingDocument(withColumnHeader(value, chunks[index]), signal);
      nextGoods.push(...result.goods); nextFields.push(...result.fields); notices.push(...result.warnings);
    }
    if (generation.current !== current) return;
    const uniqueFields = nextFields.filter((field, index) => nextFields.findIndex(other => other.key === field.key && other.value === field.value) === index);
    setGoods(nextGoods.map(goodRow));
    setFields(uniqueFields.map(field => ({ ...field, picked: !state.doc_values?.[field.key]
      && uniqueFields.filter(other => other.key === field.key).length === 1 })));
    setWarnings([...new Set(notices)]); setStage("proposal");
  }
  async function read(file: File) {
    controller.current?.abort();
    const current = ++generation.current;
    const request = new AbortController(); controller.current = request;
    setFailure(""); setBusy(true); setProgress(t("intake.reading"));
    setSource(null); setGoods([]); setFields([]); setPageIndex(0); setStage("source");
    try {
      const value = await api.readPackingDocument(file, language, request.signal);
      if (generation.current !== current) return;
      setSource(value);
      await prepare(value, current, request.signal);
    } catch (cause) { if (generation.current === current) setFailure(message(cause)); }
    finally { if (generation.current === current) setBusy(false); }
  }
  async function retry() {
    if (!source || busy) return;
    const current = ++generation.current;
    const request = new AbortController(); controller.current = request;
    setBusy(true); setFailure("");
    try { await prepare(source, current, request.signal); }
    catch (cause) { if (generation.current === current) setFailure(message(cause)); }
    finally { if (generation.current === current) setBusy(false); }
  }
  async function accept() {
    if (!source || busy) return;
    setFailure("");
    try {
      const accepted = applyPackingProposal(state, source, goods, fields);
      setBusy(true); setApplying(true); setProgress(t("intake.applying"));
      const ok = await onAccept(accepted);
      if (!ok) setFailure(t("intake.applyFailed"));
    } catch (cause) { setFailure(message(cause)); }
    finally { setBusy(false); setApplying(false); }
  }
  function changeGood(index: number, update: Partial<Good>) { setGoods(values => values.map((value, i) => i === index ? { ...value, ...update } : value)); }
  function showSource(ids: string[]) {
    const index = source?.pages.findIndex(page => page.lines.some(line => ids.includes(line.id))) ?? -1;
    if (index >= 0) setPageIndex(index);
    document.getElementById("intake-source")?.scrollIntoView?.({ behavior: "auto", block: "nearest" });
  }
  const page = source?.pages[pageIndex];
  const acceptedCount = goods.filter(row => row.picked).length + fields.filter(field => field.picked).length;
  const proof = (item: PackingGood | PackingField) => <details className="intake-proof"><summary onClick={() => showSource(item.source_ids)}>{t("intake.source")}</summary><blockquote>{item.excerpt}</blockquote></details>;

  return <div className="document-intake">
    <header className="intake-heading"><div><p className="assistant-eyebrow">{t("intake.eyebrow")}</p><h3>{t("intake.title")}</h3><p>{t("intake.intro")}</p></div>
      <button type="button" className="assistant-secondary" disabled={busy} onClick={() => fileInput.current?.click()}><ImportIcon />{t(source ? "intake.otherFile" : "intake.choose")}</button>
      <input ref={fileInput} type="file" accept="application/pdf,image/jpeg,image/png,.pdf,.jpg,.jpeg,.png" className="sr-only" aria-label={t("intake.choose")}
        onChange={event => { const file = event.target.files?.[0]; event.target.value = ""; if (file) void read(file); }} />
    </header>
    {stage === "choose" && <div className="intake-drop"><ImportIcon /><p>{t("intake.formats")}</p><span>{t("intake.local")}</span></div>}
    {source && <div className="intake-layout">
      <aside className="intake-source" id="intake-source"><div className="intake-page-select"><strong>{source.name}</strong>
        <select aria-label={t("intake.page")} value={pageIndex} onChange={event => setPageIndex(Number(event.target.value))}>
          {source.pages.map((entry, index) => <option key={entry.number} value={index}>{t("intake.pageNumber", { number: entry.number })}</option>)}
        </select></div>
        {page && <><img src={page.preview} alt={t("intake.pageNumber", { number: page.number })} />
          {page.warnings.map(warning => <p className="intake-notice" key={warning}>{t(`intake.warning.${warning}`)}</p>)}
          <details className="intake-transcript"><summary>{t("intake.correctText")}</summary><p>{t("intake.correctTextHint")}</p>
            <textarea aria-label={t("intake.recognisedText")} disabled={busy} maxLength={40000} value={page.lines.map(line => line.text).join("\n")} onChange={event => {
              const lines = event.target.value.split("\n").map((text, index) => ({ id: `p${page.number}l${index + 1}`, text, confidence: null }));
              setSource({ ...source, pages: source.pages.map((entry, index) => index === pageIndex ? { ...entry, lines, corrected: true } : entry) });
              setStage("source"); setGoods([]); setFields([]); setWarnings([]);
            }} /></details></>}
      </aside>
      <section className="intake-proposal" aria-label={t("intake.proposal")}>
        {stage !== "proposal" ? <div className="intake-awaiting"><p>{t("intake.sourceHint")}</p>{!busy && <button className="assistant-primary" onClick={() => void retry()}>{t("intake.prepare")}</button>}</div>
          : <><h4>{t("intake.proposal")}</h4><p className="intake-proposal-hint">{t("intake.reviewHint")}</p>
            {warnings.map(warning => <p className="intake-notice" key={warning}>{t(`intake.warning.${warning}`)}</p>)}
            {goods.map((row, index) => <article className="intake-good" key={index} data-picked={row.picked}>
              <label className="intake-include"><input type="checkbox" checked={row.picked} disabled={busy} onChange={event => changeGood(index, { picked: event.target.checked })} />{t("intake.includeGood", { number: index + 1 })}</label>
              <fieldset disabled={busy || !row.picked}><label>{t("intake.description")}<input value={row.description} maxLength={1000} onChange={event => changeGood(index, { description: event.target.value })} /></label>
                <div className="intake-pair"><label>{t("intake.quantity")}<input inputMode="decimal" value={row.count} placeholder={t("intake.unknown")} onChange={event => changeGood(index, { count: event.target.value })} /></label>
                  <label>{t("intake.unit")}<select value={row.unit} onChange={event => changeGood(index, { unit: event.target.value })}><option value="">{t("intake.chooseUnit")}</option>
                    {[...new Set([row.unit, ...units, "pcs", "pallet", "box", "drum", "kg", "l", "m3", "m"].filter(Boolean))].map(unit => <option key={unit} value={unit}>{t(`units.name.${unit}`, { defaultValue: unit })}</option>)}</select></label></div>
                <div className="intake-pair"><label>{t("intake.weight")}<input inputMode="decimal" value={row.mass} placeholder={t("intake.unknown")} onChange={event => changeGood(index, { mass: event.target.value })} /></label>
                  <label>{t("intake.weightBasis")}<select value={row.weight_basis} disabled={!row.mass} onChange={event => changeGood(index, { weight_basis: event.target.value as Good["weight_basis"] })}>
                    <option value="unknown">{t("intake.chooseBasis")}</option><option value="each">{t("intake.each")}</option><option value="total">{t("intake.total")}</option></select></label></div>
                <details className="intake-dimensions"><summary>{t("intake.dimensions")}</summary><div>{(["length", "width", "height"] as const).map(axis => <label key={axis}>{t(`intake.${axis}`)}<input inputMode="decimal" value={row[axis]} onChange={event => changeGood(index, { [axis]: event.target.value })} /></label>)}</div></details>
              </fieldset>{proof(row)}
            </article>)}
            {fields.map((field, index) => <article className="intake-fact" key={`${field.key}:${index}`}>
              <label className="intake-include"><input type="checkbox" checked={field.picked} disabled={busy} onChange={event => setFields(values => values.map((value, i) => i === index ? { ...value, picked: event.target.checked } : value.key === field.key ? { ...value, picked: false } : value))} />{t(`intake.field.${field.key}`)}</label>
              {state.doc_values?.[field.key] && <p className="intake-existing">{t("intake.existing", { value: state.doc_values[field.key] })}</p>}
              <textarea aria-label={t(`intake.field.${field.key}`)} rows={field.key.endsWith("_address") ? 3 : 1} disabled={busy || !field.picked} value={field.value} maxLength={2000}
                onChange={event => setFields(values => values.map((value, i) => i === index ? { ...value, value: event.target.value } : value))} />{proof(field)}
            </article>)}
          </>}
      </section>
    </div>}
    {failure && <div className="assistant-error" role="alert"><p>{failure}</p></div>}
    <div role="status" className="intake-progress">{busy ? progress : stage === "proposal" ? t("intake.selected", { count: acceptedCount }) : ""}</div>
    <footer className="intake-footer"><button type="button" className="assistant-secondary" disabled={applying} onClick={onCancel}>{t("intake.cancel")}</button>
      {stage === "proposal" && <button type="button" className="assistant-primary" disabled={busy || !acceptedCount} onClick={() => void accept()}><CheckIcon />{t("intake.accept")}<ArrowRightIcon /></button>}
    </footer>
  </div>;
}

export function DocumentEvidenceList({ evidence }: { evidence: DocumentEvidence[] }) {
  const { t } = useTranslation();
  if (!evidence.length) return null;
  return <details className="document-evidence"><summary>{t("intake.savedSources", { count: evidence.length })}</summary>
    <p>{t("intake.savedSourcesHint")}</p><ul>{evidence.map((item, index) => <li key={index}>
      <strong>{item.value}</strong><span>{item.name} · {t("intake.pagesLabel")} {item.pages.join(", ")}{item.method === "corrected" ? ` · ${t("intake.corrected")}` : ""}</span>
      <blockquote>{item.excerpt}</blockquote></li>)}</ul></details>;
}
