import { useState } from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { EquipmentSnapshot } from "../../api/client";
import type { CargoGood, CargoManifest, PackagingTemplate } from "../../api/cargo";
import { cargoApi } from "../../api/cargo";
import { emptyCargo, placeCargo } from "../../utils/cargo";
import CargoWorkspace from "./CargoWorkspace";
import CargoSummary from "./CargoSummary";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string, options?: Record<string, unknown>) => options?.name ? `${key} ${options.name}` : key, i18n: { language: "nl" } }) }));
const models: PackagingTemplate[] = [{ id: "box", name: "Box", category: "box", tare_kg: 1 }];
const equipment: [] = [];
const goods: CargoGood[] = [{ id: 7, name: "Bolts", quantity: 100, unit: "pcs", weight_kg: 10 }, { id: 8, name: "Nuts", quantity: 100, unit: "pcs", weight_kg: 5 }];
let state: CargoManifest;
function Harness({ initial = emptyCargo(), assets = equipment }: { initial?: CargoManifest; assets?: EquipmentSnapshot[] }) {
  const [value, setValue] = useState(initial); state = value;
  return <CargoWorkspace value={value} goods={goods} onChange={setValue} templates={models} equipment={assets} />;
}
beforeEach(() => {
  HTMLDialogElement.prototype.showModal = function (this: HTMLDialogElement) { this.open = true; };
  HTMLDialogElement.prototype.close = function (this: HTMLDialogElement) { this.open = false; };
  vi.spyOn(cargoApi, "reusableUnits").mockResolvedValue([]);
});
afterEach(() => { vi.restoreAllMocks(); });

it("packs two selected articles in one chooser and can undo without losing quantities", async () => {
  const user = userEvent.setup(); render(<Harness />);
  await user.click(screen.getByRole("checkbox", { name: "cargo.selectItem Bolts" }));
  await user.click(screen.getByRole("checkbox", { name: "cargo.selectItem Nuts" }));
  await user.click(screen.getByRole("button", { name: "cargo.place" }));
  const dialog = screen.getByRole("dialog");
  await user.selectOptions(within(dialog).getByRole("combobox", { name: "cargo.destination" }), "model:box");
  await user.click(within(dialog).getByRole("button", { name: "cargo.apply" }));
  await waitFor(() => expect(state.units).toHaveLength(1));
  expect(state.allocations.map(a => a.goods_id)).toEqual([7, 8]);
  expect(state.allocations.map(a => a.quantity)).toEqual([100, 100]);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "cargo.undo" }));
  expect(state.units).toHaveLength(0);
  expect(state.allocations).toHaveLength(0);
  expect(screen.getByText("Bolts")).toBeVisible();
});

it("creates equal boxes in one action and displays a compact group rather than a thousand fields", async () => {
  const user = userEvent.setup(); render(<Harness />);
  await user.click(screen.getByRole("checkbox", { name: "cargo.selectItem Bolts" }));
  await user.click(screen.getByRole("button", { name: "cargo.place" }));
  const dialog = screen.getByRole("dialog");
  await user.selectOptions(within(dialog).getByRole("combobox", { name: "cargo.destination" }), "model:box");
  await user.clear(within(dialog).getByRole("spinbutton", { name: "cargo.packageCount" }));
  await user.type(within(dialog).getByRole("spinbutton", { name: "cargo.packageCount" }), "3");
  expect(within(dialog).getByText("cargo.eachAndRemaining")).toBeVisible();
  await user.click(within(dialog).getByRole("button", { name: "cargo.apply" }));
  await waitFor(() => expect(state.units).toHaveLength(3));
  expect(state.allocations.map(a => a.quantity)).toEqual([33, 33, 33]);
  expect(screen.getByText("3 × Box")).toBeVisible();
  expect(screen.getByText("Bolts")).toBeVisible();
  expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
});

it("keeps the read-only tree expandable without displaying disabled editor controls", async () => {
  const value = placeCargo(emptyCargo(), goods, { unit_ids: [], goods: [{ goods_id: 7, quantity: 100 }] }, { template: models[0] });
  const user = userEvent.setup(); render(<CargoSummary value={value} goods={goods} />);
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "cargo.newUnit" })).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: new RegExp("Box") }));
  expect(screen.getByText("Bolts")).toBeVisible();
  expect(cargoApi.reusableUnits).not.toHaveBeenCalled();
});

it("retains the reusable crate identity while its prior shipment contents stay separate", async () => {
  const previous = placeCargo(emptyCargo(), goods, { unit_ids: [], goods: [{ goods_id: 8, quantity: 100 }] }, { template: models[0], unit_options: { reusable: true } });
  const reusable = { ...previous.units[0], name: "Reusable crate" };
  vi.mocked(cargoApi.reusableUnits).mockResolvedValue([reusable]);
  const user = userEvent.setup(); render(<Harness />);
  await user.click(screen.getByRole("checkbox", { name: "cargo.selectItem Bolts" }));
  await user.click(screen.getByRole("button", { name: "cargo.place" }));
  const dialog = screen.getByRole("dialog");
  await user.selectOptions(within(dialog).getByRole("combobox", { name: "cargo.destination" }), `reuse:${reusable.id}`);
  expect(within(dialog).queryByRole("spinbutton", { name: "cargo.packageCount" })).not.toBeInTheDocument();
  await user.clear(within(dialog).getByRole("textbox", { name: "cargo.name" }));
  await user.type(within(dialog).getByRole("textbox", { name: "cargo.name" }), "This shipment crate");
  await user.click(within(dialog).getByText("cargo.dimensionsAndWeight"));
  await user.clear(within(dialog).getByRole("spinbutton", { name: "cargo.tare_kg" }));
  await user.type(within(dialog).getByRole("spinbutton", { name: "cargo.tare_kg" }), "2");
  await user.click(within(dialog).getByRole("button", { name: "cargo.apply" }));
  await waitFor(() => expect(state.units).toHaveLength(1));
  expect(state.units[0].id).toBe(reusable.id);
  expect(state.units[0].code).toBe(reusable.code);
  expect(state.units[0].template_id).toBe("box");
  expect(state.units[0]).toMatchObject({ name: "This shipment crate", tare_kg: 2 });
  expect(previous.units[0].tare_kg).toBe(1);
  expect(state.allocations.map(a => a.goods_id)).toEqual([7]);
  expect(previous.allocations.map(a => a.goods_id)).toEqual([8]);
});

it("keeps an unknown external destination valid without requiring a registration or vehicle weight", async () => {
  const user = userEvent.setup(); render(<Harness />);
  await user.click(screen.getByRole("checkbox", { name: "cargo.selectItem Bolts" }));
  await user.click(screen.getByRole("button", { name: "cargo.place" }));
  const dialog = screen.getByRole("dialog");
  await user.selectOptions(within(dialog).getByRole("combobox", { name: "cargo.destination" }), "external");
  await user.click(within(dialog).getByRole("button", { name: "cargo.apply" }));
  await waitFor(() => expect(state.units).toHaveLength(1));
  expect(state.units[0]).toMatchObject({ kind: "ctu", category: "vehicle", source: "external" });
  expect(state.units[0].external_reference).toBeUndefined();
  expect(state.units[0].tare_kg).toBeUndefined();
  expect(state.allocations[0].quantity).toBe(100);
});


it("resolves an own vehicle identity outside the first catalogue page before placing goods", async () => {
  const physical = { ...placeCargo(emptyCargo(), [], { unit_ids: [], goods: [] }, { template: models[0] }).units[0], equipment_id: 999, kind: "ctu" as const, reusable: true };
  vi.mocked(cargoApi.reusableUnits).mockImplementation(async (_query, equipmentId) => equipmentId === 999 ? [physical] : []);
  const assets = [{ equipment_id: 999, specifications: "Truck 999", kind: "vehicle", weight_kg: 8000 } as EquipmentSnapshot];
  const user = userEvent.setup(); render(<Harness assets={assets} />);
  await user.click(screen.getByRole("checkbox", { name: "cargo.selectItem Bolts" }));
  await user.click(screen.getByRole("button", { name: "cargo.place" }));
  const dialog = screen.getByRole("dialog");
  await user.selectOptions(within(dialog).getByRole("combobox", { name: "cargo.destination" }), "asset:999");
  await user.click(within(dialog).getByRole("button", { name: "cargo.apply" }));
  await waitFor(() => expect(state.units).toHaveLength(1));
  expect(cargoApi.reusableUnits).toHaveBeenCalledWith("", 999);
  expect(state.units[0]).toMatchObject({ id: physical.id, code: physical.code, source: "own", tare_kg: 8000 });
});
