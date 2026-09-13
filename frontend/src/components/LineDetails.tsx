/**
 * Everything about one goods line that does not fit on its row — opened where
 * the row is, not in a window over it.
 *
 * The history of this file is two overcorrections. It began as a table of
 * thirteen input columns, which no screen narrower than a large monitor could
 * hold. v1.192.0 replaced that with a dialog, which fixed the width and
 * charged a window: three actions to change a number, none of them the number.
 * v1.193.0 put the four things people actually come back to change on the row
 * itself, and the dialog kept the rest.
 *
 * This is the last of it. The rest is not behind a window either: the row
 * expands and the fields stand underneath it, with the list still on screen
 * above and below. Nothing is modal, nothing is submitted — the wizard
 * recalculates from the lines as they are typed, exactly as it did.
 *
 * **The substance is here too.** For a line that carries dangerous goods, this
 * is where its identity is stated: the UN number, the proper shipping name,
 * the packing group, and how it is packed. Those questions used to be asked on
 * the dangerous-goods step — one step after the step that recognised the
 * substance and put a UN number on the line. Asking the same thing twice, a
 * screen apart, is what this ends.
 *
 * What is not here is the class. It follows from the UN number through Table
 * A, and a field for it would invite somebody to state something the tables
 * then contradict. The same goes for everything the assessment needs — the
 * tunnel code, the transport category, mixed loading, the 1.1.3.6 calculation:
 * that is the dangerous-goods step's work and it stays there.
 */
import { useTranslation } from "react-i18next";

import { LineItem, UnitCatalogue } from "../api/client";
import type { DraftLine } from "./ReviewLinesPanel";
import ArticleCombobox from "./ArticleCombobox";
import EquipmentCombobox from "./EquipmentCombobox";
import { usePreferences } from "../settings/preferences";
import NumberInput from "./NumberInput";
import UnitSelect from "./UnitSelect";
import DensityReference from "./DensityReference";

/**
 * Cross-sections with a wall, where length-width-height does not determine the
 * weight.
 *
 * An 80x80 angle is two legs a few millimetres thick, not a solid bar of
 * 80x80 — a factor of five. For a plate, beam or plank that does not come into
 * play and the field therefore should not be there either.
 */
export const WALL_PROFILE_TYPES = new Set(["angle_profile", "square_tube", "round_tube"]);

/**
 * Round cross-sections. There the width *is* the diameter and there is no
 * height: with a diameter, a length and — for a tube — a wall thickness, the
 * weight is fixed. Asking for a height that adds nothing is only an
 * opportunity to fill in something wrong.
 */
export const ROUND_TYPES = new Set(["round_tube", "round_bar"]);

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2.5 text-sm min-h-[44px]";
const numberClass = `${inputClass} text-right`;
const labelClass = "text-sm font-medium text-slate-800 dark:text-slate-200";

interface Props {
  line: DraftLine;
  /** The computed line, when the wizard has calculated. Decides which fields
   *  apply at all: no cross-section, no wall thickness. */
  result: LineItem | null;
  /** 1-based position, for the field ids and the substance heading. */
  position: number;
  catalogue: UnitCatalogue | null;
  /** The id the row's toggle points at with `aria-controls`. */
  id: string;
  onChange: (patch: Partial<DraftLine>) => void;
  onWeightChange?: (field: "weight_each_kg" | "weight_total_kg", value: number | null) => void;
}

/** Whether this line carries dangerous goods, by any of the three routes: the
 *  user ticked it, they took a suggested UN number, or the calculation found
 *  one in the description. */
export function isDangerous(line: DraftLine, result: LineItem | null): boolean {
  return !!(line.dangerous_goods || line.confirmed_un || result?.dangerous_goods);
}

export default function LineDetails({
  line,
  result,
  position,
  catalogue,
  id,
  onChange,
  onWeightChange,
}: Props) {
  const { t } = useTranslation();
  // The articles library lives beside the history; without one there is
  // nothing to pick from and the field stays away.
  const hasArticles = !!usePreferences().publicSettings?.history_enabled;

  const round = ROUND_TYPES.has(result?.product_type ?? "");
  const productType = result?.product_type;
  const showWall = Boolean(productType && WALL_PROFILE_TYPES.has(productType));
  const wallMissing = result?.messages.includes("wall_thickness_missing");
  const forms = (result?.material_category && catalogue?.forms_by_category[result.material_category]) || [];

  const number = (field: "length_cm" | "width_cm" | "height_cm" | "wall_thickness_mm") =>
    (event: React.ChangeEvent<HTMLInputElement>) =>
      onChange({ [field]: event.target.value === "" ? "" : Number(event.target.value) });

  const field = (name: string) => `line-${position}-${name}`;

  return (
    <div
      id={id}
      className="mt-2 rounded-xl border border-slate-200 bg-slate-50/60 dark:border-slate-700 dark:bg-slate-950/40"
    >
        <div className="space-y-4 px-3 py-3 sm:px-4">
          {result?.density_reference && <details className="text-sm">
            <summary className="cursor-pointer font-medium">{t("densities.sourceDetails")}</summary>
            <div className="pt-2"><DensityReference value={result.density_reference} /></div>
          </details>}
          {hasArticles && (
            <div>
              <span className={labelClass}>{t("articles.onLine")}</span>
              <div className="mt-1">
                <ArticleCombobox
                  value={line.article?.code}
                  onPick={(article) =>
                    onChange({
                      article: {
                        code: article.code, name: article.name, un_number: article.un_number,
                        proper_shipping_name: article.proper_shipping_name, technical_name: article.technical_name,
                        class: article.class, packing_group: article.packing_group,
                        type_of_package: article.type_of_package, net_per_package: article.net_per_package,
                      },
                      description: line.description.trim() ? line.description : article.name || article.code,
                      // A UN number on the article flags the line and travels
                      // to the DG step the way a confirmed suggestion does.
                      ...(article.un_number ? { dangerous_goods: true, confirmed_un: article.un_number } : {}),
                      ...(article.net_per_package ? { package_content: article.net_per_package } : {}),
                    })
                  }
                  onClear={() => onChange({ article: undefined })}
                />
              </div>
            </div>
          )}
          {/* The description, the quantity and the unit are not repeated here.
              In a dialog over the list they had to be — the list was behind
              it. Open under the row, they are one line above, and a second
              copy of a field is a second place for the answer to be wrong. */}

          {/* Only for goods whose stored density describes the material itself;
              for gravel, grain or a liquid the density already describes it as
              it is carried. */}
          {forms.length > 0 && (
            <div>
              <label className={labelClass} htmlFor={field("cargo-form")}>
                {t("review.cargoForm")}
              </label>
              <select
                id={field("cargo-form")}
                className={`${inputClass} mt-1`}
                value={line.cargo_form ?? result?.cargo_form ?? ""}
                onChange={(event) => onChange({ cargo_form: event.target.value })}
              >
                {forms.map((form) => (
                  <option key={form} value={form}>
                    {t(`forms.${form}`, form)}
                  </option>
                ))}
              </select>
            </div>
          )}

          <fieldset>
            <legend className={labelClass}>{t("review.dimensions")}</legend>
            <div className={`mt-1 grid gap-3 ${round ? "sm:grid-cols-2" : "sm:grid-cols-3"}`}>
              <Measure
                label={t("review.length_cm")}
                id={field("length")}
                value={line.length_cm ?? ""}
                placeholder={result?.length_cm}
                onChange={number("length_cm")}
              />
              <Measure
                // With a round cross-section the width *is* the diameter, and
                // the field says so rather than the heading having to.
                label={round ? t("review.diameter") : t("review.width_cm")}
                id={field("width")}
                value={line.width_cm ?? ""}
                placeholder={result?.width_cm}
                onChange={number("width_cm")}
              />
              {!round && (
                <Measure
                  label={t("review.height_cm")}
                  id={field("height")}
                  value={line.height_cm ?? ""}
                  placeholder={result?.height_cm}
                  onChange={number("height_cm")}
                />
              )}
            </div>
          </fieldset>

          {showWall && (
            <div>
              <label className={labelClass} htmlFor={field("wall")}>
                {t("review.wallThickness")}
              </label>
              <NumberInput
                id={field("wall")}
                step="0.1"
                inputMode="decimal"
                className={`${numberClass} mt-1 ${wallMissing ? "border-amber-400 dark:border-amber-600" : ""}`}
                value={line.wall_thickness_mm ?? ""}
                onChange={number("wall_thickness_mm")}
              />
            </div>
          )}

          {result && onWeightChange && (
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className={labelClass} htmlFor={field("weight-each")}>
                  {t("review.weightEach")}
                </label>
                <NumberInput
                  id={field("weight-each")}
                  step="0.01"
                  inputMode="decimal"
                  className={`${numberClass} mt-1`}
                  value={result.weight_each_kg ?? ""}
                  onChange={(event) =>
                    onWeightChange(
                      "weight_each_kg",
                      event.target.value === "" ? null : Number(event.target.value),
                    )
                  }
                />
              </div>
              <div>
                <label className={labelClass} htmlFor={field("weight-total")}>
                  {t("review.weightTotal")}
                </label>
                <NumberInput
                  id={field("weight-total")}
                  step="0.01"
                  inputMode="decimal"
                  className={`${numberClass} mt-1`}
                  value={result.weight_total_kg ?? ""}
                  onChange={(event) =>
                    onWeightChange(
                      "weight_total_kg",
                      event.target.value === "" ? null : Number(event.target.value),
                    )
                  }
                />
              </div>
            </div>
          )}

          {/* The calculation marks a line dangerous when it reads a UN number
              in the description, and says so on the row. A tick that stayed
              empty next to that told the user the opposite of what the row
              said, so it follows the calculation until somebody sets it
              themselves — and unticking then means what it says. */}
          <label className="flex items-center gap-2.5 rounded-lg border border-slate-200 px-3 py-2.5 dark:border-slate-700">
            <input
              type="checkbox"
              checked={line.dangerous_goods ?? result?.dangerous_goods ?? false}
              onChange={(event) => onChange({ dangerous_goods: event.target.checked })}
              className="h-4 w-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500"
            />
            <span className={labelClass}>{t("review.dangerousGoods")}</span>
            {line.confirmed_un && (
              <span className="ml-auto rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                UN {line.confirmed_un}
              </span>
            )}
          </label>

          {isDangerous(line, result) && (
            <fieldset className="rounded-lg border border-amber-200 bg-amber-50/60 px-3 py-3 dark:border-amber-900/50 dark:bg-amber-950/20">
              <legend className="px-1 text-sm font-medium text-amber-900 dark:text-amber-200">
                {t("review.substanceTitle")}
              </legend>
              <p className="text-xs text-amber-900 dark:text-amber-300">{t("review.substanceHint")}</p>
              <div className="mt-2 grid gap-3 sm:grid-cols-2">
                <div>
                  <label className={labelClass} htmlFor={field("un")}>
                    {t("review.unNumber")}
                  </label>
                  <input
                    id={field("un")}
                    className={`${inputClass} mt-1`}
                    value={line.confirmed_un ?? ""}
                    inputMode="numeric"
                    // What the recogniser read out of the description stands
                    // here as the placeholder, not as the value. It is what
                    // the dangerous goods step will start from if nobody says
                    // otherwise — but nobody has said it yet, and a field
                    // that fills itself in has answered on the user's behalf.
                    placeholder={result?.detected_un_numbers?.[0] ?? ""}
                    // Typing a UN number is declaring the line dangerous.
                    // Clearing it says nothing about that either way, so the
                    // tick is left exactly as the user set it.
                    onChange={(event) => {
                      const un = event.target.value.trim();
                      onChange(un ? { confirmed_un: un, dangerous_goods: true } : { confirmed_un: undefined });
                    }}
                  />
                </div>
                <div>
                  <label className={labelClass} htmlFor={field("packing-group")}>
                    {t("review.packingGroup")}
                  </label>
                  <select
                    id={field("packing-group")}
                    className={`${inputClass} mt-1`}
                    value={line.packing_group ?? ""}
                    onChange={(event) => onChange({ packing_group: event.target.value || undefined })}
                  >
                    <option value="">{t("review.derivedLater")}</option>
                    <option value="I">I</option>
                    <option value="II">II</option>
                    <option value="III">III</option>
                  </select>
                </div>
              </div>
              <div className="mt-3">
                <label className={labelClass} htmlFor={field("psn")}>
                  {t("review.properShippingName")}
                </label>
                <input
                  id={field("psn")}
                  className={`${inputClass} mt-1`}
                  placeholder={t("review.derivedLater")}
                  value={line.proper_shipping_name ?? ""}
                  onChange={(event) => onChange({ proper_shipping_name: event.target.value || undefined })}
                />
              </div>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <div>
                  <label className={labelClass} htmlFor={field("package-type")}>
                    {t("review.typeOfPackage")}
                  </label>
                  <input
                    id={field("package-type")}
                    className={`${inputClass} mt-1`}
                    value={line.type_of_package ?? ""}
                    onChange={(event) => onChange({ type_of_package: event.target.value || undefined })}
                  />
                </div>
                <div>
                  <label className={labelClass} htmlFor={field("package-content")}>
                    {t("review.netPerPackage")}
                  </label>
                  <input
                    id={field("package-content")}
                    className={`${inputClass} mt-1`}
                    value={line.package_content ?? ""}
                    onChange={(event) => onChange({ package_content: event.target.value || undefined })}
                  />
                </div>
              </div>
            </fieldset>
          )}
        </div>
    </div>
  );
}

function Measure({
  label,
  id,
  value,
  placeholder,
  onChange,
}: {
  label: string;
  id: string;
  value: number | "";
  /** What was read out of the description; what the user fills in beats it. */
  placeholder?: number | null;
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <div>
      <label className="text-xs text-slate-500 dark:text-slate-400" htmlFor={id}>
        {label}
      </label>
      <NumberInput
        id={id}
        step="0.1"
        inputMode="decimal"
        aria-label={label}
        placeholder={placeholder != null ? String(placeholder) : ""}
        className={`${numberClass} mt-0.5`}
        value={value}
        onChange={onChange}
      />
    </div>
  );
}
