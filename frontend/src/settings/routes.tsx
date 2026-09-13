import { Navigate, useSearchParams } from "react-router";
import type { User } from "../api/client";
import { canManage } from "../permissions";

export type SettingsArea = "account" | "admin";

export function settingsPath(area: SettingsArea, tab: string) {
  return area === "admin" ? `/admin/settings/${tab === "admin" ? "organisation" : tab}` : `/account/${tab}`;
}

/** Preserve saved links while keeping personal security separate from policy. */
export function LegacySettingsRoute({ user }: { user: User }) {
  const [params] = useSearchParams();
  const tab = params.get("tab") || "profile";
  const adminTabs = ["admin", "dg", "branding", "mail", "updates", "maintenance", "network", "cards", "assistant", "access"];
  const allowed = user.role === "admin" || (canManage(user) && tab === "admin");
  const area = adminTabs.includes(tab) && allowed ? "admin" : "account";
  const target = adminTabs.includes(tab) && !allowed ? "profile" : tab === "maintenance" ? "updates" : tab;
  return <Navigate to={settingsPath(area, target)} replace />;
}
