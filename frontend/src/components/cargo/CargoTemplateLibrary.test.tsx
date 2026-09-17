import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { User } from "../../api/client";
import { cargoApi, type PackagingTemplate } from "../../api/cargo";
import CargoTemplateLibrary from "./CargoTemplateLibrary";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key, i18n: { language: "nl" } }) }));
const builtin: PackagingTemplate = { id: "builtin-box", name: "Box", category: "box", builtin: true, version: 1, language_labels: { nl: "Doos", en: "Box", de: "Karton", fr: "Carton" } };
const own: PackagingTemplate = { id: "own", name: "Our crate", category: "crate", version: 2 };
const manager = { role: "admin" } as User;
beforeEach(() => {
  HTMLDialogElement.prototype.showModal = function (this: HTMLDialogElement) { this.open = true; };
  HTMLDialogElement.prototype.close = function (this: HTMLDialogElement) { this.open = false; };
  vi.spyOn(cargoApi, "templates").mockResolvedValue([builtin, own]);
});
afterEach(() => { vi.restoreAllMocks(); });

it("lets ordinary users read models without exposing catalogue mutations", async () => {
  render(<CargoTemplateLibrary user={{ role: "user" } as User} />);
  expect(await screen.findByText("Doos")).toBeVisible();
  expect(screen.queryByText("cargo.addModel")).not.toBeInTheDocument();
  expect(screen.queryByText("equipmentSimple.more")).not.toBeInTheDocument();
});

it("copies a built-in into an editable own model rather than submitting an unsupported builtin edit", async () => {
  const create = vi.spyOn(cargoApi, "createTemplate").mockResolvedValue({ ...builtin, id: "new", builtin: false });
  const update = vi.spyOn(cargoApi, "updateTemplate");
  const user = userEvent.setup(); render(<CargoTemplateLibrary user={manager} />);
  const row = (await screen.findByText("Doos")).closest("li")!;
  await user.click(within(row).getByText("equipmentSimple.more"));
  expect(within(row).queryByText("cargo.archive")).not.toBeInTheDocument();
  await user.click(within(row).getByRole("button", { name: "cargo.copyModel" }));
  const dialog = screen.getByRole("dialog");
  await user.click(within(dialog).getByRole("button", { name: "cargo.save" }));
  await waitFor(() => expect(create).toHaveBeenCalledOnce());
  expect(update).not.toHaveBeenCalled();
  expect(create).toHaveBeenCalledWith(expect.objectContaining({ name: "Doos", language_labels: builtin.language_labels }));
});

it("archives and restores the same reviewed version without disturbing packaging already used in shipments", async () => {
  const archive = vi.spyOn(cargoApi, "archiveTemplate").mockResolvedValue({ ...own, active: false, version: 3 });
  const update = vi.spyOn(cargoApi, "updateTemplate").mockResolvedValue({ ...own, active: true, version: 4 });
  const user = userEvent.setup(); render(<CargoTemplateLibrary user={manager} />);
  const row = (await screen.findByText("Our crate")).closest("li")!;
  await user.click(within(row).getByText("equipmentSimple.more"));
  await user.click(within(row).getByRole("button", { name: "cargo.archive" }));
  await waitFor(() => expect(archive).toHaveBeenCalledWith(own));
  await user.click(screen.getByRole("button", { name: "cargo.undo" }));
  await waitFor(() => expect(update).toHaveBeenCalledWith({ ...own, active: true, version: 3 }));
  expect(await screen.findByText("Our crate")).toBeVisible();
});
