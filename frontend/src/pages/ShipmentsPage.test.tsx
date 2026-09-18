/**
 * The shipments page: what it lists, what it says when there is nothing to
 * list, and the one action that must ask first.
 */
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ShipmentSummary } from "../api/client";
import ShipmentsPage, { wizardLinkFor } from "./ShipmentsPage";
import { ToastProvider } from "../toast/ToastProvider";
import { createCargoUnit, emptyCargo } from "../utils/cargo";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options && "count" in options ? `${key}:${options.count}/${options.total}` : key,
    i18n: { language: "nl" },
  }),
}));

const settings = { history_enabled: true };
vi.mock("../settings/preferences", () => ({
  usePreferences: () => ({ publicSettings: settings, preferences: {}, loaded: true, mode: "organisation" }),
}));

const kept: ShipmentSummary[] = [
  {
    id: 7, reference: "CP-2026-100", modality: "road", language: "nl", regulations: ["ADR"],
    consignor_name: "Afzender BV", consignee_name: "Ontvanger GmbH", goods_count: 3,
    has_dangerous_goods: true, has_documents: true, work_status: "ready", created_by: "ada",
    created_at: "2026-09-05T08:00:00Z", updated_at: "2026-09-05T08:00:00Z",
  },
  {
    id: 8, reference: "", modality: "sea", language: "en", regulations: [],
    consignor_name: "Afzender BV", consignee_name: "", goods_count: 1,
    has_dangerous_goods: false, has_documents: false, created_by: "",
    created_at: "2026-09-04T08:00:00Z", updated_at: "2026-09-04T08:00:00Z",
  },
];

const api = vi.hoisted(() => ({
  shipments: vi.fn(),
  shipment: vi.fn(),
  forgetShipment: vi.fn(),
  shipmentDocuments: vi.fn(),
  departments: vi.fn(),
  runningDraft: vi.fn(),
  shipmentExportUrl: (id: number) => `/api/shipments/${id}/export.json`,
}));
vi.mock("../api/client", () => ({ api }));

function renderAt(path: string, user?: { id: number; username: string; email: string; role: string; active: boolean }) {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/shipments" element={<ShipmentsPage user={user} />} />
          <Route path="/shipments/:id" element={<ShipmentsPage user={user} />} />
          <Route path="/wizard/:modality" element={<p>wizard</p>} />
        </Routes>
      </MemoryRouter>
    </ToastProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  settings.history_enabled = true;
  api.shipments.mockResolvedValue({ items: kept, total: 2, page: 1, per_page: 25 });
  api.shipment.mockImplementation(async (id: number) => ({
    ...kept.find((s) => s.id === id)!,
    snapshot: { version: 1 },
    export: { format: "emcargo.shipment", documents: ["cmr"] },
  }));
  api.forgetShipment.mockResolvedValue({ ok: true });
  api.departments.mockResolvedValue([{ id: 1, name: "Sales", users: 2, shipments: 5 }]);
  api.runningDraft.mockResolvedValue(null);
});

it("sends selected local shipment dates as complete UTC day bounds", async () => {
  renderAt("/shipments");
  await screen.findAllByText("CP-2026-100");
  await userEvent.click(screen.getByRole("button", { name: "history.filters" }));
  fireEvent.change(screen.getByLabelText("history.from"), { target: { value: "2026-03-29" } });
  fireEvent.change(screen.getByLabelText("history.to"), { target: { value: "2026-03-29" } });
  await waitFor(() => expect(api.shipments).toHaveBeenLastCalledWith(expect.objectContaining({
    date_from: new Date(2026, 2, 29, 0).toISOString(),
    date_to: new Date(2026, 2, 29, 23, 59, 59, 999).toISOString().replace(".999Z", ".999999Z"),
  })));
  fireEvent.change(screen.getByLabelText("history.from"), { target: { value: "" } });
  fireEvent.change(screen.getByLabelText("history.to"), { target: { value: "" } });
  await waitFor(() => expect(api.shipments).toHaveBeenLastCalledWith(expect.objectContaining({
    date_from: undefined, date_to: undefined,
  })));
});

describe("de zendingenpagina", () => {
  it("zegt dat er niets bewaard wordt waar de historie uitstaat", () => {
    settings.history_enabled = false;
    renderAt("/shipments");
    expect(screen.getByText("historyAccess.disabled")).toBeInTheDocument();
    expect(api.shipments).not.toHaveBeenCalled();
  });

  it("toont de bewaarde zendingen met referentie, partijen en een DG-badge", async () => {
    renderAt("/shipments");
    expect(await screen.findAllByText("CP-2026-100")).not.toHaveLength(0);
    expect(screen.getAllByText("Afzender BV → Ontvanger GmbH").length).toBeGreaterThan(0);
    // The one without a reference says so instead of showing an empty cell.
    expect(screen.getAllByText("history.noReference").length).toBeGreaterThan(0);
    // The regimes stand on the badge; a shipment without dangerous goods has
    // none. The phone cards and the desktop table are both in the DOM (CSS
    // shows one), so the one DG shipment carries two badges.
    expect(screen.getAllByTitle("history.dg")).toHaveLength(2);
    expect(screen.getAllByText("ADR")).toHaveLength(2);
    expect(screen.getByText("history.count:2/2")).toBeInTheDocument();
  });

  it("biedt de drie dingen die je met een bewaarde zending doet, op de regel zelf", async () => {
    // The baseline found no reuse action on the list at all: the detail page
    // was compulsory before anything could be done.
    renderAt("/shipments");
    await screen.findAllByText("CP-2026-100");
    const edit = screen.getAllByRole("link", { name: "history.edit" });
    expect(edit[0]).toHaveAttribute("href", "/wizard/road?shipment=7");
    const template = screen.getAllByRole("link", { name: "history.useTemplate" });
    expect(template[0]).toHaveAttribute("href", "/wizard/road?template=7");
    // Only the one that has a kept package is offered its documents again.
    expect(screen.getAllByRole("button", { name: "history.documents" })).toHaveLength(2);
  });

  it("zegt van elke regel wat hij is", async () => {
    renderAt("/shipments");
    await screen.findAllByText("CP-2026-100");
    // Preparation readiness comes from the source facts, not document presence.
    expect(screen.getAllByText("history.stateReady")).toHaveLength(2);
    expect(screen.getAllByText("history.stateOpen")).toHaveLength(2);
  });

  it("marks a document-free prepared shipment as ready", async () => {
    api.shipments.mockResolvedValue({ items: [{ ...kept[0], has_documents: false, work_status: "ready", modality: "" }], total: 1, page: 1, per_page: 30 });
    renderAt("/shipments");
    await screen.findAllByText("CP-2026-100");
    expect(screen.getAllByText("history.stateReady")).toHaveLength(2);
    expect(screen.queryByText("modality.")).not.toBeInTheDocument();
  });

  it("maakt van een selectie een rit", async () => {
    renderAt("/shipments");
    await screen.findAllByText("CP-2026-100");
    // Each shipment is on the page twice — as a card and as a table row, one
    // of which the width hides — and since v1.206.0 both boxes carry the same
    // name. They used to differ: the card's said only "Select", five times
    // over, with nothing saying which shipment each one selected.
    await userEvent.click(screen.getAllByLabelText("history.pick — CP-2026-100")[0]);
    await userEvent.click(screen.getAllByLabelText("history.pick — history.noReference")[0]);
    expect(screen.getByText(/history\.selectedShort:2/)).toBeInTheDocument();
    // The trip is opened with the selection in the address; the server
    // decides per shipment whether this viewer may read it.
    expect(screen.getByRole("link", { name: /history\.toDelivery:2/ })).toHaveAttribute(
      "href", "/deliveries/new?shipments=7,8");
  });

  it("zet het concept waar de gebruiker mee bezig was bovenaan", async () => {
    api.runningDraft.mockResolvedValue({
      ...kept[0], id: 12, reference: "Concept", is_draft: true,
      snapshot: {}, export: {},
    });
    renderAt("/shipments");
    expect(await screen.findByText("history.stateDraft")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "history.resumeDraft" })).toHaveAttribute(
      "href", "/wizard/road?shipment=12");
  });

  it("stuurt de zoekopdracht en de modaliteit als filters mee", async () => {
    renderAt("/shipments");
    await screen.findAllByText("CP-2026-100");
    await userEvent.click(screen.getByRole("button", { name: "history.filters" }));
    await userEvent.selectOptions(screen.getByLabelText("history.modality"), "sea");
    await waitFor(() =>
      expect(api.shipments).toHaveBeenLastCalledWith(expect.objectContaining({ modality: "sea", page: 1 })),
    );
  });

  it("opent een zending met de knoppen die erbij horen, en verwijdert pas na bevestiging", async () => {
    renderAt("/shipments/7");
    expect(await screen.findByRole("heading", { name: "CP-2026-100" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "history.open" })).toHaveAttribute("href", "/wizard/road?shipment=7");
    // A template is the same shipment opened as a new one: its own address.
    expect(screen.getByRole("link", { name: "history.useTemplate" })).toHaveAttribute("href", "/wizard/road?template=7");
    expect(screen.getByRole("button", { name: "history.documents" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "history.remove" }));
    expect(api.forgetShipment).not.toHaveBeenCalled();
    // The dialog's confirm button carries the same label as the trigger.
    const confirms = screen.getAllByRole("button", { name: "history.remove" });
    await userEvent.click(confirms[confirms.length - 1]);
    await waitFor(() => expect(api.forgetShipment).toHaveBeenCalledWith(7));
  });

  it("biedt zonder bewaard pakket geen documenten opnieuw aan", async () => {
    renderAt("/shipments/8");
    expect(await screen.findByRole("heading", { name: "history.noReference" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "history.documents" })).toBeNull();
    expect(screen.getByText("routing.documentsLater")).toBeInTheDocument();
  });

  it("geeft alleen een beheerder het afdelingsfilter, en stuurt de keuze mee", async () => {
    // Anybody else sees their own department whatever they ask for, so a
    // filter would only promise a choice the server does not offer them.
    renderAt("/shipments");
    await screen.findAllByText("CP-2026-100");
    expect(screen.queryByLabelText("departments.userDepartment")).toBeNull();
    expect(api.departments).not.toHaveBeenCalled();

    renderAt("/shipments", { id: 1, username: "root", email: "r@example.com", role: "admin", active: true });
    await userEvent.click(screen.getAllByRole("button", { name: "history.filters" })[1]);
    const filter = await screen.findByLabelText("departments.userDepartment");
    await userEvent.selectOptions(filter, "none");
    await waitFor(() =>
      expect(api.shipments).toHaveBeenLastCalledWith(expect.objectContaining({ department: "none" })),
    );
    await userEvent.selectOptions(filter, "1");
    await waitFor(() =>
      expect(api.shipments).toHaveBeenLastCalledWith(expect.objectContaining({ department: "1" })),
    );
  });

  it("opent een zending in de wizard van haar eigen modaliteit", () => {
    expect(wizardLinkFor(kept[1])).toBe("/wizard/sea?shipment=8");
  });
});

describe("compact shipment actions", () => {
  it("keeps active filters when collapsed and resets them explicitly", async () => {
    // A collapsed filter must not silently lose its value or hide the fact
    // that the list is filtered. Search stays independent of the reset.
    renderAt("/shipments");
    await screen.findAllByText("CP-2026-100");
    const filters = screen.getByRole("button", { name: "history.filters" });
    expect(filters).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByLabelText("history.modality")).not.toBeVisible();
    await userEvent.click(filters);
    await userEvent.selectOptions(screen.getByLabelText("history.modality"), "road");
    await userEvent.click(filters);
    expect(filters).toHaveAttribute("data-active", "true");
    expect(screen.getByLabelText("history.modality")).toHaveValue("road");
    await userEvent.click(filters);
    await userEvent.click(screen.getByRole("button", { name: "history.clearFilters" }));
    await waitFor(() => expect(api.shipments).toHaveBeenLastCalledWith(expect.objectContaining({ modality: "", page: 1 })));
    expect(filters).toHaveAttribute("data-active", "false");
  });

  it("removes a selected shipment directly from its card only after confirmation", async () => {
    // Deletion was missing from the list. Its replacement must name the
    // shipment, allow cancellation and remove the deleted id from the trip
    // selection without accidentally following the row's navigation.
    renderAt("/shipments");
    await screen.findAllByText("CP-2026-100");
    await userEvent.click(screen.getAllByLabelText("history.pick — CP-2026-100")[0]);
    const actions = screen.getAllByRole("group", { name: "history.actions — CP-2026-100" })[0];
    await userEvent.click(within(actions).getByRole("button", { name: "history.remove" }));
    let dialog = screen.getByRole("alertdialog");
    expect(within(dialog).getByText("CP-2026-100")).toBeInTheDocument();
    expect(api.forgetShipment).not.toHaveBeenCalled();
    expect(api.shipment).not.toHaveBeenCalled();
    await userEvent.click(within(dialog).getByRole("button", { name: "toast.cancel" }));
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(api.forgetShipment).not.toHaveBeenCalled();
    await userEvent.click(within(actions).getByRole("button", { name: "history.remove" }));
    dialog = screen.getByRole("alertdialog");
    api.shipments.mockResolvedValue({ items: [kept[1]], total: 1, page: 1, per_page: 25 });
    await userEvent.click(within(dialog).getByRole("button", { name: "history.remove" }));
    await waitFor(() => expect(api.forgetShipment).toHaveBeenCalledOnce());
    expect(api.forgetShipment).toHaveBeenCalledWith(7);
    await waitFor(() => expect(screen.queryByText("CP-2026-100")).toBeNull());
    expect(screen.queryByRole("link", { name: /history\.toDelivery/ })).toBeNull();
    expect(await screen.findByText("history.count:1/1")).toBeInTheDocument();
  });

  it("preserves the row and its selection when deleting from the desktop table fails", async () => {
    // A server-side rejection must not look like successful removal, and a
    // delete button inside a clickable table row must not open that row.
    api.forgetShipment.mockRejectedValueOnce(new Error("Deletion unavailable"));
    renderAt("/shipments");
    await screen.findAllByText("CP-2026-100");
    await userEvent.click(screen.getAllByLabelText("history.pick — CP-2026-100")[1]);
    const actions = screen.getAllByRole("group", { name: "history.actions — CP-2026-100" })[1];
    await userEvent.click(within(actions).getByRole("button", { name: "history.remove" }));
    await userEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "history.remove" }));
    expect(await screen.findByText("Error: Deletion unavailable")).toBeInTheDocument();
    expect(screen.getAllByText("CP-2026-100")).toHaveLength(2);
    expect(screen.getByRole("link", { name: /history\.toDelivery:1/ })).toHaveAttribute("href", "/deliveries/new?shipments=7");
    expect(api.shipment).not.toHaveBeenCalled();
  });

  it("returns to the previous page after deleting the final row on the last page", async () => {
    // After deletion, a valid page can cease to exist. Staying there used
    // to leave the planner looking at an empty list despite remaining data.
    const firstPage = Array.from({ length: 25 }, (_, index) => ({ ...kept[0], id: index + 20, reference: `SHIP-${index}` }));
    let deleted = false;
    api.shipments.mockImplementation(async ({ page }: { page: number }) => ({
      items: page === 1 ? firstPage : deleted ? [] : [kept[0]],
      total: deleted ? 25 : 26, page, per_page: 25,
    }));
    api.forgetShipment.mockImplementationOnce(async () => { deleted = true; return { ok: true }; });
    renderAt("/shipments");
    await screen.findAllByText("SHIP-0");
    await userEvent.click(screen.getByRole("button", { name: "history.next" }));
    await screen.findAllByText("CP-2026-100");
    const actions = screen.getAllByRole("group", { name: "history.actions — CP-2026-100" })[0];
    await userEvent.click(within(actions).getByRole("button", { name: "history.remove" }));
    await userEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "history.remove" }));
    await screen.findAllByText("SHIP-0");
    expect(api.shipments).toHaveBeenLastCalledWith(expect.objectContaining({ page: 1 }));
    expect(screen.queryByText("history.empty")).toBeNull();
  });

  it("ignores a slow response for a filter that is no longer selected", async () => {
    // Collapsible filters remain live; an older request completing later
    // must never put shipments from a different filter back on screen.
    let finishOld: (value: unknown) => void = () => {};
    api.shipments.mockImplementationOnce(() => new Promise(resolve => { finishOld = resolve; }));
    renderAt("/shipments");
    await waitFor(() => expect(api.shipments).toHaveBeenCalledOnce());
    api.shipments.mockResolvedValue({ items: [kept[1]], total: 1, page: 1, per_page: 25 });
    await userEvent.click(screen.getByRole("button", { name: "history.filters" }));
    await userEvent.selectOptions(screen.getByLabelText("history.modality"), "sea");
    await screen.findAllByText("history.noReference");
    await act(async () => finishOld({ items: [kept[0]], total: 1, page: 1, per_page: 25 }));
    expect(screen.queryByText("CP-2026-100")).toBeNull();
  });

  it("leaves the DGSA entry in DG control instead of duplicating it in shipments", async () => {
    renderAt("/shipments", { id: 1, username: "root", email: "r@example.com", role: "admin", active: true });
    await screen.findAllByText("CP-2026-100");
    expect(screen.queryByRole("link", { name: "dgsa.title" })).toBeNull();
  });

  it("refreshes the current filters when a pending deletion finishes", async () => {
    // A planner can change filters while the server is deleting a row.
    // Refreshing the delete handler's old closure would restore the previous
    // filter's data underneath the newly selected filter controls.
    let finishDelete: (value: unknown) => void = () => {};
    api.forgetShipment.mockImplementationOnce(() => new Promise(resolve => { finishDelete = resolve; }));
    renderAt("/shipments");
    await screen.findAllByText("CP-2026-100");
    await userEvent.click(screen.getAllByRole("button", { name: "history.remove" })[0]);
    await userEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "history.remove" }));
    await userEvent.click(screen.getByRole("button", { name: "history.filters" }));
    api.shipments.mockResolvedValue({ items: [kept[1]], total: 1, page: 1, per_page: 25 });
    await userEvent.selectOptions(screen.getByLabelText("history.modality"), "sea");
    await waitFor(() => expect(api.shipments).toHaveBeenLastCalledWith(expect.objectContaining({ modality: "sea" })));
    const calls = api.shipments.mock.calls.length;
    await act(async () => finishDelete({ ok: true }));
    await waitFor(() => expect(api.shipments).toHaveBeenCalledTimes(calls + 1));
    expect(api.shipments).toHaveBeenLastCalledWith(expect.objectContaining({ modality: "sea" }));
    expect(screen.queryByText("CP-2026-100")).toBeNull();
  });

  it("offers a retry instead of reporting an empty history after a load failure", async () => {
    // An unavailable server is not evidence that the installation kept no
    // shipments. The recovery action should restore the list in place.
    api.shipments.mockRejectedValueOnce(new Error("History unavailable"));
    renderAt("/shipments");
    expect(await screen.findByText("history.loadFailed")).toBeInTheDocument();
    expect(screen.queryByText("history.empty")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "history.retry" }));
    await screen.findAllByText("CP-2026-100");
    expect(screen.queryByText("history.loadFailed")).toBeNull();
  });
});

/** The shipment detail must display the canonical exported packing snapshot;
 * a stale editor snapshot must not silently replace the submitted contents. */
it("shows saved cargo from the canonical export without offering mutations", async () => {
  const box = createCargoUnit({ id: "box-model", name: "Saved mixed box", category: "box", tare_kg: 1 });
  const cargo = { ...emptyCargo(), units: [box], allocations: [{ id: "allocation-1", goods_id: 1, unit_id: box.id, quantity: 12 }] };
  api.shipment.mockResolvedValue({ ...kept[0],
    snapshot: { version: 2, cargo: { ...cargo, units: [{ ...box, name: "Stale editor box" }] } },
    export: { format: "emcargo.shipment", documents: ["cmr"], cargo, goods: [{ line_id: 1, description: "Pipe fittings", quantity: 12, unit: "pcs", include: true, weight_total_kg: 24 }] },
  });
  renderAt("/shipments/7");
  expect(await screen.findByText("Saved mixed box")).toBeVisible();
  expect(screen.queryByText("Stale editor box")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Saved mixed box/ }));
  expect(screen.getByText("Pipe fittings")).toBeVisible();
  expect(screen.queryByRole("button", { name: "cargo.newUnit" })).not.toBeInTheDocument();
});

vi.mock("../components/DeliveryActivity", () => ({ default: () => null }));
