import { useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  api,
  DgEntry,
  DgInstructions,
  DgPackaging,
  DgPrepareResult,
  DgProduct,
  DgUnEntry,
  LineItem,
} from "../api/client";
import { documentLanguage, localised } from "../i18n/language";
import CollapsibleSection, { SummaryChip } from "./CollapsibleSection";
import { ChevronDownIcon, DocumentIcon, RefreshIcon, WarningIcon } from "./icons";
import InfoTooltip from "./InfoTooltip";
import SuggestInput, { SuggestItem } from "./SuggestInput";

/** What the derivation added, laid over the form as it stands *now*.
 *
 *  `dg/prepare` is debounced and then takes a round trip, and it only runs again
 *  when the UN number, the counts or the packaging change. Anything else the user
 *  types while a request is in flight — a total, a technical name — is typed into
 *  a form the reply knows nothing about, and replacing the entries with that reply
 *  put the old value back. The field emptied itself under the cursor.
 *
 *  So the reply is not taken as the new truth. `sent` is what the request was
 *  built from, `derived` is what came back, and the difference between those two
 *  is exactly what the backend contributed. That difference is applied to
 *  `current`, and only where `current` still has nothing of its own — which is the
 *  rule the derivation already followed, now applied against the right form.
 *
 *  If the shape moved while the request was out (a position or a product added or
 *  removed), the reply is dropped: the indices no longer line up, and a new
 *  derivation is on its way regardless.
 */
export function mergeDerived(
  current: DgEntry[],
  sent: DgEntry[],
  derived: DgEntry[],
): DgEntry[] {
  if (current.length !== sent.length || sent.length !== derived.length) return current;
  return current.map((entry, i) => {
    const sentEntry = sent[i];
    const derivedEntry = derived[i];
    if (entry.products.length !== sentEntry.products.length
        || sentEntry.products.length !== derivedEntry.products.length) {
      return entry;
    }
    return {
      ...entry,
      products: entry.products.map((product, j) => {
        const sentProduct = sentEntry.products[j] as Record<string, unknown>;
        const derivedProduct = derivedEntry.products[j] as Record<string, unknown>;
        const now = product as Record<string, unknown>;
        const patch: Record<string, unknown> = {};
        for (const key of Object.keys(derivedProduct)) {
          const contributed = JSON.stringify(derivedProduct[key]) !== JSON.stringify(sentProduct[key]);
          const empty = now[key] === undefined || now[key] === null || now[key] === "";
          if (contributed && empty) patch[key] = derivedProduct[key];
        }
        return Object.keys(patch).length ? ({ ...product, ...patch } as DgProduct) : product;
      }),
    };
  });
}

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm";
const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";

interface Props {
  lines: LineItem[];
  entries: DgEntry[];
  onChange: (entries: DgEntry[]) => void;
  /** Show one position per screen with navigation */
  perPosition?: boolean;
  /** Extra DG fields for the selected documents (IATA/IMO for instance) */
  extraFields?: string[];
  /** Regulatory profiles of the chosen forms (ADR, IMDG, IATA_DGR, …) */
  profiles?: string[];
}

/** The special cases of 5.4.1.1 — waste, empty uncleaned, salvage, molten,
 *  UN 3509 residues, the 2.1.2.8 statement, containers-only — behind one
 *  door, closed by default. The answer is "none" on nearly every consignment,
 *  and eight always-open selects made the step look like eight questions. */
const SPECIAL_FIELDS = [
  "is_waste",
  "empty_uncleaned",
  "salvage_packaging",
  "molten",
  "residue_classes",
  "classified_2_1_2_8",
  "containers_only",
  "full_load",
] as const;

/** What the derived summary shows, in reading order: identification first,
 *  then what follows from the table, then the quantities of this consignment. */
const SUMMARY_FIELDS = [
  "proper_shipping_name",
  "class",
  "subsidiary_risks",
  "packing_group",
  "labels",
  "tunnel_code",
  "transport_category",
  "hazard_number",
  "limited_quantity",
  "excepted_quantity",
  "packing_instruction",
  "quantity_packages",
  "type_of_package",
  "net_mass_liters_per_package",
  "gross_mass_per_package",
  "adr_total_quantity",
  "tank_code",
  "ems_code",
] as const;

const CORE_FIELDS = [
  "un_number",
  "proper_shipping_name",
  "class",
  "subsidiary_risks",
  "packing_group",
  "type_of_package",
  "quantity_packages",
  "quantity_items_per_package",
  "net_per_inner_packaging",
  "net_mass_liters_per_package",
  "gross_mass_per_package",
  "eq_lq_points",
  "dimensions",
  "additional_information",
] as const;

/** What `buildDgEntries` reads off a goods line. Narrower than `DraftLine` on
 *  purpose: this says exactly which of the line's answers the step starts
 *  from, and nothing here has to change when the goods step gains a field. */
export interface LineDraft {
  confirmed_un?: string;
  proper_shipping_name?: string;
  packing_group?: string;
  type_of_package?: string;
  package_content?: string;
}

function emptyProduct(): DgProduct {
  return {
    un_number: "",
    proper_shipping_name: "",
    class: "",
    subsidiary_risks: "",
    packing_group: "",
    packing_instruction: "",
    type_of_package: "",
    quantity_packages: "",
    quantity_items_per_package: "",
    net_per_inner_packaging: "",
    net_mass_liters_per_package: "",
    gross_mass_per_package: "",
    eq_lq_points: "",
    dimensions: "",
    additional_information: "",
    caliber: "",
  };
}

/**
 * The step's starting point, built from the goods.
 *
 * Three things feed it, in the order of who is most likely to be right:
 *
 * 1. **What the user stated on the line** (v1.203.0). The goods step now asks
 *    for the substance's identity where the substance is — UN number, proper
 *    shipping name, packing group, packaging — and an answer typed by the
 *    person shipping the goods beats anything derived from them.
 * 2. **The library article** the line was picked from, for what the user did
 *    not state.
 * 3. **What the recogniser found** in the description, for the UN number.
 *
 * Everything left empty stays empty and is filled by `dg/prepare` out of the
 * tables, exactly as before. `drafts` is index-aligned with `lines`; a caller
 * without them (an older snapshot, a test) gets the behaviour of 1 and 2 only.
 */
export function buildDgEntries(lines: LineItem[], drafts: LineDraft[] = []): DgEntry[] {
  return lines
    .map((line, index) => ({ line, draft: drafts[index] }))
    .filter(({ line }) => line.include && line.dangerous_goods)
    .map(({ line, draft }) => ({
      line_id: line.line_id,
      vehicle: line.output_description || line.description,
      registration: "",
      products: [
        {
          ...emptyProduct(),
          un_number: line.detected_un_numbers?.[0] || "",
          // What the library knows about the article the line was picked
          // from. Only what it holds; the tables fill the rest as usual.
          ...(line.article?.un_number
            ? {
                ...(line.article.proper_shipping_name ? { proper_shipping_name: line.article.proper_shipping_name } : {}),
                ...(line.article.technical_name ? { technical_name: line.article.technical_name } : {}),
                ...(line.article.class ? { class: line.article.class } : {}),
                ...(line.article.packing_group ? { packing_group: line.article.packing_group } : {}),
                ...(line.article.type_of_package ? { type_of_package: line.article.type_of_package } : {}),
                ...(line.article.net_per_package ? { net_mass_liters_per_package: line.article.net_per_package } : {}),
              }
            : {}),
          // The number of packages is the line's own quantity whichever route
          // brought the substance here; it was tied to the article by
          // accident of where the code sat.
          ...(line.quantity ? { quantity_packages: String(line.quantity) } : {}),
          ...(draft?.confirmed_un ? { un_number: draft.confirmed_un } : {}),
          ...(draft?.proper_shipping_name ? { proper_shipping_name: draft.proper_shipping_name } : {}),
          ...(draft?.packing_group ? { packing_group: draft.packing_group } : {}),
          ...(draft?.type_of_package ? { type_of_package: draft.type_of_package } : {}),
          ...(draft?.package_content ? { net_mass_liters_per_package: draft.package_content } : {}),
        },
      ],
    }));
}

export default function DangerousGoodsStep({
  lines,
  entries,
  onChange,
  perPosition = false,
  extraFields = [],
  profiles = [],
}: Props) {
  const { t, i18n } = useTranslation();
  const lang = documentLanguage(i18n.language);
  const [instructions, setInstructions] = useState<DgInstructions | null>(null);
  const [lookupError, setLookupError] = useState("");
  const [positionIndex, setPositionIndex] = useState(0);
  const [preparing, setPreparing] = useState(false);
  const [prepareError, setPrepareError] = useState(false);
  const [prepared, setPrepared] = useState<DgPrepareResult | null>(null);
  // Per product: the full form instead of the summary. A choice the user
  // makes, never a mode the step falls into by itself.
  const [editAll, setEditAll] = useState<Record<string, boolean>>({});
  // What the form holds at the moment a reply lands, which is not what it held
  // when the request left. Kept in a ref so reading it does not re-run the effect.
  const entriesRef = useRef(entries);
  entriesRef.current = entries;

  useEffect(() => {
    api.dgInstructions().then(setInstructions).catch(() => setInstructions(null));
  }, []);

  // Automatic derivation: everything that follows from the UN number and the
  // packages is filled in by the backend. Only empty fields are completed, so
  // manual corrections stay.
  // The signature also covers counts, contents and packaging: the derived totals
  // (ADR quantity, Q value) compute with those, so a change there has to trigger
  // a new derivation just as a new UN number does.
  const unSignature = entries
    .map((entry) =>
      entry.products
        .map((p) =>
          [p.un_number, p.quantity_packages, p.net_mass_liters_per_package, p.type_of_package,
           p.q_net_quantity, p.q_max_net_quantity,
           // These answers change what the derivation produces: the mode
           // decides the tank questions and the table C density, the chosen
           // names become the shipping name, the technical name settles SP 274.
           p.carriage_mode, p.chosen_name, p.chosen_name_en, p.technical_name]
            .map((v) => v ?? "")
            .join("~"),
        )
        .join("|"),
    )
    .join("#");
  const profileKey = profiles.join(",");

  useEffect(() => {
    if (!entries.some((entry) => entry.products.some((p) => (p.un_number ?? "").trim()))) {
      setPrepared(null);
      setPreparing(false);
      setPrepareError(false);
      return;
    }
    let cancelled = false;
    setPrepared(null);
    setPreparing(true);
    setPrepareError(false);
    const timer = window.setTimeout(() => {
      const sent = entriesRef.current;
      api
        .dgPrepare(sent, lines, profiles, lang)
        .then((res) => {
          if (cancelled) return;
          setPreparing(false);
          setPrepared(res);
          const merged = mergeDerived(entriesRef.current, sent, res.entries);
          if (JSON.stringify(merged) !== JSON.stringify(entriesRef.current)) {
            onChange(merged);
          }
        })
        .catch(() => {
          if (!cancelled) { setPrepared(null); setPreparing(false); setPrepareError(true); }
        });
    }, 250);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
    // Derive again on every relevant input change (debounced).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unSignature, profileKey, lang]);

  const optionsFor = (field: string) => {
    const item = instructions?.dg_fields?.[field];
    if (!item || item.type !== "select" || !item.options) return undefined;
    return item.options.map((option) => ({
      value: option.value,
      label: localised(option.label, lang) || option.value,
    }));
  };

  const helpFor = (field: string) => {
    const item = instructions?.dg_fields?.[field];
    return localised(item?.help, lang);
  };

  const labelFor = (field: string) => {
    const item = instructions?.dg_fields?.[field];
    return localised(item?.label, lang) || field;
  };

  const updateEntry = (index: number, patch: Partial<DgEntry>) => {
    onChange(entries.map((entry, i) => (i === index ? { ...entry, ...patch } : entry)));
  };

  const updateProduct = (entryIndex: number, productIndex: number, patch: Partial<DgProduct>) => {
    if (!("imdg_source_reviewed" in patch)) patch = { ...patch, imdg_source_reviewed: "N" };
    const entry = entries[entryIndex];
    const products = entry.products.map((product, i) => (i === productIndex ? { ...product, ...patch } : product));
    updateEntry(entryIndex, { products });
  };

  const classBadge = (cls: string, pg?: string) => (
    <span className="ml-auto flex shrink-0 items-center gap-1">
      {cls && (
        <span className="rounded bg-orange-100 px-1.5 py-0.5 text-[11px] font-semibold text-orange-800 dark:bg-orange-900/50 dark:text-orange-200">
          {t("dgsearch.classShort")} {cls}
        </span>
      )}
      {pg && (
        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          PG {pg}
        </span>
      )}
    </span>
  );

  const unFetcher = async (q: string): Promise<SuggestItem<DgUnEntry>[]> => {
    const { results } = await api.dgSearch(q, 12, lang, profiles);
    return results.map((entry, i) => ({
      key: `${entry.un}-${i}`,
      data: entry,
      render: (
        <span className="flex items-center gap-2">
          <span className="shrink-0 font-mono font-semibold">UN {entry.un}</span>
          <span className="min-w-0 truncate">
            {entry.proper_shipping_name || entry.name_en || entry.name_de}
          </span>
          {classBadge(entry.class, entry.packing_group)}
        </span>
      ),
    }));
  };

  const applyUnEntry = (entryIndex: number, productIndex: number, un: DgUnEntry) => {
    // Set the UN number only: the rest (proper shipping name, division,
    // subsidiary risks from the labels column, packing group, transport
    // category, tunnel code, EmS and air freight rules) is derived by
    // /dg/prepare. The classification code (F1, M4, C1) is emphatically *not* a
    // subsidiary risk.
    // The name the server already resolved for these profiles, not the English
    // column: the suggestion showed "BENZINE OF MOTORBRANDSTOF (GASOLINE)" and
    // writing "GASOLINE" into the field instead made the click undo what the
    // list had just got right.
    updateProduct(entryIndex, productIndex, {
      un_number: un.un,
      proper_shipping_name: (un.proper_shipping_name || un.name_en || un.name_de).toUpperCase(),
    });
    // Live ADR 2025 enrichment (exact PSN and so on) when the external source is reachable.
    void lookupUn(entryIndex, productIndex, un.un, true);
  };

  const packagingFetcher = async (q: string): Promise<SuggestItem<DgPackaging>[]> => {
    const { results } = await api.dgPackagings(q, 40);
    return results.map((p) => ({
      key: p.code,
      data: p,
      render: (
        <span className="flex items-center gap-2">
          <span className="w-14 shrink-0 font-mono font-semibold">{p.code}</span>
          <span className="min-w-0 truncate">{p.label[lang as "nl" | "en"]}</span>
          {p.contents !== "beide" && (
            <span className="ml-auto shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              {p.contents === "vloeistof" ? t("dgsearch.liquid") : t("dgsearch.solid")}
            </span>
          )}
        </span>
      ),
    }));
  };

  const lookupUn = async (entryIndex: number, productIndex: number, un: string, silent = false) => {
    setLookupError("");
    if (!un || un.replace(/\D/g, "").length < 4) return;
    try {
      const data = await api.dgLookup(un, lang, profiles);
      // Only overwrite with fields the source actually supplies.
      const patch: Partial<DgProduct> = { un_number: data.un_number || un };
      if (data.proper_shipping_name) patch.proper_shipping_name = data.proper_shipping_name;
      if (data.class) patch.class = data.class;
      if (data.subsidiary_risks) patch.subsidiary_risks = data.subsidiary_risks;
      if (data.classification_code) patch.classification_code = data.classification_code;
      if (data.packing_group) patch.packing_group = data.packing_group;
      if (data.packing_instruction) patch.packing_instruction = data.packing_instruction;
      if (data.transport_category != null && data.transport_category !== "") {
        (patch as Record<string, string>).transport_category = String(data.transport_category);
      }
      updateProduct(entryIndex, productIndex, patch);
    } catch (e) {
      if (!silent) setLookupError(String(e));
    }
  };

  const safePositionIndex = Math.min(positionIndex, Math.max(0, entries.length - 1));
  const visibleEntries = perPosition && entries.length > 0 ? [entries[safePositionIndex]] : entries;
  const visibleEntryOffset = perPosition ? safePositionIndex : 0;

  return (
    <div className="dg-workspace space-y-4">
      <header className="dg-step-heading"><div><h3>{t("dgFocus.title")}</h3></div>
        <details className="dg-source"><summary><DocumentIcon />{t("dgFocus.sources")}</summary><div><p>{localised(instructions?.dg_intro, lang) || t("wizard.dgIntro")}</p><p>{t("wizard.dgSource")}</p></div></details>
      </header>
      {preparing && <p className="dg-preparing" role="status"><RefreshIcon className="h-4 w-4 animate-spin" />{t("dgFocus.preparing")}</p>}
      {prepareError && <p className="dg-prepare-error" role="alert"><WarningIcon />{t("dgFocus.prepareError")}</p>}

      {perPosition && entries.length > 1 && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-600 dark:text-slate-400">
            {t("wizard.dgPositionOf", { current: positionIndex + 1, total: entries.length })}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={positionIndex === 0}
              onClick={() => setPositionIndex((i) => i - 1)}
              className={buttonSecondary}
            >
              {t("wizard.back")}
            </button>
            <button
              type="button"
              disabled={positionIndex >= entries.length - 1}
              onClick={() => setPositionIndex((i) => i + 1)}
              className={buttonSecondary}
            >
              {t("wizard.next")}
            </button>
          </div>
        </div>
      )}

      {/* Fields that exist only where they mean something: NEM only for class 1
          (ADR 1.1.3.6.3), and the inner packaging only where an LQ or EQ route
          exists (column 7a ≠ 0 or code ≠ E0). */}
      {visibleEntries.map((entry, localIndex) => {
        const entryIndex = visibleEntryOffset + localIndex;
        return (
        <div key={entry.line_id} className={`${panelClass} dg-entry p-5 space-y-4`}>
          <header className="dg-entry-heading"><span className="dg-entry-index">{String(entryIndex + 1).padStart(2, "0")}</span>
            <div><p>{t("wizard.dgLine")} {entry.line_id}</p><h3>{entry.vehicle}</h3></div>
          </header>
          <details className="dg-position-edit"><summary>{t("dgFocus.editPosition")}<ChevronDownIcon /></summary>
            <Field label={t("wizard.dgVehicle")} value={entry.vehicle}
              onChange={(v) => updateEntry(entryIndex, { vehicle: v })} />
          </details>
          {entry.products.map((product, productIndex) => {
            const isClass1 = String(product.class ?? "").trim().startsWith("1");
            const noExemptionRoute =
              (product.limited_quantity ?? "").trim() === "0" &&
              (product.excepted_quantity ?? "").trim().toUpperCase() === "E0";
            const productFields = CORE_FIELDS.filter(
              (field) =>
                field !== "un_number" &&
                (field !== "net_per_inner_packaging" || !noExemptionRoute),
            ).flatMap((field) =>
              field === "gross_mass_per_package" && isClass1
                ? [field, "net_explosive_mass"]
                : [field],
            );
            const un = String(product.un_number ?? "").trim();
            const stateKey = `${entryIndex}:${productIndex}`;
            // Start with substance identity. After selection, show the
            // summary; the full form remains an explicit editing choice.
            const showAll = !!editAll[stateKey];
            const productQuestions = (prepared?.open_questions ?? [])
              .filter(
                (block) =>
                  block.line_id === entry.line_id && block.product_index === productIndex,
              )
              .flatMap((block) => block.questions);
            const specialFields = SPECIAL_FIELDS.filter((f) => extraFields.includes(f)).filter(
              (f) => f !== "residue_classes" || un.includes("3509"),
            );
            const specialAnswered = specialFields.filter((f) =>
              String(product[f as keyof DgProduct] ?? "").trim(),
            ).length;

            const renderField = (field: string) =>
              field === "type_of_package" ? (
                <div key={field}>
                  <div className="flex items-center gap-1.5">
                    <label htmlFor={`dg-${entry.line_id}-${productIndex}-package`} className="text-sm font-medium text-slate-800 dark:text-slate-200">{labelFor(field)}</label>
                    {helpFor(field) && <InfoTooltip text={helpFor(field)} />}
                  </div>
                  <div className="mt-1">
                    <SuggestInput<DgPackaging>
                      id={`dg-${entry.line_id}-${productIndex}-package`}
                      ariaLabel={labelFor(field)}
                      value={String(product.type_of_package ?? "")}
                      onChange={(v) => updateProduct(entryIndex, productIndex, { type_of_package: v })}
                      onPick={(p) =>
                        updateProduct(entryIndex, productIndex, {
                          type_of_package: `${p.code} ${p.label[lang as "nl" | "en"]}`,
                        })
                      }
                      fetcher={packagingFetcher}
                      placeholder={t("dgsearch.packagingPlaceholder")}
                      minLength={1}
                    />
                  </div>
                </div>
              ) : (
                <Field
                  key={field}
                  label={labelFor(field)}
                  help={helpFor(field)}
                  options={optionsFor(field)}
                  value={String(product[field as keyof DgProduct] ?? "")}
                  onChange={(v) => updateProduct(entryIndex, productIndex, { [field]: v })}
                />
              );

            return (
            <div key={productIndex} className="dg-product space-y-4">
              {profiles.some((p) => p.toUpperCase() === "IMDG") && <fieldset className="rounded-lg border border-amber-300 dark:border-amber-700 p-3 space-y-3">
                <legend className="px-1 font-medium">{t("imdgSource.title")}</legend>
                <p className="text-sm">{t("imdgSource.explanation")}</p>
                <label className="block"><span>{t("imdgSource.reference")}</span><input className={inputClass} maxLength={1000} value={product.imdg_source_reference || ""} onChange={(e) => updateProduct(entryIndex, productIndex, { imdg_source_reference: e.target.value })} /></label>
                <label className="flex gap-2 items-start"><input type="checkbox" checked={product.imdg_source_reviewed === "Y"} disabled={!product.imdg_source_reference?.trim()} onChange={(e) => updateProduct(entryIndex, productIndex, { imdg_source_reviewed: e.target.checked ? "Y" : "N" })} /><span className="text-sm">{t("imdgSource.confirm")}</span></label>
              </fieldset>}

              <div className={`grid gap-4 ${showAll ? "md:grid-cols-2" : ""}`}>
                <div className="dg-identity-search">
                  <div className="flex items-center gap-1.5">
                    <label htmlFor={`dg-${entry.line_id}-${productIndex}-un`} className="text-sm font-medium text-slate-800 dark:text-slate-200">
                      {labelFor("un_number")}
                    </label>
                    {helpFor("un_number") && <InfoTooltip text={helpFor("un_number")} />}
                  </div>
                  <div className="mt-1">
                    <SuggestInput<DgUnEntry>
                      id={`dg-${entry.line_id}-${productIndex}-un`}
                      ariaLabel={labelFor("un_number")}
                      value={product.un_number ?? ""}
                      onChange={(v) => updateProduct(entryIndex, productIndex, { un_number: v })}
                      onPick={(un) => applyUnEntry(entryIndex, productIndex, un)}
                      fetcher={unFetcher}
                      placeholder={t("dgsearch.unPlaceholder")}
                      minLength={2}
                      onBlur={() => lookupUn(entryIndex, productIndex, product.un_number ?? "")}
                    />
                  </div>
                </div>
                {showAll &&
                  [...productFields, ...extraFields.filter((f) => !(CORE_FIELDS as readonly string[]).includes(f))]
                    // A tank code is a question about a tank. Asking it of a
                    // packages consignment is noise, and noise on this step is
                    // what makes people stop reading it.
                    .filter(
                      (field) =>
                        !["tank_code", "filling_temperature", "density_15", "density_50"].includes(
                          field,
                        ) || product.carriage_mode === "tank",
                    )
                    // Holds belong to a dry cargo vessel. A cargo tank has no hold
                    // to be in, and 7.1.4.11 is a chapter 7.1 provision — asking
                    // for one on a tank vessel would be asking the wrong question.
                    // The residues field belongs to UN 3509 alone (5.4.1.1.19);
                    // for every other substance it is noise.
                    .filter(
                      (field) =>
                        field !== "residue_classes" ||
                        (product.un_number ?? "").includes("3509"),
                    )
                    .filter(
                      (field) =>
                        !["hold", "container_number"].includes(field) ||
                        (product.carriage_mode ?? "packages") !== "tank",
                    )
                    .map(renderField)}
              </div>

              {!showAll && un && (
                <>
                  <div className="dg-identity-summary">
                    <strong>{product.proper_shipping_name || `UN ${un}`}</strong>
                    <div>{product.class && <span>{t("dgsearch.classShort")} {product.class}</span>}{product.packing_group && <span>PG {product.packing_group}</span>}
                      {product.type_of_package && <span>{product.quantity_packages && `${product.quantity_packages} × `}{product.type_of_package}</span>}
                      {product.adr_total_quantity && <span>{labelFor("adr_total_quantity")}: {String(product.adr_total_quantity)}</span>}
                    </div>
                  </div>
                  {productQuestions.length > 0 && (
                    <div className="dg-open-questions">
                      <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                        {t("dgstep.openTitle")} <span className="dg-question-count">{productQuestions.length}</span>
                      </p>
                      <div className="mt-2 grid gap-3 md:grid-cols-2">
                        {productQuestions.map((question) => (
                          <div key={question.field}>
                            {question.options?.length ? (
                              // A closed answer set from the backend (the
                              // 3.1.2.2 name alternatives): a select, with an
                              // empty first entry so nothing is pre-chosen.
                              <Field
                                label={labelFor(question.field)}
                                help={helpFor(question.field)}
                                options={[
                                  { value: "", label: "—" },
                                  ...question.options.map((option) => ({
                                    value: option,
                                    label: option,
                                  })),
                                ]}
                                value={String(
                                  (product as Record<string, unknown>)[question.field] ?? "",
                                )}
                                onChange={(v) =>
                                  updateProduct(entryIndex, productIndex, {
                                    [question.field]: v,
                                  })
                                }
                              />
                            ) : (
                              renderField(question.field)
                            )}
                            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                              {t(`dgopen.${question.reason}` as "dgopen.sp274")}
                              {question.required ? " *" : ""}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* What the tables answered, shown as answers. Every value is
                      still editable — behind the one button below, not as
                      twenty-two open fields. */}
                  <details className="dg-derived-details"><summary>{t("dgstep.summaryTitle")}<ChevronDownIcon /></summary><div>
                    <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1.5 md:grid-cols-3">
                      {SUMMARY_FIELDS.filter((field) => field !== "proper_shipping_name").map((field) => {
                        const value = String(
                          (product as Record<string, unknown>)[field] ?? "",
                        ).trim();
                        if (!value) return null;
                        return (
                          <div key={field}>
                            <dt className="text-xs text-slate-500 dark:text-slate-400">{labelFor(field)}</dt>
                            <dd className="break-words text-sm text-slate-800 dark:text-slate-200">{value}</dd>
                          </div>
                        );
                      })}
                    </dl>
                  </div></details>


                  {specialFields.length > 0 && (
                    <CollapsibleSection
                      title={t("dgstep.special")}
                      chips={
                        <SummaryChip>
                          {specialAnswered > 0 ? specialAnswered : t("dgstep.noneApply")}
                        </SummaryChip>
                      }
                    >
                      <div className="grid gap-3 md:grid-cols-2">{specialFields.map(renderField)}</div>
                    </CollapsibleSection>
                  )}
                </>
              )}

              {un && (
                <button
                  type="button"
                  className="dg-edit-all"
                  aria-expanded={!!editAll[stateKey]}
                  onClick={() =>
                    setEditAll((state) => ({ ...state, [stateKey]: !state[stateKey] }))
                  }
                >
                  {editAll[stateKey] ? t("dgstep.backToSummary") : t("dgstep.editAll")}
                </button>
              )}
            </div>
            );
          })}
        </div>
        );
      })}

      {prepared && <AutoDerivedPanel prepared={prepared} />}

      {lookupError && <p className="text-amber-600 dark:text-amber-300 text-sm">{lookupError}</p>}
    </div>
  );
}

/** Shows what the app derived automatically: document lines, points of
 *  attention and the additional data the user has to supply themselves. */
function AutoDerivedPanel({ prepared }: { prepared: DgPrepareResult }) {
  const { t } = useTranslation();
  const profiles = Object.keys(prepared.document_lines).filter(
    (profile) => prepared.document_lines[profile].length > 0,
  );
  const blockers = prepared.hints
    .filter((hint) => hint.transport_forbidden && hint.transport_forbidden_note)
    .map((hint) => ({ un: hint.un_number, text: hint.transport_forbidden_note as string }));
  const notes = prepared.hints.flatMap((hint) =>
    [
      hint.ems_description && `EmS — ${hint.ems_description}`,
      hint.ems_variants?.length &&
        t("dgauto.emsByVariant", {
          options: hint.ems_variants.map((v) => `${v.label} → ${v.code}`).join(", "),
        }),
      hint.ems_packing_group_options &&
        t("dgauto.emsByPackingGroup", {
          options: Object.entries(hint.ems_packing_group_options)
            .map(([pg, code]) => `${pg} → ${code}`)
            .join(", "),
        }),
      hint.segregation_groups_text && `IMDG 7.2.5 — ${hint.segregation_groups_text}`,
      hint.marine_pollutant_text,
      // Stowage and segregation per substance (IMDG columns 16a/16b). The codes
      // alone say nothing to a user, so the card's explanation comes with them.
      // The description from chapters 7.1.5 and 7.2.8 takes precedence over the
      // sentence that came from the UN card; the latter is a paraphrase.
      hint.imdg_stowage_codes?.length &&
        `IMDG 16a — ${
          hint.imdg_stowage_definitions?.length
            ? hint.imdg_stowage_definitions.map((d) => `${d.code}: ${d.text}`).join(" ")
            : `${hint.imdg_stowage_codes.join(", ")}${
                hint.imdg_stowage_text ? `: ${hint.imdg_stowage_text}` : ""
              }`
        }`,
      hint.imdg_segregation_codes?.length &&
        `IMDG 16b — ${
          hint.imdg_segregation_definitions?.length
            ? hint.imdg_segregation_definitions.map((d) => `${d.code}: ${d.text}`).join(" ")
            : `${hint.imdg_segregation_codes.join(", ")}${
                hint.imdg_segregation_text ? `: ${hint.imdg_segregation_text}` : ""
              }`
        }`,
      hint.imdg_stowage_category && `IMDG 7.1.4 — ${t("dgauto.stowageCategory", {
        category: hint.imdg_stowage_category,
      })}`,
      // Column 6 of the list. A special provision can change the
      // classification, the packaging or the exemption of a substance, so the
      // number belongs in view even though its text is not in this app.
      hint.imdg_special_provisions?.length &&
        `IMDG 3.2 — ${t("dgauto.specialProvisions", {
          list: hint.imdg_special_provisions.join(", "),
        })}`,
      hint.imdg_amended_in_42_24 && `IMDG 42-24 — ${t("dgauto.amendedIn4224")}`,
      // What Amendment 42-24 changes about this substance. The base data comes
      // from ADR 2025 and the 41-22 UN cards; where the mandatory edition
      // differs, that belongs with the substance and not only in the docs.
      ...(hint.imdg_amendment_changes ?? []).map((change) => `IMDG 42-24 — ${change}`),
      hint.imdg_document_requirement &&
        `IMDG ${hint.imdg_document_requirement.section} — ${hint.imdg_document_requirement.text}`,
      hint.packing_group_note,
      hint.density_note,
      hint.air_note,
      hint.label_reference_note,
      hint.limited_quantity_text,
      hint.excepted_quantity_text,
    ]
      .filter((text): text is string => Boolean(text))
      .map((text) => ({ un: hint.un_number, text, forbidden: Boolean(hint.air_forbidden) })),
  );

  if (
    profiles.length === 0 &&
    notes.length === 0 &&
    blockers.length === 0 &&
    prepared.requirements.length === 0
  )
    return null;

  const documentLineCount = profiles.reduce(
    (sum, profile) => sum + prepared.document_lines[profile].length,
    0,
  );

  return (
    <div className={`${panelClass} p-5 space-y-3`}>
      <div>
        <h3 className="font-semibold text-slate-900 dark:text-slate-100">{t("dgauto.title")}</h3>
      </div>

      {/* A carriage prohibition stays in view at all times: it must never
          disappear behind a collapsed heading. */}
      {blockers.map((blocker, i) => (
        <div
          key={i}
          className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-900/60 dark:bg-red-900/20 dark:text-red-200"
        >
          <p className="font-semibold">
            {t("dgauto.forbidden")}
            {blocker.un && <span className="ml-1 font-mono">UN {blocker.un}</span>}
          </p>
          <p className="mt-0.5">{blocker.text}</p>
        </div>
      ))}

      {(documentLineCount > 0 || prepared.adr_category_totals?.statement) && (
        <CollapsibleSection
          title={t("dgauto.documentLinesTitle")}
          chips={<SummaryChip>{documentLineCount}</SummaryChip>}
        >
          {profiles.map((profile) => (
            <div key={profile}>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                {t("dgauto.documentLine", { profile })}
              </p>
              <ul className="mt-1 space-y-1">
                {prepared.document_lines[profile].map((line, i) => (
                  <li
                    key={i}
                    className="rounded-lg bg-slate-50 dark:bg-slate-950 px-3 py-2 font-mono text-xs text-slate-800 dark:text-slate-200"
                  >
                    {line}
                  </li>
                ))}
              </ul>
            </div>
          ))}

          {prepared.adr_category_totals?.statement && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                {t("dgauto.adrTotals")}
              </p>
              <p className="mt-1 rounded-lg bg-slate-50 dark:bg-slate-950 px-3 py-2 text-xs text-slate-800 dark:text-slate-200">
                {prepared.adr_category_totals.statement}
              </p>
            </div>
          )}
        </CollapsibleSection>
      )}

      {notes.length > 0 && (
        <CollapsibleSection
          title={t("dgauto.notes")}
          // A red air freight warning belongs open and in view.
          defaultOpen={notes.some((note) => note.forbidden)}
          chips={<SummaryChip>{notes.length}</SummaryChip>}
        >
          <ul className="space-y-1 text-sm">
            {notes.map((note, i) => (
              <li
                key={i}
                className={
                  note.forbidden
                    ? "text-red-700 dark:text-red-300"
                    : "text-slate-700 dark:text-slate-300"
                }
              >
                {note.un && <span className="font-mono font-semibold">UN {note.un}: </span>}
                {note.text}
              </li>
            ))}
          </ul>
        </CollapsibleSection>
      )}

      {prepared.requirements.length > 0 && (
        <CollapsibleSection
          title={t("dgauto.requirements")}
          chips={<SummaryChip>{prepared.requirements.length}</SummaryChip>}
        >
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700 dark:text-slate-300">
            {prepared.requirements.map((requirement, i) => (
              <li key={i}>{requirement}</li>
            ))}
          </ul>
        </CollapsibleSection>
      )}
    </div>
  );
}

const buttonSecondary = "px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50";

function Field({
  label,
  help,
  value,
  onChange,
  onBlur,
  options,
}: {
  label: string;
  help?: string;
  value: string;
  onChange: (v: string) => void;
  onBlur?: () => void;
  /** A closed set of answers renders as a list rather than a text box.
   *  The mode of carriage is the first field here where free text would be
   *  worse than useless: "tank " with a space, or "Tank", would fall through
   *  every check that branches on it and the consignment would quietly be
   *  judged as packages again — the exact failure the field exists to end. */
  options?: { value: string; label: string }[];
}) {
  const id = useId();
  return (
    <div>
      <div className="flex items-center gap-1.5">
        <label htmlFor={id} className="text-sm font-medium text-slate-800 dark:text-slate-200">{label}</label>
        {help && <InfoTooltip text={help} />}
      </div>
      {options && options.length > 0 ? (
        <select
          id={id}
          className={`${inputClass} mt-1`}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
        >
          {!options.some((option) => option.value === "") && <option value="">—</option>}
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : (
        <input id={id} className={`${inputClass} mt-1`} value={value} onChange={(e) => onChange(e.target.value)} onBlur={onBlur} />
      )}
    </div>
  );
}
