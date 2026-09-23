# Tendere AI — hackathon submission

> **Stop ranking people. Start aiming them.**
> A consulting bench engine that reads a role's messy job spec, maps it against a
> consultant's *real* profile, and plans them toward where demand is going — then
> zooms out to show capability leadership where the firm's training has holes.

- **Live demo:** https://pkusch.github.io/tendere-ai/
- **Repo:** https://github.com/PKusch/tendere-ai
- **Pitch deck:** [`Tendere-AI-Pitch.pptx`](./Tendere-AI-Pitch.pptx)
- **Try it locally:** `python3 engine.py` (add `ANTHROPIC_API_KEY` for the live Claude layer)

---

## Inspiration

Consulting firms staff people with a keyword search over CVs and a back-channel of
who-knows-who. It wastes billable people on the bench, misroutes them (a banking BA
gets a public-sector role because both say "BA"), and leaves the firm blind to its own
capability gaps. The root problem: a search bar treats a human as a bag of keywords.
It can't tell *"never done it"* from *"did it but it's gone cold"* from *"can do it but
can't prove it."* Tendere refuses that premise.

## What it does

- **Maps, doesn't rank.** Every capability gets an honest marker, not a score.
- **Distinguishes three kinds of gap** — `stale/thin`, `gap · no firm content`,
  `latent strength` — and plans each differently.
- **Is anticipatory.** It works the roll-off *runway* and schedules learning around the
  person's real calendar, so they arrive prepared instead of idle.
- **Aims at future demand**, weighting scarce, high-value skills (AI/GenAI, cloud,
  regulated-FS clearance) so people build toward what compounds.
- **Zooms out for leadership.** The same engine runs across the whole bench: open demand
  × people, and **provision gaps ranked by exposure** — "this platform is demanded by N
  open roles, M benched people would need it, and the firm has *zero* internal content."

## How we built it

- **Engine — Python, zero-dependency core** (`engine.py`). A deterministic pipeline:
  parse → diff (level + recency + evidence) → classify → plan → schedule → Workday
  write-back → firm provision-gap scan.
- **The AI layer — Claude (`claude-opus-5` by default, overridable with `TENDERE_MODEL`).** Two places genuinely need judgment:
  - **Spec parsing** — Claude turns messy free-text specs into structured requirements
    with a *forced tool call*, normalising to the firm's own vocabulary so matches don't
    silently break.
  - **Classification second opinion** — Claude reads the free-text profile notes a rules
    engine can't, returning **calibrated confidence + a citation from the profile**. It
    *never silently overrides the rules*: when the model and rules disagree, that's
    surfaced for human review. Honest means auditable.
  - Both paths **fall back to a deterministic stub** with no API key — so it always runs
    and a venue network blip can't crash the demo.
- **Dashboard — React (`dashboard.jsx`), hosted via Vite** (`web/`). Self-contained;
  toggle roles to watch the verdict recompute from strong fit ↔ strategic misfit.

## Challenges we ran into

- **Taxonomy alignment.** "Postgres" vs "PostgreSQL" vs "Database Admin" — if the parser
  invents a name, a held skill reads as a gap. We hand Claude the firm's canonical
  vocabulary so parsed items line up.
- **Trust.** The whole pitch is *honesty*, so an LLM that confidently mislabels a gap
  would undo it. We made the model additive — confidence, citations, and visible
  disagreement — never a silent override.

## Accomplishments we're proud of

A working end-to-end pipeline where the AI does the genuinely hard part and the
deterministic core keeps it honest and crash-proof — plus a leadership view that turns
one person's plan into a firm-wide capability map.

## What we learned

The valuable AI isn't the flashy generation — it's reading the *nuance a rules engine
throws away* (a 3-month stint the client cut short; self-taught with no cert) and being
honest about confidence.

## What's next

- Realistic data slice from public sources (job-postings demand, survey-based profiles,
  course-catalogue content) on a shared **O\*NET/ESCO** taxonomy.
- Calibration + eval harness for the classifier's confidence.
- Live write-back to Workday / the HR system of record; real calendar integration.

## The data is synthetic — and that's the point

"Maya R." is fictional; providers and demand signals are illustrative. The private data
a firm holds on its people is exactly what this stands in for, so a public prototype
*models* it rather than uses it. No real people, clients, or proprietary content.
