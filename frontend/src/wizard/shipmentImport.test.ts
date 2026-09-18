import { describe, expect, it } from "vitest";
import { readShipmentFile } from "./shipmentImport";

describe("shipment source import", () => {
  const source = () => ({ format: "emcargo.shipment", format_version: "3.0",
    goods: [{ line_id: 1, cargo_goods_id: 7, description: "Boxes", quantity: 10, unit: "pcs", weight_total_kg: 100 }],
    consignment: { shipment_reference: "SOURCE" },
    routing: { version: 1, locations: [], distributions: [{ id: "old", goods_id: "7", quantity: "10", pickup_id: "p", delivery_id: "a", unit_ids: ["box"], dangerous_goods: [], dg_confirmation: { accepted: true } }] },
    cargo: { schema_version: 1, shipment_id: "old-shipment", revision: 2, units: [{ id: "box", code: "BOX-OLD", name: "Box", category: "box", kind: "package", tare_kg: 2 }], allocations: [{ id: "packed", goods_id: 7, unit_id: "box", quantity: 10 }] },
  });
  it("copies facts and packing relationships with fresh identities and no approval", () => {
    const imported = readShipmentFile(source())!;
    expect(imported).not.toBeNull();
    expect(imported.cargo?.shipment_id).not.toBe("old-shipment");
    expect(imported.routing?.distributions[0].unit_ids).toEqual([imported.cargo?.units[0].id]);
    expect(imported.routing?.distributions[0].dg_confirmation).toBeNull();
    expect(imported.routing?.distributions[0].id).not.toBe("old");
    expect(imported.draftLines[0].id).toBe(7);
    expect(imported.selectedDocs).toEqual([]);
    expect(imported.signature).toBeNull();
  });
  it("opens an older export without inventing missing country or address", () => {
    const imported = readShipmentFile({ format: "emcargo.shipment", format_version: "2.1", goods: source().goods,
      consignment: { consignor_name: "Sender", consignee_name: "Receiver" } })!;
    expect(imported.routing?.locations[0].country).toBe("");
    expect(imported.routing?.locations[0].address).toBe("");
    expect(imported.routing?.distributions[0].goods_id).toBe("7");
  });
  it("rejects unknown versions and unrelated files", () => {
    expect(readShipmentFile({ ...source(), format_version: "99.0" })).toBeNull();
    expect(readShipmentFile({ anything: true })).toBeNull();
  });
});
