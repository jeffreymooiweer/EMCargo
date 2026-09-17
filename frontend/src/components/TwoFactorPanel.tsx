import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, TwoFactorSetup, TwoFactorStatus } from "../api/client";
import { useToast } from "../toast/ToastProvider";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";
const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2.5 text-sm min-h-[44px]";
const buttonPrimary =
  "bg-brand-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50 min-h-[44px] text-sm";
const buttonSecondary =
  "px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 min-h-[44px] text-sm";

/** Setting up, checking on, and switching off your own second factor.
 *
 *  The recovery codes are shown once, here, and never again: only their
 *  hashes are kept. That is worth saying on the screen rather than only in
 *  the documentation, because somebody who closes this panel without
 *  writing them down has lost them. */
export default function TwoFactorPanel() {
  const { t } = useTranslation();
  const [status, setStatus] = useState<TwoFactorStatus | null>(null);
  const [setup, setSetup] = useState<TwoFactorSetup | null>(null);
  const [code, setCode] = useState("");
  const [renewing, setRenewing] = useState(false);
  const [renewCode, setRenewCode] = useState("");
  const [disabling, setDisabling] = useState(false);
  const [codes, setCodes] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [loadError, setLoadError] = useState("");
  const running = useRef(false);
  const toast = useToast();

  const load = () => {
    setLoadError("");
    return api.twoFactorStatus().then(setStatus).catch((e) => setLoadError(e instanceof Error ? e.message : String(e)));
  };
  useEffect(() => {
    void load();
  }, []);

  const run = async (action: () => Promise<unknown>) => {
    if (running.current) return;
    running.current = true;
    setBusy(true);
    try {
      await action();
    } catch (e) {
      toast.error(String(e));
    } finally {
      running.current = false;
      setBusy(false);
    }
  };

  const start = (method: "totp" | "email") =>
    run(async () => {
      setCodes(null);
      setSetup(await api.twoFactorStart(method));
      setCode("");
    });

  const confirm = () =>
    run(async () => {
      const result = await api.twoFactorConfirm(code);
      setCodes(result.recovery_codes);
      setSetup(null);
      setCode("");
      await load();
    });

  const disable = () =>
    run(async () => {
      await api.twoFactorDisable(code);
      setCode("");
      setCodes(null);
      setDisabling(false);
      toast.success(t("twoFactor.disabled"));
      await load();
    });

  // With the mail method there is no code to type until one has been sent:
  // without this button the setting could be switched on and never off.
  const sendCode = () =>
    run(async () => {
      await api.twoFactorSendCode();
      toast.success(t("twoFactor.codeSent"));
    });

  const newCodes = () =>
    run(async () => {
      const result = await api.twoFactorNewRecoveryCodes(renewCode);
      setRenewCode("");
      setRenewing(false);
      setCodes(result.recovery_codes);
      await load();
    });

  if (!status) return <section className={`${panelClass} p-5 space-y-4`}>
    <h3 className="text-lg font-semibold">{t("twoFactor.title")}</h3>
    {loadError ? <><p role="alert" className="text-red-700 dark:text-red-300">{loadError}</p>
      <button type="button" className={buttonSecondary} onClick={() => void load()}>{t("history.retry")}</button></>
      : <p role="status">{t("wizard.loading")}</p>}
  </section>;

  return (
    <section className={`${panelClass} p-5 space-y-4`} aria-busy={busy}>
      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {t("twoFactor.title")}
        </h3>
      </div>
      {loadError && <p role="alert" className="text-red-700 dark:text-red-300">{loadError}</p>}

      {status.required && !status.active && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-300">
          {t("twoFactor.requiredStatus")}
        </p>
      )}

      {status.active ? (
        <div className="space-y-3">
          <p className="text-sm text-slate-700 dark:text-slate-200">
            {t(status.method === "email" ? "twoFactor.onByMail" : "twoFactor.onByApp")}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {t("twoFactor.codesLeft", { count: status.recovery_codes_left })}
          </p>
          <div className="flex flex-wrap gap-2">
            <button type="button" className={buttonSecondary} disabled={busy} aria-expanded={renewing} aria-controls="renew-codes-form" onClick={() => { setRenewing(true); setDisabling(false); setCode(""); setCodes(null); }}>
              {t("twoFactor.newCodes")}
            </button>
            {!status.required && !disabling && <button type="button" className={buttonSecondary} disabled={busy} aria-expanded={false}
              onClick={() => { setDisabling(true); setRenewing(false); setRenewCode(""); }}>{t("twoFactor.turnOff")}</button>}
          </div>
          {renewing && <form id="renew-codes-form" className="space-y-2" onSubmit={event => { event.preventDefault(); if (renewCode.trim() && !busy) void newCodes(); }}>
            <label htmlFor="renew-code" className="block text-sm font-medium">{t("twoFactor.renewCode")}</label>
            <p className="text-xs text-slate-500 dark:text-slate-400" id="renew-hint">{t("twoFactor.replacesCodes")}</p>
            <div className="flex flex-wrap gap-2">
              {status.method === "email" && <button type="button" className={buttonSecondary} disabled={busy} onClick={sendCode}>{t("twoFactor.sendCode")}</button>}
              <input id="renew-code" autoFocus disabled={busy} autoComplete="one-time-code" aria-describedby="renew-hint" className={`${inputClass} max-w-[12rem]`} value={renewCode} onChange={event => setRenewCode(event.target.value)} />
              <button className={buttonPrimary} disabled={busy || !renewCode.trim()}>{t("twoFactor.confirm")}</button>
              <button type="button" className={buttonSecondary} disabled={busy} onClick={() => { setRenewing(false); setRenewCode(""); }}>{t("twoFactor.cancel")}</button>
            </div>
          </form>}
          {!status.required && disabling && (
            <form id="disable-two-factor-form" className="border-t border-slate-100 pt-3 dark:border-slate-800" onSubmit={event => { event.preventDefault(); if (code.trim() && !busy) void disable(); }}>
              <label className="text-sm font-medium text-slate-800 dark:text-slate-200" htmlFor="off-code">
                {t("twoFactor.verificationOrRecoveryCode")}
              </label>
              <div className="mt-2 flex flex-wrap gap-2">
                {status.method === "email" && (
                  <button type="button" className={buttonSecondary} disabled={busy} onClick={sendCode}>
                    {t("twoFactor.sendCode")}
                  </button>
                )}
                <input
                  id="off-code"
                  autoFocus
                  autoComplete="one-time-code"
                  disabled={busy}
                  className={`${inputClass} max-w-[12rem]`}
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                />
                <button type="submit" className={buttonSecondary} disabled={busy || !code.trim()}>
                  {t("twoFactor.turnOffDo")}
                </button>
                <button type="button" className={buttonSecondary} disabled={busy} onClick={() => { setDisabling(false); setCode(""); }}>{t("twoFactor.cancel")}</button>
              </div>
            </form>
          )}
        </div>
      ) : setup ? (
        <form className="space-y-3" onSubmit={event => { event.preventDefault(); if (code.trim() && !busy) void confirm(); }}>
          {setup.method === "totp" ? (
            <>
              <h4 className="text-sm font-medium text-slate-700 dark:text-slate-200">{t("twoFactor.authenticatorQr")}</h4>
              {/* Drawn by this server, not fetched from a QR service: the
                  secret in it is the whole secret. */}
              <div
                className="inline-block rounded-lg bg-white p-2"
                dangerouslySetInnerHTML={{ __html: setup.qr_svg }}
              />
              <details className="text-sm text-slate-500 dark:text-slate-400">
                <summary className="cursor-pointer min-h-[44px] py-3">{t("twoFactor.setupKey")}</summary>
                <code className="block break-all select-all font-mono">{setup.secret}</code>
              </details>
            </>
          ) : (
            <p className="text-sm text-slate-700 dark:text-slate-200">{t("twoFactor.mailSent")}</p>
          )}
          <label className="block text-sm font-medium text-slate-800 dark:text-slate-200" htmlFor="confirm-code">
            {t("twoFactor.enterCode")}
          </label>
          <div className="flex flex-wrap gap-2">
            <input
              id="confirm-code"
              className={`${inputClass} max-w-[12rem]`}
              autoComplete="one-time-code"
              inputMode="numeric"
              disabled={busy}
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />
            <button type="submit" className={buttonPrimary} disabled={busy || !code.trim()}>
              {t("twoFactor.confirm")}
            </button>
            <button type="button" className={buttonSecondary} disabled={busy} onClick={() => { setSetup(null); setCode(""); }}>
              {t("twoFactor.cancel")}
            </button>
          </div>
        </form>
      ) : (
        <div className="flex flex-wrap gap-2">
          <button type="button" className={buttonPrimary} disabled={busy} onClick={() => start("totp")}>
            {t("twoFactor.setUpApp")}
          </button>
          <button type="button" className={buttonSecondary} disabled={busy} onClick={() => start("email")}>
            {t("twoFactor.setUpMail")}
          </button>
        </div>
      )}

      {codes && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 dark:border-emerald-900/50 dark:bg-emerald-900/20">
          <p className="text-sm font-medium text-emerald-900 dark:text-emerald-200">
            {t("twoFactor.recoveryTitle")}
          </p>
          <p className="mt-0.5 text-xs text-emerald-800 dark:text-emerald-300">
            {t("twoFactor.recoveryHint")}
          </p>
          <ul className="mt-2 grid grid-cols-2 gap-1 font-mono text-sm text-emerald-900 dark:text-emerald-100">
            {codes.map((one) => (
              <li key={one}>{one}</li>
            ))}
          </ul>
        </div>
      )}

    </section>
  );
}
