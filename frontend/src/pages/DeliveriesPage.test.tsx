/** Receipt failures must preserve input and restricted accounts must stay scoped. */
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, expect, it, vi } from "vitest";
import DeliveriesPage from "./DeliveriesPage";
import { type Delivery, newLeg } from "../api/deliveries";
import type { User } from "../api/client";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key, i18n: { language: "nl" } }) }));
vi.mock("../settings/preferences", () => ({ usePreferences: () => ({ publicSettings: { history_enabled: true } }) }));
vi.mock("../api/cargo", () => ({ cargoApi: { reusableUnits: () => Promise.resolve([]) } }));
vi.mock("../components/SignaturePad", () => ({ default: () => null }));
vi.mock("../components/DeliveryActivity", () => ({ default: () => null }));
vi.mock("../components/DeliveryDocumentDetails", () => ({ default: () => null }));
const api = vi.hoisted(() => ({ shipments: vi.fn(), documentsRegistry: vi.fn() }));
vi.mock("../api/client", () => ({ api }));
const calls = vi.hoisted(() => ({ get: vi.fn(), event: vi.fn(), source: vi.fn(), balances: vi.fn(), save: vi.fn(), assessment: vi.fn(), unload: vi.fn() }));
vi.mock("../api/deliveries", async original => ({ ...await original<typeof import("../api/deliveries")>(), deliveries: calls }));
const user = { id: 1, role: "user" } as User;
function record(): Delivery {
  return { id: "delivery", name: "Warehouse delivery", version: 3, status: "released", legs: [{ ...newLeg(), id: "leg", status: "released" }],
    allocations: [{ id: "allocation", shipment_id: 7, goods_id: "0", quantity: "10", leg_ids: ["leg"] }],
    sources: { "7": { reference: "S7", goods: [{ id: "0", description: "Steel bolts" }] } },
    can_plan: true, can_review: false, assignments: [], events: [], files: [] };
}
function show(path = "/deliveries/delivery", account = user) {
  render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/deliveries/:id" element={<DeliveriesPage user={account} />} /></Routes></MemoryRouter>);
}
beforeEach(() => {
  vi.clearAllMocks(); calls.get.mockResolvedValue(record()); api.shipments.mockResolvedValue({ items: [] });
  calls.source.mockResolvedValue({ reference: "S7", goods: [{ delivery_goods_id: "0", quantity: 10, description: "Steel bolts" }],
    routing: { version: 1, locations: [{ id: "p", kind: "pickup", name: "Warehouse", address: "A", country: "NL", contact: "" }, { id: "r", kind: "delivery", name: "Receiver", address: "B", country: "NL", contact: "" }], distributions: [{ id: "dist", goods_id: "0", quantity: "10", pickup_id: "p", delivery_id: "r", unit_ids: [] }] },
    distributions: [{ id: "dist", goods_id: "0", quantity: "10", available: "3", pickup_id: "p", delivery_id: "r", unit_ids: [] }] });
  calls.balances.mockResolvedValue({ goods: [{ id: "0", quantity: "10", available: "3" }], deliveries: [] });
});
it("uses the remaining source quantity and preserves a zero goods identifier", async () => {
  show("/deliveries/new?shipments=7");
  expect(await screen.findByLabelText("deliveries.quantity S7 · Steel bolts → Receiver")).toHaveValue("3");
});
it("keeps failed receipt values and the same request id for a safe retry", async () => {
  calls.event.mockRejectedValue(new Error("Connection interrupted")); show();
  await userEvent.click(await screen.findByRole("button", { name: "deliveries.execution" }));
  await userEvent.type(screen.getByLabelText("deliveries.recipient"), "Test receiver");
  const goods = within(screen.getByRole("group", { name: "S7 · Steel bolts (10)" }));
  await userEvent.type(goods.getByLabelText("deliveries.quantity"), "4");
  await userEvent.click(screen.getByRole("button", { name: "deliveries.receipt" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Connection interrupted");
  expect(goods.getByLabelText("deliveries.quantity")).toHaveValue("4");
  const first = calls.event.mock.calls[0][2];
  await userEvent.click(screen.getByRole("button", { name: "deliveries.receipt" }));
  await waitFor(() => expect(calls.event).toHaveBeenCalledTimes(2));
  expect(calls.event.mock.calls[1][2].request_id).toBe(first.request_id);
  expect(first.lines[0]).toEqual({ allocation_id: "allocation", quantity: "4", damaged: "0", refused: "0" });
});
it("disables ordinary loading and receipt after completion", async () => {
  const completed = record(); completed.status = "completed"; completed.legs[0].status = "completed";
  calls.get.mockResolvedValue(completed); show();
  await userEvent.click(await screen.findByRole("button", { name: "deliveries.execution" }));
  fireEvent.change(screen.getByLabelText("deliveries.recipient"), { target: { value: "Receiver" } });
  expect(screen.getByRole("button", { name: "deliveries.load" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "deliveries.receipt" })).toBeDisabled();
});
it("opens an assigned recipient directly in execution without shipment browsing", async () => {
  const scoped = record(); scoped.can_plan = false;
  scoped.assignments = [{ id: "grant", role: "recipient", leg_id: "leg", shipment_ids: [7] }];
  calls.get.mockResolvedValue(scoped); show(undefined, { id: 4, role: "recipient" } as User);
  expect(await screen.findByRole("button", { name: "deliveries.receipt" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "deliveries.load" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "deliveries.checks" })).not.toBeInTheDocument();
  expect(api.shipments).not.toHaveBeenCalled();
});
it("links a pending follow-up from the original receipt history", async () => {
  const linked = record(); linked.events = [{ request_id: "event", leg_id: "leg", kind: "resolution", occurred_at: "2026-09-17T10:00:00Z", recipient: "Planner", reason: "Arrange return", lines: [], resolution: "return", followup_id: "return-draft", followup_complete: false }];
  calls.get.mockResolvedValue(linked); show();
  await userEvent.click(await screen.findByRole("button", { name: "deliveries.history" }));
  expect(screen.getByRole("link", { name: "deliveries.returnDelivery" })).toHaveAttribute("href", "/deliveries/return-draft");
  expect(screen.getByText(/deliveries.followupPending/)).toBeInTheDocument();
});

it("takes the source distribution route automatically and protects its leg selection", async () => {
  show("/deliveries/new?shipments=7");
  expect(await screen.findByLabelText("deliveries.quantity S7 · Steel bolts → Receiver")).toHaveValue("3");
  expect(screen.getByLabelText("deliveries.origin")).toHaveValue("Warehouse, A, NL");
  expect(screen.getByLabelText("deliveries.destination")).toHaveValue("Receiver, B, NL");
  expect(screen.getByRole("checkbox", { name: "1. deliveries.modes.road" })).toBeDisabled();
});

it("keeps derived return quantities fixed while permitting transport planning", async () => {
  const child = record(); child.status = "draft"; child.legs[0].status = "draft"; child.followup = { parent_id: "original", kind: "return" };
  calls.get.mockResolvedValue(child); show();
  expect(await screen.findByLabelText("deliveries.quantity S7 · Steel bolts")).toBeDisabled();
  expect(screen.getByLabelText("deliveries.origin")).toBeEnabled();
  expect(screen.queryByRole("button", { name: /deliveries.addLeg/ })).not.toBeInTheDocument();
});


it("offers intermediate receipt to an operator with a filtered itinerary", async () => {
  const scoped = record(); scoped.can_plan = false;
  scoped.assignments = [{ id: "grant", role: "operator", leg_id: "leg", shipment_ids: [7], allocation_ids: ["allocation"] }];
  scoped.allocations[0].receivable_leg_ids = ["leg"];
  calls.get.mockResolvedValue(scoped); show(undefined, { id: 3, role: "operator" } as User);
  expect(await screen.findByRole("button", { name: "deliveries.receipt" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "deliveries.load" })).toBeInTheDocument();
});
