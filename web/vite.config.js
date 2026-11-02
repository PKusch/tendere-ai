import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));

// The dashboard component lives at the repo root (../dashboard.jsx) and stays the
// single source of truth — this app just mounts it. fs.allow lets the dev server
// read it from outside the web/ root; the production build bundles it in directly.
// base is "/" for Netlify/Vercel (served at the domain root) and "/tendere-ai/"
// for a GitHub Pages project site (served under the repo name). The Pages workflow
// sets GH_PAGES=true; local dev and other hosts serve at root.
export default defineConfig({
  base: process.env.GH_PAGES ? "/tendere-ai/" : "/",
  plugins: [react()],
  // dashboard.jsx sits outside web/, so Vite 8 would not find web/node_modules for its imports.
  resolve: {
    alias: [
      { find: /^react$/, replacement: here("./node_modules/react") },
      { find: /^react\/(.*)$/, replacement: here("./node_modules/react") + "/$1" },
      { find: /^react-dom$/, replacement: here("./node_modules/react-dom") },
      { find: /^react-dom\/(.*)$/, replacement: here("./node_modules/react-dom") + "/$1" },
    ],
  },
  server: { fs: { allow: [".."] } },
});
