/** Restore reads must survive effect cleanup and must finish before autosave. */
import { StrictMode } from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AssistantState, DgEntry, DocumentRegistry, ShipmentDetail } from "../api/client";
import type { DraftLine } from "../components/ReviewLinesPanel";
import type { CargoManifest } from "../api/cargo";
import type { CargoWorkspaceProps } from "../components/cargo/CargoWorkspace";
import { unpackCargo } from "../utils/cargo";
import WizardPage from "./WizardPage";

const mocks = vi.hoisted(() => ({
  api: {
    documentsRegistry: vi.fn(), shipments: vi.fn(), shipment: vi.fn(), runningDraft: vi.fn(),
    saveDraft: vi.fn(), calculate: vi.fn(), updateShipment: vi.fn(), keepShipment: vi.fn(),
  },
  cargoApi: { assess: vi.fn(), reusableUnits: vi.fn() },
  cargoProps: null as CargoWorkspaceProps | null,
  assistantProps: null as null | { onApplyState: (state: AssistantState) => void; buildState: () => AssistantState },
  toast: { info: vi.fn(), error: vi.fn(), success: vi.fn() },
  settings: { history_enabled: true },
  preferences: { prefill_documents: false, consignor_name: "", default_unit: "pcs" },
}));
vi.mock("../api/client", () => ({ api: mocks.api }));
vi.mock("../api/cargo", () => ({ cargoApi: mocks.cargoApi }));
vi.mock("../components/cargo/CargoWorkspace", () => ({ default: (props: CargoWorkspaceProps) => {
  mocks.cargoProps = props;
  return <pre aria-label="Cargo manifest">{JSON.stringify(props.value)}</pre>;
} }));
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
  modalities: [{ key: "road", documents: [] }, { key: "rail", documents: [] }, { key: "sea", documents: [] }],
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
    <Route path="/" element={<p>Transport mode selection</p>} />
    <Route path="/wizard/:modality" element={<WizardPage />} />
  </Routes></MemoryRouter>;
  return render(strict ? <StrictMode>{app}</StrictMode> : app);
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
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
  mocks.api.keepShipment.mockResolvedValue({ id: 42, cargo_revision: 10, updated_at: "2026-09-17T10:00:00Z" });
  mocks.cargoProps = null;
  mocks.cargoApi.reusableUnits.mockResolvedValue([]);
  mocks.cargoApi.assess.mockImplementation(async (cargo: CargoManifest) => ({ cargo, units: [], loose: [], issues: [],
    totals: { goods_kg: 50, packaging_kg: 1, cargo_gross_kg: 51, transport_tare_kg: 0,
      transport_gross_kg: 51, occupied_volume_m3: null, complete: true } }));
  mocks.api.calculate.mockImplementation(() => new Promise(() => {}));
});
afterEach(() => { vi.useRealTimers(); });

describe("shipment restoration", () => {
  // Restoring only the tile would still strand bookmarks and saved sea
  // shipments at the wizard's own availability guard. Exercise that guard
  // with the actual wizard and verify that saved inputs reach the editor.
  it("opens a direct sea wizard URL", async () => {
    open("/wizard/sea");
    expect(await screen.findByLabelText("Goods description")).toBeInTheDocument();
    expect(screen.queryByText("Transport mode selection")).not.toBeInTheDocument();
    expect(mocks.api.runningDraft).toHaveBeenCalled();
  });

  it("reopens an existing sea shipment with its saved goods and reference", async () => {
    mocks.api.shipment.mockResolvedValue(saved("Saved sea cargo", "sea"));
    open("/wizard/sea?shipment=42");
    expect(await screen.findByLabelText("Goods description")).toHaveValue("Saved sea cargo");
    expect(screen.getByLabelText("wizard.referenceLabel")).toHaveValue("SAVED-42");
    expect(mocks.api.runningDraft).not.toHaveBeenCalled();
  });

  it.each(["air", "multimodal"])("keeps an unreleased %s wizard URL closed", async modality => {
    open(`/wizard/${modality}`);
    expect(await screen.findByText("Transport mode selection")).toBeInTheDocument();
    expect(screen.queryByLabelText("Goods description")).not.toBeInTheDocument();
  });

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
      line_overrides: [{ line_id: 1, cargo_goods_id: 1, ...override }],
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

const PACKAGE_ID = "f53bd26f-fcdc-4e44-9b74-446f71edced8";
const SHIPMENT_CARGO_ID = "3b98a64e-dafe-4840-8e04-149554bb78ed";
const ALLOCATION_ID = "dc9bd290-1e3d-4555-9f64-226a89c264df";

function packedShipment(stepKey = "lines"): ShipmentDetail {
  const cargo: CargoManifest = {
    schema_version: 1, shipment_id: SHIPMENT_CARGO_ID, revision: 3,
    units: [{ id: PACKAGE_ID, code: "BOX-145", name: "Mixed box", category: "box", kind: "package", parent_id: null, tare_kg: 1 }],
    allocations: [{ id: ALLOCATION_ID, goods_id: 7, unit_id: PACKAGE_ID, quantity: 2 }],
  };
  return {
    ...saved(), cargo_revision: 9,
    snapshot: {
      ...saved().snapshot, version: 2, cargo, cargoBaseRevision: 2, stepKey, nextId: 8,
      draftLines: [{ id: 7, description: "Packed bolts", quantity: 2, unit: "pcs", weight_total_kg: 50 }],
      result: {
        success: true,
        lines: [{ line_id: 1, cargo_goods_id: 7, description: "Packed bolts", quantity: 2,
          unit: "pcs", include: true, status: "ok", weight_total_kg: 50, weight_each_kg: 25,
          messages: [], detected_un_numbers: [] }],
        totals: { line_count: 1, included_count: 1, total_quantity: 2, total_weight_kg: 50,
          total_material_volume_m3: 0, total_transport_volume_m3: 0, warning_count: 0, error_count: 0 },
      },
    },
  };
}

/** Cargo uses stable draft IDs; calculation row positions and a locally stored
 * revision must not replace the authoritative saved revision during autosave. */
it("restores cargo identities and serializes autosaves against the latest saved revision", async () => {
  vi.useFakeTimers();
  mocks.api.runningDraft.mockResolvedValue(packedShipment());
  mocks.api.saveDraft.mockResolvedValue({ id: 42, cargo_revision: 10, updated_at: "2026-09-17T10:00:00Z" });
  open();
  await act(async () => { await vi.advanceTimersByTimeAsync(0); });
  await act(async () => { await vi.advanceTimersByTimeAsync(2700); });
  const first = mocks.api.saveDraft.mock.lastCall![0];
  expect(first.expected_cargo_revision).toBe(9);
  expect(first.cargo).toMatchObject({ shipment_id: SHIPMENT_CARGO_ID, units: [{ id: PACKAGE_ID }],
    allocations: [{ id: ALLOCATION_ID, goods_id: 7, unit_id: PACKAGE_ID }] });
  expect(first.lines[0]).toMatchObject({ line_id: 1, cargo_goods_id: 7 });
  expect(first.snapshot.cargo).toEqual(first.cargo);
  fireEvent.change(screen.getByLabelText("wizard.referenceLabel"), { target: { value: "SECOND-SAVE" } });
  await act(async () => { await vi.advanceTimersByTimeAsync(2600); });
  expect(mocks.api.saveDraft.mock.lastCall![0]).toMatchObject({ expected_cargo_revision: 10,
    cargo: { shipment_id: SHIPMENT_CARGO_ID, units: [{ id: PACKAGE_ID }] } });
});

/** The guided intake can replace goods too. It must not bypass the normal
 * deletion guard and leave a box referencing goods that no longer exist. */
it("rejects an assistant deletion of allocated goods before changing the shipment", async () => {
  mocks.api.runningDraft.mockResolvedValue(packedShipment());
  open(); await screen.findByLabelText("Goods description");
  await act(async () => mocks.assistantProps!.onApplyState({ draft_lines: [], dg_entries: [], doc_values: {} }));
  expect(mocks.assistantProps!.buildState().draft_lines).toEqual(expect.arrayContaining([
    expect.objectContaining({ id: 7, description: "Packed bolts" }),
  ]));
  expect(mocks.assistantProps!.buildState().doc_values?.shipment_reference).toBe("SAVED-42");
  expect(mocks.toast.error).toHaveBeenCalledWith("cargoIntegration.assignedGoods");
});

/** Legacy containers existed as goods lines carrying tare. Unpacking removes
 * the carrier from this shipment, and undo restores its identity without a
 * second copy of its empty mass or dangling original container references. */
it("unpacks and restores a migrated container without turning its tare into loose goods", async () => {
  vi.useFakeTimers();
  const legacy = saved("Container");
  legacy.snapshot = { ...legacy.snapshot, nextId: 9, draftLines: [
    { id: 3, description: "Container", quantity: 1, unit: "pcs", equipment_role: "container", weight_total_kg: 2000,
      equipment: { equipment_id: 8, version: 1, kind: "container", specifications: "Container", weight_kg: 2000, container_number: "TEST1234567" } },
    { id: 7, description: "Steel", quantity: 2, unit: "pcs", weight_total_kg: 50, container_line_id: 3 },
  ] };
  mocks.api.runningDraft.mockResolvedValue(legacy);
  open(); await act(async () => { await vi.advanceTimersByTimeAsync(0); });
  fireEvent.click(screen.getByRole("button", { name: /^cargoIntegration.cargo/ }));
  const before = structuredClone(mocks.cargoProps!.value);
  const carrier = before.units[0];
  await act(async () => mocks.cargoProps!.onChange(unpackCargo(before, mocks.cargoProps!.goods, [carrier.id])));
  await act(async () => { await vi.advanceTimersByTimeAsync(2600); });
  const unpacked = mocks.api.saveDraft.mock.lastCall![0];
  expect(unpacked.cargo.units).toEqual([]);
  expect(unpacked.lines.filter((line: { equipment_role?: string }) => line.equipment_role === "container")).toEqual([]);
  expect(unpacked.lines.map((line: { weight_total_kg: number }) => line.weight_total_kg)).toEqual([50]);
  expect(unpacked.snapshot.draftLines.every((line: DraftLine) => line.container_line_id == null)).toBe(true);
  await act(async () => mocks.cargoProps!.onChange({ ...before, revision: mocks.cargoProps!.value.revision + 1 }));
  await act(async () => { await vi.advanceTimersByTimeAsync(2600); });
  const restored = mocks.api.saveDraft.mock.lastCall![0];
  expect(restored.cargo.units).toEqual(expect.arrayContaining([expect.objectContaining({ id: carrier.id })]));
  expect(restored.cargo.allocations).toEqual(before.allocations);
  const restoredCarrier = restored.cargo.units.find((unit: { id: string }) => unit.id === carrier.id);
  const carrierLines = restored.lines.filter((line: { equipment_role?: string }) => line.equipment_role === "container");
  expect(carrierLines).toHaveLength(restoredCarrier.legacy_goods_id == null ? 0 : 1);
});

/** A failed network autosave used to poison pendingDraft forever, so the
 * explicit save could not recover even after the connection returned. */
it("allows an explicit save after an earlier autosave failed", async () => {
  vi.useFakeTimers();
  mocks.api.runningDraft.mockResolvedValue(packedShipment("export"));
  mocks.api.saveDraft.mockRejectedValueOnce(new Error("offline"));
  mocks.api.updateShipment.mockResolvedValue({ id: 42, cargo_revision: 10, updated_at: "2026-09-17T10:00:00Z" });
  open(); await act(async () => { await vi.advanceTimersByTimeAsync(0); });
  await act(async () => { await vi.advanceTimersByTimeAsync(2700); });
  expect(mocks.api.saveDraft).toHaveBeenCalledTimes(1);
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "history.keep" })); });
  expect(mocks.api.updateShipment).toHaveBeenCalledWith(42, expect.objectContaining({ draft: false, expected_cargo_revision: 9 }));
  expect(screen.getByTestId("history-status")).toHaveTextContent("history.keptAt");
});

/** Final save must cancel an autosave timer that has not fired and await an
 * in-flight one. A late draft write must never hide a published shipment. */
it("waits for pending autosave before publication and prevents later draft writes", async () => {
  vi.useFakeTimers();
  const pending = deferred<{ id: number; cargo_revision: number; updated_at: string }>();
  mocks.api.runningDraft.mockResolvedValue(packedShipment("export"));
  mocks.api.saveDraft.mockReturnValueOnce(pending.promise);
  mocks.api.updateShipment.mockResolvedValue({ id: 42, cargo_revision: 11, updated_at: "2026-09-17T10:00:00Z" });
  open(); await act(async () => { await vi.advanceTimersByTimeAsync(0); });
  await act(async () => { await vi.advanceTimersByTimeAsync(2700); });
  expect(mocks.api.saveDraft).toHaveBeenCalledTimes(1);
  fireEvent.change(screen.getByLabelText("wizard.referenceLabel"), { target: { value: "READY-42" } });
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "history.keep" })); });
  expect(mocks.api.updateShipment).not.toHaveBeenCalled();
  await act(async () => pending.resolve({ id: 42, cargo_revision: 10, updated_at: "2026-09-17T10:00:00Z" }));
  expect(mocks.api.updateShipment).toHaveBeenCalledWith(42, expect.objectContaining({ draft: false, expected_cargo_revision: 10,
    values: expect.objectContaining({ shipment_reference: "READY-42" }) }));
  await act(async () => { await vi.advanceTimersByTimeAsync(6000); });
  expect(mocks.api.saveDraft).toHaveBeenCalledTimes(1);
});

/** Switching modality while editing a retained shipment must not turn it into
 * a fresh draft with the same physical unit IDs or lose its revision guard. */
it("keeps the saved shipment and cargo identity when carrying edits to another modality", async () => {
  const shipment = packedShipment("export");
  mocks.api.shipment.mockResolvedValue(shipment);
  mocks.api.calculate.mockResolvedValue(shipment.snapshot.result);
  open("/wizard/road?shipment=42");
  await screen.findByRole("button", { name: "history.update" });
  fireEvent.change(screen.getByRole("combobox", { name: "wizard.mode" }), { target: { value: "rail" } });
  expect(await screen.findByLabelText("Goods description")).toHaveValue("Packed bolts");
  fireEvent.change(screen.getByLabelText("wizard.referenceLabel"), { target: { value: "CARRIED-42" } });
  fireEvent.click(screen.getByRole("button", { name: "review.continueTo" }));
  fireEvent.click(await screen.findByRole("button", { name: "history.update" }));
  await waitFor(() => expect(mocks.api.updateShipment).toHaveBeenCalledWith(42, expect.objectContaining({
    modality: "rail", draft: false, expected_cargo_revision: 9,
    cargo: expect.objectContaining({ shipment_id: SHIPMENT_CARGO_ID, units: [expect.objectContaining({ id: PACKAGE_ID })] }),
    values: expect.objectContaining({ shipment_reference: "CARRIED-42" }),
  })));
  expect(mocks.api.saveDraft).not.toHaveBeenCalled();
  expect(mocks.api.keepShipment).not.toHaveBeenCalled();
});
