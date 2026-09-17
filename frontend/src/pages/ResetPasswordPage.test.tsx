import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, expect, it, vi } from "vitest";
import ResetPasswordPage from "./ResetPasswordPage";
import { api } from "../api/client";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
vi.mock("../branding", () => ({ useBranding: () => ({ branding: { name: "EMCargo", logo: null } }) }));
vi.mock("../api/client", () => ({ api: {
  resetLinkValid: vi.fn().mockResolvedValue({ valid: true }),
  resetPassword: vi.fn(),
  loginTwoFactor: vi.fn(),
} }));

beforeEach(() => vi.clearAllMocks());

/** A reset must not claim that a second-factor email was sent when the server
 * reports delivery failure. Recovery remains available through the same field. */
it("preserves the failed-delivery state and offers a recovery code after resetting a password", async () => {
  vi.mocked(api.resetPassword).mockResolvedValueOnce({ two_factor_required: true, challenge: "challenge", method: "email", code_sent: false });
  render(<MemoryRouter initialEntries={["/reset-password?token=valid"]}><ResetPasswordPage /></MemoryRouter>);
  await userEvent.type(await screen.findByLabelText("reset.password"), "new-password");
  await userEvent.type(screen.getByLabelText("reset.repeat"), "new-password");
  await userEvent.click(screen.getByRole("button", { name: "reset.submitAndSignIn" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("login.twoFactorMailFailed");
  expect(screen.getByLabelText("login.twoFactorEmailCode")).toBeInTheDocument();
  expect(screen.queryByText("login.twoFactorMailSent")).toBeNull();
});

it("keeps invalid reset links out of the password form", async () => {
  vi.mocked(api.resetLinkValid).mockResolvedValueOnce({ valid: false });
  render(<MemoryRouter initialEntries={["/reset-password?token=expired"]}><ResetPasswordPage /></MemoryRouter>);
  expect(await screen.findByRole("alert")).toHaveTextContent("reset.spent");
  expect(screen.queryByLabelText("reset.password")).toBeNull();
  expect(screen.getByRole("link", { name: "reset.toLogin" })).toHaveAttribute("href", "/login");
});
