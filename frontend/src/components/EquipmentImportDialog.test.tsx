/**
 * A visible import action replaces instructions about toolbar icons. A rejected
 * upload must remain retryable, partial imports must expose their row failures,
 * and closing while a mutation is pending must not encourage a duplicate import.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import EquipmentImportDialog from "./EquipmentImportDialog";

const api = vi.hoisted(() => ({ importEquipmentFile: vi.fn(), downloadEquipmentTemplate: vi.fn() }));
vi.mock("../api/client", () => ({ api, translateMessage: (message: { message: string }) => message.message }));
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
vi.mock("../toast/ToastProvider", () => ({ useToast: () => ({ success: vi.fn() }) }));

// jsdom does not implement the native dialog lifecycle.
Object.defineProperty(HTMLDialogElement.prototype, "showModal", { configurable: true, writable: true, value() { this.setAttribute("open", ""); } });
Object.defineProperty(HTMLDialogElement.prototype, "close", { configurable: true, writable: true, value() { this.removeAttribute("open"); } });

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(HTMLDialogElement.prototype, "showModal").mockImplementation(function (this: HTMLDialogElement) { this.setAttribute("open", ""); });
  vi.spyOn(HTMLDialogElement.prototype, "close").mockImplementation(function (this: HTMLDialogElement) { this.removeAttribute("open"); });
});
afterEach(() => vi.restoreAllMocks());
const file = () => new File(["specifications,weight_kg\nCrate,42"], "equipment.csv", { type: "text/csv" });

it("keeps failed uploads visible and allows the same file to be retried", async () => {
  const onClose = vi.fn(); const onComplete = vi.fn();
  api.importEquipmentFile.mockRejectedValueOnce(new Error("Connection unavailable"))
    .mockResolvedValueOnce({ created: 1, updated: 0, skipped: 0, errors: [] });
  render(<EquipmentImportDialog open onClose={onClose} onComplete={onComplete} />);
  expect(screen.getByRole("button", { name: "import.chooseFile" })).toBeVisible();
  await userEvent.upload(screen.getByLabelText("import.chooseFile"), file());
  expect(await screen.findByRole("alert")).toHaveTextContent("Connection unavailable");
  expect(onClose).not.toHaveBeenCalled();
  await userEvent.upload(screen.getByLabelText("import.chooseFile"), file());
  await waitFor(() => expect(onComplete).toHaveBeenCalledOnce());
  expect(api.importEquipmentFile).toHaveBeenCalledTimes(2);
  expect(onClose).toHaveBeenCalledOnce();
});

it("keeps partial import errors on screen instead of dismissing the report", async () => {
  api.importEquipmentFile.mockResolvedValue({ created: 1, updated: 0, skipped: 1, errors: [{ code: "import.row", message: "Row 3: weight is missing" }] });
  const onClose = vi.fn(); const onComplete = vi.fn();
  render(<EquipmentImportDialog open onClose={onClose} onComplete={onComplete} />);
  await userEvent.upload(screen.getByLabelText("import.chooseFile"), file());
  expect(await screen.findByRole("alert")).toHaveTextContent("Row 3: weight is missing");
  expect(onComplete).toHaveBeenCalledOnce();
  expect(onClose).not.toHaveBeenCalled();
});

it("prevents dismissal and a second upload while the import is pending", async () => {
  let finish!: (value: { created: number; updated: number; skipped: number; errors: never[] }) => void;
  api.importEquipmentFile.mockReturnValue(new Promise(resolve => { finish = resolve; }));
  const onClose = vi.fn();
  render(<EquipmentImportDialog open onClose={onClose} onComplete={vi.fn()} />);
  await userEvent.upload(screen.getByLabelText("import.chooseFile"), file());
  expect(screen.getByRole("button", { name: "import.importingFile" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "assets.close" })).toBeDisabled();
  fireEvent(screen.getByRole("dialog"), new Event("cancel", { bubbles: true, cancelable: true }));
  expect(onClose).not.toHaveBeenCalled();
  expect(api.importEquipmentFile).toHaveBeenCalledOnce();
  finish({ created: 1, updated: 0, skipped: 0, errors: [] });
  await waitFor(() => expect(onClose).toHaveBeenCalledOnce());
});
