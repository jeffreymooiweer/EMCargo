/** Account and administration routes must never share access-policy controls. */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SettingsPage from "./SettingsPage";
import { ToastProvider } from "../toast/ToastProvider";
import { MemoryRouter, Navigate, Route, Routes } from "react-router";
import { api, User } from "../api/client";
import { LegacySettingsRoute } from "../settings/routes";
import { canManage } from "../permissions";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, vars?: Record<string, unknown>) =>
      vars && typeof vars.defaultValue === "string" ? String(vars.defaultValue) : key,
    i18n: { language: "nl" },
  }),
}));

vi.mock("../api/client", () => ({
  api: {
    myProfile: vi.fn().mockResolvedValue({ display_name: "", first_name: "", last_name: "", job_title: "", phone_number: "" }),
    health: vi.fn().mockResolvedValue({ version: "1.115.0" }),
    settingsOptions: vi.fn().mockResolvedValue({ modalities: ["road"], units: [] }),
    instanceSettings: vi.fn().mockResolvedValue({}),
    organisationSettings: vi.fn().mockResolvedValue({ organisation_name: "Test", organisation_address: "", default_language: "nl", default_theme: "dark" }),
    assistantStatus: vi.fn().mockResolvedValue({
      mode: "deterministic", installed: false, available: true, installable: true,
      download: { state: "idle" },
    }),
    // The maintenance tab's panels ask for their state on mount.
    updateStatus: vi.fn().mockResolvedValue({current:"2.1.1",enabled:false}),
    updateCapability: vi.fn().mockResolvedValue({ available: false }),
    updateState: vi.fn().mockResolvedValue({ current: "1.115.0", state: null }),
    unCardStoreStatus: vi.fn().mockResolvedValue({
      local: { installed: false }, remote: null,
    }),
    // My details carries the second factor, which asks for its own state.
    twoFactorStatus: vi.fn().mockResolvedValue({
      active: false, method: "", required: false, recovery_codes_left: 0,
    }),
  },
}));

const preferences = {
  theme: "system", language: "nl", default_modality: "", default_unit: "pcs",
  prefill_documents: true, consignor_name: "", consignor_address: "",
  consignor_contact: "", carrier_name: "", loading_point: "",
  emergency_contact: "", signature_image: "",
};

vi.mock("../settings/preferences", () => ({
  usePreferences: () => ({ preferences, save: vi.fn(), loaded: true }),
}));

/** The open tab lives in the address now, so the page needs a router — and a
 *  test can point at a tab the way the two-factor notice does. */
function renderAt(user: User, path = "/account/appearance") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ToastProvider>
        <Routes>
          <Route path="/settings" element={<LegacySettingsRoute user={user} />} />
          <Route path="/account/:section" element={<SettingsPage user={user} />} />
          <Route path="/account/about/terms" element={<SettingsPage user={user} sectionOverride="terms" />} />
          <Route path="/admin/settings/:section" element={canManage(user) ? <SettingsPage user={user} area="admin" /> : <Navigate to="/account/profile" replace />} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>,
  );
}

const userOf = (role: string) => ({ id: 1, username: "u", role, active: true }) as unknown as User;

beforeEach(() => vi.clearAllMocks());

describe("SettingsPage tabs", () => {
  it("opens on appearance and shows only that group", async () => {
    renderAt(userOf("user"));
    expect(await screen.findByText("settings.appearance")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "account.documentDetails" })).toBeNull();
    expect(screen.queryByText("settings.shipmentDefaults")).toBeNull();
  });

  it("switching tabs shows the other group", async () => {
    renderAt(userOf("user"));
    await userEvent.click(await screen.findByRole("button", { name: "account.documentDetails" }));
    expect(screen.getByRole("heading", { name: "account.documentDetails" })).toBeTruthy();
    expect(screen.queryByText("settings.appearance")).toBeNull();
    // The save button travels with the personal tabs; one draft, one button.
    expect(screen.getByRole("button", { name: "settings.save" })).toBeTruthy();
  });

  it("the phone dropdown selects the same groups", async () => {
    renderAt(userOf("user"));
    const picker = await screen.findByLabelText("settings.tabPick");
    await userEvent.selectOptions(picker, "shipment");
    expect(screen.getByText("settings.shipmentDefaults")).toBeTruthy();
  });

  it("the administrator groups exist only for an administrator", async () => {
    const { unmount } = renderAt(userOf("user"));
    await screen.findByText("settings.appearance");
    expect(screen.queryByRole("button", { name: "settingsNav.organisation" })).toBeNull();
    expect(screen.queryByRole("button", { name: "settings.adminUpdates" })).toBeNull();
    unmount();

    renderAt(userOf("admin"), "/admin/settings/organisation");
    expect(await screen.findByRole("button", { name: "settingsNav.organisation" })).toBeTruthy();
    // Maintenance actions now have distinct destinations. The update must be
    // discoverable without loading the UN-card store or assistant model.
    await userEvent.click(screen.getByRole("button", { name: "settings.adminUpdates" }));
    expect(await screen.findByRole("heading", { name: "settings.adminUpdates" })).toBeTruthy();
    expect(screen.queryByText("settings.unCardsStoreTitle")).toBeNull();
    expect(screen.queryByText("settings.assistantTitle")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "settingsNav.cards" }));
    expect(await screen.findByText("settings.unCardsStoreTitle")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "settingsNav.assistant" }));
    expect(await screen.findByText("settings.assistantTitle")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "settings.saveAdmin" })).toBeNull();
  });

  it("a link can point straight at a tab", async () => {
    // What the two-factor notice relies on: its button lands on the panel it
    // is about, not on the theme settings with the panel three tabs away.
    renderAt(userOf("user"), "/settings?tab=details");
    expect(await screen.findByRole("heading", { name: "account.documentDetails" })).toBeTruthy();
    expect(screen.queryByText("settings.appearance")).toBeNull();
  });

  it("an unknown tab in the address falls back rather than showing nothing", async () => {
    renderAt(userOf("user"), "/account/nonsense");
    expect(await screen.findByRole("heading", { name: "account.profile" })).toBeTruthy();
  });

  it("a plain user cannot reach an administrator tab through the address", async () => {
    renderAt(userOf("user"), "/settings?tab=admin");
    // The server refuses their writes anyway; this keeps the screen honest.
    expect(await screen.findByRole("heading", { name: "account.profile" })).toBeTruthy();
  });
});


it("gives Super Users organisation defaults without exposing system or DG policy tabs", async () => {
  renderAt(userOf("super_user"), "/settings?tab=admin");
  expect(await screen.findByDisplayValue("Test")).toBeInTheDocument();
  for (const label of ["settings.adminBranding", "settings.mailTitle", "settingsNav.connections", "settings.adminUpdates", "settingsNav.assistant", "dgReview.settingsTitle"]) {
    expect(screen.queryByRole("button", { name: label })).toBeNull();
  }
  expect(screen.queryByRole("button", { name: "settingsNav.security" })).toBeNull();
  expect(screen.queryByText("settingsNav.accessPolicy")).toBeNull();
});


it("keeps an administrator's own security separate from access policy", async () => {
  renderAt(userOf("admin"), "/account/security");
  expect(await screen.findByLabelText("account.currentPassword")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "account.accessPolicy" })).toBeNull();
  expect(api.instanceSettings).not.toHaveBeenCalled();
  expect(api.twoFactorStatus).toHaveBeenCalled();
});

it("keeps password and profile controls out of administration", async () => {
  renderAt(userOf("admin"), "/admin/settings/access");
  expect(await screen.findByText("settingsNav.accessPolicy")).toBeVisible();
  expect(screen.queryByLabelText("account.currentPassword")).toBeNull();
  expect(screen.queryByRole("button", { name: "account.profile" })).toBeNull();
  expect(api.myProfile).not.toHaveBeenCalled();
  expect(api.twoFactorStatus).not.toHaveBeenCalled();
});

it("shows product information and opens terms inside account settings", async () => {
  renderAt(userOf("user"), "/account/about");
  expect(await screen.findByText("v1.115.0")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "account.sourceCode" })).toHaveAttribute("href", "https://github.com/jeffreymooiweer/emcargo");
  await userEvent.click(screen.getByRole("link", { name: /legal.title/ }));
  expect(await screen.findByRole("heading", { name: "legal.title" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /account.about/ })).toHaveAttribute("href", "/account/about");
  expect(screen.getByRole("button", { name: "account.about" })).toHaveAttribute("aria-current", "page");
});
