import { canManage } from "./permissions";
import { lazy, Suspense, useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router";
import { api, User } from "./api/client";
import { useTranslation } from "react-i18next";
import Layout from "./components/Layout";
const DgReviewsPage = lazy(() => import("./pages/DgReviewsPage"));
const CardsPage = lazy(() => import("./pages/CardsPage"));
const GroupagePage = lazy(() => import("./pages/GroupagePage"));
import LoginPage from "./pages/LoginPage";
const ResetPasswordPage = lazy(() => import("./pages/ResetPasswordPage"));
import ModalitySelectPage from "./pages/ModalitySelectPage";
import OverviewPage from "./pages/OverviewPage";
const WizardPage = lazy(() => import("./pages/WizardPage"));
const UsersPage = lazy(() => import("./pages/UsersPage"));
const MaterieelPage = lazy(() => import("./pages/MaterieelPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const ShipmentsPage = lazy(() => import("./pages/ShipmentsPage"));
const DgsaReportPage = lazy(() => import("./pages/DgsaReportPage"));
const CargoTemplateLibrary = lazy(() => import("./components/cargo/CargoTemplateLibrary"));
const ArticlesPage = lazy(() => import("./pages/ArticlesPage"));
const AuditPage = lazy(() => import("./pages/AuditPage"));
const TripsPage = lazy(() => import("./pages/TripsPage"));
const LegacyTripRoute = lazy(() => import("./pages/TripsPage").then(module => ({ default: module.LegacyTripRoute })));
import { LegacySettingsRoute } from "./settings/routes";
import { BrandingProvider } from "./branding";
import { PreferencesProvider } from "./settings/preferences";
import { ToastProvider } from "./toast/ToastProvider";

export default function App() {
  const { t } = useTranslation();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const location = useLocation();
  const from = location.state?.from;
  const afterLogin = typeof from === "string" && from.startsWith("/") && !from.startsWith("//") && !from.startsWith("/login") ? from : "/";

  useEffect(() => {
    let cancelled = false;
    api.me().then(
      ({ user: account }) => { if (!cancelled) setUser(account); },
      () => { if (!cancelled) setUser(null); },
    ).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  async function signedIn() {
    const { user: account } = await api.me();
    setUser(account);
  }

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-slate-500 dark:text-slate-400" role="status">{t("wizard.loading")}</div>;
  }

  if (!user) {
    return (
      <BrandingProvider>
      <ToastProvider>
      <Suspense fallback={<div className="route-loading" role="status">{t("wizard.loading")}</div>}>
      <Routes>
        <Route path="/login" element={<LoginPage onLogin={signedIn} />} />
        {/* A reset link is opened by somebody who cannot sign in; sending
            them to /login would swallow the token in the address. */}
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="*" element={<Navigate to="/login" replace state={{ from: location.pathname + location.search + location.hash }} />} />
      </Routes>
      </Suspense>
      </ToastProvider>
      </BrandingProvider>
    );
  }

  return (
    <BrandingProvider>
    <PreferencesProvider>
      <ToastProvider>
      <Suspense fallback={<div className="route-loading" role="status">{t("wizard.loading")}</div>}>
      <Routes>
        <Route element={<Layout user={user} onLogout={() => setUser(null)} />}>
          {/* `/` is the transport-mode chooser and stays the front door. The
              overview has its own address so that nobody with a preferred
              mode is sent through a dashboard on their way into the wizard. */}
          <Route path="/" element={<ModalitySelectPage />} />
          <Route path="/overzicht" element={<OverviewPage user={user} />} />
          <Route path="/wizard" element={<Navigate to="/" replace />} />
          <Route path="/wizard/:modality" element={<WizardPage user={user} />} />
          <Route path="/groupage" element={<GroupagePage />} />
          {/* Retention remains optional; each page explains when it is off. */}
          <Route path="/shipments" element={<ShipmentsPage user={user} />} />
          <Route path="/shipments/report" element={<DgsaReportPage user={user} />} />
          <Route path="/shipments/:id" element={<ShipmentsPage user={user} />} />
          <Route path="/trips" element={<TripsPage user={user} />} />
          <Route path="/trips/:id" element={<LegacyTripRoute />} />
          <Route path="/packaging" element={<CargoTemplateLibrary user={user} />} />
          <Route path="/articles" element={<ArticlesPage user={user} />} />
          {canManage(user) && <Route path="/materieel" element={<MaterieelPage />} />}
          <Route path="/dg-reviews" element={<DgReviewsPage user={user} />} />
          <Route path="/dg-reviews/:id" element={<DgReviewsPage user={user} />} />
          {canManage(user) && <Route path="/users" element={<UsersPage user={user} />} />}
          {user.role === "admin" && <Route path="/audit" element={<AuditPage />} />}
          <Route path="/account" element={<Navigate to="/account/profile" replace />} />
          <Route path="/account/:section" element={<SettingsPage key="account" user={user} onUserChange={setUser} onPasswordChanged={() => setUser(null)} />} />
          <Route path="/account/about/terms" element={<SettingsPage key="account" user={user} sectionOverride="terms" />} />
          <Route path="/admin/settings" element={<Navigate to={canManage(user) ? "/admin/settings/organisation" : "/account/profile"} replace />} />
          <Route path="/admin/settings/:section" element={canManage(user) ? <SettingsPage key="admin" area="admin" user={user} /> : <Navigate to="/account/profile" replace />} />
          <Route path="/settings" element={<LegacySettingsRoute user={user} />} />
          <Route path="/legal" element={<Navigate to="/account/about/terms" replace />} />
        </Route>
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/cards" element={<CardsPage />} />
        <Route path="/login" element={<Navigate to={afterLogin} replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </Suspense>
      </ToastProvider>
    </PreferencesProvider>
    </BrandingProvider>
  );
}
