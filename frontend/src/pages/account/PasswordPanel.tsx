import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { api } from "../../api/client";
import { CheckIcon } from "../../components/icons";

export default function PasswordPanel({ onPasswordChanged }: { onPasswordChanged: () => void }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [current, setCurrent] = useState("");
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const running = useRef(false);
  const confirmation = useRef<HTMLInputElement>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (running.current) return;
    if (password !== repeat) { setError(t("reset.mismatch")); confirmation.current?.focus(); return; }
    if (password === current) { setError(t("account.passwordDifferent")); return; }
    running.current = true; setBusy(true); setError("");
    try {
      await api.changePassword(current, password);
      setCurrent(""); setPassword(""); setRepeat("");
      onPasswordChanged();
      navigate("/login", { replace: true, state: { from: "/account/security", passwordChanged: true } });
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { running.current = false; setBusy(false); }
  }

  return <form className="account-panel account-password" onSubmit={submit} aria-busy={busy}>
    <div className="account-section-heading"><h3>{t("account.changePassword")}</h3></div>
    <fieldset disabled={busy} className="account-fields">
      <label className="account-field-wide">{t("account.currentPassword")}<input required type={visible ? "text" : "password"} autoComplete="current-password"
        value={current} onChange={e => setCurrent(e.target.value)} /></label>
      <label>{t("account.newPasswordMinimum")}<input required minLength={8} type={visible ? "text" : "password"} autoComplete="new-password"
        value={password} onChange={e => setPassword(e.target.value)} /></label>
      <label>{t("account.repeatPassword")}<input ref={confirmation} required minLength={8} type={visible ? "text" : "password"} autoComplete="new-password"
        value={repeat} onChange={e => setRepeat(e.target.value)} /></label>
    </fieldset>
    <div className="account-password-options">
      <label><input type="checkbox" checked={visible} onChange={e => setVisible(e.target.checked)} />{t("account.showPassword")}</label></div>
    {error && <p className="account-error" role="alert">{error}</p>}
    <div className="account-save"><span>{t("account.passwordSessionEnd")}</span><button type="submit" className="action-primary" disabled={busy || !current || !password || !repeat}><CheckIcon />{t(busy ? "settings.saving" : "account.changePassword")}</button></div>
  </form>;
}
