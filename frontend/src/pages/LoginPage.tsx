import AuthLayout from "../components/AuthLayout";
import BrandLockup from "../components/BrandLockup";
import { ArrowRightIcon } from "../components/icons";
import { useState } from "react";
import { useLocation } from "react-router";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { useBranding } from "../branding";

const fieldClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2";

export default function LoginPage({ onLogin }: { onLogin: () => void }) {
  const { t } = useTranslation();
  const location = useLocation();
  const { branding } = useBranding();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [setupWarning, setSetupWarning] = useState("");
  // Forgetting a password happens on this screen or nowhere: somebody who
  // cannot get in cannot reach a page behind the sign-in.
  // The second step, when the account has a second factor.
  const [challenge, setChallenge] = useState("");
  const [method, setMethod] = useState<"totp" | "email">("totp");
  const [codeSent, setCodeSent] = useState(false);
  const [code, setCode] = useState("");
  const [verifying, setVerifying] = useState(false);

  const submitCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (verifying || !code.trim()) return;
    setVerifying(true);
    setError("");
    try {
      await api.loginTwoFactor(challenge, code);
      onLogin();
    } catch (err) {
      setError(String(err));
      setCode("");
    } finally {
      setVerifying(false);
    }
  };

  const [forgotOpen, setForgotOpen] = useState(false);
  const [identifier, setIdentifier] = useState("");
  const [forgotBusy, setForgotBusy] = useState(false);
  const [forgotDone, setForgotDone] = useState("");

  const askReset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (forgotBusy || !identifier.trim()) return;
    setForgotBusy(true);
    try {
      await api.forgotPassword(identifier.trim());
    } catch {
      // The server answers the same either way; a network hiccup should not
      // be the one thing that tells somebody the address was unknown.
    } finally {
      // The same sentence whatever happened — see the endpoint's own reason.
      setForgotDone(t("login.forgotSent"));
      setForgotBusy(false);
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const answer = await api.login(username, password);
      if (answer.two_factor_required) {
        // The password was right; the account has a second factor. Nothing
        // is signed in yet — the challenge is not a session.
        setChallenge(answer.challenge);
        setMethod(answer.method);
        setCodeSent(answer.code_sent);
        return;
      }
      onLogin();
    } catch (err) {
      setError(String(err));
      const status = await api.setupStatus().catch(() => null);
      if (status && !status.has_admin) setSetupWarning(t("login.setup"));
    } finally { setBusy(false); }
  };

  if (challenge) {
    return (
      <AuthLayout>
        <form
          onSubmit={submitCode}
          className="auth-card page-enter space-y-5"
        >
          <div className="text-center">
            <img
              src={branding.logo ?? "/emcargo.svg?v=2.11.1"}
              alt=""
              aria-hidden="true"
              className={`mx-auto h-16 w-16 object-contain ${branding.logo ? "" : ""}`}
            />
            <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 mt-3">
              {t("login.twoFactorTitle")}
            </h1>
            {method === "email" && <p role={codeSent ? "status" : "alert"} className="text-slate-500 dark:text-slate-400 text-sm mt-1">
              {codeSent
                  ? t("login.twoFactorMailSent")
                  : t("login.twoFactorMailFailed")}
            </p>}
          </div>
          <div>
            <label className="block text-sm font-medium mb-1 text-slate-800 dark:text-slate-200" htmlFor="code">
              {t(method === "email" ? "login.twoFactorEmailCode" : "login.twoFactorAppCode")}
            </label>
            <input
              id="code"
              className={fieldClass}
              autoComplete="one-time-code"
              autoFocus
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />
          </div>
          {error && <p role="alert" className="text-red-600 dark:text-red-400 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={verifying || !code.trim()}
            className="w-full bg-brand-600 hover:bg-brand-700 text-white rounded-lg py-2.5 font-medium disabled:opacity-50"
          >
            {verifying ? t("login.twoFactorChecking") : t("login.twoFactorSubmit")}
          </button>
          <button
            type="button"
            onClick={() => {
              setChallenge("");
              setCode("");
              setError("");
            }}
            className="w-full text-sm text-slate-500 hover:underline dark:text-slate-400"
          >
            {t("login.twoFactorBack")}
          </button>
        </form>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      <div className="auth-card page-enter space-y-5">
        <div className="auth-brand"><BrandLockup name={branding.name} logo={branding.logo} /></div>
        <h1>{t(forgotOpen ? "login.forgot" : "studio.loginTitle")}</h1>
        {location.state?.passwordChanged && <p role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">{t("account.passwordChanged")}</p>}
        {setupWarning && <p className="text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg p-3 text-sm">{setupWarning}</p>}
        {!forgotOpen ? <form onSubmit={submit} className="space-y-5">
        <div>
          <label htmlFor="username" className="block text-sm font-medium mb-2 text-slate-800 dark:text-slate-200">{t("login.username")}</label>
          <input id="username" name="username" autoComplete="username" required className="w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2" value={username} onChange={(e) => setUsername(e.target.value)} />
        </div>
        <div>
          <label htmlFor="password" className="block text-sm font-medium mb-2 text-slate-800 dark:text-slate-200">{t("login.password")}</label>
          <input id="password" name="password" autoComplete="current-password" required type="password" className="w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        {error && <p role="alert" className="text-red-600 dark:text-red-400 text-sm">{error}</p>}
        <button type="submit" disabled={busy} aria-busy={busy} className="action-primary w-full">
          {busy ? t("studio.loginBusy") : t("login.submit")}<ArrowRightIcon className="h-4 w-4" />
        </button>

            <button
              type="button"
              onClick={() => { setIdentifier(username); setForgotOpen(true); }}
              className="text-sm text-brand-700 hover:underline dark:text-brand-300"
            >
              {t("login.forgot")}
            </button>
        </form> : <div className="space-y-4">
          {!forgotDone ? <form onSubmit={askReset} className="space-y-3">
              <label htmlFor="reset-identifier" className="block text-sm font-medium text-slate-800 dark:text-slate-200">
                {t("login.forgotLabel")}
              </label>
              <input
                id="reset-identifier" autoComplete="username"
                autoFocus required
                className={fieldClass}
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
              />
              <button
                type="submit"
                disabled={forgotBusy || !identifier.trim()}
                className="action-primary w-full"
              >
                {forgotBusy ? t("login.forgotSending") : t("login.forgotSubmit")}
              </button>
          </form> : <p role="status" className="text-sm text-slate-600 dark:text-slate-300">{forgotDone}</p>}
          <button type="button" className="action-secondary w-full" disabled={forgotBusy}
            onClick={() => { setForgotOpen(false); setForgotDone(""); }}>{t("login.twoFactorBack")}</button>
        </div>}
      </div>
    </AuthLayout>
  );
}
