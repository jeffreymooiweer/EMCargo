/** The user's work and the assessment must refer to the same load at every step. */
import { StrictMode } from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, expect, it, vi } from "vitest";
import TripsPage from "./TripsPage";
import { ToastProvider } from "../toast/ToastProvider";
import type { TripIn } from "../api/client";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string, args?: Record<string, unknown>) => key + (args?.name ? ` ${args.name}` : ""), i18n: { language: "nl" } }) }));
const settings = { history_enabled: true };
vi.mock("../settings/preferences", () => ({ usePreferences: () => ({ publicSettings: settings }) }));
const api = vi.hoisted(() => ({ trips: vi.fn(), trip: vi.fn(), shipments: vi.fn(), shipment: vi.fn(), dgTrip: vi.fn(), keepTrip: vi.fn(), updateTrip: vi.fn(), forgetTrip: vi.fn(), departments: vi.fn() }));
vi.mock("../api/client", () => ({ api }));
const goods = [{ products: [{ un_number: "1203", class: "3", transport_category: "2", adr_total_quantity: "100" }] }];
const shipment = (id: number, dg = true) => ({ id, reference: `S${id}`, modality: "road", consignor_name: "Wezep", consignee_name: "Oirschot", has_dangerous_goods: dg, regulations: ["ADR"],
  export: { format: "emcargo.shipment", consignment: { reference: `S${id}`, consignor_name: "Wezep", consignee_name: "Oirschot" },
    ...(dg ? { dangerous_goods: goods, regulations: ["ADR"] } : { goods: [{ include: true, dangerous_goods: false, detected_un_numbers: [] }] }) } });
const verdict = (total = 300) => ({ consignments: [{ name: "S7", points: total, exempt: total <= 1000, status: total > 1000 ? "above_threshold" : "exempt_possible" }], adr_points: { total_points: total, threshold: 1000, status: total > 1000 ? "above_threshold" : "exempt_possible" }, mixed_loading: [], lq_eq: { warnings: [] }, lq_marking: { message: "LQ details", lq_gross_kg: 0, required: false, reason: "within_8t_dispensation" }, exemption_lost: null });
const saved = (id = 3) => ({ id, name: id === 3 ? "Monday" : "Tuesday", language: "nl", regulations: ["ADR"], unit_max_mass_tonnes: 18, consignment_count: 1, total_points: 300, exemption_lost: false,
  created_at: "2026-09-05T08:00:00Z", updated_at: "2026-09-05T08:00:00Z", consignments: [{ name: "S7", entries: goods, shipment_id: 7 }], result: verdict(), editions: { adr: "2025" } });
function renderPage(path = "/trips", strict = false) {
  const tree = <ToastProvider><MemoryRouter initialEntries={[path]}><Routes><Route path="/trips" element={<TripsPage />} /></Routes></MemoryRouter></ToastProvider>;
  return render(strict ? <StrictMode>{tree}</StrictMode> : tree);
}
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(r => { resolve = r; }); return { promise, resolve }; }

beforeEach(() => {
  vi.clearAllMocks(); settings.history_enabled = true;
  api.trips.mockResolvedValue({ items: [saved(), saved(4)], total: 2 }); api.trip.mockImplementation(async id => saved(id));
  api.shipments.mockResolvedValue({ items: [shipment(7), shipment(8, false)], total: 2 }); api.shipment.mockImplementation(async id => shipment(id, id !== 8));
  api.dgTrip.mockResolvedValue(verdict()); api.forgetTrip.mockResolvedValue({ ok: true }); api.departments.mockResolvedValue([]);
  api.keepTrip.mockImplementation(async (payload: TripIn) => ({ ...saved(), ...payload, unit_max_mass_tonnes: payload.unit_max_mass_tonnes, regulations: payload.profiles, result: verdict() }));
  api.updateTrip.mockImplementation(async (id: number, payload: TripIn) => ({ ...saved(id), ...payload, regulations: payload.profiles, result: verdict() }));
});

it("adds ordinary and DG shipments in place, and checks without an extra action", async () => {
  renderPage(); await userEvent.click(screen.getByRole("button", { name: "tripWorkspace.add" }));
  await userEvent.click(await screen.findByRole("button", { name: "tripWorkspace.add S7" }));
  expect(await screen.findByRole("button", { name: "tripWorkspace.added S7" })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: "tripWorkspace.add S8" }));
  await waitFor(() => expect(api.dgTrip).toHaveBeenLastCalledWith(expect.objectContaining({ consignments: [expect.objectContaining({ shipment_id: 7 }), expect.objectContaining({ shipment_id: 8, entries: [] })] })));
  expect(screen.getAllByLabelText(/groupage.consignmentName/)).toHaveLength(2);
});

it("saves a single shipment and displays the canonical server assessment", async () => {
  renderPage("/trips?shipments=7");
  await screen.findByText("tripWorkspace.assessment.complete");
  fireEvent.change(screen.getByLabelText("groupage.tripName"), { target: { value: "My route" } });
  await userEvent.click(screen.getByRole("button", { name: "tripWorkspace.save" }));
  await waitFor(() => expect(api.keepTrip).toHaveBeenCalledWith(expect.objectContaining({ name: "My route", consignments: [expect.objectContaining({ name: "S7" })] })));
  expect(await screen.findByText("tripWorkspace.saved")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "tripWorkspace.save" })).toBeDisabled();
});

it("opens a stored snapshot directly and survives React StrictMode", async () => {
  renderPage("/trips?trip=3", true);
  expect(await screen.findByDisplayValue("Monday")).toBeInTheDocument();
  expect(await screen.findByText("tripWorkspace.snapshot")).toBeInTheDocument();
  expect(api.dgTrip).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("groupage.tripName"), { target: { value: "Renamed" } });
  await userEvent.click(screen.getByRole("button", { name: "tripWorkspace.save" }));
  await waitFor(() => expect(api.updateTrip).toHaveBeenCalledWith(3, expect.objectContaining({ name: "Renamed" })));
  expect(api.keepTrip).not.toHaveBeenCalled();
});

it("invalidates the displayed result immediately and ignores late responses", async () => {
  const first = deferred<ReturnType<typeof verdict>>();
  api.dgTrip.mockReturnValueOnce(first.promise).mockResolvedValue(verdict(1200));
  renderPage("/trips?trip=3"); await screen.findByDisplayValue("Monday");
  fireEvent.change(screen.getByLabelText("groupage.unitMass"), { target: { value: "20" } });
  expect(screen.queryByText("tripWorkspace.assessment.complete")).toBeNull();
  expect(screen.getByRole("button", { name: "tripWorkspace.save" })).toBeDisabled();
  await waitFor(() => expect(api.dgTrip).toHaveBeenCalledTimes(1));
  fireEvent.change(screen.getByLabelText("groupage.unitMass"), { target: { value: "21" } });
  await screen.findByText("tripWorkspace.assessment.attention");
  first.resolve(verdict(5));
  await waitFor(() => expect(screen.queryByText("tripWorkspace.assessment.complete")).toBeNull());
  expect(screen.getByText("1.200")).toBeInTheDocument();
});

it("accepts decimal commas and refuses invalid vehicle mass without sending it", async () => {
  renderPage("/trips?trip=3"); await screen.findByDisplayValue("Monday");
  fireEvent.change(screen.getByLabelText("groupage.unitMass"), { target: { value: "12,5" } });
  await waitFor(() => expect(api.dgTrip).toHaveBeenLastCalledWith(expect.objectContaining({ unit_max_mass_tonnes: 12.5 })));
  fireEvent.change(screen.getByLabelText("groupage.unitMass"), { target: { value: "-5" } });
  expect(screen.getByText("tripWorkspace.assessment.invalidMass")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "tripWorkspace.save" })).toBeDisabled();
  expect(api.dgTrip).toHaveBeenCalledTimes(1);
});

it("keeps vehicle details and focus after correcting an invalid mass", async () => {
  renderPage("/trips?trip=3"); await screen.findByDisplayValue("Monday");
  await userEvent.click(screen.getByText("tripWorkspace.vehicle"));
  const input = screen.getByLabelText("groupage.unitMass");
  await userEvent.clear(input);
  await userEvent.type(input, "-5");
  expect(input).toHaveAttribute("aria-invalid", "true");
  await userEvent.clear(input);
  await userEvent.type(input, "19");
  expect(input).toHaveValue("19");
  expect(input.closest("details")).toHaveAttribute("open");
  expect(input).toHaveFocus();
  await waitFor(() => expect(api.dgTrip).toHaveBeenLastCalledWith(expect.objectContaining({ unit_max_mass_tonnes: 19 })));
  expect(input.closest("details")).toHaveAttribute("open");
});

it("keeps edits after a failed save and permits retry", async () => {
  api.updateTrip.mockRejectedValueOnce(new Error("offline"));
  renderPage("/trips?trip=3"); await screen.findByDisplayValue("Monday");
  fireEvent.change(screen.getByLabelText("groupage.tripName"), { target: { value: "Keep my work" } });
  await userEvent.click(screen.getByRole("button", { name: "tripWorkspace.save" }));
  expect(await screen.findByText("tripWorkspace.saveFailed")).toBeInTheDocument();
  expect(screen.getByLabelText("groupage.tripName")).toHaveValue("Keep my work");
  expect(screen.queryByText("tripWorkspace.saved")).toBeNull();
  await userEvent.click(screen.getByRole("button", { name: "tripWorkspace.save" }));
  expect(await screen.findByText("tripWorkspace.saved")).toBeInTheDocument();
});

it("warns before changing trips and preserves the draft when cancelled", async () => {
  renderPage("/trips?trip=3"); await screen.findByDisplayValue("Monday");
  fireEvent.change(screen.getByLabelText("groupage.tripName"), { target: { value: "Work in progress" } });
  await userEvent.click(screen.getByRole("button", { name: /Tuesday/ }));
  expect(screen.getByRole("alertdialog")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "toast.cancel" }));
  expect(screen.getByLabelText("groupage.tripName")).toHaveValue("Work in progress");
  await userEvent.click(screen.getByRole("button", { name: /Tuesday/ }));
  await userEvent.click(screen.getByRole("button", { name: "tripWorkspace.discard" }));
  expect(await screen.findByDisplayValue("Tuesday")).toBeInTheDocument();
});

it("deletes only after confirmation and does not delete source shipments", async () => {
  renderPage("/trips?trip=3"); await screen.findByDisplayValue("Monday");
  await userEvent.click(screen.getByRole("button", { name: "trips.remove" }));
  expect(api.forgetTrip).not.toHaveBeenCalled();
  await userEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "trips.remove" }));
  await waitFor(() => expect(api.forgetTrip).toHaveBeenCalledWith(3));
  expect(await screen.findByText("tripWorkspace.start")).toBeInTheDocument();
});

it("still permits file checks without retaining shipments or trips", async () => {
  settings.history_enabled = false; renderPage();
  expect(screen.getByText("tripWorkspace.noStorage")).toBeInTheDocument();
  const file = new File([JSON.stringify(shipment(8, false).export)], "general.json", { type: "application/json" });
  await userEvent.upload(screen.getByLabelText("tripWorkspace.import"), file);
  expect(await screen.findByText("tripWorkspace.assessment.neutral")).toBeInTheDocument();
  expect(api.trips).not.toHaveBeenCalled(); expect(api.shipments).not.toHaveBeenCalled(); expect(api.keepTrip).not.toHaveBeenCalled();
  expect(screen.queryByRole("button", { name: "tripWorkspace.save" })).toBeNull();
});

it("deduplicates files and rejects an export with missing DG data", async () => {
  renderPage();
  const file = new File([JSON.stringify(shipment(7).export)], "dg.json", { type: "application/json" });
  await userEvent.upload(screen.getByLabelText("tripWorkspace.import"), [file, file]);
  expect(screen.getAllByLabelText(/groupage.consignmentName/)).toHaveLength(1);
  const incomplete = { ...shipment(7).export, dangerous_goods: undefined };
  await userEvent.upload(screen.getByLabelText("tripWorkspace.import"), new File([JSON.stringify(incomplete)], "invalid.json", { type: "application/json" }));
  expect(await screen.findByText("tripWorkspace.importFailed")).toBeInTheDocument();
  expect(screen.getAllByLabelText(/groupage.consignmentName/)).toHaveLength(1);
});

it("distinguishes unavailable shipment results from an empty list and retries", async () => {
  api.shipments.mockRejectedValueOnce(new Error("offline")); renderPage();
  await userEvent.click(screen.getByRole("button", { name: "tripWorkspace.add" }));
  await screen.findByText("tripWorkspace.shipmentsFailed");
  expect(screen.queryByText("tripWorkspace.noShipments")).toBeNull();
  await userEvent.click(screen.getByRole("button", { name: "tripWorkspace.retry" }));
  expect(await screen.findByRole("button", { name: "tripWorkspace.add S7" })).toBeInTheDocument();
});

it("does not silently omit an inaccessible shipment from an incoming selection", async () => {
  api.shipment.mockImplementation(async id => { if (id === 8) throw new Error("not found"); return shipment(id); });
  renderPage("/trips?shipments=7,8");
  expect(await screen.findByText("tripWorkspace.someMissing")).toBeInTheDocument();
  expect(screen.getAllByLabelText(/groupage.consignmentName/)).toHaveLength(1);
});

it("sends complete local day bounds when filtering saved trips", async () => {
  renderPage(); await screen.findByRole("button", { name: /Monday/ });
  fireEvent.change(screen.getByLabelText("history.from"), { target: { value: "2026-10-25" } });
  fireEvent.change(screen.getByLabelText("history.to"), { target: { value: "2026-10-25" } });
  await waitFor(() => expect(api.trips).toHaveBeenLastCalledWith(expect.objectContaining({ date_from: new Date(2026, 9, 25, 0).toISOString(), date_to: new Date(2026, 9, 25, 23, 59, 59, 999).toISOString().replace(".999Z", ".999999Z") })));
});

it("distinguishes a newly calculated assessment from the saved snapshot", async () => {
  renderPage("/trips?trip=3"); await screen.findByDisplayValue("Monday");
  expect(screen.getByText("tripWorkspace.saved")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "tripWorkspace.recheck" }));
  await screen.findByText("tripWorkspace.assessment.complete");
  expect(screen.getByText("tripWorkspace.unsaved")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "tripWorkspace.save" })).toBeEnabled();
});

it("does not leave a success verdict on screen after a failed recalculation", async () => {
  api.dgTrip.mockRejectedValueOnce(new Error("offline"));
  renderPage("/trips?trip=3"); await screen.findByDisplayValue("Monday");
  fireEvent.change(screen.getByLabelText("groupage.unitMass"), { target: { value: "19" } });
  await screen.findByText("tripWorkspace.assessment.failed");
  expect(screen.queryByText("tripWorkspace.assessment.complete")).toBeNull();
  expect(screen.getByRole("button", { name: "tripWorkspace.save" })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: "tripWorkspace.recheck" }));
  expect(await screen.findByText("tripWorkspace.assessment.complete")).toBeInTheDocument();
});
