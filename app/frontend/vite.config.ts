import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backend = process.env.VITE_BACKEND ?? "http://localhost:8010";

export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(process.env.VITE_PORT ?? 5180),
    strictPort: true,
    proxy: {
      "/api": backend,
    },
  },
  build: {
    outDir: "dist",
  },
});
