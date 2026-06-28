import React, { useState, useMemo } from "react";

/* ============================================================
   Tendere AI — demo dashboard
   Reads a job spec, diffs it against a consultant's real profile,
   plans the roll-off runway. The diff is the hero; the gap-marker
   vocabulary replaces a ranked score.
   ============================================================ */

// ---------- palette / type ----------
const C = {
  surface: "#0E1213",
  card: "#161B1D",
  ink: "#E8ECEC",
  muted: "#9BA4A6",
  faint: "#6B7476",
  hair: "#262D2F",
  hairStrong: "#3A4244",
  signal: "#36C2C0", // teal — forward / high-value demand
  signalSoft: "rgba(54,194,192,0.12)",
  // semantic tints (dark)
  danger: "#F0707E",
  dangerBg: "rgba(178,58,72,0.16)",
  dangerBorder: "rgba(240,112,126,0.28)",
  amber: "#E0A53C",
  amberBg: "rgba(166,106,12,0.18)",
  indigo: "#8B86F0",
  indigoBg: "rgba(80,72,196,0.18)",
};
const MONO = 'ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace';
const SANS = 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';

// gap-marker vocabulary — the signature
const STATUS = {
  MET:             { label: "met",                  color: "#4FCB8C", bg: "rgba(31,138,91,0.16)", gutter: "=", glyph: "●" },
  STALE_THIN:      { label: "stale / thin",         color: "#E0A53C", bg: "rgba(166,106,12,0.18)", gutter: "~", glyph: "◑" },
  NO_CONTENT:      { label: "gap · no firm content",color: "#F0707E", bg: "rgba(178,58,72,0.18)", gutter: "!", glyph: "△" },
  LATENT_STRENGTH: { label: "latent strength",      color: "#8B86F0", bg: "rgba(80,72,196,0.18)", gutter: "?", glyph: "◇" },
  LEARNABLE:       { label: "gap · learnable",      color: "#36C2C0", bg: "rgba(54,194,192,0.16)", gutter: "+", glyph: "+" },
};

// ---------- data (mirrors the engine's json) ----------
const RANK = { none: 0, familiar: 1, moderate: 2, experienced: 3, deep: 4, certified: 4 };
const WEAK = new Set(["self-taught", "partial", "none"]);

const MAYA = {
  name: "Maya R.", seniority: "Consultant", rollOff: 7, geo: "UK",
  profile: [
    { item: "Business Analysis", type: "capability", level: "deep", recency: "current", evidence: "verified" },
    { item: "Core Banking", type: "domain", family: "Financial Services", level: "deep", recency: "current", evidence: "verified", note: "3+ years" },
    { item: "Commercial Banking", type: "domain", family: "Financial Services", level: "moderate", recency: "stale", evidence: "partial", note: "several years ago, plus a recent 3-month stint the client closed early" },
    { item: "Agile / Transformation", type: "capability", level: "certified", recency: "current", evidence: "certified" },
    { item: "Claude Cowork / GenAI tooling", type: "platform", level: "moderate", recency: "current", evidence: "self-taught", note: "lots of internal training in spare time, no cert, no formal showcase" },
  ],
  ambitions: ["Claude Cowork / GenAI tooling", "Operating Model"],
};

const SPECS = {
  "ROLE-Z": {
    id: "ROLE-Z", title: "BA — Commercial Banking", account: "Client Z · Tier-1 Bank",
    from: "Delivery Lead, Client Z", domainFamily: "Financial Services", suggested: false,
    raw: ["5+ years as a BA in commercial banking",
          "agile certified, worked on nCino platform before",
          "familiar with agile delivery lifecycle",
          "familiar and worked on Claude Cowork before"],
    reqs: [
      { item: "Business Analysis", need: "deep" },
      { item: "Commercial Banking", need: "deep" },
      { item: "Agile / Transformation", need: "certified" },
      { item: "nCino", need: "experienced" },
      { item: "Claude Cowork / GenAI tooling", need: "familiar" },
    ],
  },
  "ROLE-PH": {
    id: "ROLE-PH", title: "BA — Public Health Programme", account: "Public Sector",
    from: "Resourcing (auto-suggested)", domainFamily: "Public Sector", suggested: true,
    raw: ["BA for a public health transformation programme",
          "stakeholder management, process mapping",
          "available immediately"],
    reqs: [
      { item: "Business Analysis", need: "deep" },
      { item: "Public Health", need: "deep" },
    ],
  },
};

const CONTENT = {
  "Commercial Banking": { coverage: "refresh",
    items: [{ title: "Commercial Banking current-state primer", provider: "Provider B", hours: 4, verifiable: false },
            { title: "FS commercial products & lending update", provider: "Provider C", hours: 3, verifiable: false }] },
  "Claude Cowork / GenAI tooling": { coverage: "full",
    items: [{ title: "Applied GenAI / Cowork practitioner (capstone)", provider: "Provider A", hours: 18, verifiable: true }],
    evidence: "Internal capstone / showcase — converts self-taught → evidenced + Workday-credited." },
  "nCino": { coverage: "none",
    fragments: [{ title: "Assorted nCino intro decks", provider: "Internal share drive", hours: 2, verifiable: false }],
    workaround: "No real firm course exists. Options: vendor enablement (nCino University), or shadow a certified colleague on a live engagement." },
};

const DEMAND = {
  "Claude Cowork / GenAI tooling": { acuteness: "critical", recurrence: "most accounts", value: 98 },
  "nCino": { acuteness: "high", recurrence: "FS accounts", value: 74 },
};

// ---------- engine (ported) ----------
function classify(req, pmap) {
  const p = pmap[req.item];
  const need = RANK[req.need] ?? 2;
  if (!p) {
    const cov = CONTENT[req.item]?.coverage ?? "none";
    return cov === "full" || cov === "refresh" ? "LEARNABLE" : "NO_CONTENT";
  }
  const have = RANK[p.level] ?? 0;
  const stale = p.recency === "stale";
  const weak = WEAK.has(p.evidence);
  if (have >= need && !stale && !weak) return "MET";
  if (have >= need && weak && !stale) return "LATENT_STRENGTH";
  if (stale || have < need) return "STALE_THIN";
  return "MET";
}
function runDiff(spec) {
  const pmap = Object.fromEntries(MAYA.profile.map((e) => [e.item, e]));
  const rows = spec.reqs.map((r) => ({ req: r, status: classify(r, pmap), have: pmap[r.item] || null }));
  const asked = new Set(spec.reqs.map((r) => r.item));
  const transferable = MAYA.profile.filter((e) => !asked.has(e.item) && (e.level === "deep" || e.level === "experienced"));
  return { rows, transferable };
}
function verdict(spec, rows) {
  const famMatch = new Set(MAYA.profile.map((e) => e.family)).has(spec.domainFamily);
  const voids = rows.filter((r) => r.status === "NO_CONTENT");
  const stale = rows.filter((r) => r.status === "STALE_THIN");
  const metCore = rows.filter((r) => r.status === "MET" || r.status === "LATENT_STRENGTH");
  if (!famMatch) return { tone: "bad", title: "Surface match — strategic misfit",
    gloss: `A skill keyword matches, but the domain family is wrong (${spec.domainFamily} vs Maya's Financial Services background). Off-trajectory — don't auto-route here.` };
  if (metCore.length && voids.length) return { tone: "good", title: "Strong fit — gaps include a provision hole",
    gloss: "Right domain, most of the spec already met. One gap has no firm content — plan around it." };
  if (metCore.length && stale.length) return { tone: "good", title: "Strong fit — narrow, closeable gaps",
    gloss: "Right domain, most of the spec met. Gaps close inside the runway. Tag, prepare, place ready." };
  if (metCore.length) return { tone: "good", title: "Strong fit", gloss: "Right domain, spec met." };
  return { tone: "warn", title: "Stretch fit", gloss: "Right direction; meaningful gaps." };
}
function buildPlan(rows, weeklyHours, runway) {
  const actions = [];
  for (const r of rows) {
    const item = r.req.item, s = r.status, c = CONTENT[item] || {}, dem = DEMAND[item] || null;
    if (s === "MET") continue;
    if (s === "STALE_THIN") actions.push({ item, kind: "REFRESH", priority: 1, headline: `Refresh currency in ${item}`,
      content: c.items || [], evidence: "Frame the recent stint as evidence; restore to current.", dem });
    else if (s === "NO_CONTENT") actions.push({ item, kind: "NO_FIRM_CONTENT", priority: 2, headline: `${item}: no firm course exists`,
      content: c.fragments || [], workaround: c.workaround, provision: true, dem });
    else if (s === "LATENT_STRENGTH") actions.push({ item, kind: "EVIDENCE_LATENT", priority: 3, headline: `Surface ${item}; optional accelerant`,
      content: (c.items || []).filter((i) => i.verifiable), evidence: c.evidence, future: true, dem });
    else if (s === "LEARNABLE") actions.push({ item, kind: "BUILD", priority: 2, headline: `Build ${item}`, content: c.items || [], dem });
  }
  actions.sort((a, b) => a.priority - b.priority);

  // calendar-aware schedule
  const weeks = Array.from({ length: runway }, () => []);
  let cursor = 0, budget = weeklyHours;
  for (const a of actions) {
    if (["REFRESH", "BUILD", "NO_FIRM_CONTENT"].includes(a.kind)) {
      for (const it of a.content) {
        if (it.hours > budget && cursor < runway - 1) { cursor++; budget = weeklyHours; }
        weeks[cursor].push({ label: it.title, hours: it.hours, item: a.item, kind: a.kind });
        budget -= it.hours;
      }
    } else if (a.kind === "EVIDENCE_LATENT" && a.content[0]) {
      const it = a.content[0], per = Math.round((it.hours / runway) * 10) / 10;
      for (let w = 0; w < runway; w++) weeks[w].push({ label: it.title, hours: per, item: a.item, kind: a.kind, track: true });
    }
  }
  return { actions, weeks };
}
function workdayFx(actions) {
  const out = [];
  for (const a of actions) {
    if (a.kind === "REFRESH") out.push({ item: a.item, from: "stale", to: "current", note: "Logged in Workday; profile updated." });
    else if (a.kind === "EVIDENCE_LATENT") out.push({ item: a.item, from: "self-taught", to: "evidenced", note: "Workday credit; profile uplift; counts toward the high-value AI capability the firm is short on." });
    else if (a.kind === "NO_FIRM_CONTENT") out.push({ item: a.item, from: "no provision", to: "flagged", note: "Vendor/shadow logged as effort; raised to capability lead as a provision gap." });
  }
  return out;
}

// ---------- small UI atoms ----------
function Marker({ status, small }) {
  const s = STATUS[status];
  return (
    <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center",
      width: small ? 18 : 22, height: small ? 18 : 22, borderRadius: 5, background: s.bg,
      color: s.color, fontFamily: MONO, fontSize: small ? 11 : 13, fontWeight: 700, flexShrink: 0 }}>
      {s.glyph}
    </span>
  );
}
function Chip({ status }) {
  const s = STATUS[status];
  return (
    <span style={{ fontFamily: MONO, fontSize: 11, letterSpacing: ".02em", color: s.color,
      background: s.bg, padding: "3px 8px", borderRadius: 5, whiteSpace: "nowrap", fontWeight: 600 }}>
      {s.label}
    </span>
  );
}
function DemandTag({ dem }) {
  if (!dem) return null;
  const crit = dem.acuteness === "critical";
  return (
    <span style={{ fontFamily: MONO, fontSize: 10.5, color: crit ? "#fff" : C.signal,
      background: crit ? C.signal : C.signalSoft, padding: "2px 7px", borderRadius: 4,
      fontWeight: 600, letterSpacing: ".02em" }}>
      firm demand · {dem.acuteness} · {dem.value}
    </span>
  );
}

// ---------- main ----------
export default function TendereAI() {
  const [specId, setSpecId] = useState("ROLE-Z");
  const [hours, setHours] = useState(4);
  const spec = SPECS[specId];
  const { rows, transferable } = useMemo(() => runDiff(spec), [specId]);
  const v = useMemo(() => verdict(spec, rows), [specId]);
  const plan = useMemo(() => buildPlan(rows, hours, MAYA.rollOff), [specId, hours]);
  const fx = useMemo(() => workdayFx(plan.actions), [plan]);
  const provision = plan.actions.find((a) => a.provision);
  const isMisfit = v.tone === "bad";

  const toneColor = v.tone === "good" ? C.signal : v.tone === "bad" ? C.danger : C.amber;
  const toneBg = v.tone === "good" ? C.signalSoft : v.tone === "bad" ? C.dangerBg : C.amberBg;

  return (
    <div style={{ background: C.surface, color: C.ink, fontFamily: SANS, minHeight: "100%",
      padding: "0", lineHeight: 1.5 }}>
      <style>{`
        * { box-sizing: border-box; }
        .bc-wrap { max-width: 1080px; margin: 0 auto; padding: 28px 22px 56px; }
        .bc-card { background: ${C.card}; border: 1px solid ${C.hair}; border-radius: 12px; }
        .bc-fade { animation: bcFade .32s ease both; }
        @keyframes bcFade { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
        .bc-tab { cursor: pointer; border: 1px solid ${C.hair}; background: ${C.card};
          border-radius: 9px; padding: 11px 14px; text-align: left; transition: border-color .15s, box-shadow .15s; font-family: ${SANS}; }
        .bc-tab:hover { border-color: ${C.hairStrong}; }
        .bc-tab:focus-visible { outline: 2px solid ${C.signal}; outline-offset: 2px; }
        .bc-step { cursor: pointer; width: 26px; height: 26px; border-radius: 6px; border: 1px solid ${C.hairStrong};
          background: ${C.card}; color: ${C.ink}; font-size: 15px; line-height: 1; font-family: ${MONO}; }
        .bc-step:hover { background: ${C.surface}; }
        .bc-row { display: grid; grid-template-columns: 22px 1fr auto; gap: 12px; align-items: start;
          padding: 13px 0; border-top: 1px solid ${C.hair}; }
        .bc-weeks { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 6px; }
        .bc-week { min-width: 116px; flex: 1; }
        @media (max-width: 720px) { .bc-grid2 { grid-template-columns: 1fr !important; } .bc-hero { grid-template-columns: 1fr !important; } }
      `}</style>

      <div className="bc-wrap">
        {/* header */}
        <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 22, flexWrap: "wrap", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <svg width="30" height="30" viewBox="0 0 30 30" fill="none" aria-hidden="true">
              <circle cx="15" cy="15" r="13" stroke={C.signal} strokeWidth="1.6" />
              <path d="M15 7 L18 15 L15 23 L12 15 Z" fill={C.signal} opacity="0.85" />
              <circle cx="15" cy="15" r="1.6" fill={C.card} />
            </svg>
            <div>
              <div style={{ fontWeight: 700, fontSize: 18, letterSpacing: "-.01em" }}>Tendere AI</div>
              <div style={{ fontFamily: MONO, fontSize: 11.5, color: C.faint }}>reads the spec · maps the person · plans the runway</div>
            </div>
          </div>
          <div style={{ fontFamily: MONO, fontSize: 11, color: C.faint, textAlign: "right" }}>
            supply ↔ demand · pre-bench
          </div>
        </header>

        {/* subject + controls */}
        <div className="bc-card" style={{ padding: "16px 18px", marginBottom: 18, display: "flex",
          alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 14, flexWrap: "wrap" }}>
            <span style={{ fontWeight: 700, fontSize: 17 }}>{MAYA.name}</span>
            <span style={{ fontFamily: MONO, fontSize: 12.5, color: C.muted }}>{MAYA.seniority}</span>
            <span style={{ fontFamily: MONO, fontSize: 12.5, color: C.muted }}>· {MAYA.geo}</span>
            <span style={{ fontFamily: MONO, fontSize: 12.5, color: C.signal, fontWeight: 600 }}>· rolls off in {MAYA.rollOff}w</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontFamily: MONO, fontSize: 11.5, color: C.muted }}>learning budget</span>
            <button className="bc-step" onClick={() => setHours((h) => Math.max(1, h - 1))} aria-label="Decrease weekly hours">−</button>
            <span style={{ fontFamily: MONO, fontSize: 13, fontWeight: 700, minWidth: 44, textAlign: "center" }}>{hours}h/wk</span>
            <button className="bc-step" onClick={() => setHours((h) => Math.min(12, h + 1))} aria-label="Increase weekly hours">+</button>
          </div>
        </div>

        {/* role toggle — the demo lever */}
        <div style={{ marginBottom: 18 }}>
          <div style={{ fontFamily: MONO, fontSize: 11, color: C.faint, marginBottom: 8, letterSpacing: ".03em" }}>
            ROLE UNDER CONSIDERATION
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }} className="bc-grid2">
            {Object.values(SPECS).map((s) => {
              const active = s.id === specId;
              return (
                <button key={s.id} className="bc-tab" onClick={() => setSpecId(s.id)}
                  style={{ borderColor: active ? C.signal : C.hair, boxShadow: active ? `0 0 0 1px ${C.signal}` : "none",
                    background: active ? C.signalSoft : C.card }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                    <span style={{ fontWeight: 700, fontSize: 14 }}>{s.title}</span>
                    {s.suggested && <span style={{ fontFamily: MONO, fontSize: 10, color: C.faint }}>auto-suggested</span>}
                  </div>
                  <div style={{ fontFamily: MONO, fontSize: 11.5, color: C.muted, marginTop: 2 }}>{s.account} · {s.from}</div>
                </button>
              );
            })}
          </div>
        </div>

        {/* HERO: spec received -> diff */}
        <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 16, marginBottom: 18 }} className="bc-hero">
          {/* spec as received */}
          <div className="bc-card" style={{ padding: 16 }}>
            <div style={{ fontFamily: MONO, fontSize: 11, color: C.faint, marginBottom: 10, letterSpacing: ".03em" }}>
              SPEC, AS RECEIVED
            </div>
            <div style={{ fontFamily: MONO, fontSize: 12.5, color: C.ink, lineHeight: 1.7 }}>
              {spec.raw.map((b, i) => (
                <div key={i} style={{ display: "flex", gap: 7 }}>
                  <span style={{ color: C.hairStrong }}>–</span><span>{b}</span>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 14, paddingTop: 12, borderTop: `1px solid ${C.hair}`,
              fontFamily: MONO, fontSize: 10.5, color: C.faint }}>
              parsed by LLM → structured requirements
            </div>
          </div>

          {/* verdict + diff */}
          <div className="bc-card bc-fade" key={specId} style={{ padding: 16 }}>
            <div style={{ background: toneBg, border: `1px solid ${toneColor}22`, borderRadius: 9,
              padding: "12px 14px", marginBottom: 6 }}>
              <div style={{ fontFamily: MONO, fontSize: 13.5, fontWeight: 700, color: toneColor, letterSpacing: ".01em" }}>
                {v.title}
              </div>
              <div style={{ fontSize: 13, color: C.ink, marginTop: 4, opacity: 0.92 }}>{v.gloss}</div>
            </div>

            <div style={{ fontFamily: MONO, fontSize: 11, color: C.faint, margin: "14px 0 2px", letterSpacing: ".03em" }}>
              SPEC × MAYA — THE DIFF
            </div>
            <div>
              {rows.map((r, i) => {
                const s = STATUS[r.status];
                return (
                  <div className="bc-row" key={r.req.item}>
                    <span style={{ fontFamily: MONO, color: s.color, fontWeight: 700, fontSize: 15, textAlign: "center" }}>{s.gutter}</span>
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                        <span style={{ fontWeight: 600, fontSize: 14 }}>{r.req.item}</span>
                        <DemandTag dem={DEMAND[r.req.item]} />
                      </div>
                      {r.have?.note && (
                        <div style={{ fontSize: 12.5, color: C.muted, marginTop: 3, fontStyle: "italic" }}>{r.have.note}</div>
                      )}
                    </div>
                    <Chip status={r.status} />
                  </div>
                );
              })}
            </div>
            {transferable.length > 0 && (
              <div style={{ marginTop: 12, paddingTop: 11, borderTop: `1px solid ${C.hair}`,
                fontFamily: MONO, fontSize: 11.5, color: C.muted }}>
                + transferable, not asked for: {transferable.map((e) => e.item).join(", ")}
              </div>
            )}
          </div>
        </div>

        {/* PLAN or REDIRECT */}
        {isMisfit ? (
          <div className="bc-card bc-fade" key={"misfit" + specId} style={{ padding: 18, marginBottom: 18,
            borderColor: C.dangerBorder, background: C.dangerBg }}>
            <div style={{ fontWeight: 700, fontSize: 15, color: C.danger, marginBottom: 6 }}>No learning plan — wrong direction</div>
            <div style={{ fontSize: 13.5, color: C.ink, maxWidth: 760 }}>
              This is the role a keyword search would surface: it matches on <b>Business Analysis</b> and availability, but it's the wrong
              domain family and off Maya's trajectory. Compass doesn't build a plan toward a misfit — it points to where she should go instead.
            </div>
            <button className="bc-tab" onClick={() => setSpecId("ROLE-Z")}
              style={{ marginTop: 14, display: "inline-block", width: "auto", borderColor: C.signal, background: C.signalSoft }}>
              <span style={{ fontWeight: 700, fontSize: 13.5, color: C.signal }}>→ See the right fit: BA — Commercial Banking, Client Z</span>
            </button>
          </div>
        ) : (
          <>
            {/* learning plan actions */}
            <div className="bc-card" style={{ padding: 18, marginBottom: 18 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4, flexWrap: "wrap", gap: 8 }}>
                <div style={{ fontWeight: 700, fontSize: 16 }}>Learning plan</div>
                <div style={{ fontFamily: MONO, fontSize: 11.5, color: C.muted }}>{MAYA.rollOff}w runway · {hours}h/week · scheduled around client calendar</div>
              </div>
              <div style={{ fontSize: 12.5, color: C.muted, marginBottom: 14 }}>
                Built from the diff — currency refresh, the provision-gap workaround, and the future-demand track. Not a one-size course list.
              </div>

              {plan.actions.map((a) => {
                const accent = a.kind === "NO_FIRM_CONTENT" ? C.danger : a.kind === "EVIDENCE_LATENT" ? C.indigo : C.signal;
                return (
                  <div key={a.item} style={{ borderLeft: `3px solid ${accent}`, paddingLeft: 14, marginBottom: 16 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 9, flexWrap: "wrap" }}>
                      <span style={{ fontFamily: MONO, fontSize: 10.5, fontWeight: 700, color: accent, letterSpacing: ".04em" }}>
                        {a.kind.replace(/_/g, " ")}
                      </span>
                      <span style={{ fontWeight: 600, fontSize: 14 }}>{a.headline}</span>
                      <DemandTag dem={a.dem} />
                    </div>
                    {a.content.map((it, j) => (
                      <div key={j} style={{ fontFamily: MONO, fontSize: 12.5, color: C.ink, marginTop: 6, display: "flex", gap: 8, flexWrap: "wrap" }}>
                        <span style={{ color: C.faint }}>›</span>
                        <span>{it.title}</span>
                        <span style={{ color: C.muted }}>({it.hours}h · {it.provider})</span>
                        {it.verifiable && <span style={{ color: C.signal, fontWeight: 600 }}>· verifiable</span>}
                      </div>
                    ))}
                    {a.workaround && (
                      <div style={{ fontSize: 12.5, color: C.danger, marginTop: 7, background: C.dangerBg, padding: "7px 10px", borderRadius: 6 }}>
                        ⚠ {a.workaround}
                      </div>
                    )}
                    {a.evidence && (
                      <div style={{ fontSize: 12, color: C.muted, marginTop: 6 }}>{a.evidence}</div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* weekly schedule */}
            <div className="bc-card" style={{ padding: 18, marginBottom: 18 }}>
              <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 3 }}>Weekly schedule</div>
              <div style={{ fontSize: 12.5, color: C.muted, marginBottom: 14 }}>
                Role-critical currency front-loaded; the verifiable AI track runs in parallel and continues past placement.
              </div>
              <div className="bc-weeks">
                {plan.weeks.map((w, i) => (
                  <div className="bc-week" key={i}>
                    <div style={{ fontFamily: MONO, fontSize: 11, color: i >= MAYA.rollOff - 1 ? C.signal : C.faint,
                      fontWeight: 600, marginBottom: 6, paddingBottom: 6, borderBottom: `1px solid ${C.hair}` }}>
                      wk {i + 1}{i >= MAYA.rollOff - 1 ? " · buffer" : ""}
                    </div>
                    {w.length === 0 && <div style={{ fontFamily: MONO, fontSize: 11, color: C.hairStrong }}>—</div>}
                    {w.map((it, j) => (
                      <div key={j} style={{ fontSize: 11, lineHeight: 1.35, marginBottom: 6,
                        padding: "5px 6px", borderRadius: 5,
                        background: it.track ? C.indigoBg : it.kind === "NO_FIRM_CONTENT" ? C.dangerBg : C.signalSoft,
                        color: it.track ? C.indigo : it.kind === "NO_FIRM_CONTENT" ? C.danger : C.signal }}>
                        <span style={{ fontFamily: MONO, fontWeight: 700 }}>{it.hours}h</span> {it.track ? "AI track" : it.item}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>

            {/* two panels */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }} className="bc-grid2">
              {/* workday */}
              <div className="bc-card" style={{ padding: 18 }}>
                <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 3 }}>Workday credit + reward</div>
                <div style={{ fontSize: 12.5, color: C.muted, marginBottom: 14 }}>Effort closes the loop — it lands on her profile.</div>
                {fx.map((f, i) => (
                  <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start", marginBottom: 12 }}>
                    <span style={{ fontFamily: MONO, fontSize: 12, color: C.faint, marginTop: 1 }}>{String(i + 1).padStart(2, "0")}</span>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{f.item}</div>
                      <div style={{ fontFamily: MONO, fontSize: 12, marginTop: 2 }}>
                        <span style={{ color: C.amber }}>{f.from}</span>
                        <span style={{ color: C.faint }}> → </span>
                        <span style={{ color: C.signal, fontWeight: 700 }}>{f.to}</span>
                      </div>
                      <div style={{ fontSize: 12, color: C.muted, marginTop: 3 }}>{f.note}</div>
                    </div>
                  </div>
                ))}
              </div>

              {/* provision gap */}
              <div className="bc-card" style={{ padding: 18, borderColor: provision ? C.dangerBorder : C.hair,
                background: provision ? C.dangerBg : C.card }}>
                <div style={{ fontFamily: MONO, fontSize: 10.5, color: C.danger, letterSpacing: ".04em", marginBottom: 8 }}>
                  FOR CAPABILITY LEADERSHIP
                </div>
                <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 6 }}>Firm provision gap</div>
                {provision ? (
                  <>
                    <div style={{ fontSize: 13.5, color: C.ink }}>
                      <b>{provision.item}</b> — demand exists across FS accounts, but the firm has <b>no internal content</b> for it.
                      Maya is one of many benched BAs who'd hit this same wall.
                    </div>
                    <div style={{ fontSize: 13, color: C.danger, marginTop: 10, fontWeight: 600 }}>
                      Decision surfaced: build it, buy vendor enablement, or formalise a shadowing path.
                    </div>
                    <div style={{ fontSize: 12, color: C.muted, marginTop: 10 }}>
                      The tool doesn't just plan one person — it exposes where the firm's own learning supply has holes against live demand.
                    </div>
                  </>
                ) : (
                  <div style={{ fontSize: 13, color: C.muted }}>No provision gaps for this role — all required capabilities have firm content.</div>
                )}
              </div>
            </div>
          </>
        )}

        <div style={{ fontFamily: MONO, fontSize: 10.5, color: C.hairStrong, marginTop: 24, textAlign: "center" }}>
          synthetic data · demo · Tendere AI
        </div>
      </div>
    </div>
  );
}
