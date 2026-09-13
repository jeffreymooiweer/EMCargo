/**
 * The reminder for an account without a second factor.
 *
 * What is pinned here is mostly about restraint: it appears for the accounts
 * that need it, it says nothing about the ones that do not, it says nothing
 * when it could not find out, and it asks once per sign-in rather than on
 * every render — because a notice people learn to dismiss unread is worse
 * than one that is never shown.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import TwoFactorNudge, { NUDGED_KEY, clearTwoFactorNudge } from "./TwoFactorNudge";
import { ToastProvider } from "../toast/ToastProvider";
import { TWO_FACTOR_REQUIRED_EVENT, api, User } from "../api/client";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: "nl" },
  }),
}));

const user = { id: 7, username: "ada", role: "user", active: true } as User;

const OFF = { active: false, method: "", required: false, recovery_codes_left: 0 };
const ON = { active: true, method: "totp", required: false, recovery_codes_left: 8 };

/** Where the router actually ended up, since MemoryRouter never touches
 *  window.location. */
function Whereabouts() {
  const location = useLocation();
  return <p data-testid="where">{location.pathname + location.search}</p>;
}

function renderNudge() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <ToastProvider>
        <TwoFactorNudge user={user} />
        <Whereabouts />
        <Routes>
          <Route path="/" element={<p>home</p>} />
          <Route path="/account/security" element={<p>settings page</p>} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  sessionStorage.clear();
});

describe("TwoFactorNudge", () => {
  it("reminds an account without a second factor", async () => {
    vi.spyOn(api, "twoFactorStatus").mockResolvedValue(OFF);
    renderNudge();
    expect(await screen.findByText("twoFactor.nudge")).toBeInTheDocument();
  });

  it("is firmer when the installation's policy demands one", async () => {
    vi.spyOn(api, "twoFactorStatus").mockResolvedValue({ ...OFF, required: true });
    renderNudge();
    // A policy the account does not meet is a different thing to be told than
    // a recommendation not taken, so it does not get the same sentence.
    expect(await screen.findByText("twoFactor.nudgeRequired")).toBeInTheDocument();
    expect(screen.queryByText("twoFactor.nudge")).not.toBeInTheDocument();
  });

  it("keeps the mild wording where a second factor is only advisable", async () => {
    vi.spyOn(api, "twoFactorStatus").mockResolvedValue(OFF);
    renderNudge();
    expect(await screen.findByText("twoFactor.nudge")).toBeInTheDocument();
    expect(screen.queryByText("twoFactor.nudgeRequired")).not.toBeInTheDocument();
  });

  it("says nothing to an account that already has one", async () => {
    vi.spyOn(api, "twoFactorStatus").mockResolvedValue(ON);
    renderNudge();
    await waitFor(() => expect(api.twoFactorStatus).toHaveBeenCalled());
    expect(screen.queryByText("twoFactor.nudge")).not.toBeInTheDocument();
  });

  it("says nothing when it could not find out", async () => {
    vi.spyOn(api, "twoFactorStatus").mockRejectedValue(new Error("offline"));
    renderNudge();
    await waitFor(() => expect(api.twoFactorStatus).toHaveBeenCalled());
    // A backend that will not answer is not evidence the account is exposed.
    expect(screen.queryByText("twoFactor.nudge")).not.toBeInTheDocument();
  });

  it("stays put rather than sliding away with its own button", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.spyOn(api, "twoFactorStatus").mockResolvedValue(OFF);
    renderNudge();
    await screen.findByText("twoFactor.nudge");
    await vi.advanceTimersByTimeAsync(60000);
    expect(screen.getByText("twoFactor.nudge")).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("its button opens the settings, at the tab the second factor is on", async () => {
    vi.spyOn(api, "twoFactorStatus").mockResolvedValue(OFF);
    renderNudge();
    await screen.findByText("twoFactor.nudge");
    await userEvent.click(screen.getByRole("button", { name: "twoFactor.nudgeAction" }));
    expect(screen.getByText("settings page")).toBeInTheDocument();
    // Not just "the settings" — the tab the panel is actually on. Landing on
    // the theme settings would make the button a dead end.
    expect(screen.getByTestId("where")).toHaveTextContent("/account/security");
  });

  it("asks once per sign-in, not on every page load", async () => {
    vi.spyOn(api, "twoFactorStatus").mockResolvedValue(OFF);
    const first = renderNudge();
    await screen.findByText("twoFactor.nudge");
    expect(sessionStorage.getItem(NUDGED_KEY)).toBe("7");
    first.unmount();

    // A refresh mid-work: the marker survives and nothing asks again.
    renderNudge();
    await new Promise((resolve) => setTimeout(resolve, 10));
    expect(screen.queryByText("twoFactor.nudge")).not.toBeInTheDocument();
  });

  it("takes a refused account to the panel, and explains once", async () => {
    vi.spyOn(api, "twoFactorStatus").mockResolvedValue(ON);
    renderNudge();
    await waitFor(() => expect(api.twoFactorStatus).toHaveBeenCalled());
    // What the API client raises when the server answers a call with
    // auth.two_factor_required: the account owes a factor and may reach
    // nothing else, so every page it lands on ends up here.
    window.dispatchEvent(new CustomEvent(TWO_FACTOR_REQUIRED_EVENT));
    expect(await screen.findByText("settings page")).toBeInTheDocument();
    expect(screen.getByTestId("where")).toHaveTextContent("/account/security");
    expect(screen.getByText("twoFactor.nudgeRequired")).toBeInTheDocument();
    window.dispatchEvent(new CustomEvent(TWO_FACTOR_REQUIRED_EVENT));
    window.dispatchEvent(new CustomEvent(TWO_FACTOR_REQUIRED_EVENT));
    expect(screen.getAllByText("twoFactor.nudgeRequired")).toHaveLength(1);
  });

  it("asks again after a logout", async () => {
    vi.spyOn(api, "twoFactorStatus").mockResolvedValue(OFF);
    const first = renderNudge();
    await screen.findByText("twoFactor.nudge");
    first.unmount();

    clearTwoFactorNudge();
    expect(sessionStorage.getItem(NUDGED_KEY)).toBeNull();
    renderNudge();
    expect(await screen.findByText("twoFactor.nudge")).toBeInTheDocument();
  });
});
