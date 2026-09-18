import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { useTranslation } from "react-i18next";
import { useBranding } from "../branding";
import { ModalityIcon } from "../components/WizardShell";
import { ArrowRightIcon, ImportIcon } from "../components/icons";
import { usePreferences } from "../settings/preferences";

export const MODALITIES = ["road", "rail", "sea", "inland", "air", "multimodal"] as const;
export type ModalityKey = (typeof MODALITIES)[number] | "preparation";

/** Released modes share one allowlist for tiles, preferences and wizard URLs.
 * Sea was verified and released in v1.152.0. Restore access after the v2.4.0
 * selection lock; document validation and specialist release still apply.
 * Air preparation is available; operational release requires a qualified modal review.
 * Combined journeys are planned as individual delivery legs. */
export const AVAILABLE_MODALITIES: readonly ModalityKey[] = ["preparation", "road", "rail", "sea", "inland", "air"];

export function isModalityKey(value: string | undefined): value is ModalityKey {
  return value === "preparation" || !!value && (MODALITIES as readonly string[]).includes(value);
}

export function isModalityAvailable(value: string | undefined): value is ModalityKey {
  return isModalityKey(value) && AVAILABLE_MODALITIES.includes(value);
}

export default function ModalitySelectPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  useEffect(() => { navigate(`/wizard/preparation${params.has("input") ? `?input=${encodeURIComponent(params.get("input") || "")}` : ""}`, { replace: true }); }, [navigate, params]);
  return null;
}
