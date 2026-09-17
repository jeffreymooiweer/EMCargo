import { afterEach, expect, it, vi } from "vitest";
import { cargoApi, type PackagingTemplate } from "./cargo";

afterEach(() => { vi.unstubAllGlobals(); });
const model: PackagingTemplate = { id: "builtin-box", name: "Box", category: "box", builtin: true, active: true, version: 7, language_labels: { nl: "Doos", en: "Box", de: "Karton", fr: "Carton" } };

it("sends only the template contract when saving a catalogue object or a physical unit as a model", async () => {
  const fetch = vi.fn().mockResolvedValue({ ok: true, status: 200, headers: new Headers({ "content-type": "application/json" }), json: async () => model }); vi.stubGlobal("fetch", fetch);
  await cargoApi.updateTemplate(model);
  expect(fetch).toHaveBeenCalledWith("/api/cargo/templates/builtin-box", expect.objectContaining({ credentials: "include", method: "PUT" }));
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ name: "Box", category: "box", active: true, version: 7, language_labels: model.language_labels });
  await cargoApi.createTemplate({ ...model, kind: "package", code: "BOX-001", source: "unknown" } as PackagingTemplate);
  expect(JSON.parse(fetch.mock.calls[1][1].body)).not.toHaveProperty("kind");
  expect(JSON.parse(fetch.mock.calls[1][1].body)).not.toHaveProperty("id");
  expect(JSON.parse(fetch.mock.calls[1][1].body)).not.toHaveProperty("builtin");
});

it("archives exactly the model version the user reviewed", async () => {
  const fetch = vi.fn().mockResolvedValue({ ok: true, status: 200, headers: new Headers({ "content-type": "application/json" }), json: async () => ({ ...model, active: false, version: 8 }) }); vi.stubGlobal("fetch", fetch);
  const archived = await cargoApi.archiveTemplate(model);
  expect(fetch).toHaveBeenCalledWith("/api/cargo/templates/builtin-box?version=7", expect.objectContaining({ method: "DELETE" }));
  expect(archived.version).toBe(8);
});
