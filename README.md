<div align="center">

# 🧭 Tendere AI

### **Stop ranking people. Start aiming them.**

*Tendere* (Latin) — to stretch toward, to aim at.

*Reads a role's job spec. Maps it against a consultant's real profile. Builds a learning plan that aims them at where demand actually is — **before** the bench, not after.*

</div>

---

## 🧨 The problem

A consulting firm is its people. So how does it decide who goes where? A keyword
search over CVs and a back-channel of who-knows-who. That fails three ways, and
everyone inside it already knows it:

- 💸 **It wastes people.** You roll off with nothing lined up. You ping contacts,
  fire your CV into group chats, and sit idle — billable talent earning nothing,
  for days or weeks.
- 🎯 **It misroutes people.** The best roles are never advertised; they move
  through relationships. What *is* advertised gets matched by keyword — so a
  banking BA lands a public-sector role because both say *BA*.
- 🕳️ **It can't see its blind spots.** The firm wants AI-capable, cloud-certified,
  cleared people. It has a quiet army teaching themselves exactly that. Nobody
  connects the two.

> [!IMPORTANT]
> The root cause is a search bar that treats a human as a bag of keywords. Tendere refuses that premise.

---

## 🧭 What Tendere does

**It maps — it doesn't rank.** A leaderboard pretends one person is simply
"better." Nonsense. A person is *deep* in some things, an adjacent *stretch* in
others, weak where it doesn't even matter for the role. So the output is a fit
map with an honest marker per capability — not a score.

**It knows there are three kinds of gap** — and a keyword search can't tell them
apart. Conflating them is how good people get misrouted:

| Marker | What it really means | What Tendere does about it |
|:--|:--|:--|
| 🟠 `stale / thin` | Has the experience — but it's years old, or 3 months that got cut short | Refresh currency, frame the recent evidence. Don't make them relearn it. |
| 🔴 `gap · no firm content` | Doesn't have it, **and the firm has no training for it** | Honest workaround (vendor, shadow a colleague) — and flag it as a provision gap. No invented course. |
| 🟣 `latent strength` | Can do it, can't yet *prove* it (self-taught, no cert) | Surface it as a signal. Evidence is an accelerant, not a gate. |

### Tendere vs a search bar

| | Keyword search | **Tendere** |
|:--|:--:|:--:|
| Tells *stale* from *never done it* | ❌ | ✅ |
| Spots skill you have but can't prove | ❌ | ✅ |
| Acts **before** the bench, not after | ❌ | ✅ |
| Flags where the *firm* has no training | ❌ | ✅ |
| Aims at future demand, not just the role | ❌ | ✅ |

> [!NOTE]
> **The core idea lives in one design choice:** every capability carries *level, recency, and evidence* — never a single proficiency number. That's the whole reason Tendere can tell *never done it* from *did it but it's gone cold* from *can do it but can't prove it*.

**It's anticipatory.** It works the *runway* — the weeks before someone rolls off
— and schedules learning around their real client calendar, so they arrive
prepared instead of getting up to speed while idle and unbilled.

**It aims at future demand, not the role's checklist.** Plans are weighted toward
scarce, recurring, high-value skills (AI/GenAI, cloud, regulated-FS clearance), so
people build toward what compounds. The role is the vehicle, not the ceiling.

**It indicts the firm, not just plans a person.** When a real demand has no
internal content, Tendere raises it to capability leadership as a provision gap.
One person gets a plan; the organisation gets a map of where its learning supply
has holes against live demand.

**It closes the loop.** Completed effort is credited (modelled as a Workday
write-back) and lands on the profile — `stale → current`, `self-taught →
evidenced`. The work compounds instead of evaporating.

---

## ⚙️ How it works

```
job spec (as it lands — messy bullets)
   →  parse to structured requirements
   →  diff against the consultant's profile   (level + recency + evidence)
   →  classify each requirement   (met / stale / no-content / latent / learnable)
   →  map gaps to firm learning content   (or flag where none exists)
   →  build a calendar-aware learning plan toward future demand
   →  credit effort + reward
   →  surface the firm's provision gaps
```

> [!TIP]
> Exactly one step needs an LLM: turning a messy free-text spec into structured requirements. A deterministic stub stands in for it — so everything else runs locally, with zero dependencies.

<details>
<summary><b>🔧 Under the hood — the data model</b></summary>

<br>

Every capability in a consultant's profile carries **three axes**, not one number:

- **level** — `none → familiar → moderate → experienced → deep`
- **recency** — `current` or `stale`
- **evidence** — `verified / certified` (strong) vs `self-taught / partial` (weak)

The classifier reads all three. The same `level: moderate` resolves completely
differently depending on the other two axes:

| level | recency | evidence | → verdict |
|:--|:--|:--|:--|
| deep | current | verified | `met` |
| moderate | stale | partial | `stale / thin` |
| moderate | current | self-taught | `latent strength` |
| *(absent)* | — | — | `gap` → then check if the firm even has content |

That single table is the difference between a tool that understands a career and a
search bar that counts keywords.

</details>

---

## ▶️ Run it

**The engine** — Python 3, nothing to install:

```bash
python3 engine.py
```

It prints the whole pipeline on a worked example: a spec from a delivery lead, the
diff against the consultant, the learning plan, the weekly schedule, the Workday
write-back, the firm provision gap — and, for contrast, the misfit role a keyword
search would have shoved them into. Watch the verdict flip from **strong fit** to
**strategic misfit**.

**The dashboard** — `dashboard.jsx`, the same logic as a React component. Toggle
between the two roles and the verdict recomputes live; the weekly-hours control
re-paces the plan. Drop it into a React app or a JSX sandbox.

---

## 🗂️ Project structure

```
engine.py        the fit-mapping + planning engine
dashboard.jsx    the dashboard (same logic, ported)
data/
  spec.json      job specs as they arrive, plus the parsed stub
  roster.json    consultant profiles — level + recency + evidence
  content.json   firm learning content, with coverage flags
  demand.json    high-value demand signals — scarcity, recurrence
```

---

## 🛣️ Roadmap

- [ ] Swap the deterministic stub for a real LLM spec parser
- [ ] Live write-back to Workday / the HR system of record
- [ ] Calendar integration for genuinely calendar-aware scheduling
- [ ] Firm-wide provision-gap view — aggregate the holes across the whole bench
- [ ] Multi-consultant matrix: one role, the shape of every candidate at once

---

> [!WARNING]
> **The data is synthetic — and that's the point.** "Maya R." is a fictional persona; the providers and content are placeholders; the demand signals are illustrative. The *private* data a firm holds on its people is exactly what this stands in for — so a public prototype models it rather than uses it. No real people, clients, or proprietary content.

---

## ⚖️ License

**MIT** — see [LICENSE](LICENSE). Take it, fork it, build the real thing.

<div align="center">
<br>

### Tendere AI — *aim people at demand.*

<sub>A prototype, built from a real frustration with how consulting staffs its people.</sub>

</div>
