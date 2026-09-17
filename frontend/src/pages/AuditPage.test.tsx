/**
 * The audit page: what it lists, how the action codes read, and that a
 * filter asks the server rather than hiding rows.
 */
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AuditEvent } from "../api/client";
import AuditPage from "./AuditPage";
import { ToastProvider } from "../toast/ToastProvider";

const SENTENCES: Record<string, string> = {
  "audit.actions.auth.login": "signed in",
  "audit.actions.shipment.kept": "kept a shipment",
  "audit.groups.shipment": "Shipments",
};

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      if (key in SENTENCES) return SENTENCES[key];
      if (options && "count" in options) return `${key}:${options.count}/${options.total}`;
      if (options && "group" in options) return `${key}:${options.group}`;
      return key;
    },
    i18n: { language: "nl" },
  }),
}));

const lines: AuditEvent[] = [
  {
    id: 2, at: "2026-09-05T08:00:00Z", actor_id: 1, actor_username: "ada", action: "shipment.kept",
    target_type: "shipment", target_id: "7", summary: "CP-2026-100", client: "10.0.0.5",
  },
  {
    id: 1, at: "2026-09-05T07:00:00Z", actor_id: 1, actor_username: "ada", action: "auth.login",
    target_type: "", target_id: "", summary: "password", client: "10.0.0.5",
  },
  {
    id: 3, at: "2026-09-05T09:00:00Z", actor_id: null, actor_username: "bob", action: "shipment.launched",
    target_type: "", target_id: "", summary: "", client: "",
  },
];

const api = vi.hoisted(() => ({
  audit: vi.fn(),
  auditActions: vi.fn(),
  auditExportUrl: (query: Record<string, string | undefined>) =>
    `/api/audit/export.csv?${Object.entries(query).filter(([, v]) => v).map(([k, v]) => `${k}=${v}`).join("&")}`,
}));
vi.mock("../api/client", () => ({ api }));

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={["/audit"]}>
        <AuditPage />
      </MemoryRouter>
    </ToastProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  api.audit.mockResolvedValue({ items: lines, total: 3, page: 1, per_page: 50 });
  api.auditActions.mockResolvedValue({ actions: ["auth.login", "shipment.kept"], actors: ["ada", "bob"] });
});

describe("de auditpagina", () => {
  it("toont de regels met de actie als zin en de code als fallback", async () => {
    renderPage();
    // The card, the table row and the filter's option all carry the sentence.
    expect((await screen.findAllByText("kept a shipment")).length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("signed in").length).toBeGreaterThan(0);
    // An action the interface has no sentence for keeps its code.
    expect(screen.getAllByText("shipment.launched").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/CP-2026-100/).length).toBeGreaterThan(0);
    expect(screen.getByText("shipment #7")).toBeInTheDocument();
    expect(screen.getByText("audit.count:3/3")).toBeInTheDocument();
  });

  it("filtert via de server en zet de selectie in de exportlink", async () => {
    renderPage();
    await screen.findAllByText("kept a shipment");
    expect(api.audit).toHaveBeenLastCalledWith(expect.objectContaining({ actor: "", action: "", page: 1 }));

    const actorFilter = await screen.findByLabelText("audit.actor");
    await userEvent.selectOptions(actorFilter, "bob");
    await waitFor(() =>
      expect(api.audit).toHaveBeenLastCalledWith(expect.objectContaining({ actor: "bob", page: 1 })));

    const actionFilter = screen.getByLabelText("audit.action");
    await userEvent.selectOptions(actionFilter, "shipment");
    await waitFor(() =>
      expect(api.audit).toHaveBeenLastCalledWith(expect.objectContaining({ action: "shipment" })));

    const link = screen.getByText("audit.export").closest("a");
    expect(link?.getAttribute("href")).toBe("/api/audit/export.csv?actor=bob&action=shipment");
  });

  it("zegt dat er niets is als de selectie leeg is", async () => {
    api.audit.mockResolvedValue({ items: [], total: 0, page: 1, per_page: 50 });
    renderPage();
    expect(await screen.findByText("audit.empty")).toBeInTheDocument();
  });

  it("recovers from a failed request without presenting the error as an empty audit log", async () => {
    api.audit.mockRejectedValueOnce(new Error("Audit unavailable"));
    renderPage();
    expect(await screen.findByRole("alert")).toHaveTextContent("Audit unavailable");
    expect(screen.queryByText("audit.empty")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "historyAccess.retry" }));
    expect((await screen.findAllByText(/CP-2026-100/)).length).toBeGreaterThan(0);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("keeps the latest filter result when an older request finishes later", async () => {
    let resolveOlder: (value: unknown) => void = () => {};
    api.audit.mockImplementationOnce(() => new Promise(resolve => { resolveOlder = resolve; }));
    api.audit.mockResolvedValueOnce({ items: [{ ...lines[0], summary: "Latest selection" }], total: 1 });
    renderPage();
    await screen.findByRole("option", { name: "bob" });
    await userEvent.selectOptions(screen.getByLabelText("audit.actor"), "bob");
    await screen.findAllByText(/Latest selection/);
    await act(async () => resolveOlder({ items: lines, total: lines.length }));
    expect(screen.queryByText(/CP-2026-100/)).toBeNull();
    expect(screen.getAllByText(/Latest selection/).length).toBeGreaterThan(0);
    await userEvent.click(screen.getByRole("button", { name: "history.clearFilters" }));
    expect(screen.getByLabelText("audit.actor")).toHaveValue("");
  });
});
