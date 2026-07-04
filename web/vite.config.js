import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dashboard component lives at the repo root (../dashboard.jsx) and stays the
// single source of truth — this app just mounts it. fs.allow lets the dev server
// read it from outside the web/ root; the production build bundles it in directly.
export default defineConfig({
  plugins: [react()],
  server: { fs: { allow: [".."] } },
});
