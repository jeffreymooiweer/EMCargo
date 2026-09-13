/**
 * The update notice speaks only to the administrator, and only once per release.
 *
 * A regular user never triggers the request at all — the endpoint would
 * refuse them anyway, but not asking is the point: a user must not be able to
 * make the installation call GitHub. And "GitHub could not say" renders
 * nothing rather than pretending the installation is up to date.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MemoryRouter, useLocation } from "react-router";
import UpdateToast, { DISMISSED_KEY } from "./UpdateToast";
import { ToastProvider } from "../toast/ToastProvider";
import { api, User } from "../api/client";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options?.version ? `${key} ${options.version}` : key,
    i18n: { language: "nl" },
  }),
}));

const admin = { id: 1, username: "ada", role: "admin", active: true } as User;
const regular = { id: 2, username: "bob", role: "user", active: true } as User;

const AVAILABLE = {
  enabled: true,
  reachable: true,
  current: "1.125.0",
  latest: "1.126.0",
  url: "https://github.com/x/releases/v1.126.0",
  update_available: true,
};

function Location() { const location = useLocation(); return <span data-testid="location">{location.pathname + location.search}</span>; }

function renderNotice(user: User) {
  return render(
    <MemoryRouter><ToastProvider>
      <Location />
      <UpdateToast user={user} />
    </ToastProvider></MemoryRouter>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("UpdateToast", () => {
  it("takes the administrator directly to update controls", async () => {
    vi.spyOn(api, "updateStatus").mockResolvedValue(AVAILABLE);
    renderNotice(admin);
    expect(await screen.findByRole("status")).toBeInTheDocument();
    expect(screen.getByText(/update\.available 1\.126\.0/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "updates.open" }));
    expect(screen.getByTestId("location")).toHaveTextContent("/admin/settings/updates");
  });

  it("never even asks for a regular user", async () => {
    const status = vi.spyOn(api, "updateStatus").mockResolvedValue(AVAILABLE);
    renderNotice(regular);
    await new Promise((resolve) => setTimeout(resolve, 10));
    expect(status).not.toHaveBeenCalled();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("stays quiet when the running release is current", async () => {
    vi.spyOn(api, "updateStatus").mockResolvedValue({
      ...AVAILABLE,
      latest: "1.125.0",
      update_available: false,
    });
    renderNotice(admin);
    await waitFor(() => expect(api.updateStatus).toHaveBeenCalled());
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("not reachable is not up to date, and also not a toast", async () => {
    vi.spyOn(api, "updateStatus").mockResolvedValue({
      enabled: true,
      reachable: false,
      current: "1.125.0",
    });
    renderNotice(admin);
    await waitFor(() => expect(api.updateStatus).toHaveBeenCalled());
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("a dismissed release stays dismissed, a newer one shows again", async () => {
    vi.spyOn(api, "updateStatus").mockResolvedValue(AVAILABLE);
    renderNotice(admin);
    await screen.findByRole("status");
    await userEvent.click(screen.getByRole("button", { name: "toast.dismiss" }));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(localStorage.getItem(DISMISSED_KEY)).toBe("1.126.0");

    // The same release again: nothing.
    renderNotice(admin);
    await waitFor(() => expect(api.updateStatus).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    // A newer one: the notice returns.
    vi.spyOn(api, "updateStatus").mockResolvedValue({
      ...AVAILABLE,
      latest: "1.127.0",
    });
    renderNotice(admin);
    expect(await screen.findByRole("status")).toBeInTheDocument();
  });
});
