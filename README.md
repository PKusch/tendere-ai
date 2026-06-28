# Tendere AI

*Tendere* (Latin): to stretch toward, to aim at.

A prototype that reads a role's job spec, maps it against a consultant's real
profile, and builds a learning plan that aims them toward where demand actually
is — before they roll off a project, not after they're idle on the bench.

It started from a real, lived frustration: in consulting, matching people to
roles is slow, informal, and mostly manual. Open demand lives in people's heads,
emails, and stale internal tools. The interesting roles are never advertised.
When you roll off, you ping people, send your CV around, and wait. And when a
match *is* attempted, it's a keyword search over CVs that can't tell *"never done
this"* from *"did it but it's gone cold"* from *"can do it but can't prove it."*

Tendere is an attempt at the opposite.

## The idea

**It maps, it doesn't rank.** A ranked list pretends one person is simply
"better." The truth is a person is deep in some areas, an adjacent stretch in
others, and weak in places that may not matter for the role. So the output is a
*fit map* with an honest marker per capability — not a score.

**It distinguishes three kinds of gap**, and treats each differently:

| Gap type | Meaning | What the plan does |
|---|---|---|
| `stale / thin` | Has the experience, but it's old or shallow | Refresh currency + frame recent evidence — not learn from scratch |
| `gap · no firm content` | Doesn't have it, and the firm has *no* real training for it | Honest workaround (vendor / shadow), and flag it as a **provision gap** |
| `latent strength` | Can do it, but can't yet prove it (self-taught, no cert) | Surface as a signal; evidence is an accelerant, not a gate |

**It's anticipatory.** It works the roll-off runway — the weeks *before* someone
is benched — so they arrive prepared instead of getting up to speed while idle.
The plan is scheduled around the person's actual client calendar.

**It aims at future demand, not just the role in front of them.** High-value,
recurring, scarce skills (AI/GenAI, cloud, regulated-FS clearance) are weighted
so the plan pushes people toward skills that compound — the role becomes the
vehicle, not the ceiling.

**It surfaces the firm's own blind spots.** When a real demand has no internal
learning content (the prototype's worked example: a named platform the firm wants
people on but has no course for), it raises that as a provision gap for capability
leadership. The tool plans one person *and* exposes where the firm's learning
supply has holes against live demand.

**It closes the loop.** Completed effort is credited (modelled as a Workday
write-back) and lands on the profile — `stale → current`, `self-taught →
evidenced` — so the work compounds.

## How it works

```
job spec (as received)  →  parse to requirements
   →  diff against the consultant's profile (level + recency + evidence)
   →  classify each requirement (met / stale / no-content / latent / learnable)
   →  map gaps to firm learning content (or flag where none exists)
   →  build a calendar-aware learning plan toward future demand
   →  credit effort + reward  →  surface firm provision gaps
```

The only step that needs an LLM is parsing messy free-text specs into structured
requirements; a deterministic stub stands in so the rest of the pipeline runs
locally with no dependencies.

## Run it

**Engine** (Python 3, no dependencies):

```bash
python3 engine.py
```

Prints the full pipeline for the worked example: a job spec from a delivery lead,
the diff against the consultant's profile, the learning plan, the weekly schedule,
the Workday write-back, the firm provision gap, and — for contrast — the misfit
role a keyword search would have suggested instead.

**Dashboard** (`dashboard.jsx`): a React component visualising the same pipeline.
Toggle between the two roles to watch the verdict recompute live (strong fit ↔
strategic misfit); the weekly-hours control re-paces the schedule. Drop it into
any React app, or paste it into a sandbox that supports JSX + Tailwind.

## Structure

```
engine.py            the fit-mapping + planning engine
dashboard.jsx        the React dashboard (same logic, ported)
data/
  spec.json          job specs as they arrive (messy bullets) + parsed stub
  roster.json        consultant profiles (level + recency + evidence)
  content.json       firm learning content, with coverage flags
  demand.json        high-value demand signals (scarcity / recurrence)
```

## A note on the data

Everything here is **synthetic**. The consultant ("Maya R.") is a fictional
persona, the firm content and provider names are placeholders, and the demand
signals are illustrative. No real people, clients, or proprietary content.

## License

MIT — see [LICENSE](LICENSE).
