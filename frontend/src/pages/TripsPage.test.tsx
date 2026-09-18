/** Legacy calculations stay read-only; conversion never fabricates quantities. */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, expect, it, vi } from "vitest";
import TripsPage from "./TripsPage";
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key, i18n: { language: "nl" } }) }));
const settings = { history_enabled: true };
vi.mock("../settings/preferences", () => ({ usePreferences: () => ({ publicSettings: settings }) }));
const api = vi.hoisted(() => ({ trips: vi.fn(), trip: vi.fn(), departments: vi.fn(), dgTrip: vi.fn(), updateTrip: vi.fn() }));
const deliveries = vi.hoisted(() => ({ convert: vi.fn() }));
vi.mock("../api/client", () => ({ api }));
vi.mock("../api/deliveries", () => ({ deliveries }));
const saved = { id: 3, name: "Monday", updated_at: "2026-09-05T08:00:00Z", consignments: [{ name: "S7", entries: [] }], result: { adr_points: { total_points: 0, threshold: 1000, status: "exempt_possible" }, mixed_loading: [], lq_eq: { warnings: [] } }, editions: { adr: "2025" } };
function show(path = "/trips?trip=3") {
  return render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/trips" element={<TripsPage />} /><Route path="/deliveries/:id" element={<p>New concept</p>} /></Routes></MemoryRouter>);
}
beforeEach(() => {
  vi.clearAllMocks(); settings.history_enabled = true;
  api.trips.mockResolvedValue({ items: [saved], total: 1 }); api.trip.mockResolvedValue(saved); api.departments.mockResolvedValue([]);
  deliveries.convert.mockResolvedValue({ id: "new-concept" });
});
it("shows the stored calculation without editing or recalculation controls", async () => {
  show(); expect(await screen.findByRole("heading", { name: "Monday" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "tripWorkspace.recheck" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "tripWorkspace.save" })).not.toBeInTheDocument();
  expect(api.dgTrip).not.toHaveBeenCalled(); expect(api.updateTrip).not.toHaveBeenCalled();
});
it("converts explicitly and opens the new concept", async () => {
  show(); await userEvent.click(await screen.findByRole("button", { name: "deliveries.convertLegacy" }));
  expect(deliveries.convert).toHaveBeenCalledWith(3);
  expect(await screen.findByText("New concept")).toBeInTheDocument();
});
it("keeps the source visible if conversion fails", async () => {
  deliveries.convert.mockRejectedValue(new Error("Conversion refused")); show();
  await userEvent.click(await screen.findByRole("button", { name: "deliveries.convertLegacy" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Conversion refused");
  expect(screen.getByRole("heading", { name: "Monday" })).toBeInTheDocument();
});
it("does not read retained trips when history is disabled", () => {
  settings.history_enabled = false; show();
  expect(screen.getByText("deliveries.noHistory")).toBeInTheDocument();
  expect(api.trip).not.toHaveBeenCalled(); expect(api.trips).not.toHaveBeenCalled();
});
