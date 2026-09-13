import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import DensityCatalogue from "./DensityCatalogue";
import type { DensityPage } from "../api/client";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key, i18n: { language: "nl" } }) }));
const api = vi.hoisted(() => ({ densities: vi.fn() }));
vi.mock("../api/client", () => ({ api }));
const page: DensityPage = { total: 1, offset: 0, results: [{
  canonical_name: "wood_12", label: "Abies alba — hout, 12% vocht", density_kg_m3: 435,
  density_min_kg_m3: 430, density_max_kg_m3: 440, kind: "measurement_mean", basis: "solid",
  source_name: "GWDD", source_url: "https://zenodo.org/records/20815517", record_count: 2, condition_key: "wood_mc_12",
}] };

beforeEach(() => { vi.clearAllMocks(); api.densities.mockResolvedValue(page); });

it("keeps provenance and measurement conditions with the displayed density", async () => {
  render(<DensityCatalogue />);
  await userEvent.click(await screen.findByText(page.results[0].label));
  expect(screen.getByText("densities.conditions.wood_mc_12")).toBeVisible();
  expect(screen.getByRole("link", { name: "GWDD" })).toHaveAttribute("href", page.results[0].source_url);
  expect(screen.getByText(/430–440/)).toBeVisible();
});

it("ignores an older search response that arrives after a more recent query", async () => {
  let resolveOld!: (value: DensityPage) => void;
  api.densities.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; }));
  render(<DensityCatalogue />);
  await waitFor(() => expect(api.densities).toHaveBeenCalledOnce());
  await userEvent.type(screen.getByRole("searchbox"), "Abies");
  expect(await screen.findByText(page.results[0].label)).toBeVisible();
  resolveOld({ total: 0, offset: 0, results: [] });
  await waitFor(() => expect(screen.getByText(page.results[0].label)).toBeVisible());
});

it("filters by goods category and resets pagination", async () => {
  api.densities.mockResolvedValue({ ...page, total: 80 });
  render(<DensityCatalogue />);
  await screen.findByText(page.results[0].label);
  await userEvent.click(screen.getByRole("button", { name: "densities.next" }));
  await waitFor(() => expect(api.densities).toHaveBeenLastCalledWith("", 30, 30, ""));
  await userEvent.selectOptions(screen.getByRole("combobox", { name: "densities.category" }), "food");
  await waitFor(() => expect(api.densities).toHaveBeenLastCalledWith("", 0, 30, "food"));
});

it("shows measured temperature and pressure alongside chemical density", async () => {
  api.densities.mockResolvedValue({ ...page, results: [{ ...page.results[0], kind: "measurement", condition_key: "sample_at_conditions", temperature_c: 25, pressure_kpa: 101.325, method: "Pycnometric method" }] });
  render(<DensityCatalogue />);
  await userEvent.click(await screen.findByText(page.results[0].label));
  expect(screen.getByText(/25 °C/)).toBeVisible();
  expect(screen.getByText(/101,325 kPa/)).toBeVisible();
  expect(screen.getByText(/Pycnometric method/)).toBeVisible();
});
