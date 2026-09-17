import { DocumentIcon, DownloadIcon } from "../components/icons";
import BrandLockup from "../components/BrandLockup";
/** Authenticated card lookup for UN numbers in a transport-document QR link. */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router";

import { api } from "../api/client";

type Card = { un_number: string; available: boolean };

export default function CardsPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const un = params.get("un") ?? "";
  const modality = (params.get("m") ?? "ADR").toUpperCase();
  const [cards, setCards] = useState<Card[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setCards(null); setFailed(false);
    api
      .cardLookup(un, modality)
      .then((r) => {
        if (!cancelled) setCards(r.cards);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [un, modality, attempt]);

  return (
    <main className="public-cards page-enter">
      <div className="public-cards-brand"><BrandLockup /></div>
      <DocumentIcon className="mb-5 h-8 w-8 text-brand-600" />
      <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
        {t("cards.title")}
      </h1>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
        {modality}
      </p>

      {failed && (
        <div role="alert" className="mt-6 space-y-3 rounded-lg bg-amber-50 p-4 text-sm text-amber-800 dark:bg-amber-900/30 dark:text-amber-200">
          <p>{t("cards.loadFailed")}</p>
          <button className="action-secondary" onClick={() => setAttempt(value => value + 1)}>{t("overview.retry")}</button>
        </div>
      )}

      {!cards && !failed && <p role="status" className="mt-6 text-sm">{t("wizard.loading")}</p>}

      {cards && cards.length === 0 && (
        <p className="mt-6 text-sm text-slate-600 dark:text-slate-400">{t("cards.none")}</p>
      )}

      {cards && cards.length > 0 && (
        <ul className="mt-6 space-y-2">
          {cards.map((card) => (
            <li
              key={card.un_number}
              className="surface flex items-center justify-between gap-4 p-4"
            >
              <span className="font-medium text-slate-900 dark:text-slate-100">
                UN {card.un_number}
              </span>
              {card.available ? (
                <a
                  className="action-secondary"
                  href={`/api/cards/${card.un_number}/${modality}.pdf`}
                >
                  <DownloadIcon />{t("cards.open")}
                </a>
              ) : (
                <span className="text-sm text-slate-500 dark:text-slate-400">
                  {t("cards.missing")}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}

    </main>
  );
}
