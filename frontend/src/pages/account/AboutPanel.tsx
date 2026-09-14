import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import BrandLockup from "../../components/BrandLockup";
import { ArrowRightIcon, CodeIcon, DocumentIcon, HistoryIcon, RoadIcon, ShieldIcon, ShipmentsIcon } from "../../components/icons";
import { version as buildVersion } from "../../../package.json";

const repository = "https://github.com/jeffreymooiweer/emcargo";

export default function AboutPanel({ version }: { version: string }) {
  const { t } = useTranslation();
  const features = [
    { icon: ShipmentsIcon, title: "account.aboutShipments", text: "account.aboutShipmentsBody" },
    { icon: DocumentIcon, title: "account.aboutDocuments", text: "account.aboutDocumentsBody" },
    { icon: ShieldIcon, title: "account.aboutChecks", text: "account.aboutChecksBody" },
  ];
  return <div className="account-about">
    <section className="about-hero">
      <div className="about-route-art" aria-hidden="true"><span /><span /><span /><RoadIcon /></div>
      <div className="about-product">
        <h3><BrandLockup /></h3><span className="about-version">v{(version || buildVersion).trim().replace(/^v/, "")}</span>
      </div>
      <p className="about-statement">{t("account.aboutTagline")}</p>
      <p className="about-description">{t("account.aboutIntro")}</p>
      <div className="about-principles"><span>{t("account.openSource")}</span><span>{t("account.selfHosted")}</span><span>{t("account.fourLanguages")}</span></div>
    </section>
    <div className="about-features">{features.map(({ icon: Icon, title, text }) => <section key={title}>
      <Icon /><h4>{t(title)}</h4><p>{t(text)}</p>
    </section>)}</div>
    <Link to="/account/about/terms" className="about-terms-link"><span className="about-link-icon"><DocumentIcon /></span>
      <span><strong>{t("legal.title")}</strong><span>{t("account.termsIntro")}</span></span><ArrowRightIcon /></Link>
    <div className="about-project-links">
      <a href={repository} target="_blank" rel="noreferrer"><CodeIcon /><span>{t("account.sourceCode")}</span><ArrowRightIcon /></a>
      <a href={`${repository}/releases`} target="_blank" rel="noreferrer"><HistoryIcon /><span>{t("account.releaseNotes")}</span><ArrowRightIcon /></a>
      <a href={`${repository}/issues`} target="_blank" rel="noreferrer"><ShieldIcon /><span>{t("account.feedback")}</span><ArrowRightIcon /></a>
    </div>
    <footer className="about-footer"><span>{t("account.madeBy")}</span><a href={`${repository}/blob/main/LICENSE`} target="_blank" rel="noreferrer">Apache License 2.0</a></footer>
  </div>;
}
