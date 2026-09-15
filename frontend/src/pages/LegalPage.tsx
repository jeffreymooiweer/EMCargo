import { Fragment, useState } from "react";
import { useTranslation } from "react-i18next";
import terms from "../../../TERMS.nl.md?raw";
import { DocumentIcon, DownloadIcon } from "../components/icons";

const panelClass = "surface";
const sections = terms.split(/^### /m).slice(1).map(section => {
  const [heading, ...body] = section.split("\n");
  return { heading, body: body.join("\n").trim() };
});
function Paragraph({ text }: { text: string }) {
  return <p>{text.split(/(\*\*.*?\*\*)/g).map((part, i) => part.startsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong> : <Fragment key={i}>{part}</Fragment>)}</p>;
}
export default function LegalPage() {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  function download() {
    const url = URL.createObjectURL(new Blob([terms], { type: "text/markdown;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url; link.download = "EMCargo-gebruikersvoorwaarden-0.2-concept.md"; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <div className="collection-page page-enter legal-workspace">
    <header className="page-heading"><div><p className="eyebrow">EMCargo</p><h2>{t("legal.title")}</h2><p>{t("legal.updated")}</p></div><button className="action-secondary" onClick={download}><DownloadIcon />{t("legal.download")}</button></header>
    <section className="surface legal-introduction"><DocumentIcon className="h-8 w-8" /><div><p>{t("legal.intro")}</p><p className="mt-3 text-sm text-slate-500">{t("legal.sourceLanguage")}</p></div></section>
    <button className="action-secondary" onClick={() => setExpanded(value => !value)}>{t(expanded ? "legal.collapseAll" : "legal.expandAll")}</button>
    <div className="surface legal-articles" lang="nl" key={String(expanded)}>{sections.map((section, index) => <details key={section.heading} open={expanded || index === 0}>
      <summary>{section.heading}</summary><div className="legal-body">{section.body.split(/\n\n+/).map((paragraph, i) => <Paragraph key={i} text={paragraph} />)}</div>
    </details>)}</div>
      {/* Credits belong where the people using the application can see them,
          not only in a file in the repository: the icon set is free to use on
          the condition that it is named, and a licence condition met only in
          a developer's markdown is not met. The link is part of the required
          form and therefore hard-coded rather than translated — only the
          sentence around it changes language. */}
      <div className={`${panelClass} p-5 sm:p-6`}>
        <p className="mb-3 text-sm">{t("legal.stationCredit")} <a className="underline" href="https://github.com/trainline-eu/stations" target="_blank" rel="noreferrer">Trainline EU stations</a> · <a className="underline" href="/api/legal/odbl">ODbL 1.0</a></p>
        <div className="flex flex-wrap gap-4 mb-4 text-sm"><a className="underline" href="/api/legal/stations">{t("legal.stationDownload")}</a><a className="underline" href="/api/legal/third-party-notices">{t("legal.thirdPartyNotices")}</a></div>
        <h3 className="font-semibold text-slate-900 dark:text-slate-100">{t("legal.creditsHeading")}</h3>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          {t("legal.creditsBody")}
        </p>
        {/* Two lines, not one, because they are two sets. The first eight came
            from the Uicons set and were confirmed against it. The twenty-one
            added in v1.202.0 for the shell did not: their exported markup does
            not match a Uicons export, so naming them as Uicons would be a
            statement nobody checked. What is certain about them is where they
            were downloaded from, and that is what this says. */}
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Uicons by{" "}
          <a
            href="https://www.flaticon.com/uicons"
            target="_blank"
            rel="noreferrer"
            className="text-sky-700 underline dark:text-sky-400"
          >
            Flaticon
          </a>
        </p>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
          Icons by{" "}
          <a
            href="https://www.flaticon.com/"
            target="_blank"
            rel="noreferrer"
            className="text-sky-700 underline dark:text-sky-400"
          >
            Flaticon
          </a>
        </p>
      </div>
  </div>;
}
