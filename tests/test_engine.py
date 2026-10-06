"""The leadership view's numbers, pinned, so a data edit that breaks them fails CI."""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import engine  # noqa: E402


def load(name):
    return json.loads((ROOT / "data" / name).read_text())


class LeadershipView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster = load("roster.json")
        cls.specs = load("spec.json")
        cls.content_map = {c["capability"]: c for c in load("content.json")["content"]}
        cls.demand_map = {s["capability"]: s for s in load("demand.json")["signals"]}

    def test_every_alias_points_at_a_real_demand_and_a_real_profile_item(self):
        items = {p["item"] for c in self.roster["consultants"] for p in c["profile"]}
        for profile_name, capability in engine.load_taxonomy().items():
            self.assertIn(capability, self.demand_map, capability)
            self.assertIn(profile_name, items, profile_name)

    def test_ai_readiness_counts_the_self_taught_holder_as_latent(self):
        rows = {r["capability"]: r for r in engine.strategic_readiness(self.roster, self.demand_map)}
        ai = rows["Data & AI / GenAI"]
        self.assertEqual((ai["holders"], ai["evidenced"], ai["latent"]), (1, 0, 1))
        self.assertEqual(rows["Cloud Architecture"]["holders"], 0)

    def test_the_contrast_role_is_not_a_provision_gap(self):
        _, exposure = engine.portfolio_scan(self.roster, self.specs, self.content_map, self.demand_map)
        self.assertNotIn("Public Health", exposure)
        self.assertIn("nCino", exposure)
        self.assertEqual(len(exposure["nCino"]["consultants"]), 2)

    def test_the_demo_runs_offline_end_to_end(self):
        import io, contextlib, os
        env = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                engine.main()
        finally:
            if env is not None:
                os.environ["ANTHROPIC_API_KEY"] = env
        out = buf.getvalue()
        self.assertIn("STRATEGIC DEMAND READINESS", out)
        self.assertNotIn("Public Health: 2 of 2", out)


def _load_calibrate():
    spec = importlib.util.spec_from_file_location("calibrate", ROOT / "eval" / "calibrate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CalibrateArguments(unittest.TestCase):
    """--runs must be at least 1: 0 or a negative left passes empty and passes[-1]
    raised IndexError once a key was set. It is now refused at the argument, which
    happens before the key check, so this needs no key."""

    def test_runs_below_one_is_refused(self):
        cal = _load_calibrate()
        for bad in ("0", "-3"):
            argv = ["calibrate.py", "--runs", bad]
            saved = sys.argv
            sys.argv = argv
            try:
                with self.assertRaises(SystemExit) as cm:
                    cal.main()
                self.assertEqual(cm.exception.code, 2, bad)
            finally:
                sys.argv = saved


def _rows(*statuses):
    return [{"req": {"item": f"item{i}"}, "status": st} for i, st in enumerate(statuses)]


class Verdict(unittest.TestCase):
    """What a verdict may claim. Each branch is pinned, because 'spec met' is a
    sentence a delivery lead acts on."""

    consultant = {"profile": [{"family": "banking"}], "ambitions": []}
    spec = {"domain_family": "banking"}

    def verdict(self, *statuses, spec=None):
        return engine.verdict(self.consultant, spec or self.spec, _rows(*statuses))

    def test_spec_met_is_only_said_when_nothing_is_missing(self):
        self.assertEqual(self.verdict("MET", "LATENT_STRENGTH"), ("STRONG FIT", "Right domain, spec met."))

    def test_learnable_gaps_are_not_a_met_spec(self):
        # one requirement met and three still to be learned used to read "spec met"
        title, gloss = self.verdict("MET", "LEARNABLE", "LEARNABLE", "LEARNABLE")
        self.assertEqual(title, "STRONG FIT — NARROW, CLOSEABLE GAPS")
        self.assertNotIn("spec met", gloss)

    def test_stale_gaps_are_closeable(self):
        self.assertEqual(self.verdict("MET", "STALE_THIN")[0], "STRONG FIT — NARROW, CLOSEABLE GAPS")

    def test_a_gap_with_no_firm_content_is_named_as_a_provision_hole(self):
        self.assertEqual(self.verdict("MET", "NO_CONTENT")[0], "STRONG FIT — GAPS INCLUDE A PROVISION HOLE")
        self.assertEqual(self.verdict("MET", "STALE_THIN", "NO_CONTENT")[0], "STRONG FIT — GAPS INCLUDE A PROVISION HOLE")

    def test_nothing_met_is_a_stretch(self):
        self.assertEqual(self.verdict("LEARNABLE", "NO_CONTENT")[0], "STRETCH FIT")

    def test_the_wrong_domain_family_beats_a_keyword_match(self):
        title, _ = self.verdict("MET", "MET", spec={"domain_family": "healthcare"})
        self.assertEqual(title, "SURFACE MATCH — STRATEGIC MISFIT")


if __name__ == "__main__":
    unittest.main()
