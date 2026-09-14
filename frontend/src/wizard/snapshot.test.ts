import { describe, expect, it } from "vitest";

import { SNAPSHOT_VERSION, readSnapshot, templateValues } from "./snapshot";

it("retains accepted document evidence on reopening and ignores malformed evidence", () => {
  const evidence = { name: "packing.pdf", sha256: "a".repeat(64), pages: [1, 2], excerpt: "12 boxes 240 kg", method: "ocr", target: "goods:1", value: "12 boxes · 240 kg (total)" };
  const read = readSnapshot({ version: 1, documentEvidence: [evidence, { ...evidence, pages: [999] }, null] });
  expect(read?.documentEvidence).toEqual([evidence]);
  expect(readSnapshot({ version: 1 })).not.toHaveProperty("documentEvidence");
});

describe("een bewaarde wizardtoestand teruglezen", () => {
  it("geeft de brontoestand terug zoals hij was", () => {
    const stored = {
      version: SNAPSHOT_VERSION,
      modality: "road",
      stepKey: "export",
      docLang: "de",
      selectedDocs: ["cmr"],
      docValues: { reference: "CP-1", consignor_name: "Afzender BV" },
      skippedQuestions: ["q1"],
      draftLines: [{ id: 3, description: "Vaten", quantity: 4, unit: "pcs" }],
      nextId: 4,
      result: { success: true, column_map: {}, lines: [{ id: 3 }], totals: {}, errors: [] },
      dgEntries: [{ line_id: "3", products: [] }],
      signature: "data:image/png;base64,AAAA",
    };
    const read = readSnapshot(stored)!;
    expect(read.stepKey).toBe("export");
    expect(read.docLang).toBe("de");
    expect(read.selectedDocs).toEqual(["cmr"]);
    expect(read.docValues.reference).toBe("CP-1");
    expect(read.draftLines[0].description).toBe("Vaten");
    expect(read.nextId).toBe(4);
    expect(read.result?.lines).toHaveLength(1);
    expect(read.dgEntries).toHaveLength(1);
    expect(read.signature).toBe("data:image/png;base64,AAAA");
  });

  it("weigert wat geen snapshot is, en een versie die deze code niet kent", () => {
    // A row somebody edited by hand, or one written by a later version with
    // a shape this one cannot read, must not crash the wizard.
    expect(readSnapshot(null)).toBeNull();
    expect(readSnapshot("{}")).toBeNull();
    expect(readSnapshot({})).toBeNull();
    expect(readSnapshot({ version: SNAPSHOT_VERSION + 1 })).toBeNull();
  });

  it("vult wat ontbreekt met veilige waarden in plaats van te breken", () => {
    const read = readSnapshot({ version: 1, stepKey: "somewhere", docValues: { a: 1, b: "two" } })!;
    expect(read.stepKey).toBe("lines");
    expect(read.docValues).toEqual({ b: "two" });
    expect(read.draftLines).toHaveLength(1);
    expect(read.nextId).toBe(2);
    expect(read.result).toBeNull();
    expect(read.dgEntries).toEqual([]);
    expect(read.selectedDocs).toBeNull();
    expect(read.signature).toBeNull();
  });

  it("leidt het volgende regelnummer af uit de regels als het ontbreekt", () => {
    const read = readSnapshot({
      version: 1,
      draftLines: [{ id: 7, description: "x", quantity: 1, unit: "pcs" }, { id: 2, description: "y", quantity: 1, unit: "pcs" }],
    })!;
    expect(read.nextId).toBe(8);
  });
});

describe("een bewaarde zending als sjabloon", () => {
  it("laat de referenties en datums los en houdt de rest", () => {
    const fresh = templateValues({
      shipment_reference: "CP-1",
      booking_number: "BK-9",
      awb_number: "057-12345675",
      loading_date: "2026-09-01",
      declaration_date: "2026-09-01",
      consignor_name: "Afzender BV",
      consignor_address: "Havenweg 1",
      place_of_delivery: "Duisburg",
      contract_number: "C-2024-7",
    });
    expect(fresh).toEqual({
      consignor_name: "Afzender BV",
      consignor_address: "Havenweg 1",
      place_of_delivery: "Duisburg",
      contract_number: "C-2024-7",
    });
  });

  it("neemt geen ondertekende verklaring mee naar de kopie", () => {
    // A copy that arrives with last week's confirmation already ticked is a
    // form declaring something about goods nobody has looked at.
    const fresh = templateValues(
      {
        consignor_name: "Afzender BV",
        packing_certificate_confirmed: "true",
        receipt_confirmation: "true",
      },
      ["packing_certificate_confirmed", "receipt_confirmation"],
    );
    expect(fresh).toEqual({ consignor_name: "Afzender BV" });
  });
});
