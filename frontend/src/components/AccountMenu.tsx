import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation } from "react-router";
import type { User } from "../api/client";
import Avatar from "./Avatar";
import { LogoutIcon, RefreshIcon, SettingsIcon } from "./icons";

interface Props {
  user: User;
  onLogout: () => void;
  loggingOut: boolean;
  className?: string;
}

/** The same account actions in the mobile header and desktop toolbar. */
export default function AccountMenu({ user, onLogout, loggingOut, className = "" }: Props) {
  const { t } = useTranslation();
  const location = useLocation();
  const id = useId();
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const popup = useRef<HTMLDivElement>(null);
  const firstFocus = useRef<"first" | "last">("first");
  const [open, setOpen] = useState(false);
  const items = () => Array.from(popup.current?.querySelectorAll<HTMLElement>('[role="menuitem"]:not(:disabled)') ?? []);

  function close(restoreFocus = false) {
    setOpen(false);
    if (restoreFocus) trigger.current?.focus();
  }

  useEffect(() => setOpen(false), [location.key]);
  useEffect(() => {
    if (!open) return;
    const targets = items();
    targets[firstFocus.current === "last" ? targets.length - 1 : 0]?.focus();
    const outside = (event: Event) => {
      if (event.target instanceof Node && !root.current?.contains(event.target)) setOpen(false);
    };
    const resize = () => setOpen(false);
    document.addEventListener("pointerdown", outside);
    document.addEventListener("focusin", outside);
    window.addEventListener("resize", resize);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("focusin", outside);
      window.removeEventListener("resize", resize);
    };
  }, [open]);

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.preventDefault(); event.stopPropagation(); close(true); return;
    }
    if (event.key === " " && event.target instanceof HTMLAnchorElement) {
      event.preventDefault(); event.target.click(); return;
    }
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const targets = items();
    const current = targets.indexOf(document.activeElement as HTMLElement);
    const next = event.key === "Home" ? 0 : event.key === "End" ? targets.length - 1
      : (current + (event.key === "ArrowDown" ? 1 : -1) + targets.length) % targets.length;
    targets[next]?.focus();
  }

  return <div ref={root} className={`account-menu ${className}`}>
    <button ref={trigger} type="button" className="account-menu-trigger" aria-label={t("account.menu")}
      title={user.display_name || user.username} aria-haspopup="menu" aria-expanded={open} aria-controls={open ? id : undefined}
      onClick={() => { firstFocus.current = "first"; setOpen(value => !value); }}
      onFocus={event => {
        // Shift+Tab returns here naturally; leave the browser's Tab order intact.
        if (event.relatedTarget instanceof Node && popup.current?.contains(event.relatedTarget)) setOpen(false);
      }}
      onKeyDown={event => {
        if (event.key === "ArrowDown" || event.key === "ArrowUp") {
          event.preventDefault(); firstFocus.current = event.key === "ArrowUp" ? "last" : "first"; setOpen(true);
        }
      }}><Avatar user={user} /></button>
    {open && <div ref={popup} id={id} role="menu" aria-label={t("account.menu")} className="account-menu-popup" onKeyDown={onKeyDown}>
      <Link to="/account/profile" role="menuitem" tabIndex={-1} onClick={() => close(true)}><SettingsIcon /><span>{t("account.settings")}</span></Link>
      <button type="button" role="menuitem" tabIndex={-1} disabled={loggingOut} aria-busy={loggingOut} onClick={onLogout}>
        {loggingOut ? <RefreshIcon className="account-menu-spinner" /> : <LogoutIcon />}<span>{t("nav.logout")}</span>
      </button>
    </div>}
  </div>;
}
