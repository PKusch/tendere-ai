# Tendere AI — hosted dashboard

A thin [Vite](https://vitejs.dev) + React wrapper that mounts the self-contained
`../dashboard.jsx` component. No backend, no data fetching — the demo logic and data
are inlined in the component, so this deploys as a static site.

## Run locally

```bash
cd web
npm install
npm run dev      # http://localhost:5173
```

## Build

```bash
npm run build    # -> web/dist  (static, self-contained)
npm run preview  # serve the build at http://localhost:4173
```

## Deploy (pick one)

**Fastest — Netlify Drop (no account setup, ~20s):**
1. `npm run build`
2. Go to https://app.netlify.com/drop
3. Drag the **`web/dist`** folder onto the page → you get a live URL instantly.

**From the GitHub repo — Vercel (best for a permanent link):**
1. https://vercel.com/new → import `PKusch/tendere-ai`
2. Set **Root Directory** to `web` (framework auto-detects as Vite).
3. Deploy → live URL, auto-redeploys on every push.

**CLI — Vercel:**
```bash
cd web && npx vercel --prod    # follow the browser login once
```
