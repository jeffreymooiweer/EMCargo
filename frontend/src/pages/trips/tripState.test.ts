import { expect, it } from "vitest";
import type { TripConsignment, TripResult } from "../../api/client";
import { assessmentTone, readMass, readConsignment } from "./tripState";
const consignments: TripConsignment[] = [{ name: "DG", entries: [{ products: [{}] }], profiles: ["ADR"] }];
function result(): TripResult { return { consignments: [], adr_points: { total_points: 0, threshold: 1000, status: "exempt_possible" }, mixed_loading: [], exemption_lost: null, lq_marking: { rule: "", message: "", lq_gross_kg: 0, required: null, reason: "", orange_plates_required: null } }; }
it("does not equate below-threshold points with permission to depart", () => {
  const value = result(); value.adr_points.forbidden_products = ["UN 9999"];
  expect(assessmentTone(value, consignments)).toBe("blocked");
  delete value.adr_points.forbidden_products;
  value.mixed_loading = [{ message: "Unknown compatibility", severity: "warning" }];
  expect(assessmentTone(value, consignments)).toBe("attention");
  value.mixed_loading = [{ message: "Forbidden mix", severity: "error" }];
  expect(assessmentTone(value, consignments)).toBe("blocked");
});
it("keeps unknown quantities, unknown rules and missing LQ mass visibly incomplete", () => {
  const value = result(); value.adr_points.status = "incomplete";
  expect(assessmentTone(value, consignments)).toBe("incomplete");
  value.adr_points.status = "new_status";
  expect(assessmentTone(value, consignments)).toBe("incomplete");
  value.adr_points.status = "exempt_possible"; value.lq_marking.lq_gross_kg = 9000;
  expect(assessmentTone(value, consignments)).toBe("incomplete");
  expect(assessmentTone(result(), [{ ...consignments[0], profiles: ["IMDG"] }])).toBe("incomplete");
});
it.each(["-1", "0", "201", "1e2", "NaN", "12.5.2", "12 ton"])("refuses invalid mass %s", value => expect(readMass(value)).toBeUndefined());
it("accepts an explicitly unknown vehicle mass and local decimal punctuation", () => { expect(readMass("")).toBeNull(); expect(readMass("12,5")).toBe(12.5); });
it("does not discard malformed product data as ordinary freight", () => {
  expect(() => readConsignment({ format: "emcargo.shipment", regulations: ["ADR"], consignment: {}, dangerous_goods: [{ products: "lost" }] }, "x")).toThrow();
});

it("accepts the actual ordinary export while refusing missing DG declarations", () => {
  const payload = { format: "emcargo.shipment", format_version: "2.1", consignment: {},
    goods: [{ include: true, dangerous_goods: false, detected_un_numbers: [] }] };
  expect(readConsignment(payload, "Ordinary", 1)).toMatchObject({ shipment_id: 1, entries: [], profiles: [] });
  expect(readConsignment({ ...payload, regulations: ["ADR"] }, "Ordinary")).toMatchObject({ entries: [], profiles: ["ADR"] });
  for (const goods of [[], [{}], [{ dangerous_goods: true }], [{ dangerous_goods: false, detected_un_numbers: ["1203"] }]]) {
    expect(() => readConsignment({ ...payload, goods }, "Incomplete")).toThrow();
  }
  expect(() => readConsignment({ ...payload, dangerous_goods: null }, "Invalid")).toThrow();
});
