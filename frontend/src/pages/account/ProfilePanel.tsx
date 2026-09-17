import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type PersonalProfile, type User } from "../../api/client";
import AvatarSettings from "../../components/AvatarSettings";
import { CheckIcon, RefreshIcon } from "../../components/icons";
import { roleLabel } from "../../permissions";
import { useToast } from "../../toast/ToastProvider";

const empty: PersonalProfile = { display_name: "", first_name: "", last_name: "", job_title: "", phone_number: "" };

export default function ProfilePanel({ user, onUserChange, onDirtyChange }: {
  user: User;
  onUserChange?: (user: User) => void;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const [saved, setSaved] = useState<PersonalProfile | null>(null);
  const [draft, setDraft] = useState(empty);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [retry, setRetry] = useState(0);
  const running = useRef(false);
  const dirty = saved !== null && JSON.stringify(draft) !== JSON.stringify(saved);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    api.myProfile().then(profile => {
      if (!cancelled) { setSaved(profile); setDraft(profile); }
    }).catch(e => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [user.id, retry]);

  useEffect(() => { onDirtyChange(dirty); return () => onDirtyChange(false); }, [dirty, onDirtyChange]);
  useEffect(() => {
    if (!dirty) return;
    const protect = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", protect);
    return () => window.removeEventListener("beforeunload", protect);
  }, [dirty]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (running.current || !saved || !dirty) return;
    running.current = true; setSaving(true); setError("");
    const next = Object.fromEntries(Object.entries(draft).map(([key, value]) => [key, value.trim()])) as unknown as PersonalProfile;
    try {
      const account = await api.saveMyProfile(next);
      setSaved(next); setDraft(next); onUserChange?.(account);
      toast.success(t("account.profileSaved"));
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { running.current = false; setSaving(false); }
  }

  return <div className="account-stack">
    <section className="account-panel account-identity">
      <AvatarSettings user={user} onUserChange={onUserChange} />
      <dl className="account-identifiers">
        <div><dt>{t("users.username")}</dt><dd>{user.username}</dd></div>
        <div><dt>{t("users.email")}</dt><dd>{user.email}</dd></div>
        <div><dt>{t("users.role")}</dt><dd>{t(roleLabel(user.role))}</dd></div>
      </dl>
    </section>
    <form className="account-panel account-profile-form" onSubmit={submit} aria-busy={loading || saving}>
      <div className="account-section-heading"><h3>{t("account.profile")}</h3></div>
      {loading ? <p role="status">{t("wizard.loading")}</p> : saved && <fieldset disabled={saving} className="account-fields">
        <label className="account-field-wide">{t("account.displayName")}<input value={draft.display_name} maxLength={80} autoComplete="nickname"
          placeholder={[draft.first_name, draft.last_name].filter(Boolean).join(" ") || user.username}
          onChange={e => setDraft(current => ({ ...current, display_name: e.target.value }))} /></label>
        <label>{t("account.firstName")}<input value={draft.first_name} maxLength={80} autoComplete="given-name"
          onChange={e => setDraft(current => ({ ...current, first_name: e.target.value }))} /></label>
        <label>{t("account.lastName")}<input value={draft.last_name} maxLength={80} autoComplete="family-name"
          onChange={e => setDraft(current => ({ ...current, last_name: e.target.value }))} /></label>
        <label>{t("account.jobTitle")}<input value={draft.job_title} maxLength={120} autoComplete="organization-title"
          onChange={e => setDraft(current => ({ ...current, job_title: e.target.value }))} /></label>
        <label>{t("account.phone")}<input type="tel" value={draft.phone_number} maxLength={40} autoComplete="tel"
          onChange={e => setDraft(current => ({ ...current, phone_number: e.target.value }))} /></label>
      </fieldset>}
      {error && <p className="account-error" role="alert">{error}</p>}
      {!loading && !saved ? <button type="button" className="action-secondary" onClick={() => setRetry(value => value + 1)}><RefreshIcon />{t("history.retry")}</button>
        : <div className="account-save"><span role="status">{!loading && t(dirty ? "settingsNav.unsaved" : "settingsNav.allSaved")}</span>
          <button className="action-primary" type="submit" disabled={loading || saving || !dirty}><CheckIcon />{t(saving ? "settings.saving" : "settings.save")}</button></div>}
    </form>
  </div>;
}
