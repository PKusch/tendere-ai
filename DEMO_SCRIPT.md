# Tendere AI — 2-minute demo script

The arc: **one person → the whole firm.** The dashboard tells the human story; the
engine's zoom-out delivers the leadership payoff. Total ~2:00.

## Before you start (30-second checklist)
- [ ] Dashboard open in a browser tab — the live URL, or `cd web && npm run dev`.
- [ ] A terminal ready in `tendere-ai/`, big font, with the key loaded:
      `set -a; source .env; set +a` (so the live Claude layer runs).
- [ ] Run `python3 engine.py` once beforehand so it's warm and you know the output.
- [ ] Safety net: with no key it runs on the deterministic stub — identical shape,
      can't crash. If the venue Wi-Fi dies mid-demo, you lose nothing.

---

## [0:00–0:20] — The problem (say this over the dashboard hero)
> "A consulting firm is its people — but it staffs them with a keyword search over CVs.
> That search can't tell *never done it* from *did it but it's gone cold* from *can do
> it but can't prove it*. So good people sit idle, and get misrouted. This is Tendere.
> It maps people — it doesn't rank them."

## [0:20–1:00] — The individual story (dashboard)
**Show:** Maya R., "rolls off in 7w", the incoming spec (messy bullets), the verdict.
> "Here's a real messy spec from a delivery lead. Tendere reads it and maps it against
> Maya's *actual* profile — not keywords. Look at the diff."

**Point at the three markers:**
> "Three honest kinds of gap. Commercial Banking isn't missing — it's **stale**: she did
> it, but a recent stint got cut short, so we *refresh*, not relearn. GenAI is a **latent
> strength** — she's self-taught, current, just can't prove it yet. And nCino is a real
> **gap the firm has no content for**."

**Toggle to the Public Health role:**
> "Watch what a keyword search would do — same job title, 'BA'. Tendere flags it a
> **strategic misfit**: right word, wrong trajectory. It won't misroute her."

**(Optional, nudge the hours control):** "and the plan re-paces to her real calendar."

## [1:00–1:40] — The zoom-out (switch to terminal: `python3 engine.py`)
**Scroll to `ZOOM OUT — FIRM CAPABILITY VIEW`.**
> "Maya was one person. The *same engine* runs across the whole bench — and this is what
> capability leadership has never been able to see. **Provision gaps, ranked by
> exposure:** nCino is demanded by open roles, N benched people would need it, and the
> firm has **zero** internal training for it. That's a build-or-buy decision, quantified,
> that today lives only in people's heads."

## [1:40–2:00] — The AI + the close
> "The genuinely hard step — reading a messy spec, and judging a gap from a one-line
> note — is Claude. It gives a second opinion with **calibrated confidence and a citation
> from the person's own profile**, and when it disagrees with the rules it says so — it
> never silently overrides them. Honest means auditable.
> One consultant gets a plan; the firm gets a map of where its capability has holes.
> That's Tendere — *aim people at demand.*"

---

## If you only have 60 seconds
Cut the hours control and the AI paragraph. Keep: problem (10s) → the three markers on
the diff (25s) → the provision-gap zoom-out (25s). The zoom-out is the moment that wins.

## Likely judge questions — quick answers
- **"Is the data real?"** Synthetic on purpose — it stands in for the private data a firm
  holds on its people; a public prototype models it rather than uses it.
- **"What's actually AI vs rules?"** Claude parses the spec and gives a second opinion
  with confidence + citations; the deterministic core stays authoritative and keeps it
  honest and crash-proof.
- **"What's next?"** Real data on an O*NET/ESCO taxonomy, classifier calibration, and
  write-back to Workday.
