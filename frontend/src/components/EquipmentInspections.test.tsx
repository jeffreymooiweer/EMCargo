/**
 * The short inspection form must retain the independent-report semantics. A
 * renewal archives only the selected report and never copies its old approval,
 * dates or reference. Closing report details must retain their stored contents.
 */
import { useState } from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import type { EquipmentInspection } from "../api/client";
import EquipmentInspections from "./EquipmentInspections";
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key, i18n: { language: "nl" } }) }));

it("renews one inspection, retains unrelated records and starts with no approval", async () => {
  const old: EquipmentInspection = { id: "old", kind: "fgas", name: "Cooling", scope: "Unit 1", result: "passed", performed_on: "2025-01-01", due_on: "2026-01-01", reference: "OLD", inspector: "DEMO" };
  const electrical: EquipmentInspection = { id: "electrical", kind: "nen3140", result: "passed", performed_on: "2026-01-01", due_on: "2027-01-01" };
  const changed = vi.fn();
  function Form() {
    const [items, setItems] = useState([old, electrical]);
    return <EquipmentInspections items={items} onChange={next => { changed(next); setItems(next); }} />;
  }
  const user = userEvent.setup(); render(<Form />);
  await user.click(screen.getByText("Cooling"));
  await user.click(within(screen.getByText("Cooling").closest("details")!).getByRole("button", { name: "inspections.renew" }));
  const next = changed.mock.lastCall![0] as EquipmentInspection[];
  expect(next[0]).toEqual({ ...old, archived: true }); expect(next[1]).toEqual(electrical);
  expect(next[2]).toMatchObject({ kind: "fgas", name: "Cooling", scope: "Unit 1", result: "unknown" });
  for (const field of ["performed_on", "due_on", "reference", "inspector"]) expect(next[2]).not.toHaveProperty(field);
  const fresh = screen.getByText("Cooling").closest("details")!;
  expect(within(fresh).getByText("equipmentSimple.reportDetails").closest("details")).not.toHaveAttribute("open");
  expect(within(fresh).getByRole("combobox", { name: "inspections.result" })).toHaveValue("unknown");
});
