import { canManage, roleLabel } from "../permissions";
import BrandName from "./BrandName";
import { Suspense, useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { api, User } from "../api/client";
import { useBranding } from "../branding";
import Avatar from "./Avatar";
import CommandMenu from "./CommandMenu";
import UpdateToast from "./UpdateToast";
import TwoFactorNudge, { clearTwoFactorNudge } from "./TwoFactorNudge";
import WhatsNewModal from "./WhatsNewModal";
import { ShieldIcon, ChevronDownIcon, CloseIcon, CollapseIcon, LogoutIcon, HistoryIcon, HomeIcon, LibraryIcon, MenuIcon, PlusIcon, RoadIcon, SettingsIcon, ShipmentsIcon, TripsIcon, UserIcon } from "./icons";

interface Props { user: User; onLogout: () => void }

/** One navigation tree shared by the desktop rail and the mobile drawer. */
export default function Layout({ user, onLogout }: Props) {
  const { t } = useTranslation();
  const { branding } = useBranding();
  const location = useLocation();
  const navigate = useNavigate();
  const admin = user.role === "admin";
  const manager = canManage(user);
  const [menuOpen, setMenuOpen] = useState(false);
  const [railOpen, setRailOpen] = useState(true);
  const trigger = useRef<HTMLButtonElement>(null);
  const drawer = useRef<HTMLElement>(null);
  const previousPath = useRef(location.pathname);

  useEffect(() => {
    setMenuOpen(false);
    // A new page starts at its heading, even when the previous form was long.
    // Wizard field edits and in-page steps do not change the pathname.
    if (previousPath.current !== location.pathname) {
      previousPath.current = location.pathname;
      window.scrollTo({ top: 0, left: 0, behavior: "instant" });
    }
  }, [location.pathname]);
  useEffect(() => {
    if (!menuOpen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const targets = () => Array.from(drawer.current?.querySelectorAll<HTMLElement>("a[href], button:not([disabled]), summary") ?? []).filter((element) => element.getClientRects().length > 0);
    drawer.current?.querySelector<HTMLButtonElement>("button")?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); setMenuOpen(false); }
      if (event.key !== "Tab") return;
      const items = targets(); const first = items[0]; const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    };
    document.addEventListener("keydown", keydown);
    return () => { document.body.style.overflow = previousOverflow; document.removeEventListener("keydown", keydown); trigger.current?.focus(); };
  }, [menuOpen]);

  async function logout() {
    await api.logout(); clearTwoFactorNudge(); onLogout(); navigate("/login");
  }
  const destinations = [
    {to: "/overzicht", label: t("nav.overview")}, {to: "/shipments", label: t("nav.shipments")}, {to: "/trips", label: t("nav.trips")}, {to: "/articles", label: t("nav.articles")},
    {to: "/", label: t("nav.new")},
    ...(manager ? [{to: "/materieel", label: t("nav.materieel")}, {to: "/users", label: t("nav.users")}] : []),
    ...(admin ? [{to: "/audit", label: t("nav.audit")}] : []),
    {to: "/dg-reviews", label: t("dgReview.title")},
    {to: "/account/profile", label: t("account.settings")}, {to: "/account/about", label: t("account.about")},
    ...(manager ? [{to: "/admin/settings/organisation", label: t("account.adminSettings")}] : []),
  ];
  const currentLabel = location.pathname.startsWith("/wizard") ? t("nav.new")
    : location.pathname.startsWith("/account/") ? t("account.settings")
    : location.pathname.startsWith("/admin/settings") ? t("account.adminSettings")
    : location.pathname === "/shipments/report" ? t("dgsa.title")
    : destinations.find(item => item.to === location.pathname)?.label
      || (location.pathname.startsWith("/shipments/") ? t("nav.shipments") : location.pathname.startsWith("/trips/") ? t("nav.trips") : t("studio.workspace"));
  const name = branding.name || t("app.name");
  const brand = (compact = false) => <div className="emcargo-brand">
    <img src={branding.logo || "/emcargo.svg"} alt="" className="h-9 w-9 shrink-0 object-contain" />
    {!compact && <span className="truncate text-2xl font-semibold tracking-tight"><BrandName name={name} /></span>}
  </div>;
  const linkClass = ({ isActive }: { isActive: boolean }) => `emcargo-nav-link ${isActive ? "emcargo-nav-active" : ""}`;
  type Icon = typeof HomeIcon;
  function link(to: string, label: string, Glyph: Icon, compact: boolean) {
    return <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => linkClass({ isActive: isActive || (to === "/admin/settings/organisation" && location.pathname.startsWith("/admin/settings/")) })} title={compact ? label : undefined} aria-label={label} onClick={() => setMenuOpen(false)}>
      <Glyph className="h-[22px] w-[22px] shrink-0" />{!compact && <span className="truncate">{label}</span>}
    </NavLink>;
  }
  function navigation(compact = false) {
    return <>
      {link("/overzicht", t("nav.overview"), HomeIcon, compact)}
      {link("/", t("nav.new"), PlusIcon, compact)}
      {link("/shipments", t("nav.shipments"), ShipmentsIcon, compact)}
      {link("/trips", t("nav.trips"), TripsIcon, compact)}
      {link("/dg-reviews", t("dgReview.title"), ShieldIcon, compact)}
      {link("/articles", t("nav.articles"), LibraryIcon, compact)}
      {manager && link("/materieel", t("nav.materieel"), RoadIcon, compact)}
      {manager && (compact ? <>
        {link("/admin/settings/organisation", t("account.adminSettings"), SettingsIcon, true)}
        {link("/users", t("nav.users"), UserIcon, true)}
        {admin && link("/audit", t("nav.audit"), HistoryIcon, true)}
      </> : <details className="emcargo-nav-group" open={location.pathname.startsWith("/admin/settings") || ["/users", "/audit"].includes(location.pathname) || undefined}>
        <summary className="emcargo-nav-link"><SettingsIcon className="h-[22px] w-[22px]" /><span>{t("nav.manage")}</span><ChevronDownIcon className="ml-auto h-3.5 w-3.5" /></summary>
        <div className="emcargo-subnav">
          {link("/admin/settings/organisation", t("account.adminSettings"), SettingsIcon, false)}
          {link("/users", t("nav.users"), UserIcon, false)}
          {admin && link("/audit", t("nav.audit"), HistoryIcon, false)}
        </div>
      </details>)}
    </>;
  }
  const account = (compact = false) => <div className="emcargo-account">
    <NavLink to="/account/profile" className="account-profile-link" aria-label={t("profile.open")} title={t("account.settings")} onClick={() => setMenuOpen(false)}>
      <Avatar user={user} />
      {!compact && <div className="min-w-0"><p className="truncate text-sm">{user.display_name || user.username}</p><p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{t(roleLabel(user.role))}</p></div>}
    </NavLink>
    <button onClick={() => void logout()} className="mt-3 min-h-[44px] w-full border-t border-slate-200 pt-3 text-left text-sm dark:border-slate-700" aria-label={t("nav.logout")}>{compact ? <LogoutIcon className="h-5 w-5" /> : t("nav.logout")}</button>
  </div>;

  return <div className={`emcargo-shell ${railOpen ? "" : "emcargo-shell-folded"}`}>
    <a href="#main-content" className="skip-link">{t("nav.skipContent")}</a>
    <header className="emcargo-mobile-header">{brand()}<div className="mobile-account-actions">
      <NavLink to="/account/profile" className="mobile-avatar-link" aria-label={t("account.openSettings")} title={t("account.settings")}><Avatar user={user} /></NavLink>
      <button ref={trigger} className="flex h-11 w-11 items-center justify-center" onClick={() => setMenuOpen(true)} aria-label={t("nav.openMenu")} aria-expanded={menuOpen}><MenuIcon className="h-7 w-7" /></button>
    </div></header>
    <aside className="emcargo-sidebar">
      {brand(!railOpen)}
      <nav id="main-nav" aria-label={t("nav.menu")} className="emcargo-navigation">{navigation(!railOpen)}</nav>
      {account(!railOpen)}
      <button onClick={() => setRailOpen((value) => !value)} className="emcargo-rail-toggle" aria-controls="main-nav" aria-expanded={railOpen} aria-label={railOpen ? t("nav.collapseMenu") : t("nav.expandMenu")}><CollapseIcon className={`h-4 w-4 ${railOpen ? "" : "rotate-180"}`} /></button>
    </aside>
    <main id="main-content" tabIndex={-1} className="emcargo-main"><div className="workspace-bar"><div className="workspace-location"><span>{t("studio.workspace")}</span><span aria-hidden="true">/</span><strong>{currentLabel}</strong></div><CommandMenu destinations={destinations} /></div><Suspense fallback={<div className="route-loading" role="status">{t("wizard.loading")}</div>}><Outlet /></Suspense></main>
    <WhatsNewModal /><UpdateToast user={user} /><TwoFactorNudge user={user} />
    {menuOpen && <div className="fixed inset-0 z-50 md:hidden" role="dialog" aria-modal="true" aria-label={t("nav.menu")}>
      <div className="absolute inset-0 bg-black/60" onClick={() => setMenuOpen(false)} />
      <aside ref={drawer} className="emcargo-mobile-drawer">
        <div className="flex items-center justify-between p-4">{brand()}<button className="h-11 w-11 text-2xl" onClick={() => setMenuOpen(false)} aria-label={t("nav.closeMenu")}><CloseIcon className="mx-auto h-6 w-6" /></button></div>
        <nav className="emcargo-navigation">{navigation()}</nav>{account()}
      </aside>
    </div>}
  </div>;
}
