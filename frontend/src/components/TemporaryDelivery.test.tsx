/** An old response must never unlock final issue for newly edited goods. */
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import TemporaryDelivery from "./TemporaryDelivery";
import type { ShipmentIn } from "../api/client";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key, i18n: { language: "en" } }) }));
const request = vi.hoisted(() => vi.fn());
vi.mock("../api/client", () => ({ apiRequest: request, describeDetail: String }));
const shipment: ShipmentIn = { modality: "road", language: "en", profiles: [], values: {}, lines: [], documents: ["packing_list"], bundle: null, snapshot: {} };
beforeEach(() => { request.mockReset(); });

it("keeps unsupported checks blocked for an account without review competence", async () => {
  request.mockResolvedValue({ manual_required: true, blocked: false, can_review: false });
  render(<TemporaryDelivery shipment={shipment} />);
  await userEvent.click(screen.getByText("deliveries.temporary"));
  await userEvent.click(screen.getByRole("button", { name: "deliveries.assess" }));
  expect(await screen.findByText("deliveries.partialCoverage")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "deliveries.temporaryIssue" })).toBeDisabled();
  expect(screen.queryByRole("button", { name: "deliveries.review" })).not.toBeInTheDocument();
});

it("invalidates a qualified review when the vehicle changes", async () => {
  request.mockResolvedValueOnce({ manual_required: true, blocked: false, can_review: true }).mockResolvedValueOnce({ token: "bound-review" });
  render(<TemporaryDelivery shipment={shipment} />);
  await userEvent.click(screen.getByText("deliveries.temporary"));
  await userEvent.click(screen.getByRole("button", { name: "deliveries.assess" }));
  await userEvent.type(await screen.findByLabelText("deliveries.reason"), "Verified modal requirements and the actual vehicle");
  await userEvent.click(screen.getByRole("button", { name: "deliveries.review" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "deliveries.temporaryIssue" })).toBeEnabled());
  await userEvent.type(screen.getByLabelText("deliveries.vehicle"), "Changed vehicle");
  expect(screen.getByRole("button", { name: "deliveries.temporaryIssue" })).toBeDisabled();
});

it("ignores an assessment that arrives after the parent shipment changed", async () => {
  let complete!: (value: unknown) => void;
  request.mockReturnValue(new Promise(resolve => { complete = resolve; }));
  const page = render(<TemporaryDelivery shipment={shipment} />);
  await userEvent.click(screen.getByText("deliveries.temporary"));
  await userEvent.click(screen.getByRole("button", { name: "deliveries.assess" }));
  page.rerender(<TemporaryDelivery shipment={{ ...shipment, values: { shipment_reference: "different goods" } }} />);
  await act(async () => complete({ manual_required: false, blocked: false, can_review: true }));
  expect(screen.getByRole("button", { name: "deliveries.temporaryIssue" })).toBeDisabled();
  expect(screen.queryByText("deliveries.ordinary")).not.toBeInTheDocument();
});
