import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Outlet, useLocation } from "react-router";
import { beforeEach, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import App from "./App";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
const api = vi.hoisted(() => ({ me: vi.fn(), health: vi.fn() }));
vi.mock("./api/client", () => ({ api }));
vi.mock("./branding", () => ({ BrandingProvider: ({ children }: { children: ReactNode }) => children }));
vi.mock("./settings/preferences", () => ({ PreferencesProvider: ({ children }: { children: ReactNode }) => children }));
vi.mock("./toast/ToastProvider", () => ({ ToastProvider: ({ children }: { children: ReactNode }) => children }));
vi.mock("./components/Layout", () => ({ default: () => <Outlet /> }));
vi.mock("./pages/LoginPage", () => ({ default: ({ onLogin }: { onLogin: () => Promise<void> }) => <button onClick={() => void onLogin()}>Sign in</button> }));
vi.mock("./pages/ModalitySelectPage", () => ({ default: () => <p>Transport choices</p> }));
vi.mock("./pages/OverviewPage", () => ({ default: () => <p>Overview</p> }));
vi.mock("./pages/CardsPage", () => ({ default: () => <p>Public UN cards</p> }));
vi.mock("./pages/ShipmentsPage", () => ({ default: () => <p>Saved shipment</p> }));
vi.mock("./pages/SettingsPage", () => ({ default: ({ area = "account", sectionOverride }: { area?: string; sectionOverride?: string }) => <p>{area}:{sectionOverride || "settings"}</p> }));

const account = { id: 1, username: "Ada", email: "ada@example.com", role: "admin", active: true };
beforeEach(() => {
  vi.resetAllMocks();
  api.me.mockRejectedValue(new Error("Not authenticated"));
  // Even an old server response must never select an anonymous application.
  api.health.mockResolvedValue({ mode: "open" });
});

function Position() {
  const location = useLocation();
  return <output data-testid="position">{location.pathname + location.search + location.hash}</output>;
}
function page(path: string) {
  render(<MemoryRouter initialEntries={[path]}><App /><Position /></MemoryRouter>);
}

it.each(["/", "/overzicht", "/wizard/road", "/settings", "/account/profile", "/account/about/terms", "/admin/settings/organisation"])("requires a session for %s", async path => {
  page(path);
  expect(await screen.findByRole("button", { name: "Sign in" })).toBeInTheDocument();
  expect(screen.getByTestId("position")).toHaveTextContent("/login");
  expect(screen.queryByText("Transport choices")).toBeNull();
  expect(api.health).not.toHaveBeenCalled();
});

it("keeps the public QR page reachable without a session", async () => {
  page("/cards?un=1203&m=ADR");
  expect(await screen.findByText("Public UN cards")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Sign in" })).toBeNull();
  expect(screen.getByTestId("position")).toHaveTextContent("/cards?un=1203&m=ADR");
});

it("opens the full workspace for an authenticated account", async () => {
  api.me.mockResolvedValue({ user: account });
  page("/");
  expect(await screen.findByText("Transport choices")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Sign in" })).toBeNull();
});

it("returns to the requested application page after signing in", async () => {
  api.me.mockRejectedValueOnce(new Error("Not authenticated")).mockResolvedValue({ user: account });
  page("/shipments/17?view=documents#details");
  await userEvent.click(await screen.findByRole("button", { name: "Sign in" }));
  expect(await screen.findByText("Saved shipment")).toBeInTheDocument();
  expect(screen.getByTestId("position")).toHaveTextContent("/shipments/17?view=documents#details");
});

it.each(["user", "dg_specialist"])("keeps %s out of installation settings even with a direct link", async role => {
  api.me.mockResolvedValue({ user: { ...account, role } });
  page("/admin/settings/access");
  expect(await screen.findByText("account:settings")).toBeInTheDocument();
  expect(screen.getByTestId("position")).toHaveTextContent("/account/profile");
  expect(screen.queryByText("admin:settings")).toBeNull();
});

it.each([
  ["/settings?tab=security", "/account/security", "account:settings"],
  ["/settings?tab=maintenance", "/admin/settings/updates", "admin:settings"],
  ["/settings?tab=admin", "/admin/settings/organisation", "admin:settings"],
  ["/legal", "/account/about/terms", "account:terms"],
])("preserves the old bookmark %s", async (path, target, content) => {
  api.me.mockResolvedValue({ user: account });
  page(path);
  expect(await screen.findByText(content)).toBeInTheDocument();
  expect(screen.getByTestId("position")).toHaveTextContent(target);
});
