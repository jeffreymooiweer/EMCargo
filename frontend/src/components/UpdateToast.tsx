/**
 * A quiet corner note for the one person who can do something about it.
 *
 * The update check tells an administrator that a newer EMCargo exists;
 * nobody else operates the container, so nobody else sees the notice. The
 * component itself renders nothing — it hands the notice to the toast system
 * as a sticky info toast (information, not an interruption, so it never
 * auto-dismisses but also never blocks). Dismissing it remembers the version
 * in localStorage, so the same release does not nag on every page load but a
 * newer one shows up again; being evicted by other toasts does NOT count as
 * dismissed. The endpoint itself answers admins only and applies the
 * outbound switch server-side; this component just does not ask for anyone
 * else.
 */
import { useEffect, useRef } from "react";
import { useNavigate } from "react-router";
import { useTranslation } from "react-i18next";

import { api, User } from "../api/client";
import { useToast } from "../toast/ToastProvider";

export const DISMISSED_KEY = "emcargo-update-dismissed";

export default function UpdateToast({ user }: { user: User }) {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  // One notice per mount, even if effects re-run (StrictMode).
  const pushed = useRef(false);

  useEffect(() => {
    if (user.role !== "admin") return;
    let cancelled = false;
    void api
      .updateStatus()
      .then((answer) => {
        if (cancelled || pushed.current) return;
        if (!answer.update_available || !answer.latest) return;
        const latest = answer.latest;
        try { if (localStorage.getItem(DISMISSED_KEY) === latest) return; } catch { /* Storage may be unavailable. */ }
        pushed.current = true;
        toast.info(`${t("update.available", { version: latest })} ${t("update.hint")}`, {
          sticky: true,
          actions: [{ label: t("updates.open"), run: () => navigate("/admin/settings/updates") }],
          onDismiss: () => { try { localStorage.setItem(DISMISSED_KEY, latest); } catch { /* Optional persistence. */ } },
        });
      })
      .catch(() => {
        // An unreachable backend is not this component's news to break.
      });
    return () => {
      cancelled = true;
    };
    // toast is stable for the provider's lifetime, and t must not retrigger
    // the check: asking again on a language switch would double the notice.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user.role]);

  return null;
}
