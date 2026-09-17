import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { useTranslation } from "react-i18next";
import { useBranding } from "../branding";
import { ModalityIcon } from "../components/WizardShell";
import { ArrowRightIcon, ImportIcon } from "../components/icons";
import { usePreferences } from "../settings/preferences";

export const MODALITIES = ["road", "rail", "sea", "inland", "air", "multimodal"] as const;
export type ModalityKey = (typeof MODALITIES)[number];

/** Released modes share one allowlist for tiles, preferences and wizard URLs.
 * Sea was verified and released in v1.152.0. Restore access after the v2.4.0
 * selection lock; document validation and specialist release still apply.
 * Air and multimodal retain the coverage gaps documented in docs/dg-coverage.md. */
export const AVAILABLE_MODALITIES: readonly ModalityKey[] = ["road", "rail", "sea", "inland"];

export function isModalityKey(value: string | undefined): value is ModalityKey {
  return !!value && (MODALITIES as readonly string[]).includes(value);
}

export function isModalityAvailable(value: string | undefined): value is ModalityKey {
  return isModalityKey(value) && AVAILABLE_MODALITIES.includes(value);
}

export default function ModalitySelectPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { preferences, loaded } = usePreferences();
  const custom = useBranding().branding.modalities;

  // Someone who only ever ships by road should not tap the same tile every
  // morning. `?choose=1` switches the tiles back on for one visit — without it,
  // "change transport mode" would land here and bounce straight back.
  const skipDefault = params.get("choose") === "1";
  const preferred = preferences.default_modality;
  useEffect(() => {
    if (!loaded || skipDefault) return;
    // A preference set while a modality was open must not keep opening it after
    // it has been locked. The tiles come back instead, with the reason on them.
    if (isModalityAvailable(preferred)) navigate(`/wizard/${preferred}`, { replace: true });
  }, [loaded, skipDefault, preferred, navigate]);

  return (
    <div className="start-workspace page-enter">
      <header className="page-heading">
        <div><p className="eyebrow">{t("nav.new")}</p><h2>{t("modality.title")}</h2>
        </div>
      </header>
      <div className="start-layout">
        <section className="mode-grid" aria-label={t("wizard.mode")}>
          {MODALITIES.map((key) => <button key={key} type="button" disabled={!isModalityAvailable(key)} className={`mode-card mode-card-${key}`} onClick={() => navigate(`/wizard/${key}`)}>
            <span className="mode-card-visual"><img src={custom[key] || `/art/${key}.webp`} alt="" width="768" height="384" decoding="async" />
              <span className="mode-card-rule">{({ road: "ADR", rail: "RID", sea: "IMDG", inland: "ADN" } as Record<string,string>)[key]}</span>
            </span>
            <span className="mode-card-content"><ModalityIcon modality={key} className="mode-card-icon" />
              <span className="mode-copy"><strong>{t(`modality.${key}`)}</strong>{!isModalityAvailable(key) && <span>{t("modality.inDevelopment")}</span>}</span>
              {isModalityAvailable(key) && <span className="mode-card-arrow"><ArrowRightIcon className="h-5 w-5" /></span>}
            </span>
          </button>)}
        </section>
        <aside className="start-import surface">
          <span className="import-glyph"><ImportIcon className="h-6 w-6" /></span>
          <h3>{t("studio.importTitle")}</h3>
          <button className="action-primary" onClick={() => navigate(`/wizard/${isModalityAvailable(preferred) ? preferred : "road"}?input=paste`)}>{t("overview.paste")}<ArrowRightIcon className="h-4 w-4" /></button>
          <span className="import-formats">XLSX <span>·</span> CSV <span>·</span> TXT</span>
        </aside>
      </div>
    </div>
  );
}
