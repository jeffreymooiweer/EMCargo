/**
 * A reminder, once per sign-in, for an account without a second factor.
 *
 * A password alone is one leaked reuse away from somebody else drawing up
 * consignment papers in your name. This is the gentlest thing that still
 * works: a snackbar that names the gap and offers the button that closes it,
 * rather than a screen the user has to get past before they can work.
 *
 * Three decisions worth stating, because each could reasonably have gone the
 * other way:
 *
 * - **It stays until it is closed.** It carries an action, and an action that
 *   slides away after four seconds is a button nobody clicks. It is an `info`
 *   toast rather than a `question`, because there is no wrong answer here —
 *   "not now" is a legitimate one and costs a single click.
 * - **It comes back next sign-in.** The marker sits in `sessionStorage` and is
 *   cleared on logout, so refreshing the page mid-work does not renew the
 *   nudge, while the next sign-in does. Nagging on every render would train
 *   people to dismiss it unread, which is worse than not asking.
 * - **The button goes to the panel, not to the page.** `/account/security`
 *   opens the tab the second factor actually lives on. Landing on the theme
 *   settings with the panel three tabs away is not an answer to the notice
 *   the user just clicked.
 *
 * Nothing is shown when the status cannot be fetched: a backend that will not
 * answer is not evidence that the account is unprotected.
 *
 * Since v1.190.0 the server enforces a required factor on every call rather
 * than mentioning it at sign-in, and answers everything but the panel's own
 * routes with `auth.two_factor_required`. The API client raises that as a
 * window event; this component is where it lands, because it is mounted for
 * every signed-in user and already knows the way to the panel. The person
 * is taken there and told why, once — the refused call's own error toast
 * says the rest.
 */
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router";

import { api, TWO_FACTOR_REQUIRED_EVENT, User } from "../api/client";
import { useToast } from "../toast/ToastProvider";

/** Where the second factor is set up. */
export const TWO_FACTOR_PANEL = "/account/security";

export const NUDGED_KEY = "emcargo-2fa-nudged";

/** Called on logout, so the next sign-in is nudged again. */
export function clearTwoFactorNudge() {
  try {
    sessionStorage.removeItem(NUDGED_KEY);
  } catch {
    // A browser that refuses session storage still gets the nudge; it simply
    // gets it on every load, which is the safe side to fail on.
  }
}

export default function TwoFactorNudge({ user }: { user: User }) {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  // One notice per mount, even if effects run twice (StrictMode) — and one
  // between the sign-in reminder and the server's refusals, however many
  // calls a page fires before it has left: the same sentence twice, in two
  // amber boxes, is what the first cut of this showed.
  const pushed = useRef(false);
  const here = useRef(location.pathname + location.search);
  here.current = location.pathname + location.search;

  useEffect(() => {
    const onRefused = () => {
      if (!pushed.current) {
        pushed.current = true;
        toast.warn(t("twoFactor.nudgeRequired"), {
          actions: [{ label: t("twoFactor.nudgeAction"), run: () => navigate(TWO_FACTOR_PANEL) }],
        });
      }
      if (here.current !== TWO_FACTOR_PANEL) navigate(TWO_FACTOR_PANEL);
    };
    window.addEventListener(TWO_FACTOR_REQUIRED_EVENT, onRefused);
    return () => window.removeEventListener(TWO_FACTOR_REQUIRED_EVENT, onRefused);
    // t, toast and navigate are stable enough for a listener registered once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    let cancelled = false;
    try {
      if (sessionStorage.getItem(NUDGED_KEY) === String(user.id)) return undefined;
    } catch {
      // Unreadable storage: carry on and show it.
    }
    void api
      .twoFactorStatus()
      .then((status) => {
        if (cancelled || pushed.current || status.active) return;
        pushed.current = true;
        try {
          sessionStorage.setItem(NUDGED_KEY, String(user.id));
        } catch {
          // See above: showing it again later is the harmless failure.
        }
        // Two situations, two sentences. `required` says the installation's
        // policy demands a second factor for this account — independent of
        // whether one is set up, and this only runs when none is. So the two
        // together are a policy the account does not meet, which is a firmer
        // thing to be told than a recommendation not taken.
        const open = [
          { label: t("twoFactor.nudgeAction"), run: () => navigate(TWO_FACTOR_PANEL) },
        ];
        if (status.required) {
          // Amber, because this is not advice the account has not taken: the
          // installation's policy demands a second factor and this account
          // does not have one, which stays wrong until somebody acts.
          toast.warn(t("twoFactor.nudgeRequired"), { actions: open });
        } else {
          toast.info(t("twoFactor.nudge"), { sticky: true, actions: open });
        }
      })
      .catch(() => {
        // Not an answer about this account, so not a claim about it either.
      });
    return () => {
      cancelled = true;
    };
    // Runs once per sign-in; t and the navigate helper must not retrigger it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user.id]);

  return null;
}
