import { buildNotices } from "./buildNotices";
import { reviewBridge } from "./reviewBridge";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command, mode }) => ({
  plugins: [react(), buildNotices(), ...(command === "serve" && mode === "development" && loadEnv(mode, process.cwd(), "").EMCARGO_VISUAL_REVIEW === "true" ? [reviewBridge()] : [])],
  server: {
    host: "0.0.0.0",
    allowedHosts: ["terminal.local"],
    proxy: {
      "/api": "http://localhost:8080",
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
}));
