import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type User } from "../api/client";
import { useToast } from "../toast/ToastProvider";
import Avatar from "./Avatar";
import { UploadIcon, TrashIcon } from "./icons";

export default function AvatarSettings({ user, onUserChange }: { user: User; onUserChange?: (user: User) => void }) {
  const { t } = useTranslation();
  const toast = useToast();
  const [profile, setProfile] = useState(user);
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const active = useRef(false);
  useEffect(() => setProfile(user), [user]);

  async function change(file?: File) {
    if (active.current) return;
    if (file && file.size > 5 * 1024 * 1024) { toast.error(t("errors.avatar.too_large")); return; }
    active.current = true; setBusy(true);
    try {
      const saved = file ? await api.uploadMyAvatar(file) : await api.deleteMyAvatar();
      setProfile(saved); onUserChange?.(saved);
      toast.success(t(file ? "profile.saved" : "profile.removed"));
    } catch (error) { toast.error(String(error)); }
    finally { active.current = false; setBusy(false); if (input.current) input.current.value = ""; }
  }

  return <section className="avatar-settings" aria-busy={busy} aria-label={t("profile.photo")}>
    <Avatar user={profile} large />
    <div><h3>{t("profile.photo")}</h3>
      <div className="avatar-actions">
        <button type="button" className="action-secondary" onClick={() => input.current?.click()} disabled={busy}>
          <UploadIcon />{t(busy ? "profile.saving" : profile.avatar_url ? "profile.replace" : "profile.upload")}
        </button>
        {profile.avatar_url && <button type="button" className="action-quiet" onClick={() => void change()} disabled={busy}><TrashIcon />{t("profile.remove")}</button>}
      </div>
      <input ref={input} type="file" hidden accept="image/jpeg,image/png,image/webp" aria-label={t("profile.upload")}
        onChange={event => { const file = event.target.files?.[0]; if (file) void change(file); }} />
    </div>
  </section>;
}
