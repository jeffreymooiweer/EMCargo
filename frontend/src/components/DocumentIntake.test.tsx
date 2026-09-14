/** A document becomes editable proposals before it can replace shipment data. */
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import type { AssistantState, PackingGood, PackingSource } from "../api/client";
import DocumentIntake, { applyPackingProposal, documentChunks } from "./DocumentIntake";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key, i18n: { language: "nl" } }) }));
const api = vi.hoisted(() => ({ unitCatalogue: vi.fn(), readPackingDocument: vi.fn(), proposePackingDocument: vi.fn() }));
vi.mock("../api/client", () => ({ api }));
const source: PackingSource = { name: "packing.pdf", sha256: "a".repeat(64), pages: [{ number: 1, method: "text", preview: "data:image/jpeg;base64,AA==", warnings: [], lines: [{ id: "p1l1", text: "Boxes of bolts 12 boxes 240 kg", confidence: null }] }] };
const good: PackingGood = { description: "Boxes of bolts", quantity: 12, unit: "box", weight_kg: 240, weight_basis: "unknown", dimensions: "", source_ids: ["p1l1"], excerpt: source.pages[0].lines[0].text };
const existing: AssistantState = { modality: "road", draft_lines: [{ id: 1, description: "Existing pump", quantity: 2, unit: "pcs" }], doc_values: { consignee_name: "Existing receiver" } };
const fact = { key: "consignee_name", value: "New receiver", source_ids: ["p1l1"], excerpt: "New receiver" };
const proposal = { goods: [good], fields: [fact], warnings: [] };
function row(update = {}) { return { ...good, picked: true, count: "12", mass: "240", length: "", width: "", height: "", ...update }; }
beforeEach(() => { vi.clearAllMocks(); api.unitCatalogue.mockResolvedValue({ units: [{ code: "box" }, { code: "pcs" }] }); api.readPackingDocument.mockResolvedValue(source); api.proposePackingDocument.mockResolvedValue(proposal); });
async function upload() { fireEvent.change(screen.getByLabelText("intake.choose"), { target: { files: [new File(["pdf"], "packing.pdf", { type: "application/pdf" })] } }); await screen.findByRole("button", { name: "intake.accept" }); }

it("requires an explicit mass basis and preserves the original state and unchecked values", () => {
  expect(() => applyPackingProposal(existing, source, [row()], [])).toThrow("intake.checkValues");
  const accepted = applyPackingProposal(existing, source, [row({ weight_basis: "total" })], [{ ...fact, picked: false }]);
  expect(existing.draft_lines).toHaveLength(1);
  expect(accepted.draft_lines).toHaveLength(2);
  expect(accepted.draft_lines?.[1]).toMatchObject({ id: 2, quantity: 12, stated_weight_kg: 240, weight_each_kg: 20, weight_total_kg: 240 });
  expect(accepted.doc_values?.consignee_name).toBe("Existing receiver");
  expect(accepted.document_evidence?.[0]).toMatchObject({ name: "packing.pdf", pages: [1], target: "goods:2", method: "text" });
});

it("keeps missing quantities unresolved and accepts decimal commas without defaulting counts", () => {
  const accepted = applyPackingProposal(existing, source, [row({ count: "", mass: "2,5", weight_basis: "each" })], []);
  expect(accepted.draft_lines?.[1]).toMatchObject({ quantity: undefined, quantity_unconfirmed: true, stated_weight_kg: 2.5 });
  expect(() => applyPackingProposal(existing, source, [row({ count: "0", mass: "" })], [])).toThrow("intake.checkValues");
  expect(() => applyPackingProposal(existing, source, [row({ length: "120", mass: "" })], [])).toThrow("intake.checkValues");
});

it("does not apply anything until the user reviews and accepts the proposal", async () => {
  const onAccept = vi.fn().mockResolvedValue(true);
  render(<DocumentIntake state={existing} language="nl" onAccept={onAccept} onCancel={vi.fn()} />);
  await upload();
  expect(onAccept).not.toHaveBeenCalled();
  expect(screen.getByRole("checkbox", { name: "intake.field.consignee_name" })).not.toBeChecked();
  await userEvent.click(screen.getByRole("button", { name: "intake.accept" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("intake.checkValues");
  expect(onAccept).not.toHaveBeenCalled();
  await userEvent.selectOptions(screen.getByRole("combobox", { name: "intake.weightBasis" }), "total");
  await userEvent.click(screen.getByRole("button", { name: "intake.accept" }));
  await waitFor(() => expect(onAccept).toHaveBeenCalledOnce());
  expect(onAccept.mock.calls[0][0].doc_values.consignee_name).toBe("Existing receiver");
});

it("retains source text after a model failure so it can be corrected and retried", async () => {
  api.proposePackingDocument.mockRejectedValueOnce(new Error("model unavailable"));
  render(<DocumentIntake state={existing} language="nl" onAccept={vi.fn()} onCancel={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("intake.choose"), { target: { files: [new File(["pdf"], "packing.pdf")] } });
  expect(await screen.findByRole("alert")).toHaveTextContent("model unavailable");
  expect(screen.getByText("packing.pdf")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("intake.recognisedText"), { target: { value: "Boxes of bolts 13 boxes 240 kg" } });
  await userEvent.click(screen.getByRole("button", { name: "intake.prepare" }));
  await screen.findByRole("button", { name: "intake.accept" });
  expect(api.proposePackingDocument).toHaveBeenLastCalledWith([{ id: "p1l1", text: "Boxes of bolts 13 boxes 240 kg" }], expect.any(AbortSignal));
});

it("aborts reading and ignores late replies when the intake is closed", async () => {
  let resolve!: (value: PackingSource) => void;
  api.readPackingDocument.mockReturnValue(new Promise(done => { resolve = done; }));
  const onAccept = vi.fn();
  const view = render(<DocumentIntake state={existing} language="nl" onAccept={onAccept} onCancel={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("intake.choose"), { target: { files: [new File(["pdf"], "packing.pdf")] } });
  const signal = api.readPackingDocument.mock.calls[0][2] as AbortSignal;
  view.unmount();
  expect(signal.aborted).toBe(true);
  await act(async () => resolve(source));
  expect(api.proposePackingDocument).not.toHaveBeenCalled(); expect(onAccept).not.toHaveBeenCalled();
});

it("does not allow cancellation or repeated acceptance during the final apply", async () => {
  let resolve!: (value: boolean) => void;
  const onAccept = vi.fn().mockReturnValue(new Promise(done => { resolve = done; }));
  render(<DocumentIntake state={existing} language="nl" onAccept={onAccept} onCancel={vi.fn()} />);
  await upload(); await userEvent.selectOptions(screen.getByRole("combobox", { name: "intake.weightBasis" }), "total");
  await userEvent.click(screen.getByRole("button", { name: "intake.accept" }));
  expect(screen.getByRole("button", { name: "intake.cancel" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "intake.accept" })).toBeDisabled();
  await act(async () => resolve(false));
  expect(await screen.findByRole("alert")).toHaveTextContent("intake.applyFailed");
});

it("chunks every source line in order and rejects text that would exceed the supported bounds", () => {
  const lines = Array.from({ length: 80 }, (_, i) => ({ id: `p1l${i + 1}`, text: `Line ${i}`, confidence: null }));
  const chunks = documentChunks({ ...source, pages: [{ ...source.pages[0], lines }] });
  expect(chunks.flat()).toEqual(lines.map(({ id, text }) => ({ id, text })));
  expect(() => documentChunks({ ...source, pages: [{ ...source.pages[0], lines: [{ id: "p1l1", text: "x".repeat(6000), confidence: null }] }] })).toThrow("intake.longLine");
});
