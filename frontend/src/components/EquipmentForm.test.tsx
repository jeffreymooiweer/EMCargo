/**
 * A container is selected in one model field, without a separate catalog/apply
 * step. Collapsing advanced fields must never discard an owner's measurements,
 * report history or transport configurations when the basic form is saved.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, ContainerTemplate, EquipmentItem } from "../api/client";
import EquipmentForm from "./EquipmentForm";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key, i18n: { language: "nl" } }) }));
const standard: ContainerTemplate = { id: "standard", name: "20ft standard", language_labels: { nl: "20ft standaard" }, family: "dry", size_ft: 20,
  supplier: "DEMO", source_url: "https://example.com", checked_on: "2026-09-16", basis: "supplier_example", container_use: "freight", length_cm: 605.8, width_cm: 243.8, height_cm: 259.1, weight_kg: 2200 };
const highCube: ContainerTemplate = { ...standard, id: "high", name: "40ft high cube", language_labels: { nl: "40ft high cube" }, family: "high_cube", size_ft: 40, length_cm: 1219.2, height_cm: 289.6, weight_kg: 3900 };
const blank: EquipmentItem = { specifications: "", kind: "container", weight_kg: 0 };

function setup(initial = blank) {
  const save = vi.fn().mockResolvedValue(undefined);
  const view = render(<><EquipmentForm formId="editor" initial={initial} onSave={save} busy={false} /><button type="submit" form="editor">Save</button></>);
  return { ...view, save, user: userEvent.setup() };
}
beforeEach(() => { vi.spyOn(api, "containerTemplates").mockResolvedValue([standard, highCube]); });
afterEach(() => { vi.restoreAllMocks(); });

async function chooseModel(id: string) {
  await screen.findByRole("option", { name: "20ft standaard" });
  await userEvent.selectOptions(screen.getByRole("combobox", { name: "assets.model_name" }), id);
}

describe("compact equipment form", () => {
  it("applies the model immediately and saves via the dialog footer, without opening optional fields", async () => {
    const { save, user } = setup();
    await chooseModel("standard");
    expect(screen.getByRole("textbox", { name: "assets.name" })).toHaveValue("20ft standaard");
    expect(screen.queryByRole("button", { name: "containerCatalog.apply" })).not.toBeInTheDocument();
    expect(screen.getByText("equipmentSimple.moreDetails").closest("details")).not.toHaveAttribute("open");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(save).toHaveBeenCalledWith(expect.objectContaining({ specifications: "20ft standaard", container_template_id: "standard", length_cm: 605.8, height_cm: 259.1, weight_kg: 2200 }));
  });

  it("updates an automatic name when changing model but preserves a name entered by the owner", async () => {
    const { user } = setup();
    await chooseModel("standard"); await chooseModel("high");
    const name = screen.getByRole("textbox", { name: "assets.name" });
    expect(name).toHaveValue("40ft high cube");
    await user.clear(name); await user.type(name, "Our site container"); await chooseModel("standard");
    expect(name).toHaveValue("Our site container");
  });

  it("does not reapply catalog defaults on edit or lose data hidden in optional sections", async () => {
    const initial: EquipmentItem = { ...blank, id: 12, version: 3, specifications: "Our site container", container_template_id: "standard", length_cm: 607, width_cm: 245, height_cm: 260, weight_kg: 2640,
      facilities: ["electricity", "water"], current_location: "Depot", notes: "Keep dry", inspections: [{ id: "check-1", kind: "nen3140", result: "passed", performed_on: "2026-01-01", due_on: "2027-01-01", reference: "REPORT-1" }],
      configurations: [{ name: "Folded", weight_kg: 2600, height_cm: 120 }] };
    const { save, user } = setup(initial);
    await screen.findByRole("option", { name: "20ft standaard" });
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(save).toHaveBeenCalledWith(initial);
  });

  it("allows manual dimensions if the catalog fails and requires an actual weight", async () => {
    vi.mocked(api.containerTemplates).mockRejectedValueOnce(new Error("offline"));
    const { save, user } = setup();
    await screen.findByRole("status");
    await user.selectOptions(screen.getByRole("combobox", { name: "assets.model_name" }), "custom");
    await user.type(screen.getByRole("textbox", { name: "assets.name" }), "My container");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(save).not.toHaveBeenCalled();
    await user.type(screen.getByRole("spinbutton", { name: "assets.tare_kg" }), "1200");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(save).toHaveBeenCalledWith(expect.objectContaining({ specifications: "My container", container_template_id: "", weight_kg: 1200 }));
  });

  it("reveals every collapsed ancestor of an invalid required configuration", async () => {
    const { container, save, user } = setup({ specifications: "DEMO crane", kind: "machine", weight_kg: 5000, configurations: [{ name: "", weight_kg: 4800 }] });
    const invalidName = screen.getByLabelText("assets.configurationName");
    expect(invalidName.closest("details")).not.toHaveAttribute("open");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(save).not.toHaveBeenCalled();
    expect(invalidName.closest("details")).toHaveAttribute("open");
    expect(invalidName.closest("details")?.parentElement?.closest("details")).toHaveAttribute("open");
    fireEvent.change(invalidName, { target: { value: "Folded" } });
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(save).toHaveBeenCalledOnce());
    expect(container.querySelector("form")).toBeInTheDocument();
  });
});

/** Search names must be editable without teaching comma-separated syntax, and
 * saving while the final name is still in the entry field must not discard it. */
it("adds and removes search names while preserving a pending name on save", async () => {
  const { save, user } = setup({ specifications: "DEMO crane", kind: "machine", weight_kg: 5000, aliases: ["Old crane"] });
  await user.click(screen.getByText("equipmentSimple.moreDetails"));
  const input = screen.getByLabelText("materieel.aliases");
  await user.type(input, "Mobile crane{Enter}");
  expect(screen.getByRole("button", { name: "materieel.delete: Mobile crane" })).toBeVisible();
  await user.click(screen.getByRole("button", { name: "materieel.delete: Old crane" }));
  await user.type(input, "Site crane");
  await user.click(screen.getByRole("button", { name: "Save" }));
  expect(save).toHaveBeenCalledWith(expect.objectContaining({ aliases: ["Mobile crane", "Site crane"] }));
});
