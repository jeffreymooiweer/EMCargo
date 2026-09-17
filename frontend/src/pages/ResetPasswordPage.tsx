import AuthLayout from "../components/AuthLayout";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router";
import { api } from "../api/client";
import { useBranding } from "../branding";

const fieldClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2";

/** Where a reset or an invitation link lands: choose a password, once.
 *
 *  Two things this page owes its visitor. It checks the link **before**
 *  drawing the form, because a spent link that looks fresh lets somebody
 *  think up a password, type it twice and only then learn they were too
 *  late. And when the password is set it signs them in: holding the link
 *  proved the mailbox, the password was just chosen here, and retyping both
 *  on a sign-in form proves nothing to anybody. */
export default function ResetPasswordPage() {
  const { t } = useTranslation();
  const { branding } = useBranding();
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [linkState, setLinkState] = useState<"checking" | "valid" | "spent">(
    token ? "checking" : "spent",
  );
  // With a second factor the password is only half: a mailbox does not
  // waive it, so the same second step as at sign-in follows.
  const [challenge, setChallenge] = useState("");
  const [method, setMethod] = useState<"totp" | "email">("totp");
  const [codeSent, setCodeSent] = useState(false);
  const [code, setCode] = useState("");

  useEffect(() => {
    if (!token) return;
    api
      .resetLinkValid(token)
      .then((answer) => setLinkState(answer.valid ? "valid" : "spent"))
      // A check that cannot be made is not a link that is spent: show the
      // form and let the attempt itself say what is wrong.
      .catch(() => setLinkState("valid"));
  }, [token]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return;
    if (password !== repeat) {
      setError(t("reset.mismatch"));
      return;
    }
    setBusy(true);
    setError("");
    try {
      const answer = await api.resetPassword(token, password);
      if (answer.two_factor_required) {
        setChallenge(answer.challenge);
        setMethod(answer.method);
        setCodeSent(answer.code_sent);
        return;
      }
      // Signed in already; the app reads the session on the way in.
      window.location.assign("/");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  const submitCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (busy || !code.trim()) return;
    setBusy(true);
    setError("");
    try {
      await api.loginTwoFactor(challenge, code);
      window.location.assign("/");
    } catch (err) {
      setError(String(err));
      setCode("");
    } finally {
      setBusy(false);
    }
  };

  const frame = (children: React.ReactNode) => (
    <AuthLayout>
      <div className="auth-card page-enter space-y-5">
        <div className="text-center">
          <img
            src={branding.logo ?? "/emcargo.svg?v=2.11.1"}
            alt=""
            aria-hidden="true"
            className={`mx-auto h-16 w-16 object-contain ${branding.logo ? "" : ""}`}
          />
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 mt-3">
            {t("reset.title")}
          </h1>
        </div>
        {children}
      </div>
    </AuthLayout>
  );

  if (linkState === "checking") {
    return frame(<p role="status" className="text-sm text-slate-500 dark:text-slate-400">{t("reset.checking")}</p>);
  }

  if (linkState === "spent") {
    return frame(
      <>
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {token ? t("reset.spent") : t("reset.noToken")}
        </p>
        <Link
          to="/login"
          className="block w-full rounded-lg bg-brand-600 py-2.5 text-center font-medium text-white hover:bg-brand-700"
        >
          {t("reset.toLogin")}
        </Link>
      </>,
    );
  }

  if (challenge) {
    return frame(
      <form onSubmit={submitCode} className="space-y-4">
        {method === "email" && <p role={codeSent ? "status" : "alert"} className="text-sm text-slate-600 dark:text-slate-300">
          {t(codeSent ? "login.twoFactorMailSent" : "login.twoFactorMailFailed")}
        </p>}
        <div>
          <label className="block text-sm font-medium mb-1 text-slate-800 dark:text-slate-200" htmlFor="reset-code">
            {t(method === "email" ? "login.twoFactorEmailCode" : "login.twoFactorAppCode")}
          </label>
          <input
            id="reset-code"
            className={fieldClass}
            autoComplete="one-time-code"
            autoFocus
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
        </div>
        {error && <p role="alert" className="text-sm text-red-600 dark:text-red-400">{error}</p>}
        <button
          type="submit"
          disabled={busy || !code.trim()}
          className="w-full rounded-lg bg-brand-600 py-2.5 font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {busy ? t("login.twoFactorChecking") : t("login.twoFactorSubmit")}
        </button>
      </form>,
    );
  }

  return frame(
    <form onSubmit={submit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium mb-1 text-slate-800 dark:text-slate-200" htmlFor="new-password">
          {t("reset.password")}
        </label>
        <input
          id="new-password"
          type="password"
          autoComplete="new-password"
          className={fieldClass}
          minLength={8}
          placeholder={t("reset.passwordHint")}
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1 text-slate-800 dark:text-slate-200" htmlFor="repeat-password">
          {t("reset.repeat")}
        </label>
        <input
          id="repeat-password"
          type="password"
          autoComplete="new-password"
          className={fieldClass}
          required
          value={repeat}
          onChange={(e) => setRepeat(e.target.value)}
        />
      </div>
      {error && <p role="alert" className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <button
        type="submit"
        disabled={busy}
        className="w-full rounded-lg bg-brand-600 py-2.5 font-medium text-white hover:bg-brand-700 disabled:opacity-50"
      >
        {busy ? t("reset.saving") : t("reset.submitAndSignIn")}
      </button>
    </form>,
  );
}
