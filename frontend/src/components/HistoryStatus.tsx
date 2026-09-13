import { Link } from "react-router";
import { useTranslation } from "react-i18next";
import { usePreferences } from "../settings/preferences";
import { HistoryIcon, SettingsIcon, RefreshIcon } from "./icons";

/** Keep destinations discoverable without changing the installation's retention policy. */
export default function HistoryStatus({ title, admin = false, embedded = false }: { title: string; admin?: boolean; embedded?: boolean }) {
  const { t } = useTranslation();
  const { publicSettings, loaded, reload } = usePreferences();
  const loading = !publicSettings && !loaded;
  return <div className={embedded ? "history-status-page" : "collection-page page-enter history-status-page"}>
    {!embedded && <header className="page-heading"><h2>{title}</h2></header>}
    <section className="surface history-status-panel">
      <HistoryIcon className="h-8 w-8" />
      <div><h3>{t(loading ? "wizard.loading" : publicSettings ? "historyAccess.disabled" : "historyAccess.unavailable")}</h3>
        {publicSettings ? <><p>{t("history.off")}</p><p>{t(admin ? "historyAccess.adminHint" : "historyAccess.memberHint")}</p></>
          : !loading && <p>{t("historyAccess.retryHint")}</p>}
        {publicSettings && <Link className="mt-3 block text-sm underline" to="/dg-reviews">{t("dgReview.privacyLink")}</Link>}
        {publicSettings && admin && <Link className="action-primary" to="/admin/settings/organisation"><SettingsIcon />{t("historyAccess.settings")}</Link>}
        {!publicSettings && !loading && <button className="action-secondary" type="button" onClick={() => void reload()}><RefreshIcon />{t("historyAccess.retry")}</button>}
      </div>
    </section>
  </div>;
}
