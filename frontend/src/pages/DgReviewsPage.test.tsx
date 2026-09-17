import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, expect, it, vi } from "vitest";
import DgReviewsPage from "./DgReviewsPage";
import { ToastProvider } from "../toast/ToastProvider";
import { createCargoUnit, emptyCargo } from "../utils/cargo";

const api = vi.hoisted(() => ({ dgReview: vi.fn(), dgReviews: vi.fn(), documentsRegistry: vi.fn(), validateDocument: vi.fn(), decideDgReview: vi.fn() }));
vi.mock("../api/client", () => ({ api }));
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key, i18n: { language: "nl" } }) }));
vi.mock("../settings/preferences", () => ({ usePreferences: () => ({ publicSettings: { dg_review_enabled: true, history_enabled: true } }) }));
vi.mock("../components/DgCompliancePanel", () => ({ default: () => <p>Compliance findings</p> }));
const review = { id: "r1", reference: "DG-100", created_by: "Ada", created_at: "2026-09-08T12:00:00", status: "pending", comment: "", reviewed_by: "", shipment: { modality: "road", profiles: ["ADR"], values: { consignor_name: "Sender Ltd" }, lines: [], dangerous_goods: [{ products: [{ un_number: "1203", proper_shipping_name: "Benzine" }] }], bundle: { documents: [{ document_key: "cmr", values: { consignor_name: "Sender Ltd" } }] } } };
function open(role: string) {
  return render(<MemoryRouter initialEntries={["/dg-reviews/r1"]}><ToastProvider><Routes><Route path="/dg-reviews/:id" element={<DgReviewsPage user={{ id: 1, username: "Ada", email: "ada@example.com", role, active: true }} />} /></Routes></ToastProvider></MemoryRouter>);
}
beforeEach(() => {
  vi.clearAllMocks();
  api.dgReview.mockResolvedValue(review);
  api.documentsRegistry.mockResolvedValue({ shared_sections: [], documents: [{ key: "cmr", label: { nl: "CMR-vrachtbrief" }, sections: [] }] });
  api.validateDocument.mockResolvedValue({ warnings: ["Check units"] });
  api.decideDgReview.mockResolvedValue({ ...review, status: "changes_requested", comment: "Verify quantity" });
});

it("shows the submitted version read-only and requires a reason before returning it", async () => {
  open("dg_specialist");
  await screen.findByRole("heading", { name: "DG-100" });
  expect(screen.queryByRole("textbox", { name: "dgReview.fields.consignor_name" })).toBeNull();
  expect(screen.getByText("CMR-vrachtbrief")).toBeInTheDocument();
  const sendBack = screen.getByRole("button", { name: "dgReview.requestChanges" });
  expect(sendBack).toBeDisabled();
  await userEvent.type(screen.getByLabelText("dgReview.comment"), "Verify quantity");
  await userEvent.click(sendBack);
  await waitFor(() => expect(api.decideDgReview).toHaveBeenCalledWith("r1", "changes_requested", "Verify quantity"));
  expect(screen.queryByRole("button", { name: "dgReview.approve" })).toBeNull();
});

it.each(["user", "super_user", "admin"])("does not offer specialist decisions to %s", async role => {
  open(role);
  await screen.findByRole("heading", { name: "DG-100" });
  expect(screen.queryByRole("button", { name: "dgReview.approve" })).toBeNull();
  expect(screen.queryByRole("textbox")).toBeNull();
  if (role !== "admin") expect(screen.queryByRole("link", { name: "dgsa.title" })).toBeNull();
});

/** A specialist must see the submitted packing tree, including mixed contents,
 * without any control being able to change the frozen submission. */
it("shows the submitted packing structure without editing controls", async () => {
  const box = createCargoUnit({ id: "box-model", name: "Mixed box", category: "box", tare_kg: 1 });
  api.dgReview.mockResolvedValue({ ...review, shipment: { ...review.shipment,
    lines: [{ line_id: 1, description: "Bolts", quantity: 100, unit: "pcs", include: true, weight_total_kg: 5 }],
    cargo: { ...emptyCargo(), units: [box], allocations: [{ id: "allocation-1", goods_id: 1, unit_id: box.id, quantity: 100 }] },
  } });
  open("dg_specialist");
  await screen.findByRole("heading", { name: "DG-100" });
  expect(screen.getByText(box.code)).toBeVisible();
  await userEvent.click(screen.getByRole("button", { name: /Mixed box/ }));
  expect(screen.getByText("Bolts")).toBeVisible();
  expect(screen.queryByRole("button", { name: "cargo.newUnit" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "cargo.place" })).not.toBeInTheDocument();
});
