/**
 * The shipment details step: one page of question groups.
 *
 * Three things are pinned. **The questions are grouped by meaning**, not by
 * document: a key several documents ask for is asked once, and a group nobody
 * still owes anything folds to a summary with a way to change it.
 *
 * **Next tells first.** A step with required fields still empty says which, on
 * the fields themselves and in a summary above them — and then lets the user go
 * on anyway, because EMCargo does not block a document it cannot finish; the
 * export step keeps saying what is missing and the server has the last word.
 * Nothing is marked while somebody is still typing: that is the difference
 * between telling and nagging.
 *
 * **And a field can be arrived at.** The export step names a missing field by
 * its key; this step opens the group that field is in, puts the cursor in it,
 * and offers the way straight back to where the question was asked.
 */
import { render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import DocumentFieldsStep, { fieldId } from "./DocumentFieldsStep";
import { DocumentDefinition, DocumentRegistry } from "../api/client";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options && "count" in options ? `${key}:${options.count}` : key,
    i18n: { language: "nl" },
  }),
}));

const text = (nl: string) => ({ nl, en: nl });

const REGISTRY: DocumentRegistry = {
  registry_version: "test",
  field_statuses: {} as DocumentRegistry["field_statuses"],
  modalities: [],
  shared_sections: [
    {
      key: "parties",
      label: text("Partijen"),
      fields: [
        { key: "consignor_name", label: text("Afzender"), status: "USER_REQUIRED", type: "text" },
        { key: "notify_party", label: text("Notify"), status: "USER_OPTIONAL", type: "text" },
      ],
    },
    {
      key: "locations",
      label: text("Route"),
      fields: [{ key: "loading_point", label: text("Laadplaats"), status: "USER_REQUIRED", type: "text" }],
    },
  ],
  documents: [],
};

const CMR: DocumentDefinition = {
  key: "cmr",
  label: text("CMR"),
  short_label: text("CMR"),
  category: "official",
  issue_status: text("Voorbereid"),
  exporter: "pdf_template",
  dg_profile: null,
  sections: [
    { ref: "parties" },
    { ref: "locations" },
    {
      key: "cmr_own",
      label: text("CMR-velden"),
      fields: [
        { key: "place_of_issue", label: text("Plaats van opmaak"), status: "USER_REQUIRED", type: "text" },
      ],
    },
  ],
};

const IMO: DocumentDefinition = {
  ...CMR,
  key: "imo_dgd",
  label: text("IMO DGD"),
  short_label: text("IMO"),
  sections: [
    { ref: "parties" },
    {
      key: "imo_own",
      label: text("IMO-velden"),
      fields: [
        { key: "place_of_issue", label: text("Plaats van aangifte"), status: "USER_REQUIRED", type: "text" },
      ],
    },
  ],
};

function Harness({ documents = [CMR], focusField, returnLabel, onReturn, onDone, filled }: {
  documents?: DocumentDefinition[];
  focusField?: string | null;
  returnLabel?: string;
  onReturn?: () => void;
  onDone?: () => void;
  filled?: Record<string, string>;
}) {
  const [values, setValues] = useState<Record<string, string>>(filled ?? {});
  return (
    <DocumentFieldsStep
      registry={REGISTRY}
      documents={documents}
      values={values}
      onChange={setValues}
      focusField={focusField}
      returnLabel={returnLabel}
      onReturn={onReturn}
      onDone={onDone}
    />
  );
}

describe("the questions, grouped by what they mean", () => {
  // Moving the reference to the persistent wizard header must not leave a
  // second editor in the optional fields or erase it when other details change.
  it("preserves the header reference while editing the remaining document fields", async () => {
    const onChange = vi.fn();
    const document: DocumentDefinition = { ...CMR, sections: [{
      key: "references", label: text("References"), fields: [
        { key: "shipment_reference", label: text("Shipment reference"), type: "text", status: "USER_OPTIONAL" },
        { key: "booking_number", label: text("Booking number"), type: "text", status: "USER_OPTIONAL" },
      ],
    }] };
    render(<DocumentFieldsStep registry={REGISTRY} documents={[document]}
      values={{ shipment_reference: "ORDER-42" }} onChange={onChange} excludedFields={["shipment_reference"]} />);
    for (const button of screen.getAllByRole("button", { name: "docgroups.change" })) await userEvent.click(button);
    expect(screen.queryByLabelText("Shipment reference")).not.toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Booking number"), "B");
    expect(onChange).toHaveBeenCalledWith({ shipment_reference: "ORDER-42", booking_number: "B" });
  });

  it("shows the translated choice in the folded summary", () => {
    const document: DocumentDefinition = { ...CMR, sections: [{
      key: "payment", label: text("Betaling"), fields: [{
        key: "freight_payment", label: text("Vrachtbetaling"), status: "USER_OPTIONAL", type: "select",
        options: [{ value: "prepaid", label: text("Franco") }],
      }],
    }] };
    render(<Harness documents={[document]} filled={{ freight_payment: "prepaid" }} />);
    expect(screen.getByText("Vrachtbetaling: Franco")).toBeInTheDocument();
    expect(screen.queryByText("Vrachtbetaling: prepaid")).toBeNull();
  });

  it("shows the three groups on one page, no form per document", () => {
    render(<Harness documents={[CMR, IMO]} />);
    expect(screen.getByRole("heading", { name: "docgroups.parties" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "docgroups.route" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "docgroups.additions" })).toBeInTheDocument();
    // Every field is reachable without pressing anything.
    expect(screen.getByLabelText(/Afzender/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Laadplaats/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Plaats van opmaak/)).toBeInTheDocument();
  });

  it("asks a field both documents want exactly once", () => {
    render(<Harness documents={[CMR, IMO]} />);
    expect(screen.getAllByLabelText(/Plaats van/)).toHaveLength(1);
    expect(screen.queryByLabelText(/Plaats van aangifte/)).toBeNull();
  });

  it("a group that wants nothing more starts folded, and can be opened again", async () => {
    render(<Harness filled={{ consignor_name: "Mooiweer BV" }} />);
    // Nothing required is left in the parties group, so it says what it holds.
    expect(screen.queryByLabelText(/Afzender/)).toBeNull();
    expect(screen.getByText(/Afzender: Mooiweer BV/)).toBeInTheDocument();
    const parties = screen.getByRole("heading", { name: "docgroups.parties" }).parentElement!;
    await userEvent.click(within(parties).getByRole("button", { name: "docgroups.change" }));
    expect(screen.getByLabelText(/Afzender/)).toBeInTheDocument();
  });

  it("says how many a group still wants", () => {
    render(<Harness filled={{ consignor_name: "Mooiweer BV" }} />);
    expect(screen.getByText("docgroups.complete")).toBeInTheDocument();
    // Route and additions each still want one.
    expect(screen.getAllByText("docgroups.stillNeeded:1")).toHaveLength(2);
  });
});

describe("Next tells before it walks on", () => {
  it("names the empty required fields instead of finishing the step", async () => {
    const onDone = vi.fn();
    render(<Harness onDone={onDone} />);
    await userEvent.click(screen.getByRole("button", { name: "wizard.toExport" }));
    expect(screen.getByRole("alert")).toHaveTextContent("docfields.stillEmpty:3");
    expect(onDone).not.toHaveBeenCalled();
  });

  it("marks the field itself, and unmarks it the moment something is typed", async () => {
    render(<Harness />);
    await userEvent.click(screen.getByRole("button", { name: "wizard.toExport" }));
    expect(screen.getAllByText("docfields.fieldMissing")).toHaveLength(3);
    await userEvent.type(screen.getByLabelText(/Afzender/), "Mooiweer BV");
    expect(screen.getAllByText("docfields.fieldMissing")).toHaveLength(2);
  });

  it("says nothing while somebody is only typing", async () => {
    render(<Harness />);
    await userEvent.type(screen.getByLabelText(/Afzender/), "Moo");
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.queryByText("docfields.fieldMissing")).toBeNull();
  });

  it("a second press goes on regardless: nothing here is blocked", async () => {
    const onDone = vi.fn();
    render(<Harness onDone={onDone} />);
    await userEvent.click(screen.getByRole("button", { name: "wizard.toExport" }));
    await userEvent.click(screen.getByRole("button", { name: "docfields.continueAnyway" }));
    expect(onDone).toHaveBeenCalled();
  });

  it("a summary entry takes the cursor to its field", async () => {
    render(<Harness />);
    await userEvent.click(screen.getByRole("button", { name: "wizard.toExport" }));
    await userEvent.click(within(screen.getByRole("alert")).getByRole("button", { name: "Afzender" }));
    await waitFor(() => expect(screen.getByLabelText(/Afzender/)).toHaveFocus());
  });

  it("opens a folded group that is hiding something empty", async () => {
    // The parties group is complete and folded; the route group is not.
    render(<Harness filled={{ consignor_name: "Mooiweer BV" }} />);
    expect(screen.queryByLabelText(/Afzender/)).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "wizard.toExport" }));
    expect(screen.getByRole("alert")).toHaveTextContent("docfields.stillEmpty:2");
    expect(screen.getByLabelText(/Laadplaats/)).toBeInTheDocument();
  });
});

describe("arriving at one field from somewhere else", () => {
  it("opens the group the field is in and puts the cursor in it", async () => {
    render(<Harness filled={{ consignor_name: "Mooiweer BV", loading_point: "Rotterdam", place_of_issue: "" }} focusField="consignor_name" />);
    await waitFor(() => expect(screen.getByLabelText(/Afzender/)).toHaveFocus());
    expect(document.getElementById(fieldId("consignor_name"))).toBeTruthy();
  });

  it("offers the way straight back to where the question was asked", async () => {
    const onReturn = vi.fn();
    render(<Harness focusField="consignor_name" returnLabel="wizard.backToOverview" onReturn={onReturn} />);
    await userEvent.click(screen.getByRole("button", { name: "wizard.backToOverview" }));
    expect(onReturn).toHaveBeenCalled();
  });

  it("without a caller waiting there is no return action", () => {
    render(<Harness />);
    expect(screen.queryByRole("button", { name: "wizard.backToOverview" })).toBeNull();
  });
});
