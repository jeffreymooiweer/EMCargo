import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import TwoFactorPanel from "./TwoFactorPanel";
import { api } from "../api/client";
import { ToastProvider } from "../toast/ToastProvider";
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
vi.mock("../api/client", () => ({ api: {
  twoFactorStatus: vi.fn(), twoFactorNewRecoveryCodes: vi.fn(), twoFactorSendCode: vi.fn(),
  twoFactorDisable: vi.fn(), twoFactorStart: vi.fn(), twoFactorConfirm: vi.fn(),
} }));
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.twoFactorStatus).mockResolvedValue({ active: true, method: "email", required: true, recovery_codes_left: 8 });
  vi.mocked(api.twoFactorNewRecoveryCodes).mockResolvedValue({ recovery_codes: ["synthetic-recovery-code"] });
  vi.mocked(api.twoFactorSendCode).mockResolvedValue({ ok: true });
  vi.mocked(api.twoFactorDisable).mockResolvedValue({ ok: true });
});
it("requires proof before replacing recovery codes even when two-factor verification is mandatory", async () => {
  render(<ToastProvider><TwoFactorPanel /></ToastProvider>);
  await userEvent.click(await screen.findByRole("button", { name: "twoFactor.newCodes" }));
  expect(api.twoFactorNewRecoveryCodes).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "twoFactor.confirm" })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: "twoFactor.sendCode" }));
  expect(api.twoFactorSendCode).toHaveBeenCalledOnce();
  await userEvent.type(screen.getByLabelText("twoFactor.renewCode"), "123456");
  await userEvent.click(screen.getByRole("button", { name: "twoFactor.confirm" }));
  await waitFor(() => expect(api.twoFactorNewRecoveryCodes).toHaveBeenCalledWith("123456"));
  expect(await screen.findByText("synthetic-recovery-code")).toBeInTheDocument();
  expect(screen.queryByLabelText("twoFactor.renewCode")).not.toBeInTheDocument();
});

/** Hiding advanced actions must preserve the mandatory-2FA boundary and still
 * require a fresh code before an optional factor can be removed. */
it("keeps disabling unavailable for mandatory accounts", async () => {
  render(<ToastProvider><TwoFactorPanel /></ToastProvider>);
  await screen.findByRole("button", { name: "twoFactor.newCodes" });
  expect(screen.queryByRole("button", { name: "twoFactor.turnOff" })).not.toBeInTheDocument();
  expect(api.twoFactorDisable).not.toHaveBeenCalled();
});

it("opens disabling on demand and accepts a verification code with Enter", async () => {
  vi.mocked(api.twoFactorStatus).mockResolvedValue({ active: true, method: "email", required: false, recovery_codes_left: 8 });
  render(<ToastProvider><TwoFactorPanel /></ToastProvider>);
  expect(screen.queryByLabelText("twoFactor.verificationOrRecoveryCode")).not.toBeInTheDocument();
  await userEvent.click(await screen.findByRole("button", { name: "twoFactor.turnOff" }));
  expect(api.twoFactorDisable).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "twoFactor.turnOffDo" })).toBeDisabled();
  const code = screen.getByLabelText("twoFactor.verificationOrRecoveryCode");
  expect(code).toHaveFocus();
  await userEvent.type(code, "123456{Enter}");
  await waitFor(() => expect(api.twoFactorDisable).toHaveBeenCalledWith("123456"));
  expect(api.twoFactorDisable).toHaveBeenCalledOnce();
});

/** A failed status request previously removed the security panel entirely,
 * leaving no recovery action after the temporary toast disappeared. */
it("offers retry after a failed security status request", async () => {
  vi.mocked(api.twoFactorStatus).mockRejectedValueOnce(new Error("Offline"));
  render(<ToastProvider><TwoFactorPanel /></ToastProvider>);
  expect(await screen.findByRole("alert")).toHaveTextContent("Offline");
  await userEvent.click(screen.getByRole("button", { name: "history.retry" }));
  expect(await screen.findByRole("button", { name: "twoFactor.newCodes" })).toBeEnabled();
});
