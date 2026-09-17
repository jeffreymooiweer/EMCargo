/** Profile edits stay recoverable; password changes clear the authenticated app. */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { beforeEach, expect, it, vi } from "vitest";
import { api, type User } from "../../api/client";
import { ToastProvider } from "../../toast/ToastProvider";
import ProfilePanel from "./ProfilePanel";
import PasswordPanel from "./PasswordPanel";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
vi.mock("../../components/AvatarSettings", () => ({ default: () => <p>avatar</p> }));
vi.mock("../../api/client", () => ({ api: { myProfile: vi.fn(), saveMyProfile: vi.fn(), changePassword: vi.fn() } }));
const user = { id: 1, username: "ada", email: "ada@example.com", role: "user", active: true } as User;
const profile = { display_name: "", first_name: "Ada", last_name: "Lovelace", job_title: "", phone_number: "" };
beforeEach(() => { vi.resetAllMocks(); vi.mocked(api.myProfile).mockResolvedValue(profile); });

it("keeps unsaved profile fields after a failed save and updates the shared account after retry", async () => {
  const changed = vi.fn(); const dirty = vi.fn();
  vi.mocked(api.saveMyProfile).mockRejectedValueOnce(new Error("Unavailable")).mockResolvedValue({ ...user, display_name: "Ada L." });
  render(<ToastProvider><ProfilePanel user={user} onUserChange={changed} onDirtyChange={dirty} /></ToastProvider>);
  const input = await screen.findByLabelText("account.displayName");
  expect(input).toHaveAttribute("placeholder", "Ada Lovelace");
  await userEvent.type(input, "  Ada L.  ");
  await userEvent.click(screen.getByRole("button", { name: "settings.save" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Unavailable");
  expect(input).toHaveValue("  Ada L.  ");
  expect(changed).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: "settings.save" }));
  await waitFor(() => expect(changed).toHaveBeenCalledWith({ ...user, display_name: "Ada L." }));
  expect(api.saveMyProfile).toHaveBeenLastCalledWith({ ...profile, display_name: "Ada L." });
  expect(screen.getByRole("button", { name: "settings.save" })).toBeDisabled();
  expect(dirty).toHaveBeenLastCalledWith(false);
});

it("cannot save an empty replacement when profile loading failed", async () => {
  vi.mocked(api.myProfile).mockRejectedValueOnce(new Error("Offline"));
  render(<ToastProvider><ProfilePanel user={user} onDirtyChange={vi.fn()} /></ToastProvider>);
  expect(await screen.findByRole("alert")).toHaveTextContent("Offline");
  expect(screen.queryByRole("button", { name: "settings.save" })).toBeNull();
  await userEvent.click(screen.getByRole("button", { name: "history.retry" }));
  expect(await screen.findByLabelText("account.firstName")).toHaveValue("Ada");
  expect(api.saveMyProfile).not.toHaveBeenCalled();
});

function Position() { const location = useLocation(); return <output data-testid="position">{JSON.stringify(location)}</output>; }
it("validates confirmation and keeps errors in place before signing out on success", async () => {
  const changed = vi.fn();
  vi.mocked(api.changePassword).mockRejectedValueOnce(new Error("Incorrect current password")).mockResolvedValue({ ok: true, reauthenticate: true });
  render(<MemoryRouter initialEntries={["/account/security"]}><PasswordPanel onPasswordChanged={changed} /><Position /></MemoryRouter>);
  await userEvent.type(screen.getByLabelText("account.currentPassword"), "old synthetic password");
  await userEvent.type(screen.getByLabelText("account.newPasswordMinimum"), "new synthetic password");
  const repeat = screen.getByLabelText("account.repeatPassword");
  await userEvent.type(repeat, "different password");
  await userEvent.click(screen.getByRole("button", { name: "account.changePassword" }));
  expect(screen.getByRole("alert")).toHaveTextContent("reset.mismatch");
  expect(api.changePassword).not.toHaveBeenCalled();
  expect(repeat).toHaveFocus();
  await userEvent.clear(repeat); await userEvent.type(repeat, "new synthetic password");
  await userEvent.click(screen.getByRole("button", { name: "account.changePassword" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect current password");
  expect(changed).not.toHaveBeenCalled();
  expect(screen.getByTestId("position")).toHaveTextContent("/account/security");
  await userEvent.click(screen.getByRole("button", { name: "account.changePassword" }));
  await waitFor(() => expect(changed).toHaveBeenCalledOnce());
  expect(screen.getByTestId("position")).toHaveTextContent('"pathname":"/login"');
  expect(screen.getByTestId("position")).toHaveTextContent('"passwordChanged":true');
  expect(screen.getByLabelText("account.currentPassword")).toHaveValue("");
});
