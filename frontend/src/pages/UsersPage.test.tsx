import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import UsersPage from "./UsersPage";
import { ToastProvider } from "../toast/ToastProvider";
import type { User } from "../api/client";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
vi.mock("../settings/preferences", () => ({ usePreferences: () => ({ publicSettings: { history_enabled: true, mail_enabled: false } }) }));
const api = vi.hoisted(() => ({ listUsers: vi.fn(), departments: vi.fn(), updateUser: vi.fn(), createUser: vi.fn(), deleteUser: vi.fn(), clearTwoFactorFor: vi.fn() }));
vi.mock("../api/client", () => ({ api }));
const deliveryApi = vi.hoisted(() => ({ account: vi.fn(), saveAccount: vi.fn() }));
vi.mock("../api/deliveries", () => ({ deliveries: deliveryApi, modes: ["road", "rail", "inland", "sea", "air"] }));
const people: User[] = [
  { id: 1, username: "Ada", email: "ada@example.com", role: "admin", active: true },
  { id: 2, username: "Bart", email: "bart@example.com", role: "user", active: true, department_id: 4 },
  { id: 3, username: "Mina", email: "mina@example.com", role: "user", active: false },
];

beforeEach(() => {
  vi.clearAllMocks();
  deliveryApi.account.mockResolvedValue({ roles: ["shipment", "planner"], modes: [] });
  deliveryApi.saveAccount.mockResolvedValue({});
  // jsdom does not implement the browser's top layer; keep its dialog visible
  // while exercising the real forms and requests, without replacing the UI.
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
  api.listUsers.mockResolvedValue(people);
  api.departments.mockResolvedValue([{ id: 4, name: "Planning", users: 1, shipments: 0 }]);
  api.updateUser.mockResolvedValue(people[1]);
  api.createUser.mockResolvedValue({ ...people[1], welcome_mail: "not_requested" });
});
const page = () => render(<ToastProvider><UsersPage user={people[0]} /></ToastProvider>);

it("keeps account controls out of the directory until a person is selected", async () => {
  page();
  await screen.findByText("Bart");
  expect(screen.queryByRole("button", { name: "users.delete" })).toBeNull();
  await userEvent.type(screen.getByRole("searchbox"), "Planning");
  expect(screen.getByText("Bart")).toBeInTheDocument();
  expect(screen.queryByText("Mina")).toBeNull();
  await userEvent.click(screen.getByRole("button", { name: "directory.edit Bart" }));
  const editor = within(screen.getByRole("dialog"));
  expect(editor.getByLabelText("users.email")).toHaveValue("bart@example.com");
  expect(api.updateUser).not.toHaveBeenCalled();
});

it("requires saving edits and preserves the form when the server refuses", async () => {
  api.updateUser.mockRejectedValue(new Error("save refused"));
  page();
  await userEvent.click(await screen.findByRole("button", { name: "directory.edit Bart" }));
  const editor = within(screen.getByRole("dialog"));
  const email = editor.getByLabelText("users.email");
  await userEvent.clear(email); await userEvent.type(email, "new@example.com");
  expect(api.updateUser).not.toHaveBeenCalled();
  await userEvent.click(editor.getByRole("button", { name: "directory.save" }));
  expect(await editor.findByRole("alert")).toHaveTextContent("save refused");
  expect(email).toHaveValue("new@example.com");
  expect(screen.getByRole("dialog")).toBeInTheDocument();
});

it("preserves the safeguards for the current and last administrator", async () => {
  page();
  await userEvent.click(await screen.findByRole("button", { name: "directory.edit Ada" }));
  const editor = within(screen.getByRole("dialog"));
  expect(editor.getByLabelText("users.role")).toBeDisabled();
  expect(editor.getByRole("checkbox", { name: "directory.activeAccount" })).toBeDisabled();
  fireEvent.click(editor.getByText("directory.security"));
  expect(editor.getByRole("button", { name: "users.delete" })).toBeDisabled();
  expect(editor.getByText("users.guardSelf")).toBeVisible();
});

it("creates an account only from the completed create form", async () => {
  page(); await screen.findByText("Bart");
  await userEvent.click(screen.getByRole("button", { name: "users.newUser" }));
  const editor = within(screen.getByRole("dialog"));
  await userEvent.type(editor.getByLabelText("users.username"), "newperson");
  await userEvent.type(editor.getByLabelText("users.email"), "new@example.com");
  await userEvent.type(editor.getByLabelText("users.password"), "strong-password");
  await userEvent.click(editor.getByRole("button", { name: "users.create" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(api.createUser).toHaveBeenCalledWith({ username: "newperson", email: "new@example.com", role: "user", password: "strong-password", send_welcome: false });
});


it("shows all roles but prevents a Super User from editing privileged accounts or assigning their roles", async () => {
  const specialist = { ...people[1], id: 8, username: "DG colleague", role: "dg_specialist" };
  api.listUsers.mockResolvedValue([...people, specialist]);
  render(<ToastProvider><UsersPage user={{ ...people[1], role: "super_user" }} /></ToastProvider>);
  expect(await screen.findByRole("button", { name: "directory.edit Ada" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "directory.edit DG colleague" })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: "users.newUser" }));
  const editor = within(screen.getByRole("dialog"));
  const roles = within(editor.getByLabelText("users.role"));
  expect(roles.getByRole("option", { name: "roles.superUser" })).toBeInTheDocument();
  expect(roles.queryByRole("option", { name: "users.roleAdmin" })).toBeNull();
  expect(roles.queryByRole("option", { name: "roles.dgSpecialist" })).toBeNull();
});
