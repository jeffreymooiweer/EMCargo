/**
 * A migrated shipment must have one editor for its physical hierarchy. Leaving
 * the old role or container selector beside the cargo workspace would let users
 * change legacy references without changing the actual allocations. Equipment
 * configuration remains independently editable because it describes the item.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import EquipmentLineFields from "./EquipmentLineFields";
import type { DraftLine } from "./ReviewLinesPanel";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key, i18n: { language: "en" } }) }));

const container: DraftLine = {
  id: 1, description: "Container", quantity: 1, unit: "pcs", equipment_role: "container",
  equipment: { equipment_id: 1, version: 1, kind: "container", specifications: "Container", weight_kg: 2300,
    configurations: [{ name: "Folded", length_cm: 610, width_cm: 244, height_cm: 60, weight_kg: 2300 }] },
};
const goods: DraftLine = { id: 2, description: "Steel", quantity: 10, unit: "pcs", container_line_id: 1 };

describe("EquipmentLineFields", () => {
  it("keeps equipment configuration editable but removes competing hierarchy editors", async () => {
    const onChange = vi.fn();
    const { rerender } = render(<EquipmentLineFields cargoManaged line={container} lines={[container, goods]} result={null} onChange={onChange} />);
    expect(screen.queryByLabelText("assets.useAs")).not.toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("assets.configuration"), "Folded");
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ height_cm: 60, equipment: expect.objectContaining({ configuration: "Folded" }) }));
    rerender(<EquipmentLineFields cargoManaged line={goods} lines={[container, goods]} result={null} onChange={onChange} />);
    expect(screen.queryByLabelText("assets.inContainer")).not.toBeInTheDocument();
  });

  it("retains container controls for callers that have no cargo workspace", () => {
    render(<EquipmentLineFields line={goods} lines={[container, goods]} result={null} onChange={vi.fn()} />);
    expect(screen.getByLabelText("assets.inContainer")).toHaveValue("1");
  });
});
