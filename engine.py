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
import os
from pathlib import Path

DATA = Path(__file__).parent / "data"
load = lambda n: json.loads((DATA / f"{n}.json").read_text())

RANK = {"none": 0, "familiar": 1, "moderate": 2, "experienced": 3, "deep": 4, "certified": 4}
WEAK_EVIDENCE = {"self-taught", "partial", "none"}

# Claude does the one genuinely AI step: reading a messy free-text spec.
# Override at the venue (e.g. claude-sonnet-4-6 for lower latency) via TENDERE_MODEL.
MODEL = os.environ.get("TENDERE_MODEL", "claude-opus-4-8")

# Tool schema forces Claude to return structured requirements (no JSON-in-prose
# parsing). need_level / need_recency match the deterministic stub's vocabulary.
_PARSE_TOOL = {
    "name": "emit_requirements",
    "description": "Return the structured requirements parsed from a job spec.",
    "input_schema": {
        "type": "object",
        "properties": {
            "requirements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "item": {"type": "string",
                                 "description": "Canonical capability/domain/platform name. "
                                                "MUST reuse a name from the known vocabulary when "
                                                "the same concept appears there, even if the spec "
                                                "phrases it differently."},
                        "type": {"type": "string", "enum": ["capability", "domain", "platform"]},
                        "need_level": {"type": "string",
                                       "enum": ["familiar", "moderate", "experienced", "deep", "certified"]},
                        "need_recency": {"type": "string", "enum": ["current", "any"]},
                    },
                    "required": ["item", "type", "need_level", "need_recency"],
                },
            }
        },
        "required": ["requirements"],
    },
}


# ---- 1. parse: Claude reads the messy spec; deterministic stub is the fallback ----
def parse_spec(spec, vocab=None):
    """Parse a free-text job spec into structured requirements.

    Uses Claude when ANTHROPIC_API_KEY is set, normalising to the firm's existing
    vocabulary so parsed items line up with the profile/content/demand maps. Falls
    back to the deterministic stub when there's no key or the call fails — so the
    pipeline always runs locally and a venue network hiccup can't crash the demo.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _parse_with_claude(spec["raw"], vocab or [])
        except Exception as e:  # never let an API/network blip kill the demo
            if spec.get("parsed_stub") is not None:
                print(f"      [parser fell back to stub: {type(e).__name__}: {e}]")
                return spec["parsed_stub"]
            raise
    return spec["parsed_stub"]


def _parse_with_claude(raw, vocab):
    """Call Claude with a forced tool to extract canonical, structured requirements."""
    import anthropic  # lazy: the stub/fallback path stays zero-dependency

    vocab_block = ("\nKnown vocabulary (reuse these exact names when the concept matches):\n"
                   + "\n".join(f"  - {v}" for v in vocab)) if vocab else ""
    prompt = (
        "You parse messy, free-text consulting job specs into structured requirements.\n"
        "Extract every distinct capability, domain, or platform the role needs. Infer "
        "need_level from the wording ('5+ years'/'lead' -> deep; 'certified' -> certified; "
        "'familiar'/'exposure' -> familiar). Use need_recency 'current' unless the spec "
        "signals past/any experience is fine ('worked on ... before' -> any).\n"
        f"{vocab_block}\n\nJOB SPEC:\n{raw}"
    )
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[_PARSE_TOOL],
        tool_choice={"type": "tool", "name": "emit_requirements"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in msg.content:
        if block.type == "tool_use" and block.name == "emit_requirements":
            return block.input["requirements"]
    raise RuntimeError("Claude returned no tool_use block")


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
    # Hand Claude the canonical names it should normalise to (the keys classify()
    # matches against), so "worked on nCino" lands as the data's "nCino".
    vocab = sorted(set(profile_map) | set(content_map))
    reqs = parse_spec(spec, vocab)
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


# ---- 2b. LLM second opinion: confidence + citation, never a silent override ----
_LABEL_DEFS = (
    "MET             — held at/above the needed level, current, and evidenced.\n"
    "STALE_THIN      — has the experience but it's stale (old) or below the needed level; "
    "needs a refresh, not learning from scratch.\n"
    "LATENT_STRENGTH — has it and it's current, but the evidence is weak (self-taught / "
    "partial); can't yet prove it.\n"
    "NO_CONTENT      — not held, and the firm has NO real content to build it (a provision gap).\n"
    "LEARNABLE       — not held, but the firm has content to build it.\n"
    "REVIEW          — genuinely ambiguous; a human should look."
)

_CLASSIFY_TOOL = {
    "name": "classify_requirements",
    "description": "Return an independent fit judgment for each requirement.",
    "input_schema": {
        "type": "object",
        "properties": {
            "classifications": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "item": {"type": "string", "description": "Echo the requirement's item name exactly."},
                        "label": {"type": "string",
                                  "enum": ["MET", "STALE_THIN", "LATENT_STRENGTH",
                                           "NO_CONTENT", "LEARNABLE", "REVIEW"]},
                        "confidence": {"type": "string", "enum": ["high", "medium", "low"],
                                       "description": "Calibrated: low when the profile note is "
                                                      "ambiguous or the call is a judgement one."},
                        "citation": {"type": "string",
                                     "description": "The exact profile fact/note the judgment rests "
                                                    "on, quoted. Empty string if the person has no "
                                                    "relevant experience at all."},
                        "rationale": {"type": "string", "description": "One sentence."},
                    },
                    "required": ["item", "label", "confidence", "citation", "rationale"],
                },
            }
        },
        "required": ["classifications"],
    },
}


def classify_with_claude(rows, consultant, content_map):
    """Enrich deterministic rows with a calibrated second opinion from Claude:
    confidence, a citation drawn from the person's real profile text, and an
    independent label. It NEVER overrides the rules — when the model and the rules
    disagree we mark the row for human review (row['agrees'] = False). Returns the
    rows untouched when there's no key or the call fails, so the pipeline is safe.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return rows
    try:
        import anthropic  # lazy: deterministic path stays zero-dependency

        cases = [{
            "item": r["req"]["item"],
            "type": r["req"]["type"],
            "need_level": r["req"]["need_level"],
            "need_recency": r["req"]["need_recency"],
            "profile_entry": r["have"],  # full entry incl. free-text note, or null (true void)
            "firm_content_coverage": content_map.get(r["req"]["item"], {}).get("coverage", "none"),
        } for r in rows]

        prompt = (
            "You are mapping a consultant against a role's requirements — honestly. "
            "The point is NOT to inflate fit. Distinguish 'never done it' from 'did it "
            "but it's gone cold' from 'can do it but can't prove it'.\n\n"
            "For each requirement, independently choose one label:\n" + _LABEL_DEFS +
            "\n\nRead the profile_entry's free-text note carefully — that nuance is the "
            "whole point. Quote the exact fact your judgment rests on as the citation. "
            "Be calibrated: use 'low' confidence when the note is genuinely ambiguous.\n\n"
            "REQUIREMENTS (with the consultant's matching profile entry):\n"
            + json.dumps(cases, indent=2)
        )
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=MODEL, max_tokens=2048,
            tools=[_CLASSIFY_TOOL],
            tool_choice={"type": "tool", "name": "classify_requirements"},
            messages=[{"role": "user", "content": prompt}],
        )
        result = None
        for block in msg.content:
            if block.type == "tool_use" and block.name == "classify_requirements":
                result = block.input["classifications"]
                break
        if result is None:
            return rows

        by_item = {c["item"]: c for c in result}
        for r in rows:
            c = by_item.get(r["req"]["item"])
            if not c:
                continue
            r["confidence"] = c["confidence"]
            r["citation"] = c.get("citation", "")
            r["model_label"] = c["label"]
            r["model_rationale"] = c.get("rationale", "")
            r["agrees"] = (c["label"] == r["status"])  # disagreement -> human review flag
        return rows
    except Exception as e:  # second opinion is additive; never break the pipeline
        print(f"      [classifier second-opinion skipped: {type(e).__name__}: {e}]")
        return rows


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


# ---- 7. portfolio scan: one person -> the whole bench (capability leadership) ----
def portfolio_scan(roster, specs, content_map, demand_map):
    """Run every open role against every benched consultant and aggregate the result
    into firm-level signal. Deterministic and fast — the leadership view is an
    aggregate, not a per-person AI call. Returns (role_fits, provision_exposure)."""
    consultants = roster["consultants"]
    open_roles = specs["specs"]

    role_fits = []
    for spec in open_roles:
        fits = []
        for c in consultants:
            rows, _ = diff(c, spec, content_map)
            title, _ = verdict(c, spec, rows)
            closeable = [r for r in rows if r["status"] in ("STALE_THIN", "LEARNABLE")]
            holes = [r for r in rows if r["status"] == "NO_CONTENT"]
            fits.append({"consultant": c, "verdict": title, "rows": rows,
                         "closeable": closeable, "holes": holes})
        role_fits.append({"spec": spec, "fits": fits})

    # provision exposure: capabilities demanded by roles that the firm has NO content
    # for, counted across the bench -> the build-or-buy case for capability leadership
    exposure = {}
    for rf in role_fits:
        for f in rf["fits"]:
            for r in f["holes"]:
                item = r["req"]["item"]
                e = exposure.setdefault(item, {"consultants": set(), "roles": set()})
                e["consultants"].add(f["consultant"]["id"])
                e["roles"].add(rf["spec"]["id"])
    return role_fits, exposure


def strategic_readiness(roster, demand_map):
    """For each high-value demand signal, how ready is the bench? Counts holders and
    splits evidenced vs latent (self-taught/partial) by exact capability name. Where
    no one holds it, that's a pure scarcity/provision gap — reported honestly rather
    than papered over with a fuzzy name match."""
    consultants = roster["consultants"]
    out = []
    for cap, sig in sorted(demand_map.items(), key=lambda kv: -kv[1].get("value_index", 0)):
        holders = evidenced = latent = 0
        for c in consultants:
            p = next((e for e in c["profile"] if e["item"] == cap), None)
            if p:
                holders += 1
                if p.get("evidence") in WEAK_EVIDENCE:
                    latent += 1
                else:
                    evidenced += 1
        out.append({"capability": cap, "signal": sig,
                    "holders": holders, "evidenced": evidenced, "latent": latent})
    return out


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
    rows = classify_with_claude(rows, maya, content_map)  # additive second opinion
    title, gloss = verdict(maya, spec_z, rows)
    print(f"\n  VERDICT:  {title}")
    print(f"      {gloss}")

    print(f"\n  THE DIFF — spec vs Maya's real profile (not a keyword match):")
    label = {"MET": "MET", "STALE_THIN": "STALE / THIN", "NO_CONTENT": "GAP · NO FIRM CONTENT",
             "LATENT_STRENGTH": "LATENT STRENGTH", "LEARNABLE": "GAP · LEARNABLE", "REVIEW": "REVIEW"}
    conf_mark = {"high": "●●●", "medium": "●●○", "low": "●○○"}
    disagreements = []
    for r in rows:
        nm = r["req"]["item"]
        have = r["have"]
        detail = ""
        if have and have.get("note"):
            detail = f"  ({have['note']})"
        print(f"      • {nm:<34} {label[r['status']]:<22}{detail}")
        print(f"          {r['why']}")
        # additive AI layer (only present when the live classifier ran)
        if "confidence" in r:
            print(f"          AI: {conf_mark.get(r['confidence'], '?')} {r['confidence']} confidence"
                  + (f" · cites: \"{r['citation']}\"" if r.get("citation") else ""))
            if not r.get("agrees", True):
                disagreements.append(r)
                print(f"          ⚑ MODEL ⇄ RULES DISAGREE — model says {label.get(r['model_label'], r['model_label'])}: "
                      f"{r.get('model_rationale','')}  → flagged for human review")
    if transferable:
        print(f"      + transferable (not required by spec): "
              + ", ".join(e['item'] for e in transferable))
    if disagreements:
        print(f"\n      ⚑ {len(disagreements)} requirement(s) where the model and the rules "
              f"disagree are flagged above — surfaced, not auto-resolved.")

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
    # firm-wide scan — powers both the real number below and the zoom-out view
    role_fits, exposure = portfolio_scan(roster, specs, content_map, demand_map)
    n_bench = len(roster["consultants"])

    if holes:
        print(f"\n  FIRM PROVISION INSIGHT (for capability leadership):")
        for h in holes:
            ex = exposure.get(h["item"], {"consultants": set(), "roles": set()})
            n = len(ex["consultants"]) or 1
            print(f"      ⚠ {h['item']}: demand exists, NO internal content. "
                  f"Maya is one of {n} of {n_bench} benched people who'd need it. Build or buy this.")

    # the contrast
    rows_ph, _ = diff(maya, spec_ph, content_map)
    t_ph, g_ph = verdict(maya, spec_ph, rows_ph)
    print(f"\n  {'-'*74}")
    print(f"  CONTRAST — the role a keyword search WOULD have suggested:")
    print(f"      {spec_ph['title']}  ->  {t_ph}")
    print(f"      {g_ph}")

    # ---- ZOOM OUT: the same engine across the whole bench ----
    bar = "=" * 78
    print(f"\n{bar}")
    print(f"  ZOOM OUT — FIRM CAPABILITY VIEW   (for capability leadership)")
    print(bar)
    print(f"  Maya was one consultant. Here is the same engine across the whole bench "
          f"({n_bench} people, {len(specs['specs'])} open roles).")

    print(f"\n  OPEN DEMAND × BENCH — who's deployable, who's a runway-closeable stretch:")
    for rf in role_fits:
        print(f"\n    {rf['spec']['id']} · {rf['spec']['title']}")
        for f in sorted(rf["fits"], key=lambda x: (len(x["holes"]), len(x["closeable"]))):
            c = f["consultant"]
            note = []
            if f["closeable"]:
                note.append(f"{len(f['closeable'])} closeable gap(s)")
            if f["holes"]:
                note.append(f"{len(f['holes'])} provision hole(s)")
            tail = (" · " + ", ".join(note)) if note else " · deployable now"
            print(f"        {c['name']:<14} {f['verdict']:<46}{tail}")

    print(f"\n  PROVISION GAPS — demand exists, firm has NO content (ranked by bench exposure):")
    ranked = sorted(exposure.items(), key=lambda kv: (-len(kv[1]["consultants"]), -len(kv[1]["roles"])))
    if not ranked:
        print("      (none surfaced by the current open roles)")
    for item, ex in ranked:
        c = content_map.get(item, {})
        print(f"      ⚠ {item}: {len(ex['consultants'])} of {n_bench} benched people need it · "
              f"{len(ex['roles'])} open role(s) · NO internal content")
        if c.get("workaround"):
            print(f"          → {c['workaround']}")

    print(f"\n  STRATEGIC DEMAND READINESS — high-value scarce skills, bench coverage:")
    for s in strategic_readiness(roster, demand_map):
        sig = s["signal"]
        gap = ""
        if s["holders"] == 0:
            gap = "  ← no one on bench holds this (pure scarcity/provision gap)"
        elif s["evidenced"] == 0 and s["latent"] > 0:
            gap = "  ← all latent, none evidenced (the value gap: prove it)"
        print(f"      {sig['label']:<42} value {sig['value_index']:>3} · scarcity {sig['scarcity']:<7} "
              f"· bench: {s['holders']} hold / {s['evidenced']} evidenced / {s['latent']} latent{gap}")


if __name__ == "__main__":
    main()
