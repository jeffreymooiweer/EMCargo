import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Layout from "./Layout";
import { BrandingContext } from "../branding";
import type { User } from "../api/client";
import { ToastProvider } from "../toast/ToastProvider";
import { clearTwoFactorNudge } from "./TwoFactorNudge";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key, i18n: { language: "nl" } }) }));
vi.mock("./WhatsNewModal", () => ({ default: () => null }));
vi.mock("./UpdateToast", () => ({ default: () => null }));
vi.mock("./TwoFactorNudge", () => ({ default: () => null, clearTwoFactorNudge: vi.fn() }));
const config = vi.hoisted(() => ({ publicSettings: { history_enabled: true } }));
vi.mock("../settings/preferences", () => ({ usePreferences: () => config }));
const api = vi.hoisted(() => ({ health: vi.fn(), logout: vi.fn() }));
vi.mock("../api/client", () => ({ api }));
const user = { id: 1, username: "tester", role: "admin", active: true } as User;

function renderAt(path = "/wizard/road", custom = false, account = user, onLogout = vi.fn()) {
  return render(<BrandingContext.Provider value={{ branding: { name: custom ? "Example Logistics" : "", logo: custom ? "/custom.svg" : null, modalities: {} }, refresh: async () => {} }}>
    <ToastProvider><MemoryRouter initialEntries={[path]}><Routes><Route element={<Layout user={account} onLogout={onLogout} />}>
      <Route path="/" element={<p>chooser</p>} /><Route path="/wizard/:modality" element={<p>wizard</p>} /><Route path="/admin/settings/organisation" element={<p>settings</p>} />
      <Route path="/account/profile" element={<p>personal settings</p>} />
    </Route><Route path="/login" element={<p>sign in</p>} /></Routes></MemoryRouter></ToastProvider>
  </BrandingContext.Provider>);
}

beforeEach(() => { vi.spyOn(window, "scrollTo").mockImplementation(() => {}); vi.clearAllMocks(); config.publicSettings.history_enabled = true; api.health.mockResolvedValue({ version: "1.206.2" }); api.logout.mockResolvedValue({ ok: true }); });

describe("the approved EMCargo navigation", () => {
  it("offers settings and sign-out through the header and toolbar avatars", async () => {
    renderAt("/", false, { ...user, display_name: "Ada L." });
    for (const area of [screen.getByRole("banner"), screen.getByRole("main")]) {
      const avatar = within(area).getByRole("button", { name: "account.menu" });
      expect(avatar).toHaveAttribute("title", "Ada L.");
      await userEvent.click(avatar);
      const menu = within(screen.getByRole("menu", { name: "account.menu" }));
      expect(menu.getAllByRole("menuitem")).toHaveLength(2);
      expect(menu.getByRole("menuitem", { name: "nav.logout" })).toBeEnabled();
      const settings = menu.getByRole("menuitem", { name: "account.settings" });
      expect(settings).toHaveAttribute("href", "/account/profile");
      await userEvent.keyboard(" ");
      expect(screen.getByText("personal settings")).toBeInTheDocument();
      expect(screen.queryByRole("menu")).toBeNull();
    }
  });
  it("gives ordinary users the avatar without a management menu", async () => {
    renderAt("/", false, { ...user, role: "user" });
    expect(screen.queryByText("nav.manage")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "nav.openMenu" }));
    const menu = within(screen.getByRole("dialog"));
    expect(menu.queryByRole("link", { name: "profile.open" })).toBeNull();
    expect(menu.queryByRole("button", { name: "nav.logout" })).toBeNull();
    expect(menu.queryByRole("link", { name: "account.adminSettings" })).toBeNull();
    expect(menu.queryByRole("link", { name: "nav.legal" })).toBeNull();
  });
  it("keeps work pages and the grouped library available when storage is off", async () => {
    config.publicSettings.history_enabled = false;
    renderAt();
    await userEvent.click(screen.getByText("nav.library"));
    for (const name of ["nav.overview", "nav.shipments", "nav.trips", "nav.articles"]) {
      expect(screen.getByRole("link", { name })).toBeVisible();
    }
    await userEvent.click(screen.getByRole("button", { name: "nav.openMenu" }));
    const menu = within(screen.getByRole("dialog"));
    await userEvent.click(menu.getByText("nav.library"));
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
  it("keeps account controls out of the expanded rail, folded rail and mobile drawer", async () => {
    renderAt();
    const rail = screen.getByRole("complementary");
    expect(rail.querySelector(".profile-avatar")).toBeNull();
    expect(within(rail).queryByText("nav.logout")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "nav.collapseMenu" }));
    expect(rail.querySelector(".profile-avatar")).toBeNull();
    expect(within(rail).queryByText("nav.logout")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "nav.openMenu" }));
    const drawer = screen.getByRole("dialog");
    expect(drawer.querySelector(".profile-avatar")).toBeNull();
    expect(within(drawer).queryByText("nav.logout")).toBeNull();
  });

  it("places the hamburger before the brand and closes the account popup when opening navigation", async () => {
    renderAt();
    const header = screen.getByRole("banner");
    const hamburger = within(header).getByRole("button", { name: "nav.openMenu" });
    const brand = header.querySelector(".emcargo-brand")!;
    expect(hamburger.compareDocumentPosition(brand) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    await userEvent.click(within(header).getByRole("button", { name: "account.menu" }));
    await userEvent.click(hamburger);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.queryByRole("menu")).toBeNull();
  });

  it("keeps the session after a failed sign-out and prevents duplicate requests during a retry", async () => {
    const onLogout = vi.fn();
    api.logout.mockRejectedValueOnce(new Error("Connection unavailable"));
    renderAt("/", false, user, onLogout);
    await userEvent.click(within(screen.getByRole("banner")).getByRole("button", { name: "account.menu" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "nav.logout" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Connection unavailable");
    expect(onLogout).not.toHaveBeenCalled();
    expect(clearTwoFactorNudge).not.toHaveBeenCalled();
    expect(screen.getByText("chooser")).toBeInTheDocument();
    let finish!: () => void;
    api.logout.mockImplementationOnce(() => new Promise(resolve => { finish = () => resolve({ ok: true }); }));
    await userEvent.click(screen.getByRole("menuitem", { name: "nav.logout" }));
    expect(screen.getByRole("menuitem", { name: "nav.logout" })).toBeDisabled();
    // Both responsive controls share the same pending sign-out request.
    await userEvent.click(within(screen.getByRole("main")).getByRole("button", { name: "account.menu" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "nav.logout" }));
    expect(api.logout).toHaveBeenCalledTimes(2);
    finish();
    await waitFor(() => expect(onLogout).toHaveBeenCalledOnce());
    expect(clearTwoFactorNudge).toHaveBeenCalledOnce();
    expect(await screen.findByText("sign in")).toBeInTheDocument();
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
