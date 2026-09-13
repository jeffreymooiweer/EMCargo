/** Restore reads must survive effect cleanup and must finish before autosave. */
import { StrictMode } from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AssistantState, DgEntry, DocumentRegistry, ShipmentDetail } from "../api/client";
import type { DraftLine } from "../components/ReviewLinesPanel";
import WizardPage from "./WizardPage";

const mocks = vi.hoisted(() => ({
  api: {
    documentsRegistry: vi.fn(), shipments: vi.fn(), shipment: vi.fn(), runningDraft: vi.fn(),
    saveDraft: vi.fn(), calculate: vi.fn(), updateShipment: vi.fn(),
  },
  assistantProps: null as null | { onApplyState: (state: AssistantState) => void; buildState: () => AssistantState },
  toast: { info: vi.fn(), error: vi.fn(), success: vi.fn() },
  settings: { history_enabled: true },
  preferences: { prefill_documents: false, consignor_name: "", default_unit: "pcs" },
}));
vi.mock("../api/client", () => ({ api: mocks.api }));
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key, i18n: { language: "nl" } }) }));
vi.mock("../settings/preferences", () => ({
  usePreferences: () => ({ preferences: mocks.preferences, publicSettings: mocks.settings, loaded: true }),
}));
vi.mock("../toast/ToastProvider", () => ({ useToast: () => mocks.toast }));
vi.mock("../components/AssistantModal", () => ({ default: (props: NonNullable<typeof mocks.assistantProps>) => { mocks.assistantProps = props; return null; } }));
vi.mock("../components/DangerousGoodsStep", async original => ({
  ...await original<typeof import("../components/DangerousGoodsStep")>(),
  default: ({ entries }: { entries: DgEntry[] }) => <pre aria-label="DG answers">{JSON.stringify(entries)}</pre>,
}));
vi.mock("../components/ReviewLinesPanel", async (original) => ({
  ...await original<typeof import("../components/ReviewLinesPanel")>(),
  default: ({ draftLines, onDraftChange, onLineWeightChange }: { draftLines: DraftLine[]; onDraftChange: (lines: DraftLine[]) => void; onLineWeightChange?: (id: number, field: "weight_total_kg", value: number) => void }) => (<>
    <input aria-label="Goods description" value={draftLines[0]?.description ?? ""}
      onChange={(event) => onDraftChange([{ ...draftLines[0], description: event.target.value }])} />
    <button onClick={() => onLineWeightChange?.(1, "weight_total_kg", 37.25)}>Enter weight</button>
    <button onClick={() => onDraftChange([{ ...draftLines[0], length_cm: 120 }])}>Change length</button>
  </>),
}));

const registry = {
  modalities: [{ key: "road", documents: [] }, { key: "rail", documents: [] }],
  documents: [], shared_sections: [],
} as unknown as DocumentRegistry;

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function saved(description = "Saved goods", modality = "road"): ShipmentDetail {
  return {
    id: 42, reference: "SAVED-42", updated_at: "2026-09-08T10:00:00Z", modality,
    snapshot: {
      version: 1, modality, stepKey: "lines", nextId: 2,
      draftLines: [{ id: 1, description, quantity: 1, unit: "pcs" }],
      docValues: { consignor_name: "Saved company", shipment_reference: "SAVED-42" },
      result: null, dgEntries: [], selectedDocs: null, skippedQuestions: [], signature: null,
    },
  } as unknown as ShipmentDetail;
}

function open(path = "/wizard/road", strict = true) {
  const app = <MemoryRouter initialEntries={[path]}><Routes>
    <Route path="/wizard/:modality" element={<WizardPage />} />
  </Routes></MemoryRouter>;
  return render(strict ? <StrictMode>{app}</StrictMode> : app);
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  mocks.settings.history_enabled = true;
  mocks.preferences.prefill_documents = false;
  mocks.preferences.consignor_name = "";
  mocks.api.documentsRegistry.mockResolvedValue(registry);
  mocks.api.shipments.mockResolvedValue({ items: [] });
  mocks.api.runningDraft.mockResolvedValue(null);
  mocks.api.shipment.mockResolvedValue(saved());
  mocks.api.saveDraft.mockResolvedValue({ id: 42, updated_at: "2026-09-08T10:00:00Z" });
  mocks.api.updateShipment.mockResolvedValue({ id: 42, updated_at: "2026-09-13T10:00:00Z" });
  mocks.api.calculate.mockImplementation(() => new Promise(() => {}));
});
afterEach(() => { vi.useRealTimers(); });

describe("shipment restoration", () => {
  it("keeps an entered total weight when dimensions change", async () => {
    mocks.api.runningDraft.mockResolvedValue(saved());
    mocks.api.calculate.mockResolvedValue({ success: true, lines: [{ line_id: 1, description: "Saved goods",
      quantity: 1, unit: "pcs", include: true, status: "ok", weight_total_kg: 50,
      weight_each_kg: 50, messages: [], detected_un_numbers: [] }], totals: {} });
    open();
    await screen.findByLabelText("Goods description");
    await waitFor(() => expect(mocks.api.calculate).toHaveBeenCalled());
    fireEvent.click(screen.getByText("Enter weight"));
    fireEvent.click(screen.getByText("Change length"));
    await waitFor(() => expect(mocks.api.calculate).toHaveBeenLastCalledWith(expect.objectContaining({
      line_overrides: [expect.objectContaining({ line_id: 1, length_m: 1.2, weight_total_kg: 37.25 })],
    })));
  });

  // Saved results round per-piece and total weights separately. Sending both
  // back made the backend multiply the rounded piece value and change a
  // shipment merely by reopening it. Older manual corrections must survive
  // too: their snapshots do not distinguish computed and entered weights.
  it.each([
    { each: 18.62, total: 37.25, override: { weight_total_kg: 37.25 } },
    { each: 20.56, total: 41.13, override: { weight_total_kg: 41.13 } },
    { each: 12.5, total: null, override: { weight_each_kg: 12.5 } },
  ])("preserves the authoritative saved weight when recalculating $total kg", async ({ each, total, override }) => {
    const shipment = saved("Benzine 25L");
    shipment.snapshot = {
      ...shipment.snapshot,
      draftLines: [{ id: 1, description: "Benzine 25L", quantity: 2, unit: "pcs" }],
      result: {
        lines: [{ line_id: 1, description: "Benzine 25L", quantity: 2, unit: "pcs",
          include: true, status: "ok", weight_each_kg: each, weight_total_kg: total,
          messages: [], detected_un_numbers: [] }],
        totals: { line_count: 1, included_count: 1, total_quantity: 2, total_weight_kg: total,
          total_material_volume_m3: 0, total_transport_volume_m3: 0, warning_count: 0, error_count: 0 },
      },
    };
    mocks.api.runningDraft.mockResolvedValue(shipment);
    open();
    await screen.findByLabelText("Goods description");
    await waitFor(() => expect(mocks.api.calculate).toHaveBeenCalledWith(expect.objectContaining({
      line_overrides: [{ line_id: 1, ...override }],
    })));
  });

  it("restores a running draft once under StrictMode", async () => {
    const draft = deferred<ShipmentDetail | null>();
    mocks.api.runningDraft.mockReturnValue(draft.promise);
    open();
    await waitFor(() => expect(mocks.api.runningDraft).toHaveBeenCalled());
    expect(screen.queryByLabelText("Goods description")).toBeNull();
    await act(async () => draft.resolve(saved()));
    expect(await screen.findByLabelText("Goods description")).toHaveValue("Saved goods");
    expect(mocks.toast.info).toHaveBeenCalledTimes(1);
    expect(mocks.toast.info).toHaveBeenCalledWith("draft.resumed");
  });

  it.each(["shipment", "template"])("restores a %s when the registry changes during its pending read", async (source) => {
    const firstRegistry = deferred<DocumentRegistry>();
    const secondRegistry = deferred<DocumentRegistry>();
    const record = deferred<ShipmentDetail>();
    mocks.api.documentsRegistry.mockReturnValueOnce(firstRegistry.promise).mockReturnValueOnce(secondRegistry.promise);
    mocks.api.shipment.mockReturnValue(record.promise);
    open(`/wizard/road?${source}=42`);
    await act(async () => firstRegistry.resolve(registry));
    await waitFor(() => expect(mocks.api.shipment).toHaveBeenCalled());
    await act(async () => secondRegistry.resolve({ ...registry }));
    await act(async () => record.resolve(saved()));
    expect(await screen.findByLabelText("Goods description")).toHaveValue("Saved goods");
    expect(screen.getByLabelText("wizard.referenceLabel")).toHaveValue(source === "template" ? "" : "SAVED-42");
    expect(mocks.api.runningDraft).not.toHaveBeenCalled();
    if (source === "template") {
      expect(mocks.toast.info).toHaveBeenCalledTimes(1);
      expect(mocks.toast.info).toHaveBeenCalledWith("history.templateOpened");
    }
  });

  it("does not reapply a saved shipment over edits when a late registry response arrives", async () => {
    const firstRegistry = deferred<DocumentRegistry>();
    const secondRegistry = deferred<DocumentRegistry>();
    mocks.api.documentsRegistry.mockReturnValueOnce(firstRegistry.promise).mockReturnValueOnce(secondRegistry.promise);
    open("/wizard/road?shipment=42");
    await act(async () => firstRegistry.resolve(registry));
    const input = await screen.findByLabelText("Goods description");
    fireEvent.change(input, { target: { value: "Edited goods" } });
    await act(async () => secondRegistry.resolve({ ...registry }));
    expect(input).toHaveValue("Edited goods");
    expect(mocks.api.shipment).toHaveBeenCalledTimes(1);
  });

  it("keeps a slow or failed draft read ahead of prefilled autosave and offers retry", async () => {
    vi.useFakeTimers();
    const draft = deferred<ShipmentDetail | null>();
    mocks.preferences.prefill_documents = true;
    mocks.preferences.consignor_name = "Default company";
    mocks.api.runningDraft.mockReturnValueOnce(draft.promise).mockResolvedValueOnce(saved());
    open();
    await act(async () => { await vi.advanceTimersByTimeAsync(3500); });
    expect(mocks.api.saveDraft).not.toHaveBeenCalled();
    expect(screen.queryByLabelText("Goods description")).toBeNull();
    await act(async () => draft.reject(new Error("offline")));
    expect(screen.getByRole("alert")).toHaveTextContent("history.loadFailed");
    await act(async () => { await vi.advanceTimersByTimeAsync(3500); });
    expect(mocks.api.saveDraft).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "overview.retry" }));
    await act(async () => { await vi.advanceTimersByTimeAsync(0); });
    expect(screen.getByLabelText("Goods description")).toHaveValue("Saved goods");
    await act(async () => { await vi.advanceTimersByTimeAsync(2600); });
    expect(mocks.api.saveDraft).toHaveBeenCalledWith(expect.objectContaining({
      snapshot: expect.objectContaining({ docValues: expect.objectContaining({ consignor_name: "Saved company" }) }),
    }));
  });

  it("carries edits through a modality change without reading the old server draft again", async () => {
    mocks.api.runningDraft.mockResolvedValue(saved());
    open();
    const input = await screen.findByLabelText("Goods description");
    fireEvent.change(input, { target: { value: "Changed before switching" } });
    fireEvent.change(screen.getByLabelText("wizard.referenceLabel"), { target: { value: "RAIL-2026-001" } });
    fireEvent.change(screen.getByRole("combobox", { name: "wizard.mode" }), { target: { value: "rail" } });
    expect(await screen.findByLabelText("Goods description")).toHaveValue("Changed before switching");
    expect(screen.getByRole("combobox", { name: "wizard.mode" })).toHaveValue("rail");
    expect(screen.getByLabelText("wizard.referenceLabel")).toHaveValue("RAIL-2026-001");
    expect(mocks.api.runningDraft).toHaveBeenCalledTimes(1);
  });

  it("never reads or autosaves drafts where history is disabled", async () => {
    vi.useFakeTimers();
    mocks.settings.history_enabled = false;
    mocks.preferences.prefill_documents = true;
    mocks.preferences.consignor_name = "Default company";
    open();
    await act(async () => { await vi.advanceTimersByTimeAsync(3500); });
    expect(screen.getByLabelText("Goods description")).toBeInTheDocument();
    expect(mocks.api.runningDraft).not.toHaveBeenCalled();
    expect(mocks.api.saveDraft).not.toHaveBeenCalled();
  });
});

/** Shipments were listed as having no reference while the only editor was
 * buried among optional document fields. A new shipment must expose it before
 * any document is selected, and autosave must restore that same reference. */
it('enters a reference on the first step and restores it from the saved draft', async () => {
  vi.useFakeTimers();
  const view = open();
  await act(async () => { await vi.advanceTimersByTimeAsync(0); });
  const reference = screen.getByRole('textbox', { name: 'wizard.referenceLabel' });
  expect(reference.closest('header')).not.toBeNull();
  expect(reference).not.toBeRequired();
  expect(reference).toHaveAttribute('maxlength', '120');
  fireEvent.change(reference, { target: { value: '  ORDER-2026-001  ' } });
  fireEvent.blur(reference);
  expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('ORDER-2026-001');
  await act(async () => { await vi.advanceTimersByTimeAsync(2600); });
  const payload = mocks.api.saveDraft.mock.lastCall![0];
  expect(payload.values.shipment_reference).toBe('ORDER-2026-001');
  expect(payload.snapshot.docValues.shipment_reference).toBe('ORDER-2026-001');
  expect(payload.documents).toEqual([]);
  view.unmount();
  mocks.api.runningDraft.mockResolvedValue({ ...saved(), snapshot: payload.snapshot });
  open();
  await act(async () => { await vi.advanceTimersByTimeAsync(0); });
  expect(screen.getByRole('textbox', { name: 'wizard.referenceLabel' })).toHaveValue('ORDER-2026-001');
});

/** The pencil on a saved shipment can reopen the export step directly. Adding
 * a reference there must update that shipment's index values and its snapshot,
 * without making a duplicate or requiring a return to optional questions. */
it('adds a reference to an existing shipment on the export step', async () => {
  const calculation = { success: true, lines: [{ line_id: 1, description: 'Saved goods', quantity: 1,
    unit: 'pcs', include: true, status: 'ok', weight_total_kg: 50, weight_each_kg: 50,
    messages: [], detected_un_numbers: [] }], totals: { line_count: 1, included_count: 1,
    total_quantity: 1, total_weight_kg: 50, total_material_volume_m3: 0,
    total_transport_volume_m3: 0, warning_count: 0, error_count: 0 } };
  mocks.api.calculate.mockResolvedValue(calculation);
  const shipment = saved();
  shipment.snapshot = { ...shipment.snapshot, stepKey: 'export', result: calculation,
    docValues: { consignor_name: 'Saved company' } };
  mocks.api.shipment.mockResolvedValue(shipment);
  open('/wizard/road?shipment=42');
  const reference = await screen.findByRole('textbox', { name: 'wizard.referenceLabel' });
  expect(reference).toHaveValue('');
  fireEvent.change(reference, { target: { value: 'ORDER-42' } });
  fireEvent.click(screen.getByRole('button', { name: 'history.update' }));
  await waitFor(() => expect(mocks.api.updateShipment).toHaveBeenCalledWith(42, expect.objectContaining({
    values: expect.objectContaining({ shipment_reference: 'ORDER-42' }),
    snapshot: expect.objectContaining({ docValues: expect.objectContaining({ shipment_reference: 'ORDER-42' }) }),
  })));
});

/** Older snapshots use reference instead of shipment_reference. An intentional
 * clear must clear both aliases, or the history index resurrects the old name. */
it('shows and clears a legacy reference without letting it reappear', async () => {
  vi.useFakeTimers();
  const draft = saved();
  draft.snapshot = { ...draft.snapshot, docValues: { reference: 'LEGACY-42' } };
  mocks.api.runningDraft.mockResolvedValue(draft);
  open();
  await act(async () => { await vi.advanceTimersByTimeAsync(0); });
  const reference = screen.getByLabelText('wizard.referenceLabel');
  expect(reference).toHaveValue('LEGACY-42');
  fireEvent.change(reference, { target: { value: '' } });
  await act(async () => { await vi.advanceTimersByTimeAsync(2600); });
  expect(reference).toHaveValue('');
  expect(mocks.api.saveDraft.mock.lastCall![0].values).toMatchObject({ shipment_reference: '', reference: '' });
});


it("carries assistant DG answers through calculation and into the DG step", async () => {
  mocks.api.calculate.mockResolvedValue({ success: true, lines: [{ line_id: 1, description: "diesel", quantity: 20,
    unit: "jerrycan", include: true, dangerous_goods: true, detected_un_numbers: ["1202"], messages: [],
    status: "ok", weight_each_kg: 20, weight_total_kg: 400 }], totals: { total_weight_kg: 400 } });
  open(); await screen.findByLabelText("Goods description");
  await act(async () => mocks.assistantProps!.onApplyState({ modality: "road",
    draft_lines: [{ id: 7, description: "diesel", quantity: 20, unit: "jerrycan", confirmed_un: "1202", dangerous_goods: true }],
    dg_entries: [{ line_id: 7, vehicle: "diesel", products: [{ un_number: "1202", carriage_mode: "packages", type_of_package: "3A1", net_mass_liters_per_package: "25 L" }] }],
    doc_values: { consignor_name: "Test company" },
  }));
  await waitFor(() => expect(mocks.api.calculate).toHaveBeenCalled());
  expect(mocks.assistantProps!.buildState().dg_entries?.[0].products[0].type_of_package).toBe("3A1");
  fireEvent.click(screen.getByRole("button", { name: "review.continueTo" }));
  const entries = JSON.parse((await screen.findByLabelText("DG answers")).textContent!);
  expect(entries[0].line_id).toBe(1);
  expect(entries[0].products[0]).toMatchObject({ carriage_mode: "packages", type_of_package: "3A1", net_mass_liters_per_package: "25 L" });
});

it("undoing the assistant intake also clears document values in the actual wizard", async () => {
  open(); await screen.findByLabelText("Goods description");
  await act(async () => mocks.assistantProps!.onApplyState({ draft_lines: [{ id: 1, description: "Test goods", quantity: 1, unit: "pcs" }], dg_entries: [], doc_values: { consignor_name: "Test company" } }));
  await act(async () => mocks.assistantProps!.onApplyState({ draft_lines: [], dg_entries: [], doc_values: {} }));
  expect(mocks.assistantProps!.buildState().draft_lines).toEqual([]);
  expect(mocks.assistantProps!.buildState().doc_values).toEqual({});
});

it("recalculates assistant weight changes made on the details step", async () => {
  // The visible novice test changed 48 to 52 kg after leaving the goods step;
  // the old effect only recalculated on that step and left export data stale.
  const shipment = saved("bureaustoelen");
  shipment.snapshot = { ...shipment.snapshot, stepKey: "details" };
  mocks.api.runningDraft.mockResolvedValue(shipment);
  open();
  await waitFor(() => expect(mocks.assistantProps).not.toBeNull());
  await waitFor(() => expect(mocks.assistantProps!.buildState().doc_values?.consignor_name).toBe("Saved company"));
  expect(screen.queryByLabelText("Goods description")).toBeNull();
  await act(async () => mocks.assistantProps!.onApplyState({ modality: "road", draft_lines: [
    { id: 1, description: "bureaustoelen", quantity: 4, unit: "pcs", weight_each_kg: 13,
      weight_total_kg: 52, stated_weight_kg: 52, weight_basis: "total" },
  ] }));
  await waitFor(() => expect(mocks.api.calculate).toHaveBeenCalledWith(expect.objectContaining({
    text: "bureaustoelen | 4 | pcs",
    line_overrides: [expect.objectContaining({ line_id: 1, weight_each_kg: 13 })],
  })));
});
