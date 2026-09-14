import { useEffect, useId, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";
import { useToast } from "../toast/ToastProvider";
import ConfirmDialog from "../toast/ConfirmDialog";
import UpdatePanel from "../components/UpdatePanel";
import NumberInput from "../components/NumberInput";
import {
  AssistantStatus,
  InstanceSettings,
  OrganisationSettings,
  SettingsOptions,
  ThemeChoice,
  UnCardStoreStatus,
  User,
  UserPreferences,
  api,
} from "../api/client";
import SignaturePad from "../components/SignaturePad";
import TwoFactorPanel from "../components/TwoFactorPanel";
import { LANGUAGE_NAMES, SUPPORTED_LANGUAGES } from "../i18n/language";
import { useBranding } from "../branding";
import { PaletteIcon, ShipmentsIcon, UserIcon, ShieldIcon, BuildingIcon, NetworkIcon, MailIcon, RefreshIcon, DocumentIcon, SettingsIcon, SunIcon, MoonIcon, MonitorIcon, InfoIcon } from "../components/icons";
import { MODALITIES, AVAILABLE_MODALITIES } from "./ModalitySelectPage";
import { usePreferences } from "../settings/preferences";
import { settingsPath, type SettingsArea } from "../settings/routes";
import ProfilePanel from "./account/ProfilePanel";
import PasswordPanel from "./account/PasswordPanel";
import AboutPanel from "./account/AboutPanel";
import LegalPage from "./LegalPage";
import "./account/account.css";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2.5 text-sm min-h-[44px]";
const buttonPrimary =
  "bg-brand-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50 min-h-[44px] text-sm";
const buttonSecondary =
  "px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 min-h-[44px] text-sm inline-flex items-center";

const THEMES: ThemeChoice[] = ["light", "dark", "system"];

/** Account settings and installation administration have separate entry points. */
const TABS = [
  { key: "profile", label: "account.profile", admin: false, group: "personal", icon: UserIcon },
  { key: "security", label: "settingsNav.security", admin: false, group: "personal", icon: ShieldIcon },
  { key: "appearance", label: "settings.tabAppearance", admin: false, group: "personal", icon: PaletteIcon },
  { key: "shipment", label: "settings.tabShipment", admin: false, group: "personal", icon: ShipmentsIcon },
  { key: "details", label: "account.documentDetails", admin: false, group: "personal", icon: DocumentIcon },
  { key: "about", label: "account.about", admin: false, group: "personal", icon: InfoIcon },
  { key: "admin", label: "settingsNav.organisation", admin: true, group: "organisation", icon: BuildingIcon },
  { key: "access", label: "account.accessPolicy", admin: true, group: "organisation", icon: ShieldIcon },
  { key: "dg", label: "dgReview.settingsTitle", admin: true, group: "organisation", icon: ShieldIcon },
  { key: "branding", label: "settings.adminBranding", admin: true, group: "organisation", icon: PaletteIcon },
  { key: "mail", label: "settings.mailTitle", admin: true, group: "organisation", icon: MailIcon },
  { key: "updates", label: "settings.adminUpdates", admin: true, group: "system", icon: RefreshIcon },
  { key: "network", label: "settingsNav.connections", admin: true, group: "system", icon: NetworkIcon },
  { key: "cards", label: "settingsNav.cards", admin: true, group: "system", icon: DocumentIcon },
  { key: "assistant", label: "settingsNav.assistant", admin: true, group: "system", icon: SettingsIcon },
] as const;

type TabKey = (typeof TABS)[number]["key"];

/** The personal tabs share one draft and therefore one save button. */
const ADMIN_TABS: string[] = ["admin", "dg", "branding", "mail", "network", "access", "cards"];
const PERSONAL_TABS: string[] = ["appearance", "shipment", "details"];

interface Props {
  user: User;
  onUserChange?: (user: User) => void;
  onPasswordChanged?: () => void;
  area?: SettingsArea;
  sectionOverride?: "terms";
}

export default function SettingsPage({ user, onUserChange, onPasswordChanged, area = "account", sectionOverride }: Props) {
  const { t } = useTranslation();
  const { preferences, save, loaded } = usePreferences();
  const [draft, setDraft] = useState<UserPreferences>(preferences);
  const [options, setOptions] = useState<SettingsOptions | null>(null);
  const [version, setVersion] = useState("");
  const [saving, setSaving] = useState(false);
  const [profileDirty, setProfileDirty] = useState(false);
  const [pendingTab, setPendingTab] = useState<TabKey | null>(null);
  const toast = useToast();
  const navigate = useNavigate();
  const { section } = useParams();
  const requestedTab = sectionOverride || section || (area === "admin" ? "admin" : "profile");
  const tab_ = requestedTab === "organisation" ? "admin" : requestedTab;
  const setTab = (key: TabKey) => {
    if (key === tab_) return;
    if (profileDirty) { setPendingTab(key); return; }
    navigate(settingsPath(area, key));
  };

  useEffect(() => setDraft(preferences), [preferences]);

  useEffect(() => {
    api.health().then((h) => setVersion(h.version)).catch(() => {});
    api.settingsOptions().then(setOptions).catch(() => {});
  }, []);

  const dirty = useMemo(
    () => JSON.stringify(draft) !== JSON.stringify(preferences),
    [draft, preferences],
  );

  const set = <K extends keyof UserPreferences>(key: K, value: UserPreferences[K]) => {
    setDraft((current) => ({ ...current, [key]: value }));
  };

  /** The theme and the language take effect the moment they are picked — they
   *  always did, and having to press Save to see a dark screen would be a step
   *  backwards. Everything else waits for the button. */
  const setAndApply = async (values: Partial<UserPreferences>) => {
    const next = { ...draft, ...values };
    setDraft(next);
    try {
      await save(next);
    } catch (e) {
      toast.error(String(e));
    }
  };

  const submit = async () => {
    setSaving(true);
    try {
      await save(draft);
      toast.success(t("settings.saved"));
    } catch (e) {
      toast.error(String(e));
    } finally {
      setSaving(false);
    }
  };

  const tabs = TABS.filter(tab => area === "account" ? !tab.admin : tab.admin && (user.role === "admin" || (user.role === "super_user" && tab.key === "admin")));
  const active = area === "account" && tab_ === "terms" ? "terms" : tabs.find(tab => tab.key === tab_)?.key ?? tabs[0]?.key;
  const selectedTab = active === "terms" ? "about" : active;
  const title = t(area === "admin" ? "account.adminSettings" : "account.settings");

  return (
    <div className="settings-workspace page-enter">
      <div className="page-heading">
      <div>
        <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          {t(area === "admin" ? "account.adminIntro" : "account.intro")}
        </p>
      </div>

      </div>
      <div className="settings-layout">
      {/* On a phone a row of tabs would either wrap or scroll out of sight;
          a dropdown says which group you are in and holds the rest one tap
          away. From the medium breakpoint the tabs themselves fit. */}
      <div className="settings-mobile-nav">
        <label htmlFor="settings-tab" className="sr-only">
          {t("settings.tabPick")}
        </label>
        <select
          id="settings-tab"
          className={inputClass}
          value={selectedTab}
          onChange={(event) => setTab(event.target.value as TabKey)}
        >
          {tabs.map((tab) => (
            <option key={tab.key} value={tab.key}>
              {t(tab.label as "settings.tabAppearance")}
            </option>
          ))}
        </select>
      </div>

      <nav className="settings-nav" aria-label={title}>
        {(["personal", "organisation", "system"] as const).map((group) => {
          const items = tabs.filter((tab) => tab.group === group);
          return items.length > 0 && <div key={group} className="settings-nav-group">
            <p>{t(`settingsNav.${group}`)}</p>
            {items.map((tab) => <button key={tab.key} type="button" aria-current={selectedTab === tab.key ? "page" : undefined}
              onClick={() => setTab(tab.key)} className={`settings-nav-item ${selectedTab === tab.key ? "is-active" : ""}`}>
              <tab.icon className="h-5 w-5" /><span>{t(tab.label)}</span>
            </button>)}
          </div>;
        })}
        {version && <p className="settings-version">EMCargo <span>{version}</span></p>}
      </nav>
      <div className="settings-content" key="settings-content">

      {active === "profile" && <ProfilePanel user={user} onUserChange={onUserChange} onDirtyChange={setProfileDirty} />}
      {active === "about" && <AboutPanel version={version} />}
      {active === "terms" && <div className="account-terms"><Link to="/account/about" className="account-back">← {t("account.about")}</Link><LegalPage /></div>}

      {active === "appearance" && (
      <section className={`${panelClass} p-5 space-y-5`}>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {t("settings.appearance")}
        </h3>

        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">{t("settings.theme")}</label>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{t("settings.themeHint")}</p>
          <div className="grid grid-cols-3 gap-2 mt-2">
            {THEMES.map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => void setAndApply({ theme: option })}
                aria-pressed={draft.theme === option}
                className={`theme-choice px-3 py-2.5 rounded-lg text-sm min-h-[44px] border ${
                  draft.theme === option
                    ? "border-brand-500 bg-brand-50 text-brand-700 dark:bg-brand-950/50 dark:text-brand-200"
                    : "border-slate-200 dark:border-slate-700"
                }`}
              >
                <span className={`theme-preview theme-preview-${option}`} aria-hidden="true"><span /><span><i /><i /><i /></span></span>
                <span className="theme-choice-label">{option === "light" ? <SunIcon /> : option === "dark" ? <MoonIcon /> : <MonitorIcon />}{t(option === "system" ? "settings.auto" : `theme.${option}`)}</span>
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">{t("settings.language")}</label>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{t("settings.languageHint")}</p>
          <select
            className={`${inputClass} mt-2`}
            value={draft.language || ""}
            onChange={(e) => void setAndApply({ language: e.target.value })}
          >
            {SUPPORTED_LANGUAGES.map((language) => (
              <option key={language} value={language}>
                {LANGUAGE_NAMES[language]}
              </option>
            ))}
          </select>
        </div>

        <p className="text-xs text-slate-500 dark:text-slate-400 border-t border-slate-100 dark:border-slate-800 pt-3">
          {t("settings.autoDetectNote")}
        </p>
      </section>
      )}

      {active === "shipment" && (
      <section className={`${panelClass} p-5 space-y-5`}>
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {t("settings.shipmentDefaults")}
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{t("settings.shipmentDefaultsHint")}</p>
        </div>

        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">{t("settings.defaultModality")}</label>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{t("settings.defaultModalityHint")}</p>
          <select
            className={`${inputClass} mt-2`}
            value={draft.default_modality}
            onChange={(e) => set("default_modality", e.target.value)}
          >
            <option value="">{t("settings.askEveryTime")}</option>
            {(options?.modalities ?? []).map((modality) => (
              <option key={modality} value={modality}>
                {t(`modality.${modality}`)}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">{t("settings.defaultUnit")}</label>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{t("settings.defaultUnitHint")}</p>
          <select
            className={`${inputClass} mt-2`}
            value={draft.default_unit}
            onChange={(e) => set("default_unit", e.target.value)}
          >
            {(options?.units ?? []).map((unit) => (
              <option key={unit.code} value={unit.code}>
                {t(`units.name.${unit.code}`, { defaultValue: `${unit.code} (${unit.symbol})` })}
              </option>
            ))}
          </select>
        </div>

        <Toggle
          label={t("settings.prefillDocuments")}
          hint={t("settings.prefillDocumentsHint")}
          checked={draft.prefill_documents}
          onChange={(value) => set("prefill_documents", value)}
        />
      </section>
      )}

      {active === "details" && (
      <section className={`${panelClass} p-5 space-y-4`}>
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {t("account.documentDetails")}
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            {t("settings.myDetailsHint")}
          </p>
        </div>

        <Field
          label={t("settings.consignorName")}
          value={draft.consignor_name}
          onChange={(value) => set("consignor_name", value)}
        />
        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
            {t("settings.consignorAddress")}
          </label>
          <textarea
            className={`${inputClass} mt-1 min-h-[80px]`}
            value={draft.consignor_address}
            onChange={(e) => set("consignor_address", e.target.value)}
          />
        </div>
        <Field
          label={t("settings.consignorContact")}
          value={draft.consignor_contact}
          onChange={(value) => set("consignor_contact", value)}
        />
        <Field
          label={t("settings.carrierName")}
          value={draft.carrier_name}
          onChange={(value) => set("carrier_name", value)}
        />
        <Field
          label={t("settings.loadingPoint")}
          value={draft.loading_point}
          onChange={(value) => set("loading_point", value)}
        />
        <Field
          label={t("settings.emergencyContact")}
          hint={t("settings.emergencyContactHint")}
          value={draft.emergency_contact}
          onChange={(value) => set("emergency_contact", value)}
        />
      </section>
      )}

      {active === "details" && (
        <div className="space-y-2">
          <p className="text-xs text-slate-500 dark:text-slate-400">{t("settings.signatureHint")}</p>
          <SignaturePad
            value={draft.signature_image || null}
            onChange={(dataUrl) => set("signature_image", dataUrl ?? "")}
          />
        </div>
      )}

      {/* One draft across the personal tabs, so one save button — switching
          tabs never loses what was typed on another. */}
      {active && PERSONAL_TABS.includes(active) && (
        <>
          <div className="settings-savebar">
            <span className="settings-save-state">{t(dirty ? "settingsNav.unsaved" : "settingsNav.allSaved")}</span>
            <button type="button" onClick={submit} disabled={saving || !dirty} className={buttonPrimary}>
              {saving ? t("settings.saving") : t("settings.save")}
            </button>
            {!loaded && <span className="text-sm text-slate-500 dark:text-slate-400">{t("wizard.loading")}</span>}
          </div>
        </>
      )}

      {active === "security" && <div className="account-stack"><PasswordPanel onPasswordChanged={onPasswordChanged ?? (() => window.location.assign("/login"))} /><TwoFactorPanel /></div>}
      {active && active !== "terms" && ADMIN_TABS.includes(active) && user.role === "admin" && <AdminSettings section={active} />}
      {active === "admin" && user.role === "super_user" && <OrganisationPanel />}
      {active === "updates" && user.role === "admin" && <UpdatePanel />}
      {active === "cards" && user.role === "admin" && <UnCardsAdminPanel />}
      {active === "assistant" && user.role === "admin" && <AssistantAdmin />}
      </div>
      </div>
      <ConfirmDialog open={pendingTab !== null} title={t("account.discardTitle")} body={t("account.discardBody")}
        confirmLabel={t("account.discard")} onCancel={() => setPendingTab(null)} onConfirm={() => {
          if (pendingTab) navigate(settingsPath(area, pendingTab));
          setPendingTab(null);
        }} />
    </div>
  );
}

/**
 * The instance-wide settings, for administrators.
 *
 * Separate from the block above in more than looks: these apply to everyone, and
 * two of them decide whether this installation talks to the internet at all. The
 * server enforces that with `require_admin`; hiding the section here only keeps
 * it out of the way of people who cannot change it anyway.
 */
function AdminSettings({ section }: { section: TabKey }) {
  const { t } = useTranslation();
  const toast = useToast();
  const { reload } = usePreferences();
  const [settings, setSettings] = useState<InstanceSettings | null>(null);
  const [draft, setDraft] = useState<InstanceSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [testTo, setTestTo] = useState("");
  const [testing, setTesting] = useState(false);
  // Switching the history off destroys what it kept. The server refuses
  // while anything is kept; the screen asks first, with the counts, and
  // deletes on confirmation before saving the switch.
  const [discard, setDiscard] = useState<{ shipments: number; trips: number } | null>(null);

  useEffect(() => {
    api
      .instanceSettings()
      .then((values) => {
        setSettings(values);
        setDraft(values);
      })
      .catch((e) => toast.error(String(e)));
    // toast is stable for the provider's lifetime; this effect runs once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!draft || !settings) return null;

  const dirty = JSON.stringify(draft) !== JSON.stringify(settings);

  const set = <K extends keyof InstanceSettings>(key: K, value: InstanceSettings[K]) => {
    setDraft((current) => (current ? { ...current, [key]: value } : current));
  };

  const runTest = async () => {
    setTesting(true);
    // A test mail takes as long as the SMTP conversation takes — the loading
    // toast holds the user's place until the server has actually answered.
    const pending = toast.loading(t("settings.mailTesting"));
    try {
      const result = await api.sendTestMail(testTo.trim());
      pending.success(t("settings.mailTestSent", { to: result.to }));
    } catch (e) {
      // Whatever the mail server said, said plainly: that sentence is the
      // whole diagnosis for a wrong port, a refused password or a firewall.
      pending.error(String(e));
    } finally {
      setTesting(false);
    }
  };

  const store = async () => {
    const stored = await api.saveInstanceSettings(draft);
    setSettings(stored);
    setDraft(stored);
    toast.success(t("settings.saved"));
    // The menu and the export step read the public settings; a switch
    // saved here must show there without a page reload.
    void reload();
  };

  const submit = async () => {
    setSaving(true);
    try {
      if (settings.history_enabled && !draft.history_enabled) {
        const counts = await api.historyCounts();
        if (counts.shipments || counts.trips) {
          setDiscard(counts);
          return;
        }
      }
      await store();
    } catch (e) {
      toast.error(String(e));
    } finally {
      setSaving(false);
    }
  };

  const discardAndSwitchOff = async () => {
    setDiscard(null);
    setSaving(true);
    try {
      await api.discardHistory();
      await store();
    } catch (e) {
      toast.error(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-500 dark:text-slate-400">{t("settings.adminIntro")}</p>

      <section hidden={section !== "admin"} className={`${panelClass} p-5 space-y-5`}>
        <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {t("settings.adminNewUsers")}
        </h4>

        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
            {t("settings.adminDefaultLanguage")}
          </label>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {t("settings.adminDefaultLanguageHint")}
          </p>
          <select
            className={`${inputClass} mt-2`}
            value={draft.default_language}
            onChange={(e) => set("default_language", e.target.value)}
          >
            {SUPPORTED_LANGUAGES.map((language) => (
              <option key={language} value={language}>
                {LANGUAGE_NAMES[language]}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
            {t("settings.adminDefaultTheme")}
          </label>
          <select
            className={`${inputClass} mt-2`}
            value={draft.default_theme}
            onChange={(e) => set("default_theme", e.target.value as ThemeChoice)}
          >
            {THEMES.map((option) => (
              <option key={option} value={option}>
                {t(option === "system" ? "settings.auto" : `theme.${option}`)}
              </option>
            ))}
          </select>
        </div>

        <Field
          label={t("settings.organisationName")}
          hint={t("settings.organisationHint")}
          value={draft.organisation_name}
          onChange={(value) => set("organisation_name", value)}
        />
        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
            {t("settings.organisationAddress")}
          </label>
          <textarea
            className={`${inputClass} mt-1 min-h-[80px]`}
            value={draft.organisation_address}
            onChange={(e) => set("organisation_address", e.target.value)}
          />
        </div>
      </section>

      <section hidden={section !== "dg"} className={`${panelClass} p-5 space-y-5`}>
        <div><h3 className="font-semibold">{t("dgReview.settingsTitle")}</h3><p className="mt-2 text-sm text-slate-500">{t("dgReview.settingsHint")}</p><Link to="/users" className="mt-3 inline-flex text-sm font-medium underline">{t("nav.users")}</Link></div>
        <Toggle label={t("dgReview.enabledSetting")} hint={t("dgReview.enabledHint")} checked={draft.dg_review_enabled !== false} onChange={value => set("dg_review_enabled", value)} />
        <Toggle label={t("dgReview.superDgsaSetting")} hint={t("dgReview.superDgsaHint")} checked={draft.super_user_dgsa_enabled === true} onChange={value => set("super_user_dgsa_enabled", value)} />
      </section>
      <section hidden={section !== "branding"} className={`${panelClass} p-5 space-y-5`}>
        <div>
          <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {t("settings.adminBranding")}
          </h4>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{t("settings.adminBrandingHint")}</p>
        </div>
        <Field
          label={t("settings.brandName")}
          hint={t("settings.brandNameHint")}
          value={draft.brand_name ?? ""}
          onChange={(value) => set("brand_name", value)}
        />
        <BrandingPictures />
      </section>

      <section hidden={section !== "network"} className={`${panelClass} p-5 space-y-5`}>
        <div>
          <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {t("settings.adminNetwork")}
          </h4>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{t("settings.adminNetworkHint")}</p>
        </div>

        <Field
          label={t("settings.publicUrl")}
          hint={t("settings.publicUrlHint")}
          value={draft.public_url}
          onChange={(value) => set("public_url", value)}
        />

        <Toggle
          label={t("settings.addressLookup")}
          hint={t("settings.addressLookupHint")}
          checked={draft.address_lookup_enabled}
          onChange={(value) => set("address_lookup_enabled", value)}
        />
        {draft.address_lookup_enabled && (
          <>
            <Field
              label={t("settings.addressApiUrl")}
              hint={t("settings.addressApiUrlHint")}
              value={draft.address_api_url}
              onChange={(value) => set("address_api_url", value)}
            />
            <div>
              <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
                {t("settings.addressTimeout")}
              </label>
              <NumberInput
                min={1}
                max={60}
                step={0.5}
                className={`${inputClass} mt-1`}
                value={draft.address_timeout_seconds}
                onChange={(e) => set("address_timeout_seconds", Number(e.target.value))}
              />
            </div>
          </>
        )}

        <Toggle
          label={t("settings.catalogAutoSync")}
          hint={t("settings.catalogAutoSyncHint")}
          checked={draft.catalog_auto_sync}
          onChange={(value) => set("catalog_auto_sync", value)}
        />


      </section>

      <section hidden={section !== "admin"} className={`${panelClass} p-5 space-y-5`}>
        <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {t("settings.adminFeatures")}
        </h4>

        <Toggle
          label={t("settings.historyEnabled")}
          hint={t("settings.historyEnabledHint")}
          checked={draft.history_enabled}
          onChange={(value) => set("history_enabled", value)}
        />
        <ConfirmDialog
          open={discard !== null}
          title={t("settings.historyDiscardTitle")}
          body={t("settings.historyDiscardBody", {
            shipments: discard?.shipments ?? 0,
            trips: discard?.trips ?? 0,
          })}
          confirmLabel={t("settings.historyDiscardConfirm")}
          onConfirm={() => void discardAndSwitchOff()}
          onCancel={() => setDiscard(null)}
        />

        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
            {t("settings.auditRetention")}
          </label>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{t("settings.auditRetentionHint")}</p>
          <NumberInput
            min={1}
            max={3650}
            step={1}
            className={`${inputClass} mt-1`}
            value={draft.audit_retention_days}
            onChange={(e) => set("audit_retention_days", Number(e.target.value))}
          />
        </div>
      </section>

      <section hidden={section !== "access"} className={`${panelClass} p-5 space-y-5`}>
        <h4>{t("settingsNav.accessPolicy")}</h4>
        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
            {t("settings.twoFactorPolicy")}
          </label>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {t("settings.twoFactorPolicyHint")}
          </p>
          <select
            className={`${inputClass} mt-2`}
            value={draft.two_factor_policy}
            onChange={(e) =>
              set("two_factor_policy", e.target.value as InstanceSettings["two_factor_policy"])
            }
          >
            <option value="off">{t("settings.twoFactorOff")}</option>
            <option value="admins">{t("settings.twoFactorAdmins")}</option>
            <option value="everyone">{t("settings.twoFactorEveryone")}</option>
          </select>
        </div>

        <div>
          <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
            {t("settings.sessionTimeout")}
          </label>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{t("settings.sessionTimeoutHint")}</p>
          <NumberInput
            min={15}
            max={10080}
            step={15}
            className={`${inputClass} mt-1`}
            value={draft.session_timeout_minutes}
            onChange={(e) => set("session_timeout_minutes", Number(e.target.value))}
          />
        </div>

      </section>
      <section hidden={section !== "cards"} className={`${panelClass} p-5 space-y-5`}>
        <h4>{t("settingsNav.cardOptions")}</h4>
        <Toggle
          label={t("settings.unCardsEnabled")}
          hint={t("settings.unCardsEnabledHint")}
          checked={draft.un_cards_enabled}
          onChange={(value) => set("un_cards_enabled", value)}
        />

        <Toggle
          label={t("settings.cardLinks")}
          hint={t("settings.cardLinksHint")}
          checked={draft.card_links_enabled}
          onChange={(value) => set("card_links_enabled", value)}
        />

        {/* A code printed without an address leads nowhere, and the driver
            holding the paper three days later cannot tell that from a code
            that simply failed to scan. */}
        {draft.card_links_enabled && !draft.public_url.trim() && (
          <p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-800 dark:bg-amber-900/30 dark:text-amber-200">
            {t("settings.cardLinksNeedsUrl")}
          </p>
        )}

      </section>
      <section hidden={section !== "mail"} className={`${panelClass} p-5 space-y-5`}>
        <div>
          <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {t("settings.mailTitle")}
          </h4>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{t("settings.mailHint")}</p>
        </div>

        <Toggle
          label={t("settings.mailEnabled")}
          hint={t("settings.mailEnabledHint")}
          checked={draft.mail_enabled}
          onChange={(value) => set("mail_enabled", value)}
        />

        {draft.mail_enabled && (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              <Field
                label={t("settings.mailHost")}
                hint={t("settings.mailHostHint")}
                value={draft.mail_host}
                onChange={(value) => set("mail_host", value)}
              />
              <div>
                <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
                  {t("settings.mailPort")}
                </label>
                <NumberInput
                  min={1}
                  max={65535}
                  className={`${inputClass} mt-1`}
                  value={draft.mail_port}
                  onChange={(e) => set("mail_port", Number(e.target.value))}
                />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
                  {t("settings.mailSecurity")}
                </label>
                <select
                  className={`${inputClass} mt-1`}
                  value={draft.mail_security}
                  onChange={(e) =>
                    set("mail_security", e.target.value as InstanceSettings["mail_security"])
                  }
                >
                  <option value="starttls">{t("settings.mailSecurityStarttls")}</option>
                  <option value="ssl">{t("settings.mailSecuritySsl")}</option>
                  <option value="none">{t("settings.mailSecurityNone")}</option>
                </select>
              </div>
              <Field
                label={t("settings.mailUsername")}
                hint={t("settings.mailUsernameHint")}
                value={draft.mail_username}
                onChange={(value) => set("mail_username", value)}
              />
              <div>
                <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
                  {t("settings.mailPassword")}
                </label>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  {settings.mail_password_set ? t("settings.mailPasswordStored") : t("settings.mailPasswordHint")}
                </p>
                <input
                  type="password"
                  autoComplete="new-password"
                  className={`${inputClass} mt-1`}
                  value={draft.mail_password}
                  onChange={(e) => set("mail_password", e.target.value)}
                />
              </div>
              <Field
                label={t("settings.mailFrom")}
                hint={t("settings.mailFromHint")}
                value={draft.mail_from}
                onChange={(value) => set("mail_from", value)}
              />
              <Field
                label={t("settings.mailFromName")}
                value={draft.mail_from_name}
                onChange={(value) => set("mail_from_name", value)}
              />
            </div>

            <div className="border-t border-slate-100 dark:border-slate-800 pt-4 space-y-2">
              <label className="text-sm font-medium text-slate-800 dark:text-slate-200">
                {t("settings.mailTest")}
              </label>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {dirty ? t("settings.mailTestSaveFirst") : t("settings.mailTestHint")}
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <input
                  type="email"
                  className={`${inputClass} max-w-xs`}
                  placeholder={t("settings.mailTestPlaceholder")}
                  value={testTo}
                  onChange={(e) => setTestTo(e.target.value)}
                />
                <button
                  type="button"
                  className={buttonSecondary}
                  disabled={testing || dirty}
                  onClick={runTest}
                >
                  {testing ? t("settings.mailTesting") : t("settings.mailTestSend")}
                </button>
              </div>
            </div>
          </>
        )}
      </section>

      <div className="flex flex-wrap items-center gap-3">
        <button type="button" onClick={submit} disabled={saving || !dirty} className={buttonPrimary}>
          {saving ? t("settings.saving") : t("settings.saveAdmin")}
        </button>
      </div>
    </div>
  );
}

function Field({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint?: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className="text-sm font-medium text-slate-800 dark:text-slate-200">{label}</label>
      {hint && <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{hint}</p>}
      <input id={id} className={`${inputClass} mt-1`} value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function Toggle({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex items-start gap-3 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
      />
      <span className="min-w-0">
        <span className="block text-sm font-medium text-slate-800 dark:text-slate-200">{label}</span>
        {hint && <span className="block text-xs text-slate-500 dark:text-slate-400 mt-0.5">{hint}</span>}
      </span>
    </label>
  );
}

/**
 * The local AI model: an opt-in download, never part of the image.
 *
 * The assistant always works — without a model it runs its deterministic
 * chain. What this block installs is flexibility only: a small local model
 * that reads free text. The download is the assistant's single external
 * fetch, verified against the SHA-256 pinned in the repository, into
 * /data/assistant; while the sources are unpinned the button stays off.
 */
function AssistantAdmin() {
  const { t } = useTranslation();
  const toast = useToast();
  const [status, setStatus] = useState<AssistantStatus | null>(null);

  const refresh = () =>
    api.assistantStatus().then(setStatus).catch((e) => toast.error(String(e)));

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (status?.download.state !== "downloading") return;
    const timer = window.setInterval(() => void refresh(), 3000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status?.download.state]);

  if (!status) return null;

  const act = async (action: "download" | "remove") => {
    try {
      await api.assistantModel(action);
      await refresh();
    } catch (e) {
      toast.error(String(e));
    }
  };

  return (
    <section className={`${panelClass} p-5 space-y-4`}>
      <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {t("settings.assistantTitle")}
      </h4>
      <p className="text-sm text-slate-600 dark:text-slate-400">{t("settings.assistantIntro")}</p>
      <ul className="space-y-1 text-sm text-slate-700 dark:text-slate-300">
        <li>
          {t("settings.assistantMode")}:{" "}
          <span className="font-medium">
            {status.mode === "model" ? status.model : t("settings.assistantDeterministic")}
          </span>
        </li>
        {status.download.state === "downloading" && (
          <li className="text-amber-700 dark:text-amber-300">
            {t("settings.assistantDownloading")} ({status.download.detail})
          </li>
        )}
        {status.download.state === "error" && (
          <li className="text-red-600 dark:text-red-400">{status.download.detail}</li>
        )}
      </ul>
      <div className="flex flex-wrap gap-2">
        {!status.installed && (
          <button
            type="button"
            disabled={!status.installable || status.download.state === "downloading"}
            onClick={() => void act("download")}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {t("settings.assistantInstall")}
          </button>
        )}
        {status.installed && (
          <button
            type="button"
            onClick={() => void act("remove")}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            {t("settings.assistantRemove")}
          </button>
        )}
      </div>
      {!status.installable && !status.installed && (
        <p className="text-xs text-slate-500 dark:text-slate-400">{t("settings.assistantUnpinned")}</p>
      )}
      {!status.installed && (
        <p className="text-xs text-slate-500 dark:text-slate-400">{t("settings.assistantFootprint")}</p>
      )}
    </section>
  );
}

/** The UN card store: what is installed, and the two ways to fill it.
 *
 *  The cards left the Docker image in v1.129.0 — thousands of generated PDFs
 *  live in a GitHub Release instead, and this panel is where an administrator
 *  pulls them in. Checking the remote feed happens only on the button, never
 *  on page load: an admin opening settings is not consent for an outbound
 *  request. The upload path exists for installations that cannot reach
 *  GitHub; both run the same server-side verification.
 */
export function UnCardsAdminPanel() {
  const { t } = useTranslation();
  const toast = useToast();
  const [status, setStatus] = useState<UnCardStoreStatus | null>(null);
  const [busy, setBusy] = useState<"" | "check" | "download" | "import" | "remove">("");

  const refresh = (remote = false) =>
    api
      .unCardStoreStatus(remote)
      .then(setStatus)
      .catch((e) => toast.error(e instanceof Error ? e.message : String(e)));

  useEffect(() => {
    void refresh(false);
  }, []);

  const run = async (
    kind: "check" | "download" | "import" | "remove",
    action: () => Promise<unknown>,
    done: string,
  ) => {
    setBusy(kind);
    try {
      await action();
      if (done) toast.success(done);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy("");
    }
  };

  const local = status?.local;
  const remote = status?.remote;
  const sizeMb = local?.total_size ? (local.total_size / 1e6).toFixed(0) : null;
  const noPublishedSet = remote?.available === false && remote.reachable !== false;

  return (
    <section className={`${panelClass} p-5 space-y-4`}>
      <div>
        <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {t("settings.unCardsStoreTitle")}
        </h4>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{t("settings.unCardsStoreIntro")}</p>
      </div>

      {local && !local.installed && (
        <p className="text-sm text-slate-700 dark:text-slate-300">{t("settings.unCardsNone")}</p>
      )}
      {local && local.installed && (
        <div className="space-y-1 text-sm text-slate-700 dark:text-slate-300">
          <p>
            {t("settings.unCardsInstalled", {
              count: local.total_cards ?? 0,
              generated: local.generated_at ?? "?",
            })}
            {sizeMb ? ` (${sizeMb} MB)` : ""}
          </p>
          {local.imported_at && (
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {t("settings.unCardsImportedAt", { date: local.imported_at })} · {local.location}
            </p>
          )}
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {Object.entries(local.counts ?? {})
              .map(([modality, count]) => `${modality}: ${count} (${local.editions?.[modality] ?? "?"})`)
              .join(" · ")}
          </p>
        </div>
      )}

      {remote && (
        <p className="text-sm text-slate-700 dark:text-slate-300">
          {remote.reachable === false
            ? t("settings.unCardsRemoteUnreachable")
            : !remote.available
              ? t("settings.unCardsNoRelease")
              : remote.update_available
                ? t("settings.unCardsUpdateAvailable", { tag: remote.tag ?? "" })
                : t("settings.unCardsUpToDate", { tag: remote.tag ?? "" })}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className={buttonSecondary}
          disabled={busy !== ""}
          onClick={() => run("check", () => refresh(true), "")}
        >
          {busy === "check" ? t("settings.unCardsChecking") : t("settings.unCardsCheck")}
        </button>
        <button
          type="button"
          className={buttonPrimary}
          disabled={busy !== "" || noPublishedSet}
          onClick={() =>
            run(
              "download",
              async () => {
                await api.unCardStoreDownloadLatest();
                await refresh(false);
              },
              t("settings.unCardsImportDone"),
            )
          }
        >
          {busy === "download" ? t("settings.unCardsDownloading") : t("settings.unCardsDownload")}
        </button>
        <label className={`${buttonSecondary} cursor-pointer`}>
          {busy === "import" ? t("settings.unCardsImporting") : t("settings.unCardsImportZip")}
          <input
            type="file"
            accept=".zip"
            className="hidden"
            disabled={busy !== ""}
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (!file) return;
              void run(
                "import",
                async () => {
                  await api.unCardStoreImport(file);
                  await refresh(false);
                },
                t("settings.unCardsImportDone"),
              );
            }}
          />
        </label>
        {local?.installed && (
          <button
            type="button"
            className={buttonSecondary}
            disabled={busy !== ""}
            onClick={() => {
              // Deferred removal with undo: the panel flips to "not installed"
              // now; the store is only cleared when the window closes. Undo
              // restores the view — nothing was removed yet.
              const before = status;
              setStatus((current) =>
                current ? { ...current, local: { ...current.local, installed: false } } : current);
              toast.undoable(t("toast.removedUnCards"), {
                execute: () => {
                  api.unCardStoreRemove().then(() => refresh(false)).catch((e) => {
                    toast.error(e instanceof Error ? e.message : String(e));
                    void refresh(false);
                  });
                },
                restore: () => setStatus(before),
              });
            }}
          >
            {t("settings.unCardsRemove")}
          </button>
        )}
      </div>

    </section>
  );
}

/**
 * The logo and the six tile pictures.
 *
 * These act the moment a file is chosen, unlike the name above them, which
 * waits for the save button: a picture is a file on the server, not a value
 * in a form, and "choose a file, then also press save" is the step everyone
 * forgets. The hint says so. The server decides what a file is from its
 * bytes and refuses anything that is not a PNG, JPEG or WebP; the message it
 * answers with is shown as it comes.
 */
function BrandingPictures() {
  const { t } = useTranslation();
  const toast = useToast();
  const { branding, refresh } = useBranding();
  const [busy, setBusy] = useState<string | null>(null);

  const act = async (key: string, work: () => Promise<unknown>, done: string) => {
    setBusy(key);
    try {
      await work();
      await refresh();
      toast.success(t(done));
    } catch (e) {
      toast.error(String(e));
    } finally {
      setBusy(null);
    }
  };

  const pick = (key: string, upload: (file: File) => Promise<unknown>) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/png,image/jpeg,image/webp";
    input.onchange = () => {
      const file = input.files?.[0];
      if (file) void act(key, () => upload(file), "settings.brandUploaded");
    };
    input.click();
  };

  const slot = (key: string, label: string, current: string | null,
                upload: (file: File) => Promise<unknown>, remove: () => Promise<unknown>,
                fallback: string, fallbackClass = "") => (
    <div key={key} data-slot={key} className="branding-slot flex items-center gap-3 rounded-xl border border-slate-200 dark:border-slate-800 p-3">
      <img
        src={current ?? fallback}
        alt=""
        aria-hidden="true"
        className={`h-12 w-20 shrink-0 rounded-lg object-contain bg-slate-50 dark:bg-slate-950 ${current ? "" : fallbackClass}`}
      />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">{label}</p>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          {current ? t("settings.brandCustom") : t("settings.brandDefault")}
        </p>
      </div>
      <div className="flex shrink-0 flex-wrap gap-2">
        <button
          type="button"
          className={buttonSecondary}
          disabled={busy !== null}
          onClick={() => pick(key, upload)}
        >
          {current ? t("settings.brandReplace") : t("settings.brandUpload")}
        </button>
        {current && (
          <button
            type="button"
            className={buttonSecondary}
            disabled={busy !== null}
            onClick={() => void act(key, remove, "settings.brandRemoved")}
          >
            {t("settings.brandRemove")}
          </button>
        )}
      </div>
    </div>
  );

  return (
    <div className="space-y-4">
      <div>
        <label className="text-sm font-medium text-slate-800 dark:text-slate-200">{t("settings.brandLogo")}</label>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 mb-2">{t("settings.brandLogoHint")}</p>
        {slot("logo", t("settings.brandLogo"), branding.logo, api.uploadBrandLogo, api.removeBrandLogo,
              "/emcargo.svg?v=2.11.1")}
      </div>
      <div>
        <label className="text-sm font-medium text-slate-800 dark:text-slate-200">{t("settings.brandModalities")}</label>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 mb-2">{t("settings.brandModalitiesHint")}</p>
        <div className="grid gap-3">
          {MODALITIES.map((key) =>
            slot(key, t(`modality.${key}`), branding.modalities[key] ?? null,
                 (file) => api.uploadBrandModality(key, file), () => api.removeBrandModality(key),
                 `/art/${key}.webp`),
          )}
        </div>
      </div>
    </div>
  );
}


function OrganisationPanel() {
  const { t } = useTranslation();
  const toast = useToast();
  const { reload } = usePreferences();
  const [draft, setDraft] = useState<OrganisationSettings | null>(null);
  const [failure, setFailure] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.organisationSettings().then(setDraft).catch(e => setFailure(String(e))); }, []);
  async function save() {
    if (!draft) return;
    setBusy(true);
    try { setDraft(await api.saveOrganisationSettings(draft)); await reload(); toast.success(t("settings.saved")); }
    catch (e) { setFailure(String(e)); }
    finally { setBusy(false); }
  }
  return <section className={`${panelClass} p-5 space-y-5`}><div><h3 className="font-semibold">{t("settingsNav.organisation")}</h3><p className="mt-2 text-sm text-slate-500">{t("roles.superSettingsHint")}</p></div>
    {failure && <p role="alert">{failure}</p>}
    {draft && <>
      <Field label={t("settings.organisationName")} value={draft.organisation_name} onChange={organisation_name => setDraft({ ...draft, organisation_name })} />
      <label className="block text-sm">{t("settings.organisationAddress")}<textarea className={`${inputClass} mt-2`} value={draft.organisation_address} onChange={e => setDraft({ ...draft, organisation_address: e.target.value })} /></label>
      <label className="block text-sm">{t("settings.adminDefaultLanguage")}<select className={`${inputClass} mt-2`} value={draft.default_language} onChange={e => setDraft({ ...draft, default_language: e.target.value })}>{SUPPORTED_LANGUAGES.map(language => <option key={language} value={language}>{LANGUAGE_NAMES[language]}</option>)}</select></label>
      <label className="block text-sm">{t("settings.adminDefaultTheme")}<select className={`${inputClass} mt-2`} value={draft.default_theme} onChange={e => setDraft({ ...draft, default_theme: e.target.value as ThemeChoice })}>{THEMES.map(theme => <option key={theme} value={theme}>{t(`settings.theme${theme[0].toUpperCase()}${theme.slice(1)}`)}</option>)}</select></label>
      <button className={buttonPrimary} disabled={busy} onClick={() => void save()}>{t("settings.save")}</button>
    </>}
  </section>;
}
