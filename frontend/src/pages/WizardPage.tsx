import TemporaryDelivery from "../components/TemporaryDelivery";
import { canManage } from "../permissions";
import type { User } from "../api/client";
import CargoWorkspace from "../components/cargo/CargoWorkspace";
import { cargoApi, type CargoManifest, type CargoAssessment } from "../api/cargo";
import { emptyCargo, cloneCargo, bindReusableCargo } from "../utils/cargo";
import { cargoLines, cargoGoods, migrateCargo, templateCargoDrafts, editCargo, preservesCargo } from "../wizard/cargoState";
import { containerAutoValues } from "../utils/containerValues";
import { equipmentPatch } from "../utils/equipment";
import { useDgReview } from "../wizard/useDgReview";
import { ArrowRightIcon, ChevronDownIcon, DownloadIcon, DocumentIcon } from "../components/icons";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, Navigate, useLocation, useNavigate, useParams, useSearchParams } from "react-router";
import { useTranslation } from "react-i18next";
import {
  api,
  CalcResult,
  DgEntry,
  DocumentDefinition,
  DocumentExportPayload,
  DocumentRegistry,
  LocalizedText,
  ShipmentIn,
  ShipmentSummary,
  UnCardsAvailability,
  WrittenInstruction,
  UserPreferences,
} from "../api/client";
import { documentLanguage, localised, LANGUAGE_NAMES, SUPPORTED_LANGUAGES, Language } from "../i18n/language";
import DangerousGoodsStep, { buildDgEntries } from "../components/DangerousGoodsStep";
import DgCompliancePanel from "../components/DgCompliancePanel";
import { groupDocumentWarnings, useDocumentValidation } from "../components/DocumentWarnings";
import AiIcon from "../components/AiIcon";
import AssistantModal from "../components/AssistantModal";
import DocumentFieldsStep, { resolveSections } from "../components/DocumentFieldsStep";
import DocumentAdvicePanel, { buildAdvice } from "../components/DocumentAdvicePanel";
import ReviewLinesPanel, { DraftLine, draftToText, openQuestions, textToDraftLines } from "../components/ReviewLinesPanel";
import DraftBar, { DraftStatus } from "../components/DraftBar";
import CheckYourAnswers, { AnswerRow } from "../components/CheckYourAnswers";
import WizardShell, { WizardActions } from "../components/WizardShell";
import ShipmentPanel, { PanelDocument } from "../components/ShipmentPanel";
import { AVAILABLE_MODALITIES, isModalityAvailable } from "./ModalitySelectPage";
import { usePreferences } from "../settings/preferences";
import { SNAPSHOT_VERSION, WizardSnapshot, readSnapshot, templateValues } from "../wizard/snapshot";
import { addedQuestions } from "../wizard/documentGroups";
import {
  applyLineWeightChange,
  recalcTotals,
  scaleLinesToTotalWeight,
  weightOverridesFromLines,
  dimensionOverridesFromDrafts,
  mergeOverrides,
} from "../utils/lineWeights";
import { buildAssistantState, draftLinesFromAssistant, wizardDgEntriesFromAssistant, retainAssistantDgAnswers } from "../utils/assistantState";
import { DocumentEvidenceList } from "../components/DocumentIntake";
import type { DocumentEvidence } from "../api/client";
import { useToast } from "../toast/ToastProvider";
import NumberInput from "../components/NumberInput";

const weightInputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm";
const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const buttonSecondary =
  "px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 min-h-[44px] text-sm";
const buttonPrimary =
  "bg-brand-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50 min-h-[44px] text-sm";

type StepKey = "lines" | "dg" | "details" | "export";

/** Dates that mean "drawn up today" and may therefore start as today. The
 *  operational dates (loading, requested departure) are facts of the trip and
 *  are never guessed. */
const TODAY_DATE_FIELDS = new Set([
  "established_date",
  "declaration_date",
  "document_date",
  "determination_date",
]);

const LAST_SHIPMENT_KEY = "emcargo:last-shipment";

type DocStatus = "ready" | "draft" | "blocked" | "not_applicable";

const DG_BASE_REQUIRED = ["un_number", "proper_shipping_name", "class"] as const;
const DG_PROFILE_REQUIRED: Record<string, string[]> = {
  ADR: [...DG_BASE_REQUIRED],
  RID: [...DG_BASE_REQUIRED],
  ADN: [...DG_BASE_REQUIRED],
  IMDG: [...DG_BASE_REQUIRED, "quantity_packages", "type_of_package"],
  IATA_DGR: [
    ...DG_BASE_REQUIRED,
    "packing_instruction",
    "quantity_packages",
    "type_of_package",
    "net_mass_liters_per_package",
  ],
};

const DG_EXTRA_FIELDS: Record<string, string[]> = {
  // The mode comes first because it decides what the rest of the answers mean:
  // admission, the tunnel code and the placarding all branch on it, and until
  // v1.66.0 a tank load silently got the answers for packages.
  // The tank's own code comes straight after the mode that makes it relevant:
  // column (12) says which code the substance requires, and ADR 4.3 decides
  // whether the tank standing on the yard may carry it. The field only shows
  // once the mode says a tank is involved.
  // The tank's own code, then what 4.3.2.2 needs to say how full it may be.
  // All four only show once the mode says a tank is involved.
  // The three special cases of 5.4.1.1.3/.5/.6 change what the description
  // line must say, and none of them is derivable from the UN number: whether
  // the goods are waste is a fact about the consignment.
  // The temperature the goods are offered at. It is on every mode that has a
  // chapter 5.3, because the elevated temperature mark turns on it and nothing
  // else in the consignment implies it — MOLTEN says the substance travels
  // liquid, not how hot, and a substance that is not molten can be loaded hot.
  ADR: ["carriage_mode", "tank_code", "filling_temperature", "density_15",
        "density_50", "transport_category", "adr_total_quantity",
        "is_waste", "empty_uncleaned", "salvage_packaging",
        "molten", "residue_classes", "classified_2_1_2_8",
        "carriage_temperature"],
  // Full load is the consignor's own statement (a wagon-level fact no table
  // supplies) and it decides the shunting labels of 5.3.4 for class 1 and the
  // orange-plate permission of 5.3.2.1.1.
  RID: ["carriage_mode", "transport_category", "adr_total_quantity",
        "full_load", "is_waste", "empty_uncleaned", "salvage_packaging",
        "molten", "residue_classes", "classified_2_1_2_8",
        "carriage_temperature"],
  // Where it goes on the vessel: 7.1.4.11.1 asks the boatmaster to say which
  // goods are in which hold or on deck, and no table can answer that.
  ADN: ["carriage_mode", "hold", "container_number", "containers_only",
        "transport_category", "adr_total_quantity", "is_waste",
        "empty_uncleaned", "salvage_packaging", "molten", "residue_classes",
        "classified_2_1_2_8", "carriage_temperature"],
  IMDG: ["technical_name", "marine_pollutant", "ems_code", "emergency_contact",
         "carriage_temperature"],
  IATA_DGR: [
    "technical_name",
    "cargo_aircraft_only",
    "overpack",
    "emergency_contact",
    "q_net_quantity",
    "q_max_net_quantity",
  ],
};

/** Which saved detail belongs in which document field.
 *
 * The consignor, the haulier and the loading point are the same on nearly every
 * consignment the same person makes, and were retyped every time. Only empty
 * fields are filled: a prefill that overwrites what someone just typed is worse
 * than no prefill at all. */
const PREFILL_FIELDS: Record<string, keyof UserPreferences> = {
  consignor_name: "consignor_name",
  consignor_address: "consignor_address",
  consignor_contact: "consignor_contact",
  carrier_name: "carrier_name",
  loading_point: "loading_point",
};

const HEADER_FIELDS = ["shipment_reference"];

const MODALITY_DG_PROFILES: Record<string, string[]> = {
  road: ["ADR"],
  rail: ["RID"],
  inland: ["ADN"],
  sea: ["IMDG"],
  air: ["IATA_DGR"],
  multimodal: ["ADR", "IATA_DGR", "IMDG"],
};

export default function WizardPage({ user }: { user?: User } = {}) {
  const { t, i18n } = useTranslation();
  const { modality } = useParams();
  const lang = documentLanguage(i18n.language);
  const L = (text?: LocalizedText) => localised(text, lang);
  // The language the documents are drawn up in is not the language the screen
  // is in. ADR 5.4.1.4.1 (and RID and ADN in the same words) asks for an
  // official language of the forwarding country and, where that is not German,
  // English or French, additionally one of those three — which is about the
  // consignment, not about who is typing. So it is a choice, defaulting to the
  // screen's language because that is right more often than not.
  const [chosenDocLang, setChosenDocLang] = useState<Language | null>(null);
  const docLang = chosenDocLang ?? lang;
  const { preferences, publicSettings, loaded: preferencesLoaded } = usePreferences();
  const prefill = preferencesLoaded && preferences.prefill_documents;

  const [registry, setRegistry] = useState<DocumentRegistry | null>(null);
  const [registryError, setRegistryError] = useState("");
  const [stepKey, setStepKey] = useState<StepKey>("lines");
  // null means "the advice decides": the selection follows the shipment until
  // the user touches it, and from that moment it is theirs.
  const [selectedDocs, setSelectedDocs] = useState<string[] | null>(null);
  const [docValues, setDocValues] = useState<Record<string, string>>({});
  const setShipmentReference = (value: string) => setDocValues((current) => ({
    ...current,
    shipment_reference: value,
    // Keep an imported legacy alias in sync so clearing the field cannot
    // make the old reference reappear in the shipment list.
    ...("reference" in current ? { reference: value } : {}),
  }));
  // Questions skipped in the assistant. Part of the travelling state: the
  // server is stateless, so forgetting these here re-asks them every turn.
  const [skippedQuestions, setSkippedQuestions] = useState<string[]>([]);
  const [draftLines, setDraftLines] = useState<DraftLine[]>([{ id: 1, description: "", quantity: 1, unit: "pcs" }]);
  const [nextId, setNextId] = useState(2);
  const [cargo, setCargo] = useState<CargoManifest>(emptyCargo);
  const cargoBaseRevision = useRef<number | null>(null);
  const cargoSaving = useRef(false);
  const [linesView, setLinesView] = useState<"goods" | "cargo">("goods");
  const [cargoOpened, setCargoOpened] = useState(false);
  const [cargoAssessmentState, setCargoAssessmentState] = useState<{ key: string; value: CargoAssessment | null; error: string } | null>(null);
  const [result, setResult] = useState<CalcResult | null>(null);
  const cargoInputLines = useMemo(() => cargoLines(draftLines, result), [draftLines, result]);
  const displayedCargoGoods = useMemo(() => cargoGoods(cargoInputLines, cargo), [cargoInputLines, cargo]);
  const cargoUsed = cargo.units.length > 0 || cargo.revision > 0 || cargoBaseRevision.current != null;
  const cargoPayload = cargoUsed ? cargo : undefined;
  const cargoKey = cargoUsed ? JSON.stringify({ cargo, lines: cargoInputLines }) : "";
  const cargoAssessment = cargoAssessmentState?.key === cargoKey ? cargoAssessmentState.value : null;
  const cargoFailure = cargoAssessmentState?.key === cargoKey ? cargoAssessmentState.error : "";
  useEffect(() => {
    if (!cargoKey) return;
    let active = true;
    const timer = setTimeout(() => {
      cargoApi.assess(cargo, cargoInputLines).then(value => {
        if (active) setCargoAssessmentState({ key: cargoKey, value, error: "" });
      }).catch(error => {
        if (active) setCargoAssessmentState({ key: cargoKey, value: null, error: String(error) });
      });
    }, 200);
    return () => { active = false; clearTimeout(timer); };
  }, [cargoKey]);
  const [dgEntries, setDgEntries] = useState<DgEntry[]>([]);
  const [signature, setSignature] = useState<string | null>(null);
  const [documentEvidence, setDocumentEvidence] = useState<DocumentEvidence[]>([]);
  const [loading, setLoading] = useState(false);
  const [exportingDoc, setExportingDoc] = useState<string | null>(null);
  const [unCards, setUnCards] = useState<UnCardsAvailability | null>(null);
  const [instructions, setInstructions] = useState<WrittenInstruction[]>([]);
  const [checklist, setChecklist] = useState<WrittenInstruction[]>([]);
  const [unCardsBusy, setUnCardsBusy] = useState(false);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const assistantDraftSignature = useRef<string | null>(null);
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  // The history, where the installation keeps its shipments. `?shipment=`
  // in the address reopens a kept one; the id then travels with the wizard
  // so that keeping it again brings the same row up to date rather than
  // adding a second. Downloading the documents keeps the shipment as well —
  // "the shipments made" is what the page lists, and a download is what
  // makes one.
  const [searchParams] = useSearchParams();
  // `?shipment=` reopens a kept shipment as itself; `?template=` starts a
  // new shipment from one, so it is restored without its identity, its
  // reference, or its dates.
  const templateId = searchParams.get("template");
  const reopenId = searchParams.get("shipment") ?? templateId;
  const reviewSourceId = searchParams.get("review");
  const asTemplate = !searchParams.get("shipment") && !!templateId;
  const historyOn = !!publicSettings?.history_enabled;
  /** The fields the registry marks as a declaration somebody signs for.
   *  A shipment copied as a template arrives without them ticked. */
  const declarationKeys = useMemo(() => {
    const keys = new Set<string>();
    if (!registry) return keys;
    const collect = (fields: { key: string; status: string }[] | undefined) => {
      for (const field of fields ?? []) if (field.status === "SIGNATURE_REQUIRED") keys.add(field.key);
    };
    for (const section of registry.shared_sections) collect(section.fields);
    for (const doc of registry.documents) for (const section of doc.sections) collect(section.fields);
    return keys;
  }, [registry]);

  /** The last few kept shipments, offered as a starting point on the goods
   *  step. Only where there is a history to read, and only while nothing has
   *  been entered — an offer, not an interruption. */
  const [recent, setRecent] = useState<ShipmentSummary[]>([]);

  const [historyId, setHistoryId] = useState<number | null>(null);
  const [keeping, setKeeping] = useState(false);
  const [keptAt, setKeptAt] = useState<Date | null>(null);
  const restoreKey = reviewSourceId ? `review:${reviewSourceId}` : reopenId
    ? `${asTemplate ? "template" : "shipment"}:${reopenId}`
    : historyOn ? `draft:${modality}` : null;
  const restoredSource = useRef<string | null>(null);
  const carriedEntry = useRef(false);
  const [settledRestoreKey, setSettledRestoreKey] = useState<string | null>(null);
  const [restoreError, setRestoreError] = useState(false);
  const [restoreAttempt, setRestoreAttempt] = useState(0);
  const restorePending = !preferencesLoaded || (restoreKey !== null && settledRestoreKey !== restoreKey);

  useEffect(() => {
    api
      .documentsRegistry()
      .then(value => setRegistry({ ...value, modalities: [...value.modalities, { key: "preparation", label: { nl: "Voorbereiding", en: "Preparation", de: "Vorbereitung", fr: "Préparation" }, description: { nl: "Modaliteit later kiezen", en: "Choose transport mode later", de: "Verkehrsträger später wählen", fr: "Choisir le mode de transport plus tard" }, documents: ["packing_list", "delivery_note", "shipment_export"] }], modality_defaults: { ...value.modality_defaults, preparation: "packing_list" } }))
      .catch((e) => setRegistryError(String(e)));
  }, []);

  useEffect(() => {
    if (!historyOn || reopenId || reviewSourceId) return;
    api
      .shipments({ per_page: 3 })
      .then((page) => setRecent(page.items))
      .catch(() => setRecent([]));
  }, [historyOn, reopenId, reviewSourceId]);

  // The saved details land in the form as soon as they arrive, and only in
  // fields that are still empty — the preferences come back over the network,
  // so someone may already have started typing by then.
  useEffect(() => {
    if (!prefill) return;
    setDocValues((current) => {
      const filled = { ...current };
      for (const [field, key] of Object.entries(PREFILL_FIELDS)) {
        const value = String(preferences[key] ?? "");
        if (value && !(filled[field] ?? "").trim()) filled[field] = value;
      }
      return filled;
    });
  }, [prefill, preferences]);

  // A signature that was drawn once in the settings. Never overwrites one drawn
  // for this shipment.
  useEffect(() => {
    if (prefill && preferences.signature_image) {
      setSignature((current) => current ?? preferences.signature_image);
    }
  }, [prefill, preferences.signature_image]);

  // The previous shipment's details, saved at export. The same consignor ships
  // to the same handful of parties; retyping them every ride was the details
  // step's whole cost. Dates stay out: last week's date on today's document
  // would be a wrong answer prefilled.
  const [lastShipment] = useState<Record<string, string> | null>(() => {
    try {
      return JSON.parse(localStorage.getItem(LAST_SHIPMENT_KEY) ?? "null");
    } catch {
      return null;
    }
  });
  const reuseLastShipment = () => {
    if (!lastShipment) return;
    setDocValues((current) => {
      const filled = { ...current };
      for (const [key, value] of Object.entries(lastShipment)) {
        if (key.endsWith("_date") || !String(value ?? "").trim()) continue;
        if (!(filled[key] ?? "").trim()) filled[key] = String(value);
      }
      return filled;
    });
  };

  // The discharge point defaults to the consignee's own address line the
  // moment the details step is done — only while the user typed nothing else,
  // and visibly editable on the way back.
  const completeDetails = () => {
    setDocValues((current) => {
      if ((current.discharge_point ?? "").trim() || !(current.consignee_address ?? "").trim()) {
        return current;
      }
      const lines = current.consignee_address
        .split(/\n/)
        .map((line) => line.trim())
        .filter(Boolean);
      const place = lines[lines.length - 1];
      return place ? { ...current, discharge_point: place } : current;
    });
    setStepKey("export");
  };

  // A blank starting line still carries the default unit; the moment something
  // has been typed it is left alone.
  useEffect(() => {
    if (!preferencesLoaded || !preferences.default_unit) return;
    setDraftLines((lines) =>
      lines.some((line) => line.description.trim())
        ? lines
        : lines.map((line) => ({ ...line, unit: preferences.default_unit })),
    );
  }, [preferencesLoaded, preferences.default_unit]);

  const modalityDef = registry?.modalities.find((m) => m.key === modality);

  /** Going to one field and coming back.
   *
   *  A missing detail used to be named as text on the export step, and getting
   *  to it meant pressing Back, finding the right form among the sub-steps,
   *  finding the field on it, filling it, and walking forward again — the
   *  baseline counted eleven actions and four step changes for one field. The
   *  chip now carries the field's key; the details step opens the form it is
   *  on and puts the cursor in it, and its primary action goes straight back
   *  to where the question was asked. */
  const [focusField, setFocusField] = useState<string | null>(null);
  const [returnTo, setReturnTo] = useState<StepKey | null>(null);
  // Steps the user has been on, so the progress bar knows what is worth
  // offering as a way back.
  const [visited, setVisited] = useState<StepKey[]>(["lines"]);

  useEffect(() => {
    setVisited((seen) => (seen.includes(stepKey) ? seen : [...seen, stepKey]));
    if (!focusField) window.scrollTo({ top: 0, behavior: "auto" });
  }, [stepKey]);

  const goToField = (key: string) => {
    if (key === "cargo") { setStepKey("lines"); setLinesView("cargo"); return; }
    if (key === "shipment_reference") {
      const field = document.getElementById("field-shipment_reference");
      field?.focus();
      field?.scrollIntoView?.({ block: "center", behavior: "smooth" });
      return;
    }
    if (key === "goods_complete") { setStepKey("lines"); return; }
    setReturnTo(stepKey);
    setFocusField(key);
    setStepKey("details");
  };

  /** What the last change to the document set added to the form. Choosing a
   *  document is a choice about paperwork, and the honest answer to "and now
   *  what do I have to fill in?" is usually *nothing* — its questions were
   *  already being asked. Where it is not nothing, the questions are named and
   *  reachable, and nothing else happens. */
  const [addedByDoc, setAddedByDoc] = useState<{ label: string; count: number; first: string | null } | null>(null);

  const returnFromField = () => {
    const back = returnTo ?? "export";
    setReturnTo(null);
    setStepKey(back);
  };

  // A substance suggestion nobody answered is not an answer. It stays visible
  // to the end, because "we thought this might be UN 1203 and never found out"
  // is exactly what a document check is for.
  const unanswered = useMemo(
    () => openQuestions(draftLines, result?.lines),
    [draftLines, result],
  );

  /** What is waiting to be looked at, in one number: what the calculation
   *  flagged on the goods plus the substance questions nobody has answered.
   *  Two counts for two kinds of "not right yet" is two counts to reconcile. */
  const attention = (result?.totals.warning_count ?? 0) + unanswered;

  const needsDg = useMemo(
    () =>
      result?.lines.some(
        (line) =>
          line.include &&
          (line.dangerous_goods || (line.detected_un_numbers?.length ?? 0) > 0),
      ) ?? false,
    [result],
  );

  // The advice assembles the document set from the shipment; the user adjusts
  // it where the questions are, before answering them. Until they do, the
  // selection follows the shipment — a DG line appearing pulls the transport
  // document and the DG papers in.
  const advice = useMemo(
    () => (registry && modalityDef ? buildAdvice(registry, modalityDef.key, needsDg) : null),
    [registry, modalityDef, needsDg],
  );
  const selected = selectedDocs ?? advice?.preselected ?? [];

  const selectedDefinitions = useMemo(
    () =>
      selected
        .map((key) => registry?.documents.find((d) => d.key === key))
        .filter((d): d is DocumentDefinition => !!d),
    [selected, registry],
  );

  const genericDocs = selectedDefinitions;

  /** Change the document set and say what that added to the form. */
  const chooseDocuments = (keys: string[]) => {
    const after = keys
      .map((key) => registry?.documents.find((d) => d.key === key))
      .filter((d): d is DocumentDefinition => !!d);
    const fresh = keys.filter((key) => !selected.includes(key));
    if (registry && fresh.length === 1) {
      const doc = after.find((d) => d.key === fresh[0]);
      const added = addedQuestions(registry, selectedDefinitions, after);
      // The way in goes to the first question that is actually needed; the
      // count says how many came with it.
      const first = added.find((field) => field.status === "USER_REQUIRED") ?? added[0];
      if (doc) {
        setAddedByDoc({
          label: L(doc.label),
          count: added.length,
          first: first?.key ?? null,
        });
      }
    } else {
      setAddedByDoc(null);
    }
    setSelectedDocs(keys);
  };

  // "Drawn up on" dates start as today — that is what they mean — and each
  // field is defaulted at most once, so a date the user deliberately cleared
  // stays cleared. The operational dates (loading, departure) are facts of
  // the trip and never guessed.
  const datesDefaulted = useRef<Set<string>>(new Set());
  useEffect(() => {
    if (!registry) return;
    const today = new Date().toISOString().slice(0, 10);
    setDocValues((current) => {
      const filled = { ...current };
      let changed = false;
      for (const doc of selectedDefinitions) {
        for (const section of resolveSections(doc, registry)) {
          for (const field of section.fields ?? []) {
            if (
              field.type === "date" &&
              TODAY_DATE_FIELDS.has(field.key) &&
              !datesDefaulted.current.has(field.key) &&
              !(filled[field.key] ?? "").trim()
            ) {
              filled[field.key] = today;
              datesDefaulted.current.add(field.key);
              changed = true;
            }
          }
        }
      }
      return changed ? filled : current;
    });
  }, [registry, selectedDefinitions]);

  const dgProfiles = useMemo(() => {
    const profiles = new Set<string>(MODALITY_DG_PROFILES[modality ?? ""] ?? []);
    for (const doc of selectedDefinitions) {
      if (doc.dg_profile) profiles.add(doc.dg_profile);
    }
    return [...profiles];
  }, [selectedDefinitions, modality]);

  const dgExtraFields = useMemo(() => {
    const fields: string[] = [];
    for (const profile of dgProfiles) {
      for (const field of DG_EXTRA_FIELDS[profile] ?? []) {
        if (!fields.includes(field)) fields.push(field);
      }
    }
    return fields;
  }, [dgProfiles]);

  const steps: StepKey[] = useMemo(() => {
    const list: StepKey[] = ["lines"];
    if (needsDg) list.push("dg");
    if (genericDocs.length > 0) list.push("details");
    list.push("export");
    return list;
  }, [needsDg, genericDocs.length]);

  const stepPills = [
    { n: 1, key: "lines" as const, label: t("wizard.stageGoods") },
    ...(genericDocs.length > 0 ? [{ n: 2, key: "details" as const, label: t("wizard.stageDetails") }] : []),
    { n: 3, key: "export" as const, label: t("wizard.stageReview") },
  ];

  const goNextFrom = (from: StepKey) => {
    const index = steps.indexOf(from);
    const next = steps[index + 1];
    if (next) setStepKey(next);
  };

  const goBackFrom = (from: StepKey) => {
    const index = steps.indexOf(from);
    const prev = steps[Math.max(0, index - 1)];
    if (prev) setStepKey(prev);
  };

  // Not only "is this a modality" but "may documents be drawn up for it". A
  // bookmark to /wizard/rail is the route that skips every tile.
  if (!isModalityAvailable(modality)) {
    return <Navigate to="/?choose=1" replace />;
  }

  const updateResultLines = (lines: CalcResult["lines"]) => {
    setResult((prev) => (prev ? { ...prev, lines, totals: recalcTotals(lines) } : prev));
  };

  const calculateFromDraft = async (): Promise<CalcResult | null> => {
    if (draftLines.some(line => line.quantity_unconfirmed)) {
      toast.error(t("assistant.quantityNeeded"));
      return null;
    }
    const text = draftToText(draftLines);
    if (!text.trim()) {
      toast.error(t("review.noLines"));
      return null;
    }
    setLoading(true);
    // Assistant answers belong to this exact draft. A recalculation must not
    // erase the DG facts the guided interview has just collected.
    if (assistantDraftSignature.current !== signatureOf(draftLines)) setDgEntries([]);
    try {
      const res = await api.calculate({
        text,
        mode: "continue",
        input_language: null,
        // Dimensions come from the input and therefore have to count towards the
        // very first calculation; weight corrections only exist once there is a
        // result to correct.
        line_overrides: mergeOverrides(
          dimensionOverridesFromDrafts(draftLines),
          result && assistantDraftSignature.current !== signatureOf(draftLines) ? weightOverridesFromLines(result.lines) : [],
        ),
      });
      // Apply the DG ticks of the packages (same order as the non-empty lines),
      // and the UN number a user confirmed from a name suggestion: that answer
      // travels to the DG step so nothing recognised is typed twice.
      const flagged = draftLines.filter((l) => l.description.trim());
      const withDg = {
        ...res,
        lines: res.lines.map((line, i) => ({
          ...line,
          cargo_goods_id: flagged[i]?.id ?? line.line_id,
          dangerous_goods: Boolean(line.dangerous_goods || flagged[i]?.dangerous_goods),
          article: flagged[i]?.article ?? null,
          detected_un_numbers: flagged[i]?.confirmed_un
            ? [
                flagged[i].confirmed_un as string,
                ...(line.detected_un_numbers ?? []).filter((un) => un !== flagged[i].confirmed_un),
              ]
            : line.detected_un_numbers,
        })),
      };
      setResult(withDg);
      return withDg;
    } catch (e) {
      toast.error(String(e));
      return null;
    } finally {
      setLoading(false);
    }
  };

  /**
   * What was entered, as one string.
   *
   * If this changes, the weight shown is no longer right. Manual weight
   * corrections are deliberately not in it: those are an *answer* to a
   * calculation and would otherwise set themselves off again.
   */
  const signatureOf = (lines: DraftLine[]) =>
    JSON.stringify(
      lines.map((line) => [
        line.equipment, line.equipment_role, line.container_line_id,
        line.description.trim(),
        line.quantity,
        line.unit,
        line.cargo_form ?? "",
        line.length_cm ?? "",
        line.width_cm ?? "",
        line.height_cm ?? "",
        line.wall_thickness_mm ?? "",
        line.weight_each_kg ?? "",
        line.weight_total_kg ?? "",
      ]),
    );
  const draftSignature = signatureOf(draftLines);

  // Recalculating used to be a button, and a button you have to press to see a
  // correct figure is a button that gets forgotten — with a stale weight on the
  // screen as the result. Now it happens by itself, shortly after the typing
  // stops. The delay is there so as not to send a request on every keystroke.
  const calculatedSignature = useRef<string | null>(null);
  useEffect(() => {
    if (restorePending || assistantOpen || draftLines.some(line => line.quantity_unconfirmed || line.unconfirmed_weight_kg != null)) return;
    if (stepKey !== "lines" && assistantDraftSignature.current !== draftSignature) return;
    if (!draftLines.some((line) => line.description.trim())) return;
    if (calculatedSignature.current === draftSignature) return;

    const timer = setTimeout(() => {
      calculatedSignature.current = draftSignature;
      void calculateFromDraft();
    }, 600);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftSignature, stepKey, restorePending, modality, assistantOpen]);

  const addLine = () => {
    const unit = preferences.default_unit || "pcs";
    setDraftLines((lines) => [...lines, { id: nextId, description: "", quantity: 1, unit }]);
    setNextId((n) => n + 1);
  };

  const removeLine = (id: number) => {
    if (cargo.allocations.some(item => item.goods_id === id) || cargo.units.some(unit => unit.legacy_goods_id === id)) {
      setLinesView("cargo"); toast.error(t("cargoIntegration.assignedGoods")); return;
    }
    setDraftLines((lines) => lines.filter((l) => l.id !== id));
    setResult(null);
  };

  const duplicateLine = (id: number) => {
    setDraftLines((lines) => {
      const index = lines.findIndex((l) => l.id === id);
      if (index === -1) return lines;
      const copy: DraftLine = { ...lines[index], id: nextId };
      return [...lines.slice(0, index + 1), copy, ...lines.slice(index + 1)];
    });
    setNextId((n) => n + 1);
    setResult(null);
  };

  /** An import, and the way back out of it.
   *
   *  Replacing what is already there is the one action on this step that
   *  destroys work, so it hands back the lines it replaced: the snackbar's
   *  **Ongedaan maken** puts them back, with the numbering they had. That is
   *  what makes offering "replace" at all reasonable. */
  const handleImport = (text: string, importMode: "append" | "replace") => {
    const before = draftLines;
    const beforeId = nextId;
    const beforeResult = result;
    const beforeCargo = cargo;
    let added = 0;
    if (importMode === "replace") {
      setCargo(previous => ({ ...previous, units: [], allocations: [], revision: previous.revision + 1 }));
      const lines = textToDraftLines(text);
      added = lines.length;
      setDraftLines(lines);
      setNextId(Math.max(...lines.map((l) => l.id), 0) + 1);
    } else {
      const imported = textToDraftLines(text, nextId);
      added = imported.length;
      setNextId((n) => n + imported.length);
      setDraftLines((prev) => [...prev.filter((l) => l.description.trim()), ...imported]);
    }
    setResult(null);
    toast.info(
      t(importMode === "replace" ? "wizard.importReplaced" : "wizard.importAppended", { count: added }),
      {
        actions: [{
          label: t("wizard.importUndo"),
          run: () => {
            setDraftLines(before);
            setNextId(beforeId);
            setResult(beforeResult);
            setCargo(beforeCargo);
            toast.success(t("wizard.importUndone"));
          },
        }],
      },
    );
  };

  const handleLineWeightChange = (
    lineId: number,
    field: "weight_each_kg" | "weight_total_kg",
    value: number | null,
  ) => {
    if (!result) return;
    updateResultLines(applyLineWeightChange(result.lines, lineId, field, value));
    const id = draftLines.filter(line => line.description.trim())[lineId - 1]?.id;
    // An entered weight is input, so later dimension edits must not erase it.
    setDraftLines(lines => lines.map(line => line.id === id ? {
      ...line, weight_each_kg: undefined, weight_total_kg: undefined,
      [field]: value == null || !Number.isFinite(value) ? undefined : value,
    } : line));
  };

  const handleTotalWeightChange = (value: number | null) => {
    if (!result || value == null || Number.isNaN(value)) return;
    const scaled = scaleLinesToTotalWeight(result.lines, value);
    updateResultLines(scaled);
    const ids = draftLines.filter(line => line.description.trim()).map(line => line.id);
    setDraftLines(lines => lines.map(line => {
      const item = scaled[ids.indexOf(line.id)];
      return item?.include ? { ...line, weight_each_kg: undefined, weight_total_kg: item.weight_total_kg ?? undefined } : line;
    }));
  };

  /** The 24-hour emergency number, which IMDG 5.4.1.5.11 and the IATA DGR
   *  shipper's declaration both ask for. It never changes and was typed again
   *  for every product on every consignment. */
  const withEmergencyContact = (entries: DgEntry[]): DgEntry[] => {
    const contact = prefill ? preferences.emergency_contact : "";
    if (!contact) return entries;
    return entries.map((entry) => ({
      ...entry,
      products: entry.products.map((product) =>
        (product.emergency_contact ?? "").trim() ? product : { ...product, emergency_contact: contact },
      ),
    }));
  };

  const goFromLines = async () => {
    const res = await calculateFromDraft();
    if (!res) return;
    const hasDg = res.lines.some(
      (line) => line.include && (line.dangerous_goods || (line.detected_un_numbers?.length ?? 0) > 0),
    );
    if (hasDg) {
      // The lines as typed travel with the computed ones, so what the user
      // answered about a substance on its own line is what the step starts
      // from rather than something it asks for again.
      const prepared = buildDgEntries(res.lines, draftLines.filter(line => line.description.trim()));
      setDgEntries(withEmergencyContact(assistantDraftSignature.current === signatureOf(draftLines)
        ? retainAssistantDgAnswers(prepared, dgEntries) : prepared));
      setStepKey("dg");
    } else if (genericDocs.length > 0) {
      setStepKey("details");
    } else {
      setStepKey("export");
    }
  };

  const autoValues = useMemo(
    () => containerAutoValues(result, docValues.container_number ?? ""),
    [result, docValues.container_number],
  );

  const exportValuesFor = (doc: DocumentDefinition): Record<string, string> => {
    if (!registry) return docValues;
    const merged = { ...docValues };
    for (const section of resolveSections(doc, registry)) {
      for (const field of section.fields ?? []) {
        if (field.auto_from && !(merged[field.key] ?? "").trim()) {
          const auto = autoValues[field.auto_from as keyof typeof autoValues];
          if (auto) merged[field.key] = auto;
        }
      }
    }
    return merged;
  };

  const docStatus = (doc: DocumentDefinition): {
    status: DocStatus;
    /** The fields that are missing, by key *and* label: the label is what the
     *  card says, the key is what takes the user to the field itself. */
    missing: { key: string; label: string }[];
    waitingCarrier: boolean;
  } => {
    if (!registry) return { status: "draft", missing: [], waitingCarrier: false };
    if (cargoUsed && (!cargoAssessment || cargoFailure || cargoAssessment.issues.some(issue => /exceeded|invalid|missing|cycle|allocated/.test(issue.code)))) {
      return { status: "blocked", missing: [{ key: "cargo", label: t("cargoIntegration.checkCargo") }], waitingCarrier: false };
    }
    if (doc.dg_only && !needsDg) return { status: "not_applicable", missing: [], waitingCarrier: false };
    if (cargoUsed && cargo.units.some(unit => unit.kind === "package") && ["cim", "iata_dgd", "imo_dgd", "adn_transport_doc", "bl_si", "awb_si", "iftdgn", "vgm"].includes(doc.key)) {
      return { status: "blocked", missing: [{ key: "cargo", label: t("errors.cargo.document_unsupported", { document: L(doc.label) }) }], waitingCarrier: false };
    }
    if (cargoUsed && ["cmr", "avc_waybill", "packing_list", "delivery_note", "vgm", "imo_dgd", "bl_si", "iftdgn"].includes(doc.key) && cargoAssessment?.totals.cargo_gross_kg == null) {
      return { status: "blocked", missing: [{ key: "cargo", label: t("errors.cargo.documents_incomplete") }], waitingCarrier: false };
    }
    const values = exportValuesFor(doc);
    const missing: { key: string; label: string }[] = [];
    if (["cmr", "avc_waybill"].includes(doc.key)) {
      const goods = result?.lines.filter((line) => line.include) ?? [];
      if (!goods.length || goods.some((line) => !line.description.trim() || !(Number(line.quantity) > 0) || !(Number(line.weight_total_kg) > 0))) {
        missing.push({ key: "goods_complete", label: t("errors.documents.goods_incomplete") });
      }
    }
    let waitingCarrier = false;
    for (const section of resolveSections(doc, registry)) {
      for (const field of section.fields ?? []) {
        const value = (values[field.key] ?? "").trim();
        if (field.status === "USER_REQUIRED" && !value) missing.push({ key: field.key, label: L(field.label) });
        if (field.status === "CARRIER_PROVIDED" && !value) waitingCarrier = true;
      }
    }
    if (doc.dg_profile && (doc.dg_only || dgEntries.length > 0)) {
      const required = DG_PROFILE_REQUIRED[doc.dg_profile] ?? [...DG_BASE_REQUIRED];
      const incomplete =
        dgEntries.length === 0 ||
        dgEntries.some((entry) =>
          entry.products.some((product) =>
            required.some((field) => !String(product[field as keyof typeof product] ?? "").trim()),
          ),
        );
      if (incomplete) return { status: "blocked", missing, waitingCarrier };
    }
    if (missing.length > 0) return { status: "draft", missing, waitingCarrier };
    return { status: "ready", missing: [], waitingCarrier };
  };

  // One payload builder for validation and export both, so that what is
  // validated is what is exported by construction. These used to be able to
  // drift — and did: the validate endpoint had no caller at all, so every
  // warning it computed (missing unit, lost exemption, VGM mismatch, eleven
  // more) was thrown away twice over. The signature is export-only; validation
  // does not read it.
  const payloadFor = (doc: DocumentDefinition): DocumentExportPayload => ({
    document_key: doc.key,
    values: exportValuesFor(doc),
    lines: cargoInputLines,
    cargo: cargoPayload,
    dangerous_goods: dgEntries.length > 0 ? dgEntries : undefined,
    output_language: docLang,
    // The regimes this consignment travels under. Only the documents that
    // answer differently per regime read it, and the package label sheet is
    // the first: the IMDG Code marks the proper shipping name on every package
    // where the land regimes ask for it on Class 1 and Class 7 only. Sending
    // it from the one payload builder means validation and export cannot
    // disagree about which rules were applied.
    profiles: dgProfiles,
    modality: modality === "preparation" ? undefined : modality,
  });

  // Warnings per document, shown on the card before the download button — a
  // warning after the file is on disk is a warning shown too late. This runs
  // whether or not there are dangerous goods: the VGM mass check warns on a
  // plain sea consignment.
  const docWarnings = useDocumentValidation(
    stepKey === "export" && result ? selectedDefinitions.filter(doc => {
      const info = docStatus(doc);
      // Known cargo failures already have a precise recovery action. Sending
      // them to validation produces a 422, not an unavailable service.
      return !(info.status === "blocked" && info.missing.some(field => field.key === "cargo"));
    }).map(payloadFor) : [],
    stepKey === "export" && !!result,
    t("exportFocus.validationFailed"),
  );

  const exportGenericDoc = async (doc: DocumentDefinition) => {
    if (!result || docStatus(doc).status !== "ready") return;
    setExportingDoc(doc.key);
    try {
      await api.exportDocument({
        ...payloadFor(doc),
        dg_review_id: dgReview.id,
        signature_image: signature ?? undefined,
      });
      // What was exported is worth offering next time.
      try {
        localStorage.setItem(LAST_SHIPMENT_KEY, JSON.stringify(docValues));
      } catch {
        // Storage full or blocked: the export succeeded, the memory is a bonus.
      }
      if (historyOn) void keepInHistory(true);
    } catch (e) {
      toast.error(String(e));
    } finally {
      setExportingDoc(null);
    }
  };

  // One click for the whole pack: every selected document that is ready,
  // plus the UN cards and the instructions in writing for this journey's
  // regimes, in one archive. Drafts and blocked documents stay behind —
  // bundling an incomplete paper would hide that it is incomplete, and the
  // server writes anything it must leave out into the archive's README.
  const readyDocs = selectedDefinitions.filter((doc) => docStatus(doc).status === "ready");
  const [downloadingAll, setDownloadingAll] = useState(false);
  //: Whether the package has been handed over on this screen. A document in
  //: the Downloads folder is not a document that reached the driver.
  const [handedOver, setHandedOver] = useState(false);
  const downloadAll = async () => {
    setDownloadingAll(true);
    try {
      await api.exportBundle({
        dg_review_id: dgReview.id,
        documents: readyDocs.map(payloadFor),
        cargo: cargoPayload,
        dangerous_goods: dgEntries.length > 0 ? dgEntries : undefined,
        profiles: dgProfiles,
        output_language: docLang,
        signature_image: signature ?? undefined,
      });
      try {
        localStorage.setItem(LAST_SHIPMENT_KEY, JSON.stringify(docValues));
      } catch {
        // Storage full or blocked: the export succeeded, the memory is a bonus.
      }
      // A download is what makes a shipment "made": it goes into the history
      // without a second press, where the installation keeps one.
      if (historyOn) void keepInHistory(true);
      // Having a document is not having sent it, and the moment somebody has
      // just pressed the finishing button is the moment to say so.
      setHandedOver(true);
    } catch (e) {
      toast.error(String(e));
    } finally {
      setDownloadingAll(false);
    }
  };

  /** The wizard's own state as one document: what a kept shipment reopens
   *  with, and what a draft is made of. */
  const wizardSnapshot = (): WizardSnapshot => ({
    version: SNAPSHOT_VERSION,
    cargo,
    cargoBaseRevision: cargoBaseRevision.current,
    modality: modality ?? "",
    stepKey,
    docLang: chosenDocLang,
    selectedDocs,
    docValues,
    skippedQuestions,
    draftLines,
    nextId,
    result,
    dgEntries,
    signature,
    documentEvidence,
  });

  /** The shipment as the server takes it. A draft carries no bundle: nothing
   *  has been produced yet, and the row stays small enough to write often. */
  const shipmentPayload = (draft: boolean): ShipmentIn => ({
    expected_cargo_revision: cargoPayload ? cargoBaseRevision.current : undefined,
    modality: modality === "preparation" ? "" : modality ?? "",
    language: docLang,
    profiles: dgProfiles,
    values: docValues,
    lines: cargoInputLines,
    cargo: cargoPayload,
    dangerous_goods: dgEntries.length > 0 ? dgEntries : undefined,
    documents: selected,
    bundle:
      !draft && readyDocs.length > 0
        ? {
            documents: readyDocs.map(payloadFor),
            cargo: cargoPayload,
            dangerous_goods: dgEntries.length > 0 ? dgEntries : undefined,
            profiles: dgProfiles,
            output_language: docLang,
            signature_image: signature ?? undefined,
          }
        : null,
    snapshot: wizardSnapshot() as unknown as Record<string, unknown>,
    draft,
  });

  const reviewRequired = (dgEntries.length > 0 || (result?.lines.some(line => line.include && line.dangerous_goods) ?? false)) && publicSettings?.dg_review_enabled !== false;
  const dgReview = useDgReview(shipmentPayload(false), reviewRequired, stepKey === "export" && preferencesLoaded && !restorePending, reviewSourceId);

  // --- the draft: what happens to the entry while it is being made ----------
  //
  // The baseline reloaded halfway through a shipment and found the wizard back
  // at the goods step with nothing left of what had been typed. Where the
  // installation keeps shipments, the running entry is kept as a draft — its
  // own row, not on the shipments page, not in the adviser's report, and its
  // author's alone — and a reload comes back to it on the step it was on.
  // Where nothing may be stored, nothing is: there the draft is a file the
  // user keeps, and leaving warns first.

  /** Whether there is anything to lose yet.
   *
   *  The dates the wizard fills in by itself do not count: a shipment nobody
   *  has typed a word into is not entry in progress, and a draft written for
   *  every visit to an empty wizard is a row per glance. */
  const hasEntry =
    draftLines.some((line) => (line.description ?? "").trim()) ||
    Object.entries(docValues).some(
      ([key, value]) => (value ?? "").trim() && !datesDefaulted.current.has(key),
    );

  const [draftStatus, setDraftStatus] = useState<DraftStatus>("idle");
  const [draftSavedAt, setDraftSavedAt] = useState<Date | null>(null);
  //: The body last written, so nothing is saved twice and a render is not a change.
  const draftBody = useRef<string>("");
  const draftTimer = useRef<number | undefined>(undefined);
  const pendingDraft = useRef<Promise<unknown>>(Promise.resolve());
  const [closing, setClosing] = useState(false);

  // Queue writes so an older autosave cannot overwrite the final explicit save.
  const persistDraft = (payload: ShipmentIn) => {
    const write = pendingDraft.current.catch(() => undefined).then(async () => {
      const saved = await api.saveDraft({ ...payload, expected_cargo_revision: payload.cargo ? cargoBaseRevision.current : undefined });
      if (payload.cargo) cargoBaseRevision.current = saved.cargo_revision ?? null;
      return saved;
    });
    pendingDraft.current = write;
    return write;
  };
  const saveAndClose = async () => {
    if (closing) return;
    setClosing(true);
    window.clearTimeout(draftTimer.current);
    try {
      setDraftStatus("saving");
      if (keptAt && historyId) {
        await pendingDraft.current.catch(() => undefined);
        const saved = await api.updateShipment(historyId, { ...shipmentPayload(false), expected_cargo_revision: cargoPayload ? cargoBaseRevision.current : undefined });
        if (cargoPayload) cargoBaseRevision.current = saved.cargo_revision ?? null;
      } else await persistDraft(shipmentPayload(true));
      navigate("/overzicht");
    } catch {
      setDraftStatus("failed");
      setClosing(false);
    }
  };

  useEffect(() => {
    if (restorePending || !historyOn || !hasEntry || reopenId || reviewSourceId || closing || keeping || keptAt) return;
    const payload = shipmentPayload(true);
    const body = JSON.stringify(payload);
    if (body === draftBody.current) return;
    window.clearTimeout(draftTimer.current);
    draftTimer.current = window.setTimeout(() => {
      if (cargoSaving.current) return;
      setDraftStatus("saving");
      persistDraft(payload)
        .then((saved) => {
          draftBody.current = body;
          setHistoryId((current) => current ?? saved.id);
          setDraftSavedAt(new Date(saved.updated_at));
          setDraftStatus("saved");
        })
        // Said, not swallowed: "could not save" is the one thing a draft must
        // never keep to itself.
        .catch(() => setDraftStatus("failed"));
    }, 2500);
    return () => window.clearTimeout(draftTimer.current);
    // The payload is rebuilt from these; the body comparison does the rest.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [historyOn, hasEntry, reopenId, reviewSourceId, stepKey, draftLines, docValues, result, dgEntries,
      selectedDocs, signature, chosenDocLang, skippedQuestions, documentEvidence, cargo, closing, restorePending, keeping, keptAt]);

  // Finish a read before allowing entry or autosave. Marking it restored when
  // the request started stranded StrictMode and registry-cancelled responses;
  // treating a failed draft read as empty could autosave over unseen work.
  useEffect(() => {
    if (!preferencesLoaded || !registry || !restoreKey) return;
    if (readSnapshot((location.state as { carry?: unknown } | null)?.carry)) return;
    if (restoredSource.current === restoreKey || (!reopenId && carriedEntry.current)) {
      setSettledRestoreKey(restoreKey);
      return;
    }
    let cancelled = false;
    setRestoreError(false);
    const request = reviewSourceId
      ? api.dgReview(reviewSourceId).then(review => ({ snapshot: review.shipment.snapshot, id: 0, updated_at: review.created_at, reference: review.reference, consignee_name: "" }))
      : reopenId ? api.shipment(Number(reopenId)) : api.runningDraft();
    request
      .then(async (detail) => {
        if (cancelled || restoredSource.current === restoreKey || (!reopenId && carriedEntry.current)) return;
        if (reopenId && !detail) throw new Error("Missing shipment");
        if (detail) {
          const snap = readSnapshot(detail.snapshot);
          if (!snap) throw new Error("Invalid shipment snapshot");
          if (reopenId || !snap.modality || snap.modality === modality) {
            let restoredCargo = migrateCargo(snap.draftLines, snap.cargo);
            if (restoredCargo.units.some(unit => unit.legacy_goods_id != null && unit.equipment_id != null)) {
              restoredCargo = bindReusableCargo(restoredCargo, (await Promise.all([...new Set(restoredCargo.units.filter(unit => unit.equipment_id != null).map(unit => unit.equipment_id!))].map(id => cargoApi.reusableUnits("", id)))).flat());
              if (cancelled) return;
            }
            setCargo(asTemplate ? cloneCargo(restoredCargo) : restoredCargo);
            cargoBaseRevision.current = asTemplate || reviewSourceId ? null : ("cargo_revision" in detail ? Number(detail.cargo_revision) : snap.cargoBaseRevision) ?? null;
            setDraftLines(asTemplate ? templateCargoDrafts(snap.draftLines, restoredCargo) : snap.draftLines);
            setDocumentEvidence(asTemplate ? [] : snap.documentEvidence ?? []);
            setNextId(snap.nextId);
            setResult(asTemplate ? null : snap.result);
            setDgEntries(snap.dgEntries);
            setDocValues(asTemplate ? templateValues(snap.docValues, declarationKeys) : snap.docValues);
            setSelectedDocs(snap.selectedDocs);
            setSkippedQuestions(snap.skippedQuestions);
            setSignature(asTemplate ? null : snap.signature);
            setChosenDocLang(snap.docLang as Language | null);
            setStepKey(asTemplate ? "lines" : snap.stepKey);
            setHistoryId(asTemplate || reviewSourceId ? null : detail.id);
            setKeptAt(reopenId && !asTemplate ? new Date(detail.updated_at) : null);
            if (!reopenId && !reviewSourceId) {
              setDraftSavedAt(new Date(detail.updated_at));
              setDraftStatus("saved");
              draftBody.current = "";
              toast.info(t("draft.resumed"));
            } else if (asTemplate) {
              toast.info(t("history.templateOpened", { reference: detail.reference || detail.consignee_name || "" }));
            }
          }
        }
        restoredSource.current = restoreKey;
        setSettledRestoreKey(restoreKey);
      })
      .catch(() => { if (!cancelled) setRestoreError(true); });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [restoreKey, reopenId, reviewSourceId, asTemplate, modality, registry, preferencesLoaded, restoreAttempt, location.state]);

  // --- switching transport mode without losing the shipment -----------------
  //
  // The mode is part of the address, so changing it is a navigation and this
  // page may remain mounted. What was typed travels in the
  // navigation's own state: the goods, the answers, the substances, the
  // signature. The calculation does not travel. It was made against the rules
  // of the mode you have just left, and carrying it over would put totals on
  // the screen that claim to come from a book they were never read out of. So
  // the entry survives, the judgement is made again, and the wizard lands back
  // on the goods step where the recalculation starts.
  const carryRestored = useRef<unknown>(null);
  useEffect(() => {
    const carried = (location.state as { carry?: unknown } | null)?.carry;
    if (!carried || carryRestored.current === carried) return;
    const snap = carried ? readSnapshot(carried) : null;
    if (!snap) return;
    carryRestored.current = carried;
    // The draft on the server is the old mode's; this entry replaces it rather
    // than being overwritten by it when the fetch comes back.
    carriedEntry.current = true;
    restoredSource.current = restoreKey;
    setSettledRestoreKey(restoreKey);
    setCargo(migrateCargo(snap.draftLines, snap.cargo));
    cargoBaseRevision.current = snap.cargoBaseRevision ?? null;
    setDraftLines(snap.draftLines);
    setDocumentEvidence(snap.documentEvidence ?? []);
    setNextId(snap.nextId);
    setDgEntries(snap.dgEntries);
    setDocValues(snap.docValues);
    setSkippedQuestions(snap.skippedQuestions);
    setSignature(snap.signature);
    setChosenDocLang(snap.docLang as Language | null);
    setResult(null);
    setSelectedDocs(null);
    setStepKey("lines");
    const origin = location.state as { sourceShipmentId?: number; keptAt?: string } | null;
    setHistoryId(origin?.sourceShipmentId ?? null);
    setKeptAt(origin?.keptAt ? new Date(origin.keptAt) : null);
    calculatedSignature.current = null;
    // Without this the entry would come back a second time on a reload, on top
    // of whatever had been typed since.
    navigate(location.pathname + location.search, { replace: true });
    // A new carry can arrive while React Router reuses this component.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state, location.pathname, restoreKey]);

  const switchModality = (next: string) => {
    if (!next || next === modality) return;
    navigate(`/wizard/${next}${keptAt && historyId ? `?shipment=${historyId}` : ""}`, { state: hasEntry ? { carry: wizardSnapshot(), sourceShipmentId: historyId, keptAt: keptAt?.toISOString() } : undefined });
    if (hasEntry) toast.info(t("wizard.modeCarried", { mode: t(`modality.${next}`) }));
  };

  const discardDraft = () => {
    window.clearTimeout(draftTimer.current);
    void api.discardDraft().catch(() => undefined);
    draftBody.current = "";
    setDraftStatus("idle");
    setDraftSavedAt(null);
    setHistoryId(null);
    setDraftLines([{ id: 1, description: "", quantity: 1, unit: "pcs" }]);
    setDocumentEvidence([]);
    setNextId(2);
    setCargo(emptyCargo());
    cargoBaseRevision.current = null;
    setLinesView("goods");
    setResult(null);
    setDgEntries([]);
    setDocValues({});
    setSelectedDocs(null);
    setSkippedQuestions([]);
    setSignature(null);
    setStepKey("lines");
  };

  // Where nothing is stored: the browser's own question before the entry is
  // lost, and the draft as a file so the answer can be "yes, I have it".
  useEffect(() => {
    if (historyOn || !hasEntry) return;
    const ask = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", ask);
    return () => window.removeEventListener("beforeunload", ask);
  }, [historyOn, hasEntry]);

  const downloadDraft = () => {
    const blob = new Blob([JSON.stringify(wizardSnapshot(), null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `emcargo-concept-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const openDraftFile = async (file: File) => {
    try {
      const snap = readSnapshot(JSON.parse(await file.text()));
      if (!snap) {
        toast.error(t("draft.notADraft"));
        return;
      }
      let importedCargo = migrateCargo(snap.draftLines, snap.cargo);
      if (importedCargo.units.some(unit => unit.legacy_goods_id != null && unit.equipment_id != null)) {
        importedCargo = bindReusableCargo(importedCargo, (await Promise.all([...new Set(importedCargo.units.filter(unit => unit.equipment_id != null).map(unit => unit.equipment_id!))].map(id => cargoApi.reusableUnits("", id)))).flat());
      }
      setCargo(importedCargo);
      cargoBaseRevision.current = snap.cargoBaseRevision ?? null;
      setHistoryId(null);
      setKeptAt(null);
      setDraftLines(snap.draftLines);
      setDocumentEvidence(snap.documentEvidence ?? []);
      setNextId(snap.nextId);
      setResult(snap.result);
      setDgEntries(snap.dgEntries);
      setDocValues(snap.docValues);
      setSelectedDocs(snap.selectedDocs);
      setSkippedQuestions(snap.skippedQuestions);
      setSignature(snap.signature);
      setChosenDocLang(snap.docLang as Language | null);
      setStepKey(snap.stepKey);
      toast.success(t("draft.opened"));
    } catch {
      toast.error(t("draft.notADraft"));
    }
  };

  // Keeping the shipment in the history. The server builds the structured
  // export from the same parts the download uses and keeps the bundle for
  // "the documents again"; the snapshot is this page's own state and comes
  // back untouched when the shipment is reopened.
  const keepInHistory = async (quietly = false) => {
    if (!historyOn || !result || cargoSaving.current) return;
    cargoSaving.current = true;
    window.clearTimeout(draftTimer.current);
    setKeeping(true);
    try {
      const payload = shipmentPayload(false);
      payload.dg_review_id = dgReview.id;
      if (payload.bundle) payload.bundle.dg_review_id = dgReview.id;
      await pendingDraft.current.catch(() => undefined);
      payload.expected_cargo_revision = payload.cargo ? cargoBaseRevision.current : undefined;
      const kept = historyId
        ? await api.updateShipment(historyId, payload)
        : await api.keepShipment(payload);
      if (payload.cargo) cargoBaseRevision.current = kept.cargo_revision ?? null;
      setHistoryId(kept.id);
      setKeptAt(new Date(kept.updated_at));
      if (!quietly) toast.success(t("history.keptToast"));
    } catch (e) {
      toast.error(String(e));
    } finally {
      cargoSaving.current = false;
      setKeeping(false);
    }
  };

  // The way back. The drums that just went out come home empty and uncleaned,
  // and the return is the outward consignment read backwards — same drums,
  // same substance, the two parties the other way round.
  //
  // The turn itself is the server's, because what may *not* come back is a
  // regulatory judgement rather than a copying convenience: every quantity the
  // outward consignment stated would be false on an empty drum, and a form
  // that carries the number over invites somebody to sign for it.
  //
  // It lands the user back on the goods step rather than leaving them on the
  // export step looking at documents for a shipment that no longer matches
  // what is loaded.
  const [turningRound, setTurningRound] = useState(false);
  const returnShipment = async () => {
    setTurningRound(true);
    try {
      const back = await api.dgReturn(docValues, result?.lines ?? [], dgEntries);
      setDocValues(back.values);
      setDgEntries(back.dangerous_goods);
      setStepKey(needsDg ? "dg" : "lines");
      toast.success(t("wizard.returnPrepared"));
    } catch (e) {
      toast.error(String(e));
    } finally {
      setTurningRound(false);
    }
  };

  // Mailing the same bundle. Offered only when an administrator configured a
  // mail server, because a button that can only fail is not a feature.
  const [mailOpen, setMailOpen] = useState(false);
  const [mailTo, setMailTo] = useState("");
  const [mailSubject, setMailSubject] = useState("");
  const [mailMessage, setMailMessage] = useState("");
  const [mailing, setMailing] = useState(false);

  const mailAll = async () => {
    setMailing(true);
    // Mailing takes as long as the mail server takes: the loading toast holds
    // the user's place until the send has actually succeeded or failed.
    const pending = toast.loading(t("wizardDocs.mailSending"));
    try {
      // One field, several addresses: a consignment's papers go to the
      // carrier and the consignee in the same breath.
      const recipients = mailTo
        .split(/[,;]/)
        .map((address) => address.trim())
        .filter(Boolean);
      const result = await api.mailBundle({
        bundle: {
          dg_review_id: dgReview.id,
          documents: readyDocs.map(payloadFor),
        cargo: cargoPayload,
          dangerous_goods: dgEntries.length > 0 ? dgEntries : undefined,
          profiles: dgProfiles,
          output_language: docLang,
          signature_image: signature ?? undefined,
        },
        to: recipients,
        subject: mailSubject,
        message: mailMessage,
      });
      pending.success(t("wizardDocs.mailSent", { to: result.to.join(", ") }));
      setMailOpen(false);
    } catch (e) {
      pending.error(String(e));
    } finally {
      setMailing(false);
    }
  };

  // Which UN cards this shipment can be given. Asked only on the export step,
  // and only when dangerous goods were actually declared.
  useEffect(() => {
    if (stepKey !== "export" || dgEntries.length === 0) {
      setUnCards(null);
      return;
    }
    let cancelled = false;
    api
      .unCardsAvailability({ dangerous_goods: dgEntries, profiles: dgProfiles, output_language: docLang })
      .then((status) => {
        if (!cancelled) setUnCards(status);
      })
      .catch(() => {
        if (!cancelled) setUnCards(null);
      });
    return () => {
      cancelled = true;
    };
  }, [stepKey, dgEntries, docLang]);

  // The instructions in writing of 5.4.3, which the crew has to carry with the
  // transport document. Asked for the regimes this shipment actually travels
  // under — ADR on the road, ADN on the water — and only when dangerous goods
  // were declared, because without them the document is not required.
  useEffect(() => {
    if (stepKey !== "export" || dgEntries.length === 0) {
      setInstructions([]);
      return;
    }
    let cancelled = false;
    api
      .writtenInstructions()
      .then((answer) => {
        if (!cancelled) setInstructions(answer.documents);
      })
      .catch(() => {
        if (!cancelled) setInstructions([]);
      });
    return () => {
      cancelled = true;
    };
  }, [stepKey, dgEntries]);

  const instructionRegimes = useMemo(
    () => ["adr", "rid", "adn"].filter((regime) => dgProfiles.includes(regime.toUpperCase())),
    [dgProfiles],
  );

  // ADN 8.6.3: the checklist that has to be filled in and signed before a tank
  // vessel is loaded or unloaded. It is asked for only when this shipment is
  // one — a dry cargo vessel does not fill it in, and a card that offered it
  // anyway would be telling the boatmaster something untrue about his trip.
  const inCargoTanks = useMemo(
    () =>
      dgProfiles.includes("ADN") &&
      dgEntries.some((entry) =>
        (entry.products ?? []).some((product) => product.carriage_mode === "tank"),
      ),
    [dgProfiles, dgEntries],
  );

  useEffect(() => {
    if (stepKey !== "export" || !inCargoTanks) {
      setChecklist([]);
      return;
    }
    let cancelled = false;
    api
      .models("8.6.3")
      .then((answer) => {
        if (!cancelled) setChecklist(answer.documents);
      })
      .catch(() => {
        if (!cancelled) setChecklist([]);
      });
    return () => {
      cancelled = true;
    };
  }, [stepKey, inCargoTanks]);

  const downloadChecklist = async (regime: string, language: string) => {
    try {
      await api.downloadModel("8.6.3", regime, language);
    } catch (e) {
      toast.error(String(e));
    }
  };

  const downloadInstructions = async (regime: string, language: string) => {
    try {
      await api.downloadInstructions(regime, language);
    } catch (e) {
      toast.error(String(e));
    }
  };

  const downloadUnCards = async () => {
    setUnCardsBusy(true);
    try {
      await api.downloadUnCards({ dangerous_goods: dgEntries, profiles: dgProfiles, output_language: docLang });
    } catch (e) {
      toast.error(String(e));
    } finally {
      setUnCardsBusy(false);
    }
  };

  /** The wizard state, in the shape the assistant exchanges. Result-derived
   *  facts (recognised candidates) ride along so the assistant asks about
   *  what the user already sees on the lines step. */
  const buildStateForAssistant = () =>
    buildAssistantState({
      modality,
      draftLines,
      resultLines: result?.lines,
      dgEntries,
      docValues,
      selectedDocs,
      skippedQuestions,
      documentEvidence,
    });

  /** What the assistant changed lands in the same state the classic wizard
   *  uses — switching between the two can therefore never lose data. */
  const applyAssistantState = (state: import("../api/client").AssistantState) => {
    const nextLines = draftLinesFromAssistant(state, draftLines);
    if (nextLines && !preservesCargo(nextLines, cargo)) {
      toast.error(t("cargoIntegration.assignedGoods")); setLinesView("cargo"); setStepKey("lines"); return;
    }
    setDocumentEvidence(state.document_evidence ?? []);
    if (nextLines) {
      if (signatureOf(nextLines) !== signatureOf(draftLines) || nextLines.some(line => line.unconfirmed_weight_kg != null)) {
        // A later-step correction must invalidate export data immediately.
        // The calculation effect refreshes it when the interview closes.
        setResult(null);
        calculatedSignature.current = null;
      }
      assistantDraftSignature.current = signatureOf(nextLines);
      setDraftLines(nextLines);
      if (!nextLines.length) { setResult(null); calculatedSignature.current = null; }
      setNextId(Math.max(0, ...nextLines.map(line => line.id)) + 1);
    }
    if (Array.isArray(state.dg_entries)) setDgEntries(wizardDgEntriesFromAssistant(state));
    if (state.doc_values) setDocValues(state.doc_values);
    if (Array.isArray(state.skipped_questions)) {
      setSkippedQuestions(state.skipped_questions.map(String));
    }
  };

  const openedDocumentIntake = useRef(false);
  useEffect(() => {
    if (searchParams.get("input") === "document" && !restorePending && preferencesLoaded && !openedDocumentIntake.current) {
      openedDocumentIntake.current = true;
      setAssistantOpen(true);
    }
  }, [searchParams, restorePending, preferencesLoaded]);

  const translateMessage = (msg: string) => {
    const key = msg.startsWith("equipment.") ? `errors.${msg}` : `messages.${msg}`;
    const translated = t(key as "messages.dg_un_detected");
    return translated === key ? msg : translated;
  };

  const includedLines = result?.lines.filter((line) => line.include) ?? [];
  // A sum of known package volumes is not the whole shipment's volume.
  const completeTransportVolume = cargoUsed ? cargoAssessment?.totals.occupied_volume_m3 ?? null
    : includedLines.length > 0 && includedLines.every(line => line.transport_volume_m3 != null)
      ? result?.totals.total_transport_volume_m3 ?? null : null;
  const completeShipmentWeight = cargoUsed ? cargoAssessment?.totals.cargo_gross_kg ?? null
    : includedLines.length > 0 && includedLines.every(line => line.weight_total_kg != null)
      ? result?.totals.total_weight_kg ?? null : null;

  /** The documents being prepared, for the panel that stands beside the work.
   *  A document that does not apply to this shipment is not being prepared and
   *  is left out; the rest carry what they are still short of. */
  const panelDocuments: PanelDocument[] = selectedDefinitions
    .map((doc) => ({ doc, info: docStatus(doc) }))
    .filter(({ info }) => info.status !== "not_applicable")
    .map(({ doc, info }) => ({
      key: doc.key,
      label: L(doc.label),
      state: info.status as PanelDocument["state"],
      missing: info.missing.length,
      firstMissing: info.missing[0]?.key ?? null,
      blockedReason: info.status === "blocked" ? info.missing.find(field => field.key === "cargo")?.label : undefined,
    }));

  /** What this shipment is called, in the header. The reference is what a
   *  forwarder calls it by; failing that the consignee, who is the other thing
   *  people say out loud ("the one going to Müller"). Neither yet, and it is
   *  honestly a new one. */
  const shipmentTitle =
    (docValues.shipment_reference ?? "").trim() ||
    (docValues.reference ?? "").trim() ||
    (docValues.consignee_name ?? "").trim() ||
    t("wizard.newShipment");

  /** The check-your-answers rows: the shipment as it stands, each with the way
   *  back to the answer itself. What is derived — the totals, the assessment —
   *  carries no way back, because it is not something to type. */
  const answerRows: AnswerRow[] = (() => {
    if (!result) return [];
    const value = (key: string) => (docValues[key] ?? "").trim();
    const route = [value("loading_point"), value("discharge_point")].filter(Boolean).join(" → ");
    const contents = includedLines
      .slice(0, 3)
      .map((line) => line.output_description || line.description)
      .filter(Boolean);
    const rest = includedLines.length - contents.length;
    const packages = contents.join("; ") + (rest > 0 ? `; ${t("check.andMore", { count: rest })}` : "");
    const assessment = [
      needsDg ? t("check.dgOnBoard", { count: dgEntries.length }) : t("check.noDg"),
      unanswered > 0 ? t("check.openQuestions", { count: unanswered }) : "",
    ].filter(Boolean).join(" · ");
    return [
      { key: "modality", label: t("check.modality"), value: t(`modality.${modality}`) },
      { key: "consignor", label: t("check.consignor"), value: value("consignor_name"),
        onChange: () => goToField("consignor_name"), wanted: true },
      { key: "consignee", label: t("check.consignee"), value: value("consignee_name"),
        onChange: () => goToField("consignee_name"), wanted: true },
      { key: "route", label: t("check.route"), value: route,
        onChange: () => goToField("loading_point"), wanted: true },
      { key: "goods", label: t("check.goods"),
        value: t("check.goodsValue", {
          count: result.totals.included_count,
          weight: completeShipmentWeight ?? "—",
          volume: completeTransportVolume ?? "—",
        }),
        onChange: () => setStepKey("lines") },
      { key: "packages", label: t("check.packages"), value: packages,
        onChange: () => setStepKey("lines") },
      { key: "assessment", label: t("check.assessment"), value: assessment },
      { key: "language", label: t("check.language"), value: LANGUAGE_NAMES[docLang] ?? docLang,
        onChange: () => document.getElementById("document-language")?.focus() },
    ];
  })();

  if (registryError) {
    return <p className="text-sm text-red-600 dark:text-red-400">{registryError}</p>;
  }

  if (!registry) {
    return <div className="py-12 text-center text-slate-500 dark:text-slate-400">{t("wizard.loading")}</div>;
  }

  if (restorePending) {
    return restoreError ? (
      <div role="alert" className="surface space-y-4 p-6 text-center">
        <p>{t("history.loadFailed")}</p>
        <button className={buttonSecondary} onClick={() => setRestoreAttempt((attempt) => attempt + 1)}>{t("overview.retry")}</button>
      </div>
    ) : <div role="status" className="py-12 text-center text-slate-500 dark:text-slate-400">{t("wizard.loading")}</div>;
  }

  return (
    <WizardShell
      title={shipmentTitle}
      reference={<label className="wizard-reference" htmlFor="field-shipment_reference">
        <span>{t("wizard.referenceLabel")}</span>
        <input id="field-shipment_reference" type="text" maxLength={120} autoComplete="off"
          value={docValues.shipment_reference || docValues.reference || ""}
          placeholder={t("wizard.referencePlaceholder")} disabled={closing}
          onChange={(event) => setShipmentReference(event.target.value)}
          onBlur={(event) => setShipmentReference(event.target.value.trim())} />
      </label>}
      modality={modality}
      modalities={AVAILABLE_MODALITIES}
      onModality={switchModality}
      steps={stepPills}
      currentStep={stepKey === "export" ? 3 : stepKey === "details" ? 2 : 1}
      visited={visited}
      onGoTo={(key) => {
        if (key !== "lines" && draftLines.some(line => line.quantity_unconfirmed)) { toast.error(t("assistant.quantityNeeded")); return; }
        setReturnTo(null);
        setStepKey(key as StepKey);
      }}
      secondaryAction={historyOn && hasEntry && !reopenId && !reviewSourceId ? (
        <button type="button" disabled={closing} className={buttonSecondary} onClick={() => void saveAndClose()}>{t("wizard.saveAndClose")}</button>
      ) : undefined}
      attention={attention}
      panel={
        <ShipmentPanel
          lines={result?.totals.line_count ?? draftLines.filter((line) => line.description.trim()).length}
          weightKg={completeShipmentWeight}
          volumeM3={completeTransportVolume}
          attention={attention}
          documents={panelDocuments}
          onMissing={goToField}
        />
      }
      draft={
        <DraftBar
          compact
          mode={historyOn ? "kept" : "file"}
          status={draftStatus}
          savedAt={draftSavedAt}
          active={hasEntry && !reopenId && !reviewSourceId && !keptAt}
          onDiscard={historyOn ? discardDraft : undefined}
          onDownload={historyOn ? undefined : downloadDraft}
          onOpenFile={historyOn ? undefined : openDraftFile}
        />
      }
      aside={
        <button
          type="button"
          onClick={() => setAssistantOpen((open) => !open)}
          aria-label={assistantOpen ? t("assistant.close") : t("assistant.open")}
          title={assistantOpen ? t("assistant.close") : t("assistant.open")}
          className={`inline-flex h-[50px] items-center justify-center gap-2 rounded-lg border border-brand-200 bg-brand-50 px-3 transition dark:border-brand-900 dark:bg-brand-950/40 ${
            assistantOpen
              ? "bg-brand-50 text-brand-700 dark:bg-brand-950/50 dark:text-brand-200"
              : "text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
          }`}
        >
          <AiIcon className="h-5 w-5" /><span className="hidden text-xs font-medium sm:inline">{t("assistant.shortTitle")}</span>
        </button>
      }
    >
      <div className="space-y-4 sm:space-y-6" inert={closing || undefined}>
      <DocumentEvidenceList evidence={documentEvidence} />
      <AssistantModal
        open={assistantOpen}
        initialDocument={searchParams.get("input") === "document"}
        onClose={() => setAssistantOpen(false)}
        modality={modality}
        buildState={buildStateForAssistant}
        onApplyState={applyAssistantState}
        onReview={() => setStepKey("lines")}
      />

      {stepKey === "lines" && (
        <div className="space-y-4">
          {/* An earlier shipment as the start of this one, on the step where a
              shipment starts. Reaching it used to mean the shipments page and
              its detail page first. */}
          {recent.length > 0 && !hasEntry && !reopenId && (
            <div className={`${panelClass} flex flex-wrap items-center gap-x-3 gap-y-2 p-4`}>
              <span className="text-sm text-slate-600 dark:text-slate-400">{t("wizard.startFrom")}</span>
              {recent.map((shipment) => (
                <Link
                  key={shipment.id}
                  to={`/wizard/${shipment.modality || "road"}?template=${shipment.id}`}
                  className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  {shipment.reference || shipment.consignee_name || `#${shipment.id}`}
                </Link>
              ))}
            </div>
          )}

          {/* The four counts were here, on this step and nowhere else. They
              are in the panel now, on every step — because the totals you are
              entering against do not stop mattering when you move on. */}
          <div className="flex gap-2" role="group" aria-label={t("cargoIntegration.view")}>
            <button type="button" className={linesView === "goods" ? "action-primary" : "action-secondary"} aria-pressed={linesView === "goods"} onClick={() => setLinesView("goods")}>{t("cargoIntegration.goods")}</button>
            <button type="button" className={linesView === "cargo" ? "action-primary" : "action-secondary"} aria-pressed={linesView === "cargo"} onClick={() => { setCargoOpened(true); setLinesView("cargo"); }}>{t("cargoIntegration.cargo")}{cargo.units.length > 0 && <span className="equipment-count">{cargo.units.length}</span>}</button>
          </div>
          {(cargoOpened || linesView === "cargo") && <div hidden={linesView !== "cargo"}><CargoWorkspace value={cargo} assessment={cargoAssessment} goods={displayedCargoGoods} onChange={(next) => {
            const change = editCargo(draftLines, cargo, next);
            if (change.migrated) { setDraftLines(change.drafts); setResult(null); calculatedSignature.current = null; }
            setCargo(change.cargo);
          }} canManageTemplates={!!user && canManage(user)} /></div>}
          <div hidden={linesView !== "goods"}><ReviewLinesPanel
            cargoManaged
            initialPaste={searchParams.get("input") === "paste"}
            draftLines={draftLines}
            resultLines={result?.lines}
            onDraftChange={(lines) => {
              lines = lines.map(line => ({ ...line, quantity_unconfirmed: line.quantity_unconfirmed
                && line.quantity === draftLines.find(old => old.id === line.id)?.quantity }));
              setDraftLines(lines);
              // Ticking DG or answering a name suggestion does not change what
              // was calculated; clearing the result for it would wipe the
              // weights off the screen for an answer, not an edit.
              if (signatureOf(lines) !== draftSignature) setResult(null);
            }}
            onRemoveLine={removeLine}
            onDuplicateLine={duplicateLine}
            onAddLine={addLine}
            onImport={handleImport}
            onLineWeightChange={result ? handleLineWeightChange : undefined}
            onChooseEquipment={equipment => {
              const blank = draftLines.find(line => !line.description.trim());
              if (blank) setDraftLines(lines => lines.map(line => line.id === blank.id ? { ...line, ...equipmentPatch(equipment) } : line));
              else {
                setDraftLines(lines => [...lines, { id: nextId, description: equipment.specifications, quantity: 1, unit: "pcs", ...equipmentPatch(equipment) }]);
                setNextId(value => value + 1);
              }
              setResult(null);
            }}
            translateMessage={translateMessage}
          /></div>
          {cargoFailure && <p role="alert" className="text-sm text-red-700 dark:text-red-300">{cargoFailure}</p>}


          <WizardActions>
            <button type="button" onClick={goFromLines} disabled={loading} className={buttonPrimary + " wizard-next"}
              aria-label={t("review.continueTo", { step: needsDg ? t("wizard.step3dg") : t("wizard.toShipmentDetails") })}>
              {t("review.continue")}<ArrowRightIcon className="h-4 w-4" />
            </button>
          </WizardActions>
        </div>
      )}

      {stepKey === "dg" && result && (
        <div className="space-y-4">
          <DangerousGoodsStep
            lines={result.lines}
            entries={dgEntries}
            onChange={setDgEntries}
            perPosition
            extraFields={dgExtraFields}
            profiles={dgProfiles}
          />
          {modality !== "preparation" && <DgCompliancePanel entries={dgEntries} profiles={dgProfiles} />}
          <WizardActions>
            <button type="button" onClick={() => goBackFrom("dg")} className={buttonSecondary}>
              {t("wizard.back")}
            </button>
            <button type="button" onClick={() => goNextFrom("dg")} className={buttonPrimary}>
              {genericDocs.length > 0 ? t("wizard.toDetails") : t("wizard.toExport")}
            </button>
          </WizardActions>
        </div>
      )}

      {stepKey === "details" && (
        <div className="space-y-4">
          {/* The advice arrives before the work, not after it: what is being
              prepared and why, while there is still a point in changing it. */}
          <DocumentAdvicePanel
            registry={registry}
            modality={modality ?? ""}
            needsDg={needsDg}
            selected={selected}
            onChange={chooseDocuments}
          />
          {addedByDoc && (
            <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4 dark:border-sky-900/50 dark:bg-sky-950/30">
              <p className="text-sm text-sky-900 dark:text-sky-200">
                {addedByDoc.count === 0
                  ? t("advice.addedNothing", { document: addedByDoc.label })
                  : t("advice.added", { document: addedByDoc.label, count: addedByDoc.count })}
              </p>
              {addedByDoc.first && (
                <button
                  type="button"
                  onClick={() => {
                    setFocusField(addedByDoc.first);
                    setAddedByDoc(null);
                  }}
                  className="mt-2 rounded-lg border border-sky-300 bg-white px-3 py-1 text-xs font-medium text-sky-900 hover:bg-sky-100 dark:border-sky-800 dark:bg-slate-900 dark:text-sky-200"
                >
                  {t("advice.toTheQuestions")}
                </button>
              )}
            </div>
          )}
          {lastShipment && (
            <div className={`${panelClass} flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between`}>

              <button type="button" onClick={reuseLastShipment} className={buttonSecondary}>
                {t("docfields.reuseLast")}
              </button>
            </div>
          )}
          <DocumentFieldsStep
            registry={registry}
            excludedFields={HEADER_FIELDS}
            documents={genericDocs}
            values={docValues}
            onChange={setDocValues}
            autoValues={autoValues}
            modality={modality}
            onBack={() => goBackFrom("details")}
            onDone={completeDetails}
            focusField={focusField}
            onFocusHandled={() => setFocusField(null)}
            returnLabel={returnTo ? t("wizard.backToOverview") : undefined}
            onReturn={returnTo ? returnFromField : undefined}
            signature={signature}
            onSignatureChange={setSignature}
            addressBook={historyOn}
          />
        </div>
      )}

      {(modality === "preparation" || modality === "air") && <p className="surface p-4">{t(modality === "air" ? "deliveries.airPreparationHint" : "deliveries.preparationHint")}</p>}
      {stepKey === "export" && result && (
        <div className="export-workspace space-y-4">
          {/* The last look before anything is produced: what is about to go on
              paper, and one way back to each answer that is not right. */}
          <CheckYourAnswers title={t("check.title")} rows={answerRows} />
          {!publicSettings?.history_enabled && <TemporaryDelivery shipment={shipmentPayload(false)} />}
          <p className="surface p-4">{t("deliveries.draftNotice")}{historyId && <> <Link className="underline" to={`/deliveries/new?shipments=${historyId}`}>{t("deliveries.new")}</Link></>}</p>

            {needsDg && (
              <p className="text-sm text-amber-700 dark:text-amber-300">
                {t("wizard.dgIncluded", { count: dgEntries.length })}
              </p>
            )}
            {unanswered > 0 && (
              <p className="text-sm text-amber-700 dark:text-amber-300">
                {t("wizard.unansweredSubstances", { count: unanswered })}{" "}
                <button
                  type="button"
                  onClick={() => setStepKey("lines")}
                  className="font-medium underline underline-offset-2"
                >
                  {t("wizard.unansweredGo")}
                </button>
              </p>
            )}
          <details className="surface export-goods">
            <summary><span>{t("exportFocus.goods", { count: result.totals.included_count })}</span><strong>{result.totals.total_weight_kg?.toLocaleString(i18n.language)} kg</strong><ChevronDownIcon /></summary>
            <div className="export-goods-content space-y-4">
            <div className="space-y-3">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{t("wizard.products")}</h4>
                <div className="sm:w-48">
                  <label className="text-xs font-medium text-slate-600 dark:text-slate-400">{t("wizard.adjustTotalWeight")}</label>
                  <NumberInput
                    step="0.01"
                    className={`${weightInputClass} mt-1`}
                    value={result.totals.total_weight_kg ?? ""}
                    onChange={(e) => handleTotalWeightChange(e.target.value === "" ? null : Number(e.target.value))}
                  />

                </div>
              </div>

              <div className="space-y-2">
                {includedLines.map((line) => (
                  <div key={line.line_id} className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm dark:border-slate-700">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0">
                        <p className="truncate font-medium text-slate-900 dark:text-slate-100">
                          {line.output_description || line.description}
                        </p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          {line.quantity ?? "—"} {line.unit ?? ""}
                        </p>
                      </div>
                      <div className="grid grid-cols-2 gap-2 sm:w-56">
                        <div>
                          <label className="text-[11px] text-slate-500 dark:text-slate-400">{t("review.weightEach")}</label>
                          <NumberInput
                            step="0.01"
                            className={`${weightInputClass} mt-0.5`}
                            value={line.weight_each_kg ?? ""}
                            onChange={(e) =>
                              handleLineWeightChange(line.line_id, "weight_each_kg", e.target.value === "" ? null : Number(e.target.value))
                            }
                          />
                        </div>
                        <div>
                          <label className="text-[11px] text-slate-500 dark:text-slate-400">{t("review.weightTotal")}</label>
                          <NumberInput
                            step="0.01"
                            className={`${weightInputClass} mt-0.5`}
                            value={line.weight_total_kg ?? ""}
                            onChange={(e) =>
                              handleLineWeightChange(line.line_id, "weight_total_kg", e.target.value === "" ? null : Number(e.target.value))
                            }
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <ul className="space-y-1 text-sm text-slate-600 dark:text-slate-400">
              <li>{t("wizard.lines")}: {result.totals.included_count}</li>
              <li>{t("wizard.totalWeight")}: {result.totals.total_weight_kg} kg</li>
              <li>{t("wizard.totalVolume")}: {completeTransportVolume ?? "—"} m³</li>
            </ul>
            </div>
          </details>

          {needsDg && dgEntries.length > 0 && modality !== "preparation" && <DgCompliancePanel entries={dgEntries} profiles={dgProfiles} />}


          <div className={`${panelClass} export-documents space-y-3 p-4 sm:p-6`}>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <h3 className="export-documents-title"><DocumentIcon className="h-6 w-6" />{t("wizardDocs.title")}</h3>
              <div className="flex flex-wrap gap-2">
                {readyDocs.length > 0 && publicSettings?.mail_enabled && (
                  <button
                    type="button"
                    onClick={() => setMailOpen((open) => !open)}
                    disabled={mailing}
                    className={buttonSecondary}
                  >
                    {t("wizardDocs.mail", { count: readyDocs.length })}
                  </button>
                )}
                {/* One action finishes the job, with one document as with
                    five. What is not ready is named below rather than turning
                    this into a choice. */}
                {readyDocs.length > 0 && (
                  <button
                    type="button"
                    onClick={downloadAll}
                    disabled={downloadingAll}
                    className={buttonPrimary}
                  >
                    {downloadingAll
                      ? t("wizardDocs.exporting")
                      : readyDocs.length < selectedDefinitions.length
                        ? t("wizardDocs.downloadPartial", {
                            ready: readyDocs.length,
                            total: selectedDefinitions.length,
                          })
                        : t("wizardDocs.downloadAll", { count: readyDocs.length })}
                  </button>
                )}
              </div>
            </div>

            {/* A partial package is called partial, and says which documents
                are not in it. */}
            {readyDocs.length > 0 && readyDocs.length < selectedDefinitions.length && (
              <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-300">
                {t("wizardDocs.partialNotice", {
                  list: selectedDefinitions
                    .filter((doc) => docStatus(doc).status !== "ready")
                    .map((doc) => L(doc.label))
                    .join(", "),
                })}
              </p>
            )}

            {/* Having a document is not having sent it. */}
            {handedOver && (
              <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-900/20 dark:text-emerald-300">
                {t("wizardDocs.downloadedNotSent")}
              </p>
            )}

            {mailOpen && (
              <div className="space-y-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700">

                <div>
                  <label className="text-sm font-medium text-slate-800 dark:text-slate-200" htmlFor="mail-to">
                    {t("wizardDocs.mailTo")}
                  </label>
                  <input
                    id="mail-to"
                    type="text"
                    className={`${weightInputClass} mt-1`}
                    placeholder={t("wizardDocs.mailToPlaceholder")}
                    value={mailTo}
                    onChange={(e) => setMailTo(e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-800 dark:text-slate-200" htmlFor="mail-subject">
                    {t("wizardDocs.mailSubject")}
                  </label>
                  <input
                    id="mail-subject"
                    type="text"
                    className={`${weightInputClass} mt-1`}
                    placeholder={t("wizardDocs.mailSubjectPlaceholder")}
                    value={mailSubject}
                    onChange={(e) => setMailSubject(e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-800 dark:text-slate-200" htmlFor="mail-message">
                    {t("wizardDocs.mailMessage")}
                  </label>
                  <textarea
                    id="mail-message"
                    className={`${weightInputClass} mt-1 min-h-[80px]`}
                    value={mailMessage}
                    onChange={(e) => setMailMessage(e.target.value)}
                  />
                </div>
                <button
                  type="button"
                  onClick={mailAll}
                  disabled={mailing || !mailTo.trim()}
                  className={buttonPrimary}
                >
                  {mailing ? t("wizardDocs.mailSending") : t("wizardDocs.mailSend")}
                </button>
              </div>
            )}

            {/* The set itself is chosen where its questions are asked. From
                here it is one press back to that choice, not a second place
                to make it. */}
            <p className="text-sm text-slate-600 dark:text-slate-400">
              <button
                type="button"
                onClick={() => {
                  setReturnTo("export");
                  setStepKey("details");
                }}
                className="font-medium text-brand-700 underline hover:text-brand-800 dark:text-brand-300"
              >
                {t("wizardDocs.changeSet")}
              </button>
            </p>
            <p className="text-xs text-slate-500">
              <Link to="/account/about/terms" className="font-medium underline">
                {t("nav.legal")}
              </Link>
            </p>
            {Object.values(docWarnings).some((warnings) => warnings.length > 0) && <section className="export-checks" id="export-checks">
              <h4>{t("exportFocus.checks")}</h4>
              <ul>{groupDocumentWarnings(docWarnings).map(({ message, documents }) => <li key={message}>
                <p>{message}</p>
                <details><summary>{t("exportFocus.appliesTo", { count: documents.length })}</summary>
                  <ul>{documents.map((key) => <li key={key}>{L(selectedDefinitions.find((doc) => doc.key === key)?.label) || key}</li>)}</ul>
                </details>
              </li>)}</ul>
            </section>}
            <div className="space-y-2">
              {selectedDefinitions.map((doc) => {
                const info = docStatus(doc);
                const busy = exportingDoc === doc.key;
                return (
                  <div key={doc.key} className="export-document-row" data-state={info.status}>
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="font-medium text-slate-900 dark:text-slate-100">{L(doc.label)}</p>
                          <StatusBadge status={info.status} />
                          {info.waitingCarrier && info.status !== "not_applicable" && (
                            <span className="rounded-full bg-sky-100 px-2 py-0.5 text-[11px] font-medium text-sky-800 dark:bg-sky-900/40 dark:text-sky-300">
                              {t("wizardDocs.waitingCarrier")}
                            </span>
                          )}
                        </div>
                        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{L(doc.issue_status)}</p>
                        {info.status === "draft" && info.missing.length > 0 && (
                          <p className="mt-1 text-xs text-amber-600 dark:text-amber-300">
                            <span className="mr-1">{t("wizardDocs.missingFieldsLead")}</span>
                            {info.missing.map((field) => (
                              <button
                                key={field.key}
                                type="button"
                                onClick={() => goToField(field.key)}
                                className="mb-1 mr-1 inline-flex rounded-lg border border-amber-300 bg-white px-2 py-0.5 text-xs font-medium text-amber-900 hover:bg-amber-100 dark:border-amber-800 dark:bg-slate-900 dark:text-amber-200"
                              >
                                {field.label}
                              </button>
                            ))}
                          </p>
                        )}
                        {info.status === "blocked" && info.missing.some(field => field.key === "cargo") ? (
                          <button type="button" onClick={() => goToField("cargo")}
                            className="mt-1 text-left text-xs text-red-600 underline underline-offset-2 dark:text-red-400">
                            {info.missing.find(field => field.key === "cargo")!.label}
                          </button>
                        ) : info.status === "blocked" && (
                          <p className="mt-1 text-xs text-red-600 dark:text-red-400">{t("wizardDocs.dgBlocked")}</p>
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={() => exportGenericDoc(doc)}
                        disabled={busy || info.status === "blocked" || info.status === "not_applicable" || info.status === "draft"}
                        className={buttonSecondary + " inline-flex items-center justify-center gap-2"}
                      >
                        <DownloadIcon />{busy ? t("wizardDocs.exporting") : t("wizard.download")}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className={`${panelClass} space-y-3 p-4 sm:p-6`}>
            <div className="flex flex-wrap items-center gap-3">
            <label
              htmlFor="document-language"
              className="text-sm font-medium text-slate-800 dark:text-slate-100"
            >
              {t("wizardDocs.documentLanguage")}
            </label>
            <select
              id="document-language"
              value={docLang}
              onChange={(event) => setChosenDocLang(event.target.value as Language)}
              className={weightInputClass + " sm:max-w-xs"}
            >
              {SUPPORTED_LANGUAGES.map((code) => (
                <option key={code} value={code}>
                  {LANGUAGE_NAMES[code]}
                </option>
              ))}
            </select>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {t("wizardDocs.documentLanguageRule")}
            </p>
          </div>

          {historyOn && (
            <div className={`${panelClass} p-4 sm:p-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between`}>
              <div className="min-w-0">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{t("history.keepTitle")}</h3>

                <p className="text-sm text-slate-700 dark:text-slate-200 mt-2" data-testid="history-status">
                  {keptAt
                    ? t("history.keptAt", { time: keptAt.toLocaleTimeString(i18n.language, { timeStyle: "short" }) })
                    : t("history.notKept")}
                </p>
              </div>
              <button
                type="button"
                onClick={() => void keepInHistory()}
                disabled={keeping}
                className={buttonSecondary}
              >
                {/* Kept, not merely written: a draft has a row of its own, and
                    a button that said "update" over a shipment nobody has kept
                    yet would be claiming something that never happened. */}
                {keeping ? t("history.keeping") : keptAt ? t("history.update") : t("history.keep")}
              </button>
            </div>
          )}

          {((instructionRegimes.length > 0 && instructions.length > 0) || checklist.length > 0 || (unCards?.enabled && unCards.count > 0)) && <details className="surface export-reference">
            <summary><DocumentIcon />{t("exportFocus.reference")}<ChevronDownIcon /></summary>
            <div className="space-y-3 p-4">
          {instructionRegimes.length > 0 && instructions.length > 0 && (
            <div className={`${panelClass} space-y-3 p-4 sm:p-6`}>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                {t("instructions.title")}
              </h3>

              <p className="text-xs text-slate-500 dark:text-slate-400">
                {t("instructions.languageRule")}
              </p>
              {instructionRegimes.map((regime) => (
                <div key={regime} className="space-y-2">
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
                    {regime.toUpperCase()}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {instructions
                      .filter((item) => item.regime === regime)
                      .map((item) => (
                        <button
                          key={`${item.regime}-${item.language}`}
                          type="button"
                          disabled={!item.available}
                          title={
                            item.available
                              ? undefined
                              : `${t("instructions.unavailable", { document: item.needs ?? "" })} ${t("instructions.howto")}`
                          }
                          onClick={() => downloadInstructions(item.regime, item.language)}
                          className={`${buttonSecondary} ${item.available ? "" : "opacity-40"}`}
                        >
                          {item.language.toUpperCase()}
                        </button>
                      ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {checklist.length > 0 && (
            <div className={`${panelClass} space-y-3 p-4 sm:p-6`}>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                {t("checklist.title")}
              </h3>

              <p className="text-xs text-slate-500 dark:text-slate-400">
                {t("checklist.notFilledIn")}
              </p>
              <div className="flex flex-wrap gap-2">
                {checklist.map((item) => (
                  <button
                    key={`${item.regime}-${item.language}`}
                    type="button"
                    disabled={!item.available}
                    title={
                      item.available
                        ? undefined
                        : `${t("instructions.unavailable", { document: item.needs ?? "" })} ${t("instructions.howto")}`
                    }
                    onClick={() => downloadChecklist(item.regime, item.language)}
                    className={`${buttonSecondary} ${item.available ? "" : "opacity-40"}`}
                  >
                    {item.language.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
          )}

          {unCards && unCards.enabled && unCards.count > 0 && (
            <div className={`${panelClass} space-y-3 p-4 sm:p-6`}>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                {t("unCards.title")}
              </h3>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="text-sm text-slate-700 dark:text-slate-200">
                    {t("unCards.forSubstances", {
                      list: unCards.available.map((un) => `UN ${un}`).join(", "),
                    })}
                  </p>
                  {unCards.missing.length > 0 && (
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      {t("unCards.missing", {
                        list: unCards.missing.map((un) => `UN ${un}`).join(", "),
                      })}
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={downloadUnCards}
                  disabled={unCardsBusy}
                  className={buttonSecondary}
                >
                  {unCardsBusy
                    ? t("wizardDocs.exporting")
                    : t("unCards.download", { count: unCards.count })}
                </button>
              </div>
            </div>
          )}

            </div>
          </details>}

          <WizardActions>
            <button type="button" onClick={() => goBackFrom("export")} className={buttonSecondary}>
              {t("wizard.back")}
            </button>
            {needsDg && (
              <button
                type="button"
                onClick={returnShipment}
                disabled={turningRound}
                className={buttonSecondary}
                title={t("wizard.returnShipmentHint")}
              >
                {turningRound ? t("wizard.returnPreparing") : t("wizard.returnShipment")}
              </button>
            )}
          </WizardActions>
        </div>
      )}

      </div>
    </WizardShell>
  );
}

function StatusBadge({ status }: { status: DocStatus }) {
  const { t } = useTranslation();
  const styles: Record<DocStatus, string> = {
    ready: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
    draft: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
    blocked: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
    not_applicable: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  };
  const labels: Record<DocStatus, string> = {
    ready: t("wizardDocs.statusReady"),
    draft: t("wizardDocs.statusDraft"),
    blocked: t("wizardDocs.statusBlocked"),
    not_applicable: t("wizardDocs.statusNotApplicable"),
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${styles[status]}`}>{labels[status]}</span>
  );
}
