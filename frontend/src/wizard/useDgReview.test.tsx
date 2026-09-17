import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, expect, it, vi } from "vitest";
import { useDgReview, DgReviewGate } from "./useDgReview";
import type { ShipmentIn } from "../api/client";

const api = vi.hoisted(() => ({ dgReviewStatus: vi.fn(), submitDgReview: vi.fn() }));
vi.mock("../api/client", () => ({ api }));
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
const payload = { modality: "road", language: "nl", profiles: ["ADR"], values: { reference: "DG-1" }, lines: [], dangerous_goods: [{ line_id: "1", products: [{ un_number: "1203" }] }], documents: ["cmr"], bundle: null, snapshot: { version: 1 } } as unknown as ShipmentIn;
const released = { id: "release-1", status: "approved", comment: "Checked" };
function Harness({ shipment = payload, enabled = true }: { shipment?: ShipmentIn; enabled?: boolean }) {
  const control = useDgReview(shipment, enabled, true);
  return <MemoryRouter><DgReviewGate control={control} ready /><button disabled={control.blocked}>Export</button><output>{control.id}</output></MemoryRouter>;
}
beforeEach(() => { vi.clearAllMocks(); api.dgReviewStatus.mockResolvedValue(null); api.submitDgReview.mockResolvedValue({ id: "request-1", status: "pending", comment: "" }); });

it("keeps exporting blocked through submission until the server confirms release", async () => {
  render(<Harness />);
  expect(screen.getByRole("button", { name: "Export" })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: "dgReview.submit" }));
  expect(api.submitDgReview).toHaveBeenCalledWith(payload);
  expect(screen.getByRole("button", { name: "Export" })).toBeDisabled();
  api.dgReviewStatus.mockResolvedValue(released);
  await userEvent.click(await screen.findByRole("button", { name: "dgReview.refresh" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Export" })).toBeEnabled());
});

it("invalidates a displayed approval immediately when document inputs change", async () => {
  api.dgReviewStatus.mockResolvedValue(released);
  const { rerender } = render(<Harness />);
  await waitFor(() => expect(screen.getByRole("button", { name: "Export" })).toBeEnabled());
  api.dgReviewStatus.mockResolvedValue(null);
  rerender(<Harness shipment={{ ...payload, values: { reference: "DG-2" } }} />);
  expect(screen.getByRole("button", { name: "Export" })).toBeDisabled();
  expect(screen.queryByText("release-1")).toBeNull();
});

it("does not revoke release merely because the wizard snapshot moves to another step", async () => {
  api.dgReviewStatus.mockResolvedValue(released);
  const { rerender } = render(<Harness />);
  await waitFor(() => expect(screen.getByRole("button", { name: "Export" })).toBeEnabled());
  rerender(<Harness shipment={{ ...payload, snapshot: { version: 1, stepKey: "details" } }} />);
  expect(screen.getByRole("button", { name: "Export" })).toBeEnabled();
});

it("lets the admin's disabled review policy take effect without a review request", () => {
  render(<Harness enabled={false} />);
  expect(screen.getByRole("button", { name: "Export" })).toBeEnabled();
  expect(api.dgReviewStatus).not.toHaveBeenCalled();
});

it("keeps release across save revisions but invalidates a changed cargo quantity", async () => {
  api.dgReviewStatus.mockResolvedValue(released);
  const cargo = { schema_version: 1 as const, revision: 2, shipment_id: "same-load", units: [], allocations: [{ id: "allocation", goods_id: 7, unit_id: "box", quantity: 8 }] };
  const shipment = { ...payload, cargo, expected_cargo_revision: 4 };
  const { rerender } = render(<Harness shipment={shipment} />);
  await waitFor(() => expect(screen.getByRole("button", { name: "Export" })).toBeEnabled());
  rerender(<Harness shipment={{ ...shipment, expected_cargo_revision: 5, cargo: { ...cargo, revision: 3 } }} />);
  expect(screen.getByRole("button", { name: "Export" })).toBeEnabled();
  api.dgReviewStatus.mockResolvedValue(null);
  rerender(<Harness shipment={{ ...shipment, cargo: { ...cargo, allocations: [{ ...cargo.allocations[0], quantity: 9 }] } }} />);
  expect(screen.getByRole("button", { name: "Export" })).toBeDisabled();
});
