import { MemoryRouter } from "react-router";
/**
 * The articles library page: lists, adds, edits, imports; and says where the
 * history is off that there is nothing to keep articles beside.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Article } from "../api/client";
import ArticlesPage from "./ArticlesPage";
import { ToastProvider } from "../toast/ToastProvider";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options?.code ? `${key}:${options.code}` : options?.created !== undefined ? `${key}:${options.created}/${options.updated}/${options.skipped}` : key,
    i18n: { language: "nl" },
  }),
}));

const settings = { history_enabled: true };
vi.mock("../settings/preferences", () => ({
  usePreferences: () => ({ publicSettings: settings, preferences: {}, loaded: true, mode: "organisation" }),
}));

const paint: Article = {
  id: 1, code: "PAINT-25", name: "Alkyd paint", un_number: "1263", proper_shipping_name: "PAINT", technical_name: "",
  class: "3", packing_group: "II", type_of_package: "jerrican", net_per_package: "25 L", notes: "", active: true,
};

const api = vi.hoisted(() => ({
  densities: vi.fn(),
  articles: vi.fn(),
  saveArticle: vi.fn(),
  updateArticle: vi.fn(),
  deleteArticle: vi.fn(),
  downloadArticleTemplate: vi.fn(),
  exportArticles: vi.fn(),
  importArticlesFile: vi.fn(),
}));
vi.mock("../api/client", () => ({ api, translateMessage: (message: { message: string }) => message.message }));

beforeEach(() => {
  vi.clearAllMocks();
  settings.history_enabled = true;
  api.articles.mockResolvedValue([paint]);
  api.densities.mockResolvedValue({ results: [], total: 0, offset: 0 });
  api.saveArticle.mockImplementation(async (payload: Article) => ({ ...payload, id: 2 }));
  api.updateArticle.mockImplementation(async (id: number, payload: Article) => ({ ...payload, id }));
  api.importArticlesFile.mockResolvedValue({ created: 2, updated: 1, skipped: 0, errors: [] });
});

function renderPage() {
  return render(
    <ToastProvider>
      <MemoryRouter><ArticlesPage /></MemoryRouter>
    </ToastProvider>,
  );
}

describe("de artikelenbibliotheek", () => {
  it("keeps reference densities available with history off", async () => {
    settings.history_enabled = false;
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "densities.tabs.densities" }));
    expect(await screen.findByRole("searchbox")).toBeVisible();
    await waitFor(() => expect(api.densities).toHaveBeenCalled());
    expect(api.articles).not.toHaveBeenCalled();
  });

  it("preserves an unfinished own-goods form when looking up a density", async () => {
    renderPage();
    await screen.findByText("PAINT-25");
    await userEvent.click(screen.getByText("articles.add"));
    await userEvent.type(screen.getAllByRole("textbox")[0], "DRAFT-42");
    await userEvent.click(screen.getByRole("button", { name: "densities.tabs.densities" }));
    await screen.findByRole("searchbox");
    await userEvent.click(screen.getByRole("button", { name: "densities.tabs.own" }));
    expect(screen.getByDisplayValue("DRAFT-42")).toBeVisible();
  });
  it("zegt waar de historie uitstaat dat er niets is om artikelen naast te bewaren", () => {
    settings.history_enabled = false;
    renderPage();
    expect(screen.getByText("historyAccess.disabled")).toBeInTheDocument();
    expect(api.articles).not.toHaveBeenCalled();
  });

  it("toont de artikelen en voegt er een toe", async () => {
    renderPage();
    expect(await screen.findByText("PAINT-25")).toBeInTheDocument();
    expect(screen.getByText("UN 1263")).toBeInTheDocument();
    expect(screen.getByText("articles.add").closest("details")).not.toHaveAttribute("open");
    await userEvent.click(screen.getByText("articles.add"));
    const inputs = screen.getAllByRole("textbox");
    // The first field of the form is the code; a form without one cannot be saved.
    expect(screen.getByRole("button", { name: "articles.create" })).toBeDisabled();
    await userEvent.type(inputs[0], "BOLT-M12");
    await userEvent.type(inputs[1], "Bolts M12");
    await userEvent.click(screen.getByRole("button", { name: "articles.create" }));
    await waitFor(() => expect(api.saveArticle).toHaveBeenCalledWith(expect.objectContaining({ code: "BOLT-M12", name: "Bolts M12", active: true })));
    expect(api.articles).toHaveBeenCalledTimes(2);
  });

  it("bewerkt een bestaand artikel op zijn id", async () => {
    renderPage();
    await screen.findByText("PAINT-25");
    await userEvent.click(screen.getByRole("button", { name: "articles.edit" }));
    expect(screen.getByDisplayValue("Alkyd paint")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "articles.save" }));
    await waitFor(() => expect(api.updateArticle).toHaveBeenCalledWith(1, expect.objectContaining({ code: "PAINT-25" })));
  });

  it("importeert een spreadsheet en zegt wat ermee gebeurde", async () => {
    renderPage();
    await screen.findByText("PAINT-25");
    const file = new File(["code,name\nX,Y"], "articles.csv", { type: "text/csv" });
    await userEvent.upload(screen.getByLabelText("articles.import"), file);
    await waitFor(() => expect(api.importArticlesFile).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("articles.imported:2/1/0")).toBeInTheDocument();
  });
});

/** Failed and filtered-empty libraries need different recovery paths; imports
 * must retain row failures so users can correct only the rejected records. */
it("retries a failed goods list instead of showing an empty library", async () => {
  api.articles.mockRejectedValueOnce(new Error("Connection unavailable"));
  renderPage();
  expect(await screen.findByRole("alert")).toHaveTextContent("Connection unavailable");
  expect(screen.queryByText("articles.empty")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "overview.retry" }));
  expect(await screen.findByText("PAINT-25")).toBeVisible();
});

it("clears an unmatched search without resetting an unfinished article", async () => {
  renderPage();
  await screen.findByText("PAINT-25");
  await userEvent.click(screen.getByText("articles.add"));
  await userEvent.type(screen.getByLabelText("articles.fields.code"), "KEEP-ME");
  await userEvent.type(screen.getByLabelText("articles.search"), "unmatched");
  expect(await screen.findByText("articles.noResults")).toBeVisible();
  await userEvent.click(screen.getByRole("button", { name: "history.clearFilters" }));
  expect(screen.getByDisplayValue("KEEP-ME")).toBeVisible();
  expect(screen.getByText("PAINT-25")).toBeVisible();
});

it("keeps rejected spreadsheet rows visible after refreshing the goods list", async () => {
  api.importArticlesFile.mockResolvedValue({ created: 1, updated: 0, skipped: 1, errors: [{ code: "articles.row_refused", message: "Row 3: invalid code" }] });
  renderPage();
  await screen.findByText("PAINT-25");
  await userEvent.upload(screen.getByLabelText("articles.import"), new File(["code,name\nA,B"], "articles.csv", { type: "text/csv" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Row 3: invalid code");
  expect(screen.getByText("articles.imported:1/0/1")).toBeVisible();
});
