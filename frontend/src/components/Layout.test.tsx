import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Layout from "./Layout";
import { BrandingContext } from "../branding";
import type { User } from "../api/client";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key, i18n: { language: "nl" } }) }));
vi.mock("./WhatsNewModal", () => ({ default: () => null }));
vi.mock("./UpdateToast", () => ({ default: () => null }));
vi.mock("./TwoFactorNudge", () => ({ default: () => null, clearTwoFactorNudge: vi.fn() }));
const config = vi.hoisted(() => ({ publicSettings: { history_enabled: true } }));
vi.mock("../settings/preferences", () => ({ usePreferences: () => config }));
const api = vi.hoisted(() => ({ health: vi.fn(), logout: vi.fn() }));
vi.mock("../api/client", () => ({ api }));
const user = { id: 1, username: "tester", role: "admin", active: true } as User;

function renderAt(path = "/wizard/road", custom = false, account = user) {
  return render(<BrandingContext.Provider value={{ branding: { name: custom ? "Example Logistics" : "", logo: custom ? "/custom.svg" : null, modalities: {} }, refresh: async () => {} }}>
    <MemoryRouter initialEntries={[path]}><Routes><Route element={<Layout user={account} onLogout={() => {}} />}>
      <Route path="/" element={<p>chooser</p>} /><Route path="/wizard/:modality" element={<p>wizard</p>} /><Route path="/admin/settings/organisation" element={<p>settings</p>} />
    </Route></Routes></MemoryRouter>
  </BrandingContext.Provider>);
}

beforeEach(() => { vi.spyOn(window, "scrollTo").mockImplementation(() => {}); vi.clearAllMocks(); config.publicSettings.history_enabled = true; api.health.mockResolvedValue({ version: "1.206.2" }); api.logout.mockResolvedValue({ ok: true }); });

describe("the approved EMCargo navigation", () => {
  it("opens personal settings through either avatar and shows the chosen display name", () => {
    renderAt("/", false, { ...user, display_name: "Ada L." });
    expect(screen.getByRole("link", { name: "account.openSettings" })).toHaveAttribute("href", "/account/profile");
    expect(screen.getByRole("link", { name: "profile.open" })).toHaveAttribute("href", "/account/profile");
    expect(screen.getByText("Ada L.")).toBeInTheDocument();
  });
  it("gives ordinary users the avatar without a management menu", async () => {
    renderAt("/", false, { ...user, role: "user" });
    expect(screen.queryByText("nav.manage")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "nav.openMenu" }));
    const menu = within(screen.getByRole("dialog"));
    expect(menu.getByRole("link", { name: "profile.open" })).toBeVisible();
    expect(menu.queryByRole("link", { name: "account.adminSettings" })).toBeNull();
    expect(menu.queryByRole("link", { name: "nav.legal" })).toBeNull();
  });
  it("keeps all four work pages directly discoverable when storage is off", async () => {
    config.publicSettings.history_enabled = false;
    renderAt();
    for (const name of ["nav.overview", "nav.shipments", "nav.trips", "nav.articles"]) {
      expect(screen.getByRole("link", { name })).toBeVisible();
    }
    await userEvent.click(screen.getByRole("button", { name: "nav.openMenu" }));
    const menu = within(screen.getByRole("dialog"));
    for (const name of ["nav.overview", "nav.shipments", "nav.trips", "nav.articles"]) {
      expect(menu.getByRole("link", { name })).toBeVisible();
    }
  });
  it("starts a newly selected page at the top without moving an unchanged page", async () => {
    renderAt();
    expect(window.scrollTo).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("link", { name: "nav.new" }));
    expect(screen.getByText("chooser")).toBeInTheDocument();
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, left: 0, behavior: "instant" });
  });

  it("keeps the labelled rail open in the wizard as shown in the mockup", () => {
    renderAt();
    expect(screen.getByRole("button", { name: "nav.collapseMenu" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("link", { name: "nav.shipments" })).toHaveTextContent("nav.shipments");
  });
  it("lets the user fold the rail while preserving direct accessible destinations", async () => {
    renderAt();
    await userEvent.click(screen.getByRole("button", { name: "nav.collapseMenu" }));
    const settings = screen.getByRole("link", { name: "account.adminSettings" });
    expect(settings.textContent).toBe("");
    expect(settings).toHaveAttribute("href", "/admin/settings/organisation");
    expect(screen.getByRole("button", { name: "nav.expandMenu" })).toHaveAttribute("aria-expanded", "false");
  });
  it("does not fight the user's rail choice on a route change", async () => {
    renderAt();
    await userEvent.click(screen.getByRole("button", { name: "nav.collapseMenu" }));
    await userEvent.click(screen.getByRole("link", { name: "account.adminSettings" }));
    expect(screen.getByText("settings")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "nav.expandMenu" })).toBeInTheDocument();
  });
  it("keeps destinations unique in the desktop rail", async () => {
    renderAt();
    expect(screen.getAllByRole("link", { name: "nav.shipments" })).toHaveLength(1);
    await userEvent.click(screen.getByRole("button", { name: "nav.collapseMenu" }));
    expect(screen.getAllByRole("link", { name: "account.adminSettings" })).toHaveLength(1);
  });
  it("opens the mobile menu, supports Escape, and returns focus", async () => {
    renderAt();
    const trigger = screen.getByRole("button", { name: "nav.openMenu" });
    await userEvent.click(trigger);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(document.body.style.overflow).toBe("hidden");
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(trigger).toHaveFocus();
    expect(document.body.style.overflow).toBe("");
  });
  it("closes the drawer after navigation", async () => {
    renderAt(); await userEvent.click(screen.getByRole("button", { name: "nav.openMenu" }));
    await userEvent.click(within(screen.getByRole("dialog")).getByRole("link", { name: "nav.new" }));
    expect(screen.queryByRole("dialog")).toBeNull(); expect(screen.getByText("chooser")).toBeInTheDocument();
  });
  it("always shows the account and sign-out action", () => {
    renderAt();
    expect(screen.getByRole("link", { name: "profile.open" })).toHaveAttribute("href", "/account/profile");
    expect(screen.getByRole("button", { name: "nav.logout" })).toBeVisible();
    expect(screen.getByText("tester")).toBeInTheDocument();
  });
  it("keeps a skip link and labels the current destination", () => {
    renderAt("/");
    expect(screen.getByRole("link", { name: "nav.skipContent" })).toHaveAttribute("href", "#main-content");
    expect(screen.getByRole("link", { name: "nav.new" })).toHaveAttribute("aria-current", "page");
  });
  it("uses the new mark without altering a custom organisation logo", () => {
    renderAt("/", true);
    expect(screen.getAllByText("Example Logistics").length).toBeGreaterThan(0);
    for (const image of document.querySelectorAll("img")) { expect(image).toHaveAttribute("src", "/custom.svg"); expect(image.className).not.toContain("invert"); }
  });
  it("uses EMCargo's own mark by default", () => {
    renderAt(); expect(document.querySelector("img")).toHaveAttribute("src", "/emcargo.svg");
  });
});
