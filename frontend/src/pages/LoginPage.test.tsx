import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";
import LoginPage from "./LoginPage";
import { api } from "../api/client";
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
vi.mock("../branding", () => ({ useBranding: () => ({ branding: { app_name: "EMCargo", logo: null } }) }));
vi.mock("../api/client", () => ({ api: { login: vi.fn(), forgotPassword: vi.fn().mockResolvedValue({}), loginTwoFactor: vi.fn().mockResolvedValue({}), setupStatus: vi.fn().mockResolvedValue({has_admin:true}) } }));
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

it("requests a reset with Enter without requiring the forgotten password", async () => {
  render(<MemoryRouter><LoginPage onLogin={vi.fn()} /></MemoryRouter>);
  await userEvent.type(screen.getByLabelText("login.username"), "review");
  await userEvent.click(screen.getByRole("button", { name: "login.forgot" }));
  const identifier = screen.getByLabelText("login.forgotLabel");
  expect(identifier).toHaveValue("review");
  expect(identifier).toHaveFocus();
  expect(screen.queryByLabelText("login.password")).toBeNull();
  await userEvent.type(identifier, "{Enter}");
  await waitFor(() => expect(api.forgotPassword).toHaveBeenCalledWith("review"));
  expect(api.login).not.toHaveBeenCalled();
  expect(await screen.findByRole("status")).toHaveTextContent("login.forgotSent");
});

it("keeps recovery codes discoverable in the second-factor field label", async () => {
  vi.mocked(api.login).mockResolvedValueOnce({ two_factor_required: true, challenge: "challenge", method: "totp", code_sent: false });
  const onLogin = vi.fn();
  render(<MemoryRouter><LoginPage onLogin={onLogin} /></MemoryRouter>);
  await userEvent.type(screen.getByLabelText("login.username"), "review");
  await userEvent.type(screen.getByLabelText("login.password"), "synthetic-password");
  await userEvent.click(screen.getByRole("button", { name: "login.submit" }));
  await userEvent.type(await screen.findByLabelText("login.twoFactorAppCode"), "RECOVERY-CODE");
  await userEvent.click(screen.getByRole("button", { name: "login.twoFactorSubmit" }));
  expect(api.loginTwoFactor).toHaveBeenCalledWith("challenge", "RECOVERY-CODE");
  await waitFor(() => expect(onLogin).toHaveBeenCalledOnce());
});
