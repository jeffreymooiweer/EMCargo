/**
 * The DG step after the overhaul: answers shown as answers, questions as
 * questions.
 *
 * With a UN number in place the step shows a summary of what the derivation
 * answered, the open questions the backend named (each with its reason), and
 * the special situations behind one closed door. The full form did not
 * disappear — it is a choice, behind one button — and without a UN number it
 * is still the default, because then the substance itself is the question.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import DangerousGoodsStep from "./DangerousGoodsStep";
import { DgEntry } from "../api/client";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: "nl" },
  }),
}));

vi.mock("../api/client", () => ({
  api: {
    dgInstructions: vi.fn().mockResolvedValue({ dg_intro: { nl: "" }, dg_fields: {} }),
    dgPrepare: vi.fn().mockResolvedValue({
      entries: [
        {
          line_id: 1,
          vehicle: "vrachtwagen",
          products: [{ un_number: "1203", proper_shipping_name: "BENZINE", class: "3" }],
        },
      ],
      document_lines: {},
      hints: [],
      requirements: [],
      open_questions: [
        {
          line_id: 1,
          product_index: 0,
          un_number: "1203",
          questions: [
            { field: "carriage_mode", required: true, reason: "carriage_mode_decides" },
            {
              field: "chosen_name",
              required: true,
              reason: "sp3122",
              options: ["BENZINE", "MOTORBRANDSTOF"],
            },
          ],
        },
      ],
    }),
    dgSearch: vi.fn().mockResolvedValue({ results: [] }),
    dgPackagings: vi.fn().mockResolvedValue({ results: [] }),
    dgLookup: vi.fn().mockRejectedValue(new Error("offline")),
  },
}));

const entries: DgEntry[] = [
  {
    line_id: 1,
    vehicle: "vrachtwagen",
    products: [
      { un_number: "1203", proper_shipping_name: "BENZINE", class: "3" } as DgEntry["products"][0],
    ],
  },
];

function renderStep(withUn = true) {
  const data = withUn
    ? entries
    : [{ ...entries[0], products: [{ un_number: "" } as DgEntry["products"][0]] }];
  render(
    <DangerousGoodsStep
      lines={[]}
      entries={data}
      onChange={vi.fn()}
      extraFields={["carriage_mode", "is_waste", "empty_uncleaned"]}
      profiles={["ADR"]}
    />,
  );
}

describe("the DG step with a UN number", () => {
  it("shows the derived answers as a summary, not as questions", async () => {
    renderStep();
    expect(await screen.findByText("dgstep.summaryTitle")).toBeTruthy();
    expect(screen.getByText("BENZINE")).toBeTruthy();
  });

  it("asks the open questions the backend named, with their reasons", async () => {
    renderStep();
    expect(await screen.findByText("dgstep.openTitle")).toBeTruthy();
    expect(screen.getByText(/dgopen\.carriage_mode_decides/)).toBeTruthy();
  });

  it("keeps the special situations behind one closed door", async () => {
    renderStep();
    await screen.findByText("dgstep.summaryTitle");
    const door = screen.getByText("dgstep.special").closest("details");
    // Closed by default: the waste select is behind it, not on the screen.
    expect(door?.open).toBe(false);
    expect(door?.textContent).toContain("is_waste");
  });

  it("a question with a closed answer set renders as a select, nothing pre-chosen", async () => {
    renderStep();
    await screen.findByText("dgstep.openTitle");
    expect(screen.getByText(/dgopen\.sp3122/)).toBeTruthy();
    const option = screen.getByRole("option", { name: "MOTORBRANDSTOF" }) as HTMLOptionElement;
    expect(option).toBeTruthy();
    expect((option.closest("select") as HTMLSelectElement).value).toBe("");
  });

  it("the full form is still there, as a choice", async () => {
    renderStep();
    await screen.findByText("dgstep.summaryTitle");
    expect(screen.queryByText("packing_group")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "dgstep.editAll" }));
    expect(screen.getByText("packing_group")).toBeTruthy();
    expect(screen.queryByText("dgstep.summaryTitle")).toBeNull();
  });
});

describe("the DG step without a UN number", () => {
  it("asks for the substance before exposing dependent fields", () => {
    renderStep(false);
    expect(screen.queryByText("proper_shipping_name")).toBeNull();
    expect(screen.getByRole("combobox", { name: "un_number" })).toBeVisible();
    expect(screen.queryByText("dgstep.summaryTitle")).toBeNull();
  });
});
