import { DocumentIcon, DownloadIcon } from "../components/icons";
import BrandLockup from "../components/BrandLockup";
/** The page a QR code on a transport document opens.
 *
 *  Public, and the only page in the application that is. The people this is
 *  for — the driver at the roadside, the warehouse taking the pallet in, the
 *  responder who arrived because something went wrong — do not have accounts
 *  here, and a code that asks them to log in is a code that does nothing.
 *
 *  It shows nothing about the consignment: no parties, no quantities, no
 *  reference. Only which UN numbers the link named and whether this
 *  installation holds a card for each. The document that carries the code
 *  already prints those numbers in plain text and larger.
 *
 *  A missing card is shown as missing rather than left out. Somebody standing
 *  at a vehicle needs to know a card is absent, not to be handed a shorter
 *  list and left to assume it was complete.
 */
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
  }, [un, modality]);

  return (
    <main className="public-cards page-enter">
      <div className="public-cards-brand"><BrandLockup /></div>
      <DocumentIcon className="mb-5 h-8 w-8 text-brand-600" />
      <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
        {t("cards.title")}
      </h1>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
        {t("cards.subtitle", { modality })}
      </p>

      {failed && (
        <p className="mt-6 rounded-lg bg-amber-50 p-4 text-sm text-amber-800 dark:bg-amber-900/30 dark:text-amber-200">
          {t("cards.unavailable")}
        </p>
      )}

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

      <p className="mt-8 text-xs text-slate-500 dark:text-slate-400">{t("cards.note")}</p>
    </main>
  );
}
