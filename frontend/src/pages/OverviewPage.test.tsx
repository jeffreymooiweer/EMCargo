/** The work list must route real tasks and retain state when writes fail. */
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, expect, it, vi } from "vitest";
import type { WorkItem, WorkPage } from "../api/client";
import OverviewPage, { workDestination } from "./OverviewPage";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key, i18n: { language: "nl" } }) }));
const settings = { history_enabled: true };
vi.mock("../settings/preferences", () => ({ usePreferences: () => ({ publicSettings: settings, preferences: {}, loaded: true, mode: "organisation" }) }));
const api = vi.hoisted(() => ({ work: vi.fn(), workPeople: vi.fn(), changeWork: vi.fn() }));
vi.mock("../api/client", () => ({ api }));
const item: WorkItem = { kind: "shipment", id: "7", reference: "PL-2048", modality: "road", consignor: "Factory", consignee: "Warehouse", status: "ready", due_date: null, owner_id: 1, owner_name: "Ada", completed_at: null, version: 3, issues: [], updated_at: "2026-09-14T08:00:00Z", is_draft: false, overdue: false, review_status: "" };
const result = (items: WorkItem[] = [item]): WorkPage => ({ items, counts: { attention: 4, waiting: 2, today: 3, ready: 8, all: 14, closed: 2 }, total: items.length, page: 1, per_page: 20, day: "2026-09-14", history_enabled: true });
const show = () => render(<MemoryRouter><OverviewPage /></MemoryRouter>);
beforeEach(() => { vi.clearAllMocks(); settings.history_enabled = true; api.work.mockResolvedValue(result()); api.workPeople.mockResolvedValue([{ id: 1, name: "Ada" }, { id: 2, name: "Sam" }]); api.changeWork.mockResolvedValue({ ok: true, version: 4 }); });

it("keeps the chooser as the front door and offers document intake", async () => {
  show(); await screen.findByText("PL-2048");
  expect(screen.getByRole("link", { name: "nav.new" })).toHaveAttribute("href", "/");
  expect(screen.getByRole("link", { name: "work.import" })).toHaveAttribute("href", "/wizard/road?input=document");
  expect(screen.getByRole("link", { name: "work.action.open" })).toHaveAttribute("href", "/wizard/road?shipment=7");
  expect(screen.getByText("work.noDate")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /work.bucket.ready/ })).toHaveTextContent("8");
});

it("routes corrections, approvals, private drafts and unavailable modes to their actual source", () => {
  expect(workDestination({ ...item, is_draft: true })).toBe("/wizard/road");
  expect(workDestination({ ...item, kind: "review", id: "abc", status: "review" })).toBe("/dg-reviews/abc");
  expect(workDestination({ ...item, kind: "review", id: "abc", status: "changes" })).toBe("/wizard/road?review=abc");
  expect(workDestination({ ...item, kind: "review", id: "abc", status: "approved" })).toBe("/wizard/road?review=abc");
  expect(workDestination({ ...item, modality: "sea" })).toBe("/wizard/sea?shipment=7");
  for (const modality of ["multimodal"]) {
    expect(workDestination({ ...item, modality })).toBe("/shipments");
  }
});

it("filters with the server so counts and rows use one scope", async () => {
  show(); await screen.findByText("PL-2048");
  await userEvent.click(screen.getByRole("button", { name: /work.bucket.waiting/ }));
  await waitFor(() => expect(api.work).toHaveBeenLastCalledWith(expect.objectContaining({ bucket: "waiting", page: 1 })));
  await userEvent.click(screen.getByRole("checkbox", { name: "work.mine" }));
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "Factory" } });
  await waitFor(() => expect(api.work).toHaveBeenLastCalledWith(expect.objectContaining({ q: "Factory", mine: true })));
});

it("does not let an older reply replace a newly selected filter", async () => {
  let resolveOld!: (value: WorkPage) => void;
  api.work.mockReturnValueOnce(new Promise(resolve => { resolveOld = resolve; })).mockResolvedValueOnce(result([{ ...item, reference: "NEW" }]));
  show(); await userEvent.click(screen.getByRole("button", { name: /work.bucket.ready/ }));
  await screen.findByText("NEW");
  await act(async () => resolveOld(result([{ ...item, reference: "OLD" }])));
  expect(screen.queryByText("OLD")).toBeNull();
});

it("retains the edit and current rows after a stale or failed assignment", async () => {
  api.changeWork.mockRejectedValueOnce(new Error("work.changed"));
  show(); await userEvent.click(await screen.findByRole("button", { name: "work.manage" }));
  await screen.findByRole("option", { name: "Sam" });
  await userEvent.selectOptions(screen.getByRole("combobox", { name: "work.owner" }), "2");
  await userEvent.click(screen.getByRole("button", { name: "work.assign" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("work.changed");
  expect(screen.getByRole("dialog")).toBeInTheDocument();
  expect(api.changeWork).toHaveBeenCalledWith(7, { version: 3, owner_id: 2 });
  await userEvent.click(screen.getByRole("button", { name: "work.assign" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
});

it("only offers office completion for ready shipments", async () => {
  api.work.mockResolvedValue(result([{ ...item, status: "prepare" }]));
  show(); await userEvent.click(await screen.findByRole("button", { name: "work.manage" }));
  expect(screen.queryByRole("button", { name: "work.finish" })).toBeNull();
});

it("still displays specialist work when optional shipment history is off", async () => {
  settings.history_enabled = false;
  api.work.mockResolvedValue(result([{ ...item, kind: "review", status: "review" }]));
  show(); expect(await screen.findByRole("link", { name: "work.action.review" })).toHaveAttribute("href", "/dg-reviews/7");
  expect(screen.getByText("work.specialistTeam")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "work.manage" })).toBeNull();
});

it("reports a failed load and lets the user retry", async () => {
  api.work.mockRejectedValueOnce(new Error("offline"));
  show(); expect(await screen.findByRole("alert")).toHaveTextContent("work.loadFailed");
  await userEvent.click(screen.getByRole("button", { name: "overview.retry" }));
  expect(await screen.findByText("PL-2048")).toBeInTheDocument();
});

vi.mock("../components/DeliveryActivity", () => ({ default: () => null }));
