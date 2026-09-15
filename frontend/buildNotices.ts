/** Inventory packages whose modules actually enter the browser chunks.
 * npm's omit=dev inventory can omit shared peer dependencies; its output is
 * therefore not sufficient evidence for a compiled frontend distribution.
 */
import { readFileSync, existsSync, readdirSync } from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import type { Plugin } from "vite";

export function buildNotices(): Plugin {
  return {
    name: "emcargo-distribution-notices",
    apply: "build",
    generateBundle(_options, bundle) {
      const packages = new Map<string, { root: string; name: string; version: string; license?: string }>();
      for (const output of Object.values(bundle)) {
        if (output.type !== "chunk") continue;
        for (const id of Object.keys(output.modules)) {
          if (!id.includes("/node_modules/")) continue;
          let directory = path.dirname(id.replace(/^\0/, "").split("?")[0]);
          while (directory.includes("/node_modules/")) {
            const metadata = path.join(directory, "package.json");
            if (existsSync(metadata)) {
              const data = JSON.parse(readFileSync(metadata, "utf8"));
              if (data.name && data.version) {
                packages.set(`${data.name}@${data.version}`, { ...data, root: directory });
                break;
              }
            }
            directory = path.dirname(directory);
          }
        }
      }
      if (!packages.size) this.error("No bundled third-party modules were inventoried");
      const components = [];
      for (const item of [...packages.values()].sort((a, b) => a.name.localeCompare(b.name))) {
        const files = readdirSync(item.root, { withFileTypes: true })
          .filter(f => f.isFile() && /^(licen[cs]e|notice|copying|copyright)(\.|$)/i.test(f.name));
        if (!files.length) this.error(`Missing license evidence for bundled package ${item.name}`);
        const notices = files.map(file => {
          const content = readFileSync(path.join(item.root, file.name));
          const name = `licenses/${item.name.replace(/[^a-zA-Z0-9_.-]/g, "_")}-${item.version}/${file.name}`;
          this.emitFile({ type: "asset", fileName: name, source: content });
          return { path: name, sha256: createHash("sha256").update(content).digest("hex") };
        });
        components.push({ type: "library", name: item.name, version: item.version,
          purl: `pkg:npm/${item.name.split("/").map(encodeURIComponent).join("/")}@${item.version}`,
          licenses: [{ license: { name: item.license || "NOASSERTION" } }],
          properties: [{ name: "emcargo:license-files", value: JSON.stringify(notices) }] });
      }
      const bom = { bomFormat: "CycloneDX", specVersion: "1.6", version: 1,
        metadata: { component: { type: "application", name: "EMCargo compiled browser bundle" } }, components };
      this.emitFile({ type: "asset", fileName: "compliance/frontend.cdx.json", source: JSON.stringify(bom, null, 2) + "\n" });
    },
  };
}
