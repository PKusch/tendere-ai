#!/usr/bin/env python3
"""Is the classifier's confidence worth anything?

The second-opinion classifier returns a label, a confidence (high / medium / low) and a
citation for every requirement. The engine already refuses to let that opinion override
the rules; what nobody has measured is whether the confidence means anything. This
harness asks three questions of it, against a labelled case bank:

  1. Calibration — does agreement with the rules fall as confidence falls? A classifier
     whose 'low' is wrong no more often than its 'high' is not calibrated, it is decorating.
  2. Citations — is every citation a verbatim quote from the profile entry it claims to
     rest on, and empty when there is no entry?
  3. Stability — run the same cases N times: how often does a label or confidence flip?

It needs the live model (ANTHROPIC_API_KEY). Without it there is nothing to measure and
the harness says so and exits 2, rather than printing a table that looks like a result.

    python3 eval/calibrate.py            # one pass
    python3 eval/calibrate.py --runs 3   # three passes, reports flip rate
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import engine  # noqa: E402

HERE = Path(__file__).resolve().parent
BANK = json.loads((HERE / "cases.json").read_text())


def rows_for_cases():
    """Shape the case bank the way engine.diff() shapes rows, so the classifier sees
    exactly what it sees in the pipeline."""
    content_map = {k: {"coverage": v} for k, v in BANK["coverage"].items()}
    rows = []
    for c in BANK["cases"]:
        profile_map = {c["have"]["item"]: c["have"]} if c["have"] else {}
        status, why = engine.classify(c["req"], profile_map, content_map)
        rows.append({"id": c["id"], "req": c["req"], "status": status, "why": why,
                     "have": c["have"], "expect_confidence": c["expect_confidence"]})
    return rows, content_map


def citation_ok(row):
    cite = (row.get("citation") or "").strip()
    if row["have"] is None:
        return cite == ""
    if cite == "":
        return False
    haystack = " ".join(str(v) for v in row["have"].values())
    return cite in haystack


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1)
    args = ap.parse_args()

    rows, content_map = rows_for_cases()
    print(f"\n{len(rows)} labelled cases · rules give: "
          + ", ".join(f"{k}={v}" for k, v in sorted(Counter(r['status'] for r in rows).items())))

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\nNot run: no ANTHROPIC_API_KEY. The confidence has not been measured.\n")
        return 2

    passes = []
    for i in range(args.runs):
        fresh = [dict(r) for r in rows]
        out = engine.classify_with_claude(fresh, {"name": "eval"}, content_map)
        if not any("confidence" in r for r in out):
            print("\nThe classifier returned nothing usable; see the message above.\n")
            return 2
        passes.append(out)
        print(f"  pass {i + 1}/{args.runs} complete")

    last = passes[-1]

    # 1. calibration
    print("\nAgreement with the rules, by stated confidence")
    by_conf = defaultdict(list)
    for r in last:
        if "confidence" in r:
            by_conf[r["confidence"]].append(r["agrees"])
    rates = {}
    for conf in ("high", "medium", "low"):
        xs = by_conf.get(conf, [])
        if xs:
            rates[conf] = sum(xs) / len(xs)
            print(f"  {conf:<7} {sum(xs)}/{len(xs)} agree  ({rates[conf]:.0%})")
        else:
            print(f"  {conf:<7} —  (never used)")
    ordered = [rates[c] for c in ("high", "medium", "low") if c in rates]
    monotone = all(a >= b for a, b in zip(ordered, ordered[1:]))
    print(f"  monotone: {'yes' if monotone else 'NO — confidence does not track agreement'}")

    hi_wrong = [r["id"] for r in last if r.get("confidence") == "high" and not r["agrees"]]
    print(f"  high-confidence disagreements with the rules: {len(hi_wrong)}"
          + (f"  ← {', '.join(hi_wrong)}" if hi_wrong else ""))

    expected = [r for r in last if r["expect_confidence"] and "confidence" in r]
    hits = [r for r in expected if r["confidence"] == r["expect_confidence"]]
    print(f"  matched a human's confidence expectation: {len(hits)}/{len(expected)}"
          + ("" if len(hits) == len(expected) else
             "  ← missed: " + ", ".join(f"{r['id']} wanted {r['expect_confidence']} got {r['confidence']}"
                                        for r in expected if r not in hits)))

    # 2. citations
    cited = [r for r in last if "citation" in r]
    good = [r for r in cited if citation_ok(r)]
    print(f"\nCitations verbatim from the profile (or empty for a void): {len(good)}/{len(cited)}"
          + ("" if len(good) == len(cited) else
             "  ← bad: " + ", ".join(r["id"] for r in cited if r not in good)))

    # 3. stability
    if len(passes) > 1:
        flips_label = flips_conf = 0
        for i in range(len(rows)):
            labels = {p[i].get("model_label") for p in passes}
            confs = {p[i].get("confidence") for p in passes}
            flips_label += len(labels) > 1
            flips_conf += len(confs) > 1
        print(f"\nAcross {len(passes)} passes: {flips_label}/{len(rows)} cases changed label, "
              f"{flips_conf}/{len(rows)} changed confidence")

    result = {
        "model": engine.MODEL, "runs": args.runs, "cases": len(rows),
        "agreement_by_confidence": rates, "monotone": monotone,
        "high_confidence_disagreements": hi_wrong,
        "citations_ok": f"{len(good)}/{len(cited)}",
    }
    (HERE / "last-run.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"\nWritten to eval/last-run.json\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
