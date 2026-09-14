import BrandLockup from "./BrandLockup";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useBranding } from "../branding";

export default function AuthLayout({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const { branding } = useBranding();
  return <main className="auth-layout">
    <section className="auth-form-side">{children}</section>
    <aside className="auth-art" aria-hidden="true">
      <img className="auth-art-image" src="/art/login-harbor.webp" alt="" width="1672" height="941" />
      <div className="auth-art-brand"><BrandLockup name={branding.name} logo={branding.logo} /></div>
      <div className="auth-art-caption"><p>{t("authArt.title")}</p><span>{["road", "rail", "sea", "inland"].map(mode => t(`modality.${mode}`)).join(" / ")}</span></div>
    </aside>
  </main>;
}
