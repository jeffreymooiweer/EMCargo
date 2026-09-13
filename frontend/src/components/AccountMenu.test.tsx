/** Account actions need predictable focus without trapping the rest of the page.
 * Touch dismissal, keyboard navigation and responsive changes must close the
 * popover without leaving a hidden menu or sending focus back after an outside tap.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { expect, it, vi } from "vitest";
import type { User } from "../api/client";
import AccountMenu from "./AccountMenu";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
const user = { id: 1, username: "tester", role: "user", active: true } as User;
function renderMenu() {
  render(<MemoryRouter><button>Before</button><AccountMenu user={user} onLogout={vi.fn()} loggingOut={false} /><button>After</button></MemoryRouter>);
  return screen.getByRole("button", { name: "account.menu" });
}

it("opens at either end, cycles with arrows and returns focus on Escape", async () => {
  const avatar = renderMenu();
  avatar.focus();
  await userEvent.keyboard("{ArrowDown}");
  const settings = screen.getByRole("menuitem", { name: "account.settings" });
  const logout = screen.getByRole("menuitem", { name: "nav.logout" });
  expect(settings).toHaveFocus();
  expect(avatar).toHaveAttribute("aria-expanded", "true");
  expect(avatar).toHaveAttribute("aria-controls", screen.getByRole("menu").id);
  await userEvent.keyboard("{ArrowUp}"); expect(logout).toHaveFocus();
  await userEvent.keyboard("{ArrowDown}"); expect(settings).toHaveFocus();
  await userEvent.keyboard("{End}"); expect(logout).toHaveFocus();
  await userEvent.keyboard("{Home}"); expect(settings).toHaveFocus();
  await userEvent.keyboard("{Escape}");
  expect(screen.queryByRole("menu")).toBeNull();
  expect(avatar).toHaveFocus();
  expect(avatar).toHaveAttribute("aria-expanded", "false");
  await userEvent.keyboard("{ArrowUp}");
  expect(screen.getByRole("menuitem", { name: "nav.logout" })).toHaveFocus();
});

it("dismisses on outside taps and viewport changes without stealing outside focus", async () => {
  const avatar = renderMenu();
  await userEvent.click(avatar);
  await userEvent.click(avatar);
  expect(screen.queryByRole("menu")).toBeNull();
  await userEvent.click(avatar);
  await userEvent.click(screen.getByRole("button", { name: "After" }));
  expect(screen.queryByRole("menu")).toBeNull();
  expect(screen.getByRole("button", { name: "After" })).toHaveFocus();
  await userEvent.click(avatar);
  fireEvent.resize(window);
  expect(screen.queryByRole("menu")).toBeNull();
  expect(avatar).toHaveAttribute("aria-expanded", "false");
});

it("lets Tab and Shift+Tab continue through the page", async () => {
  const avatar = renderMenu();
  await userEvent.click(avatar);
  await userEvent.tab();
  expect(screen.queryByRole("menu")).toBeNull();
  expect(screen.getByRole("button", { name: "After" })).toHaveFocus();
  await userEvent.click(avatar);
  await userEvent.tab({ shift: true });
  expect(screen.queryByRole("menu")).toBeNull();
  expect(avatar).toHaveFocus();
  await userEvent.tab({ shift: true });
  expect(screen.getByRole("button", { name: "Before" })).toHaveFocus();
});
