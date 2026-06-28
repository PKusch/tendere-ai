"""
Bench Compass — spec-driven supply/demand learning engine.

Pipeline (mirrors how the firm actually works):
  ingest job spec (from delivery lead)  ->  parse to requirements
  ->  diff against the consultant's RICH profile (level + recency + evidence)
  ->  classify each requirement into one of three honest gap types
  ->  map gaps to the firm's real learning content (or flag where none exists)
  ->  build a calendar-aware weekly learning plan toward future demand
  ->  credit effort in Workday + reward (the closing loop)
  ->  surface firm provision gaps (where demand exists but content doesn't)

The only step that needs an LLM in production is parsing messy free-text specs;
a deterministic stub stands in here so the rest of the pipeline runs locally.
"""

import json
from pathlib import Path

DATA = Path(__file__).parent / "data"
load = lambda n: json.loads((DATA / f"{n}.json").read_text())

RANK = {"none": 0, "familiar": 1, "moderate": 2, "experienced": 3, "deep": 4, "certified": 4}
WEAK_EVIDENCE = {"self-taught", "partial", "none"}


# ---- 1. parse (deterministic stub for the production LLM parser) ----
def parse_spec(spec):
    """In production an LLM reads spec['raw']. Here we use the pre-parsed stub."""
    return spec["parsed_stub"]


# ---- 2/3. diff + classify into the three gap types ----
def classify(req, profile_map, content_map):
    item = req["item"]
    need = RANK.get(req["need_level"], 2)
    p = profile_map.get(item)

    if p is None:                                  # true void
        cov = content_map.get(item, {}).get("coverage", "none")
        if cov in ("full", "refresh"):
            return "LEARNABLE", "Not held — but the firm has content to build it."
        return "NO_CONTENT", "Not held — and the firm has NO real content for it."

    have = RANK.get(p["level"], 0)
    stale = p.get("recency") == "stale"
    weak = p.get("evidence") in WEAK_EVIDENCE

    if have >= need and not stale and not weak:
        return "MET", "Held, current, evidenced."
    if have >= need and weak and not stale:
        return "LATENT_STRENGTH", "Has it and it's current — but can't yet prove it. Surface as signal; evidence is accelerant, not a gate."
    if stale or have < need:
        return "STALE_THIN", "Present but stale/thin — needs refresh + recent evidence, not learning from scratch."
    return "REVIEW", "Review manually."


def diff(consultant, spec, content_map):
    profile_map = {e["item"]: e for e in consultant["profile"]}
    reqs = parse_spec(spec)
    rows = []
    for r in reqs:
        status, why = classify(r, profile_map, content_map)
        rows.append({"req": r, "status": status, "why": why,
                     "have": profile_map.get(r["item"])})
    # transferable strengths the spec didn't ask for (e.g. core banking)
    asked = {r["item"] for r in reqs}
    transferable = [e for e in consultant["profile"]
                    if e["item"] not in asked and e["level"] in ("deep", "experienced")]
    return rows, transferable


# ---- verdict: a shape, not a score ----
def verdict(consultant, spec, rows):
    fam_match = spec["domain_family"] in {e.get("family") for e in consultant["profile"]}
    ambition_match = any(r["req"]["item"] in consultant["ambitions"] for r in rows)
    voids = [r for r in rows if r["status"] == "NO_CONTENT"]
    stale = [r for r in rows if r["status"] == "STALE_THIN"]
    met_core = [r for r in rows if r["status"] in ("MET", "LATENT_STRENGTH")]

    if not fam_match:
        return ("SURFACE MATCH — STRATEGIC MISFIT",
                "A skill keyword matches, but the domain family is wrong "
                f"({spec['domain_family']} vs this person's background). "
                "Off-trajectory. Don't auto-route here.")
    if met_core and not voids and stale:
        return ("STRONG FIT — NARROW, CLOSEABLE GAPS",
                "Right domain, most of the spec already met. Gaps are a currency refresh "
                "and a platform — closeable in the runway. Tag, prepare, place ready.")
    if met_core and (voids or stale):
        return ("STRONG FIT — GAPS INCLUDE A PROVISION HOLE",
                "Right domain and mostly met, but one gap has no firm content. Plan around it.")
    if met_core:
        return ("STRONG FIT", "Right domain, spec met.")
    return ("STRETCH FIT", "Right direction; meaningful gaps.")


# ---- 4/5. learning plan + calendar-aware schedule ----
def content_items_for(item, content_map):
    c = content_map.get(item, {})
    return c.get("items", []), c


def build_plan(consultant, rows, content_map, demand_map):
    runway = max(consultant["roll_off_weeks"], 1)
    weekly_hours = consultant.get("weekly_learning_hours", 4)
    actions = []

    for r in rows:
        item = r["req"]["item"]
        status = r["status"]
        if status == "MET":
            continue
        items, c = content_items_for(item, content_map)
        dem = demand_map.get(item)

        if status == "STALE_THIN":
            actions.append({
                "item": item, "kind": "REFRESH", "priority": 1,
                "headline": f"Refresh currency in {item}",
                "content": items,
                "hours": sum(i["hours"] for i in items),
                "evidence": f"Frame the recent stint as evidence; restore {item} to current.",
                "demand": dem,
            })
        elif status == "NO_CONTENT":
            actions.append({
                "item": item, "kind": "NO_FIRM_CONTENT", "priority": 2,
                "headline": f"{item}: no firm course exists",
                "content": c.get("fragments", []),
                "hours": sum(i["hours"] for i in c.get("fragments", [])),
                "workaround": c.get("workaround"),
                "provision_gap": True,
                "demand": dem,
            })
        elif status == "LATENT_STRENGTH":
            verifiable = [i for i in items if i.get("verifiable")]
            actions.append({
                "item": item, "kind": "EVIDENCE_LATENT", "priority": 3,
                "headline": f"Surface {item} as a strength; optional accelerant",
                "content": verifiable,
                "hours": sum(i["hours"] for i in verifiable),
                "evidence": c.get("evidence_path", "Capture evidence to convert self-taught -> evidenced."),
                "future_demand_push": dem is not None,
                "demand": dem,
            })
        elif status == "LEARNABLE":
            actions.append({
                "item": item, "kind": "BUILD", "priority": 2,
                "headline": f"Build {item}", "content": items,
                "hours": sum(i["hours"] for i in items), "demand": dem,
            })

    actions.sort(key=lambda a: a["priority"])

    # calendar-aware schedule: pack required-currency first within weekly budget,
    # run the longer future-demand track in parallel across the runway
    schedule = schedule_weeks(actions, runway, weekly_hours)
    return {"runway": runway, "weekly_hours": weekly_hours,
            "actions": actions, "schedule": schedule}


def schedule_weeks(actions, runway, weekly_hours):
    """Greedy: role-critical (refresh/build) packed into early weeks within the
    weekly budget; long verifiable tracks spread as an ongoing parallel strand."""
    weeks = {w: [] for w in range(1, runway + 1)}
    # sequential block for short, role-critical items
    cursor, budget = 1, weekly_hours
    for a in actions:
        if a["kind"] in ("REFRESH", "BUILD", "NO_FIRM_CONTENT"):
            for it in a["content"]:
                hrs = it["hours"]
                if hrs > budget and cursor < runway:
                    cursor += 1
                    budget = weekly_hours
                weeks[cursor].append(f"{it['title']} ({hrs}h) — {a['item']}")
                budget -= hrs
        elif a["kind"] == "EVIDENCE_LATENT" and a["content"]:
            # spread the verifiable capstone across the whole runway, ~part-time
            it = a["content"][0]
            per_week = round(it["hours"] / runway, 1)
            for w in range(1, runway + 1):
                weeks[w].append(f"~{per_week}h · {it['title']} (future-demand track)")
    return weeks


# ---- 6. Workday credit + reward (the closing loop) ----
def workday_effects(plan):
    fx = []
    for a in plan["actions"]:
        if a["kind"] == "REFRESH":
            fx.append(f"On completion -> {a['item']} recency: stale -> CURRENT; logged in Workday; profile updated.")
        elif a["kind"] == "EVIDENCE_LATENT":
            fx.append(f"On completion -> {a['item']} evidence: self-taught -> EVIDENCED (capstone); Workday credit; profile uplift; counts toward high-value AI capability the firm is short on.")
        elif a["kind"] == "NO_FIRM_CONTENT":
            fx.append(f"{a['item']}: vendor/shadow logged as effort; flagged to capability lead as a FIRM PROVISION GAP.")
        elif a["kind"] == "BUILD":
            fx.append(f"On completion -> {a['item']} added to profile; Workday credit.")
    return fx


# --------------------------- demo run ---------------------------
def main():
    roster = load("roster"); specs = load("spec")
    content = load("content"); demand = load("demand")
    content_map = {c["capability"]: c for c in content["content"]}
    demand_map = {s["capability"]: s for s in demand["signals"]}

    maya = next(c for c in roster["consultants"] if c["id"] == "CONS-001")
    spec_z = next(s for s in specs["specs"] if s["id"] == "ROLE-Z")
    spec_ph = next(s for s in specs["specs"] if s["id"] == "ROLE-PH")

    bar = "=" * 78
    print(bar)
    print(f"  BENCH COMPASS   ·   {maya['name']} ({maya['seniority']}, rolls off in {maya['roll_off_weeks']}w)")
    print(bar)

    print("\n  SPEC RECEIVED — from Delivery Lead, Client Z (as it landed):")
    for line in spec_z["raw"].split("\n"):
        print(f"      {line}")

    rows, transferable = diff(maya, spec_z, content_map)
    title, gloss = verdict(maya, spec_z, rows)
    print(f"\n  VERDICT:  {title}")
    print(f"      {gloss}")

    print(f"\n  THE DIFF — spec vs Maya's real profile (not a keyword match):")
    label = {"MET": "MET", "STALE_THIN": "STALE / THIN", "NO_CONTENT": "GAP · NO FIRM CONTENT",
             "LATENT_STRENGTH": "LATENT STRENGTH", "LEARNABLE": "GAP · LEARNABLE", "REVIEW": "REVIEW"}
    for r in rows:
        nm = r["req"]["item"]
        have = r["have"]
        detail = ""
        if have and have.get("note"):
            detail = f"  ({have['note']})"
        print(f"      • {nm:<34} {label[r['status']]:<22}{detail}")
        print(f"          {r['why']}")
    if transferable:
        print(f"      + transferable (not required by spec): "
              + ", ".join(e['item'] for e in transferable))

    plan = build_plan(maya, rows, content_map, demand_map)
    print(f"\n  LEARNING PLAN — {plan['runway']}w runway, ~{plan['weekly_hours']}h/week, "
          f"scheduled around her client calendar:")
    for a in plan["actions"]:
        print(f"\n      [{a['kind']}]  {a['headline']}")
        for it in a["content"]:
            v = " · verifiable" if it.get("verifiable") else ""
            print(f"          - {it['title']} ({it['hours']}h, {it['provider']}){v}")
        if a.get("workaround"):
            print(f"          ! {a['workaround']}")
        if a.get("evidence"):
            print(f"          evidence: {a['evidence']}")
        if a.get("demand"):
            d = a["demand"]
            print(f"          firm demand: {d['acuteness'].upper()} · {d['recurrence']} · value {d['value_index']}")

    print(f"\n  WEEKLY SCHEDULE (calendar-aware):")
    for w, items in plan["schedule"].items():
        if items:
            print(f"      Week {w}: " + "; ".join(items))

    print(f"\n  WORKDAY CREDIT + REWARD (closing the loop):")
    for fx in workday_effects(plan):
        print(f"      -> {fx}")

    # firm provision insight
    holes = [a for a in plan["actions"] if a.get("provision_gap")]
    if holes:
        print(f"\n  FIRM PROVISION INSIGHT (for capability leadership):")
        for h in holes:
            print(f"      ⚠ {h['item']}: demand exists, NO internal content. "
                  f"Maya is one of N benched BAs who'd need it. Build or buy this.")

    # the contrast
    rows_ph, _ = diff(maya, spec_ph, content_map)
    t_ph, g_ph = verdict(maya, spec_ph, rows_ph)
    print(f"\n  {'-'*74}")
    print(f"  CONTRAST — the role a keyword search WOULD have suggested:")
    print(f"      {spec_ph['title']}  ->  {t_ph}")
    print(f"      {g_ph}")


if __name__ == "__main__":
    main()
