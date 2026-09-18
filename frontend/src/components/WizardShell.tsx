/**
 * The frame around a shipment.
 *
 * Until this release the wizard's furniture was four strips stacked on top of
 * each other — a modality chip with a link beside it, a row of step segments, a
 * draft line, and then, at the bottom of whichever step was open, that step's
 * own pair of buttons. Every strip was added by the release that needed it and
 * none of them knew about the others, so the first screenful of a shipment was
 * mostly chrome and the button that moves you forward sat wherever the step
 * happened to end.
 *
 * This is one header and one action bar instead:
 *
 * - **The header** says which shipment this is, what has happened to it (the
 *   draft line), where you are in it (the steps) and which transport mode it
 *   is being entered for — the mode as a *switcher*, not a chooser. Choosing
 *   where to begin is `/`, and it stays there; this changes the mode of the
 *   shipment already in front of you.
 * - **The action bar** is `sticky bottom-0`, not `fixed`, and the difference
 *   is worth being exact about because it was measured. A sticky bar is still
 *   in the layout: it takes its own height at the end of the page, so the last
 *   row of a long form — and the error standing next to it — is never left
 *   underneath it. A fixed bar is out of the layout and covers that last row
 *   permanently, with no scroll position that reveals it. What sticky does not
 *   claim is that it never overlaps anything at all: while you are scrolled
 *   above its resting place it floats over what is behind it, the way every
 *   bar of this kind does. That overlap is transient and one scroll away; the
 *   one a fixed bar creates is not.
 *
 * Steps render their buttons through `WizardActions`, which puts them in the
 * bar. Rendered without a shell around it — as the steps' own tests do — it
 * falls back to a plain row in place, so a component stays testable on its own.
 */
import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import WizardProgress, { WizardStepKey } from "./WizardProgress";
import { AirIcon, InlandIcon, MultimodalIcon, RailIcon, RoadIcon, SeaIcon } from "./icons";

interface Slot {
  el: HTMLElement | null;
  /** Says whether anything is in the bar, so an empty bar is not drawn. */
  register: (present: boolean) => void;
}

const SlotContext = createContext<Slot | null>(null);

const actionRow = "wizard-actions flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3";

/** A step's buttons, placed in the shell's action bar. */
export function WizardActions({ children }: { children: ReactNode }) {
  const slot = useContext(SlotContext);
  const register = slot?.register;
  useEffect(() => {
    if (!register) return;
    register(true);
    return () => register(false);
  }, [register]);

  if (!slot) return <div className={actionRow}>{children}</div>;
  if (!slot.el) return null;
  return createPortal(<div className={actionRow}>{children}</div>, slot.el);
}

/** The glyph for a transport mode, so the switcher shows what it switches to. */
export function ModalityIcon({ modality, className }: { modality: string; className?: string }) {
  switch (modality) {
    case "rail":
      return <RailIcon className={className} />;
    case "sea":
      return <SeaIcon className={className} />;
    case "inland":
      return <InlandIcon className={className} />;
    case "multimodal":
      return <MultimodalIcon className={className} />;
    case "air":
      return <AirIcon className={className} />;
    default:
      return <RoadIcon className={className} />;
  }
}

interface Step {
  n: number;
  key: WizardStepKey;
  label: string;
}

interface Props {
  /** What this shipment is called — its reference, or that it is a new one. */
  title: string;
  modality: string;
  /** The modes this installation will draw documents for. */
  modalities: readonly string[];
  onModality: (key: string) => void;
  steps: Step[];
  currentStep: number;
  visited?: WizardStepKey[];
  onGoTo?: (key: WizardStepKey) => void;
  /** The draft line, built by the page that knows what may be stored. */
  draft?: ReactNode;
  /** The shipment's editable reference, visible before every step. */
  reference?: ReactNode;
  /** The assistant's button, which belongs beside the title and nowhere else. */
  aside?: ReactNode;
  /** How many things are waiting to be looked at, counted by the caller. */
  attention?: number;
  /** What the shipment adds up to, beside the work rather than after it. */
  panel?: ReactNode;
  children: ReactNode;
  secondaryAction?: ReactNode;
}

export default function WizardShell({
  title, modality, modalities, onModality, steps, currentStep, visited, onGoTo,
  draft, reference, aside, attention = 0, panel, children, secondaryAction,
}: Props) {
  const { t } = useTranslation();
  const [el, setEl] = useState<HTMLElement | null>(null);
  const [filled, setFilled] = useState(0);
  const register = useCallback((present: boolean) => {
    setFilled((n) => n + (present ? 1 : -1));
  }, []);
  const slot = useMemo<Slot>(() => ({ el, register }), [el, register]);

  const index = Math.max(0, steps.findIndex((s) => s.n === currentStep));

  return (
    <SlotContext.Provider value={slot}>
      <div className="wizard-shell page-enter space-y-4 sm:space-y-6">
        <header className="wizard-header">
          <div className="wizard-title-block">
            <div className="flex items-center gap-2">
              <h2 className="min-w-0 flex-1 break-words text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h2>
              {aside}
            </div>
            <div className="mt-2 text-sm text-slate-500 dark:text-slate-400">{draft}</div>
            {reference}
          </div>
          <div className="wizard-progress-wrap">
            <p className="wizard-progress-copy">{t("wizard.progressStep", { current: index + 1, total: steps.length })} — {steps[index]?.label}</p>
            <WizardProgress steps={steps} currentStep={currentStep} visited={visited} onGoTo={onGoTo} />
          </div>
          {modalities.length > 0 && <div className="wizard-mode-block">
            <label className="wizard-mode flex items-center gap-3 rounded-lg border border-slate-300 px-3 dark:border-slate-700">
              <ModalityIcon modality={modality} className="h-6 w-6 shrink-0 text-slate-400" />
              <select value={modality} onChange={(event) => onModality(event.target.value)} aria-label={t("wizard.mode")} className="min-h-[48px] min-w-0 flex-1 bg-transparent text-sm font-semibold">
                {modalities.map((key) => <option key={key} value={key}>{t(`modality.${key}`)}{({ road: " (ADR)", rail: " (RID)", sea: " (IMDG)", inland: " (ADN)" } as Record<string, string>)[key] ?? ""}</option>)}
              </select>
            </label>
            <Link to="/?choose=1" className="mt-1 block text-right text-xs text-slate-500 hover:underline dark:text-slate-400">{t("wizard.changeModality")}</Link>
          </div>}
        </header>

        {panel && <details className="wizard-mobile-summary"><summary>{t("studio.summary")}</summary><div>{panel}</div></details>}

        {/* `flex-row-reverse` puts the panel on the right on a wide screen
            while it stays first in the document, which is where it belongs on
            a narrow one: above the work rather than under it, where nobody
            scrolls past a form to find the totals. */}
        <div className="flex flex-col gap-4 xl:flex-row-reverse xl:items-start xl:gap-6">
          {panel && (
            <aside className="wizard-summary xl:sticky xl:top-24 xl:w-72 xl:shrink-0">{panel}</aside>
          )}
          <div className="min-w-0 flex-1">{children}</div>
        </div>

        <div
          className={
            filled > 0
              ? "wizard-action-bar sticky bottom-0 z-30 -mx-3 border-t border-slate-200 bg-white/95 px-3 py-3 backdrop-blur sm:-mx-4 sm:px-4 dark:border-slate-800 dark:bg-slate-900/95"
              : "hidden"
          }
        >
          <div className="wizard-action-layout">
            {secondaryAction}
            {/* One count, in one place at a time. From `xl` the panel is on
                the screen and carries it; below that there is no panel beside
                the work, so the bar says it. */}
            {attention > 0 ? (
              <p className={`text-xs font-medium text-amber-700 dark:text-amber-300 ${panel ? "xl:hidden" : ""}`}>
                {t("wizard.attention", { count: attention })}
              </p>
            ) : null}
            <div ref={setEl} className="wizard-action-slot" />
          </div>
        </div>
      </div>
    </SlotContext.Provider>
  );
}
