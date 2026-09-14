/** Render the website SVG's alpha filter for mail and document clients. */
import { mkdir } from "node:fs/promises";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const source = fileURLToPath(new URL("../public/emcargo.svg", import.meta.url));
const destination = process.argv[2] || fileURLToPath(new URL("../../backend/app/assets/logo.png", import.meta.url));

await mkdir(dirname(destination), { recursive: true });
await sharp(source)
  .resize(192, 192, { fit: "contain", background: { r: 0, g: 0, b: 0, alpha: 0 } })
  .png()
  .toFile(destination);
console.log(destination);
