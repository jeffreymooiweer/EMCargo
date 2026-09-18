/**
 * What the user gets to see when the server refuses their input.
 *
 * On a 422 FastAPI sends not a sentence but a list of `{loc, msg}` per field.
 * That went straight into `new Error()`, which produced "[object Object]": the
 * user saw *that* something was wrong, but not what, and certainly not which
 * field. Since v1.24.0 the compliance endpoint refuses unusable input, so this
 * is no longer an edge case but the normal path.
 *
 * Since v1.48.0 an error also carries a **code**, because the server cannot
 * translate: it raises deep in a service that has no idea who is asking, and
 * the language belongs to the screen. These tests run without a loaded language
 * bundle on purpose — that is the state the app is in on its very first paint,
 * and the English fallback has to survive it.
 */
import { describe, expect, it } from "vitest";

import { describeDetail, translateMessage } from "./client";

describe("een validatiefout van FastAPI leesbaar maken", () => {
  it("noemt het veld en de reden", () => {
    const text = describeDetail([
      {
        loc: ["body", "entries", 0, "products", 1, "adr_total_quantity"],
        msg: "Value error, quantity '-5 L' must be greater than zero",
        type: "value_error",
      },
    ]);
    expect(text).toBe(
      "entries → 0 → products → 1 → adr_total_quantity: " +
        "quantity '-5 L' must be greater than zero",
    );
  });

  it("laat 'body' weg, want dat zegt een gebruiker niets", () => {
    expect(describeDetail([{ loc: ["body", "profiles", 0], msg: "onbekend profiel" }]))
      .toBe("profiles → 0: onbekend profiel");
  });

  it("zet meerdere fouten onder elkaar", () => {
    const text = describeDetail([
      { loc: ["body", "profiles", 0], msg: "onbekend profiel" },
      { loc: ["body", "entries", 0], msg: "iets anders" },
    ]);
    expect(text.split("\n")).toHaveLength(2);
  });

  it("laat een gewone tekstmelding met rust", () => {
    expect(describeDetail("entries required")).toBe("entries required");
  });

  it("valt terug op een nette zin als er niets bruikbaars in zit", () => {
    expect(describeDetail(undefined)).toBe("Request failed");
    expect(describeDetail([])).toBe("Request failed");
    expect(describeDetail({})).toBe("Request failed");
  });

  it("vertaalt een boodschap met een code, en valt terug op de Engelse zin", () => {
    // Without a loaded language bundle the fallback is all there is; with one,
    // the translation wins. Both have to produce a readable sentence.
    expect(describeDetail({ code: "import.empty_file", message: "The file is empty" }))
      .toBe("The file is empty");
    expect(translateMessage({ code: "onbekend.iets", message: "" })).toBe("onbekend.iets");
  });

  it("gebruikt de code uit het type-veld van een 422", () => {
    // The validators put their code in `type` and their parameters in `ctx`;
    // that is the mechanism the interface translates a field error with.
    const text = describeDetail([
      {
        loc: ["body", "entries", 0, "products", 0, "adr_total_quantity"],
        msg: "quantity '0' must be greater than zero",
        type: "dg.quantity_not_positive",
        ctx: { value: "0" },
      },
    ]);
    expect(text).toContain("must be greater than zero");
    expect(text).not.toContain("dg.quantity_not_positive");
  });

  it("levert nooit [object Object] op", () => {
    for (const detail of [[{ loc: ["body"], msg: "x" }], [{}], {}, null, 42, { code: "x", message: "y" }]) {
      expect(describeDetail(detail)).not.toContain("[object Object]");
    }
  });
});


it("shows document field errors from the delivery issuance response", () => {
  expect(describeDetail({ errors: ["Required field missing: Date", "Required field missing: Place"] }))
    .toBe("Required field missing: Date\nRequired field missing: Place");
});
