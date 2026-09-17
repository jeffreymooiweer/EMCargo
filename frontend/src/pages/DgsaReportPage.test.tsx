/**
 * The adviser's annual report page: it asks for the year the server offers,
 * shows the count, lists the duties without filling them in, and hands the
 * workbook over on request.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DgsaReport } from "../api/client";
import DgsaReportPage from "./DgsaReportPage";
import { ToastProvider } from "../toast/ToastProvider";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options && "count" in options ? `${key}:${options.count}` : key,
    i18n: { language: "nl" },
  }),
}));

const settings = { history_enabled: true, super_user_dgsa_enabled: false };
vi.mock("../settings/preferences", () => ({
  usePreferences: () => ({ publicSettings: settings, preferences: {}, loaded: true, mode: "organisation" }),
}));

const report: DgsaReport = {
  year: 2026, language: "nl", generated_at: "2026-09-05T10:00:00+00:00", generated_by: "root",
  scope: "Alle afdelingen", basis: "ADR 1.8.3.3: …", source: "ADR 2025 NL", counted_note: "Geteld over…",
  totals: { shipments: 4, with_dangerous_goods: 3, without_dangerous_goods: 1, products: 5,
            quantity_kg: 1612, quantity_l: 100, quantity_unknown: 1 },
  by_month: Array.from({ length: 12 }, (_, i) => ({ month: i + 1, shipments: i === 0 ? 2 : 0, with_dangerous_goods: i === 0 ? 2 : 0 })),
  by_modality: [{ modality: "road", label: "Wegtransport", shipments: 4, with_dangerous_goods: 3 }],
  by_regulation: [{ regulation: "ADR", shipments: 4 }],
  by_department: [{ department: "Sales", shipments: 2, with_dangerous_goods: 2 }],
  by_class: [{ class: "3", shipments: 3, products: 4, quantity_kg: 1600, quantity_l: 100, quantity_unknown: 1 }],
  by_un_number: [{ un_number: "1203", name: "Benzine", class: "3", packing_group: "II", shipments: 2, products: 2,
                   quantity_kg: 1600, quantity_l: 0, quantity_unknown: 0 }],
  adr_points: [{ status: "above_threshold", label: "Boven de drempel", shipments: 3 }],
  documents: [{ document: "cmr", label: "CMR-vrachtbrief", shipments: 4 }],
  duties_heading: "Taken van de adviseur",
  duties: [{ key: "identification", text: "De werkwijzen…" }, { key: "security_plan", text: "Beveiligingsplan 1.10.3.2." }],
};

const api = vi.hoisted(() => ({
  reportYears: vi.fn(),
  dgsaReport: vi.fn(),
  dgsaReportForm: vi.fn(),
  downloadDgsaReport: vi.fn(),
  downloadDgsaReportPdf: vi.fn(),
  departments: vi.fn(),
}));
vi.mock("../api/client", () => ({ api }));

function renderPage(user = { id: 1, username: "specialist", email: "dg@example.com", role: "dg_specialist", active: true }) {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={["/shipments/report"]}>
        <DgsaReportPage user={user} />
      </MemoryRouter>
    </ToastProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  settings.history_enabled = true;
  settings.super_user_dgsa_enabled = false;
  api.reportYears.mockResolvedValue({ years: [2026, 2025] });
  api.dgsaReport.mockResolvedValue(report);
  api.downloadDgsaReport.mockResolvedValue(undefined);
  api.downloadDgsaReportPdf.mockResolvedValue(undefined);
  api.dgsaReportForm.mockResolvedValue({
    report, scope: "", answers: {}, prefill: {}, saved_at: "2026-09-05T10:00:00Z", has_signature: true,
    definition: { source: "DVSA", answer_labels: {}, sections: [{ key: "company", title: "Bedrijfsgegevens" }],
                  questions: [{ key: "company_name", section: "company", kind: "text", text: "Bedrijfsnaam" }],
                  checklist: { title: "", columns: {}, additional_heading: "", items: [] } },
  });
  api.departments.mockResolvedValue([{ id: 1, name: "Sales", users: 1, shipments: 2 }]);
});

describe("het DGSA-jaarrapport", () => {
  it("zegt dat er niets te rapporteren valt waar de historie uitstaat", () => {
    settings.history_enabled = false;
    renderPage();
    expect(screen.getByText("historyAccess.disabled")).toBeInTheDocument();
    expect(api.dgsaReport).not.toHaveBeenCalled();
  });

  it("vraagt het rapport op in de taal van de lezer en toont de cijfers en de taken", async () => {
    renderPage();
    expect(await screen.findByText("Benzine")).toBeInTheDocument();
    expect(api.dgsaReport).toHaveBeenLastCalledWith(2026, "", "nl");
    expect(screen.getByText("UN 1203")).toBeInTheDocument();
    expect(screen.getByText("Boven de drempel")).toBeInTheDocument();
    expect(screen.getByText("Taken van de adviseur")).toBeInTheDocument();
    expect(screen.getByText("Beveiligingsplan 1.10.3.2.")).toBeInTheDocument();
    // The unit-less substances are named rather than silently dropped.
    expect(screen.getByText("dgsa.unknownNote:1")).toBeInTheDocument();
  });

  it("wisselt van jaar en geeft alleen een beheerder het afdelingsfilter", async () => {
    renderPage({ id: 1, username: "root", email: "r@example.com", role: "admin", active: true });
    await screen.findByText("Benzine");
    await userEvent.selectOptions(screen.getByLabelText("dgsa.year"), "2025");
    await waitFor(() => expect(api.dgsaReport).toHaveBeenLastCalledWith(2025, "", "nl"));
    await userEvent.selectOptions(await screen.findByLabelText("departments.userDepartment"), "1");
    await waitFor(() => expect(api.dgsaReport).toHaveBeenLastCalledWith(2025, "1", "nl"));
  });

  it.each(["user", "super_user"])("refuses report access to %s before requesting data", async role => {
    renderPage({ id: 2, username: "ada", email: "a@example.com", role, active: true });
    expect(screen.queryByText("Benzine")).toBeNull();
    expect(api.dgsaReport).not.toHaveBeenCalled();
    expect(api.reportYears).not.toHaveBeenCalled();
  });

  it("allows a Super User only after the admin enables report access", async () => {
    settings.super_user_dgsa_enabled = true;
    renderPage({ id: 2, username: "ada", email: "a@example.com", role: "super_user", active: true });
    expect(await screen.findByText("Benzine")).toBeInTheDocument();
  });

  it("opent het formulier op het tabblad en downloadt het rapport als PDF", async () => {
    renderPage();
    await screen.findByText("Benzine");
    expect(api.dgsaReportForm).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("tab", { name: "dgsa.viewForm" }));
    expect(await screen.findByText("Bedrijfsgegevens")).toBeInTheDocument();
    expect(api.dgsaReportForm).toHaveBeenCalledWith(2026, "", "nl");
    expect(screen.queryByText("Benzine")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "dgsa.downloadPdf" }));
    await waitFor(() => expect(api.downloadDgsaReportPdf).toHaveBeenCalledWith(2026, "", "nl"));
  });

  it("downloadt de werkmap voor het gekozen jaar", async () => {
    renderPage();
    await screen.findByText("Benzine");
    await userEvent.click(screen.getByRole("button", { name: "dgsa.download" }));
    await waitFor(() => expect(api.downloadDgsaReport).toHaveBeenCalledWith(2026, "", "nl"));
  });
});
