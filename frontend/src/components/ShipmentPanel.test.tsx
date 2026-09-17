/**
 * What the shipment adds up to, beside the work.
 *
 * The counts are the easy half. The half worth testing is the documents: a
 * panel that says "3 still needed" and leaves somebody to find those three is
 * the export step's old failure moved to a new place, so the count is a way
 * in. And a document that does not apply to this shipment is not being
 * prepared — the caller leaves it out, and this asserts the panel never
 * invents a line for one.
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ShipmentPanel, { PanelDocument } from "./ShipmentPanel";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options && "count" in options ? `${key}:${options.count}` : key,
    i18n: { language: "nl" },
  }),
}));

const cmr: PanelDocument = {
  key: "cmr", label: "CMR-vrachtbrief", state: "draft", missing: 3, firstMissing: "consignor_name",
};
const packing: PanelDocument = {
  key: "packing_list", label: "Paklijst", state: "ready", missing: 0, firstMissing: null,
};

function panel(props: Partial<Parameters<typeof ShipmentPanel>[0]> = {}) {
  return render(
    <ShipmentPanel
      lines={3}
      weightKg={1250}
      volumeM3={4.5}
      attention={0}
      documents={[]}
      {...props}
    />,
  );
}

describe("what the shipment adds up to", () => {
  it("counts the goods, the mass and the volume", () => {
    panel();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("1250 kg")).toBeInTheDocument();
    expect(screen.getByText("4.5 m³")).toBeInTheDocument();
  });

  it("says a dash rather than a nought before anything is calculated", () => {
    // Nought kilos is a claim about the shipment. Nothing calculated yet is
    // not, and the two must not look the same.
    panel({ weightKg: null, volumeM3: null });
    expect(screen.getAllByText("—")).toHaveLength(2);
  });

  it("names what is still waiting to be looked at", () => {
    panel({ attention: 2 });
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("lists what is being prepared, with what each is short of", () => {
    panel({ documents: [cmr, packing] });
    expect(screen.getByText("CMR-vrachtbrief")).toBeInTheDocument();
    expect(screen.getByText("panel.missing:3")).toBeInTheDocument();
    expect(screen.getByText("panel.ready")).toBeInTheDocument();
  });

  it("makes the count the way in to the first missing answer", async () => {
    const onMissing = vi.fn();
    panel({ documents: [cmr], onMissing });
    await userEvent.click(screen.getByText("panel.missing:3"));
    expect(onMissing).toHaveBeenCalledWith("consignor_name");
  });

  it("says a blocked document is blocked rather than offering a jump", () => {
    // Blocked means the substance itself is not established; there is no one
    // field to go to, and pretending there is would send somebody nowhere.
    panel({
      documents: [{ key: "adr", label: "ADR", state: "blocked", missing: 0, firstMissing: null }],
      onMissing: vi.fn(),
    });
    expect(screen.getByText("panel.blocked")).toBeInTheDocument();
  });

  it("draws no document section when nothing is being prepared", () => {
    const { container } = panel();
    expect(screen.queryByText("panel.preparing")).toBeNull();
    // The counts are still there; it is the list that is absent.
    expect(within(container).getByText("wizard.lines")).toBeInTheDocument();
  });

  it("names the cargo blocker and takes the user back to the cargo", async () => {
    const onMissing = vi.fn();
    panel({ documents: [{ key: "cmr", label: "CMR", state: "blocked", missing: 1,
      firstMissing: "cargo", blockedReason: "Cargo weights are missing" }], onMissing });
    expect(screen.queryByText("panel.blocked")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Cargo weights are missing" }));
    expect(onMissing).toHaveBeenCalledWith("cargo");
  });
});
