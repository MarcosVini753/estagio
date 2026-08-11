import { copyFile, mkdir } from "node:fs/promises";
import { dirname } from "node:path";

const assets = [
  ["node_modules/htmx.org/dist/htmx.min.js", "backend/static/vendor/htmx.min.js"],
  ["node_modules/alpinejs/dist/cdn.min.js", "backend/static/vendor/alpine.min.js"],
];

for (const [source, destination] of assets) {
  await mkdir(dirname(destination), { recursive: true });
  await copyFile(source, destination);
}
