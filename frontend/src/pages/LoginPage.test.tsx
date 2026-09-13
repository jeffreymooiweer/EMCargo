import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";
import LoginPage from "./LoginPage";
import { api } from "../api/client";
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
vi.mock("../branding", () => ({ useBranding: () => ({ branding: { app_name: "EMCargo", logo: null } }) }));
vi.mock("../api/client", () => ({ api: { login: vi.fn(), setupStatus: vi.fn().mockResolvedValue({has_admin:true}) } }));
beforeEach(() => vi.clearAllMocks());
it("explains why password changes return to sign-in", () => {
  render(<MemoryRouter initialEntries={[{ pathname: "/login", state: { passwordChanged: true } }]}><LoginPage onLogin={vi.fn()} /></MemoryRouter>);
  expect(screen.getByRole("status")).toHaveTextContent("account.passwordChanged");
});
it("labels the sign-in fields and prevents duplicate requests while authentication is pending", async () => {
  let reject: (error: Error) => void = () => {};
  vi.mocked(api.login).mockImplementation(() => new Promise((_resolve, rejectPromise) => { reject = rejectPromise; }));
  render(<MemoryRouter><LoginPage onLogin={vi.fn()} /></MemoryRouter>);
  await userEvent.type(screen.getByLabelText("login.username"), "review");
  await userEvent.type(screen.getByLabelText("login.password"), "synthetic-password");
  await userEvent.click(screen.getByRole("button", { name: "login.submit" }));
  const pending = screen.getByRole("button", { name: "studio.loginBusy" });
  expect(pending).toBeDisabled();
  await userEvent.click(pending);
  expect(api.login).toHaveBeenCalledOnce();
  reject(new Error("Unavailable"));
  expect(await screen.findByRole("alert")).toHaveTextContent("Unavailable");
  await waitFor(() => expect(screen.getByRole("button", { name: "login.submit" })).toBeEnabled());
});
