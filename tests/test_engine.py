"""The leadership view's numbers, pinned, so a data edit that breaks them fails CI."""
import importlib.util
import os
import itertools
import shutil
import subprocess
import json
import sys
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import engine  # noqa: E402


def load(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


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


class Classify(unittest.TestCase):
    """The three gap types, from level, recency and evidence, and the order they win in."""

    def status(self, need, have=None, coverage=None):
        profile = {"X": have} if have else {}
        content = {"X": {"coverage": coverage}} if coverage else {}
        return engine.classify({"item": "X", "need_level": need}, profile, content)[0]

    def test_held_current_and_evidenced_is_met(self):
        self.assertEqual(self.status("experienced", {"item": "X", "level": "deep", "recency": "current", "evidence": "certified"}), "MET")

    def test_held_and_current_but_unproven_is_a_latent_strength(self):
        self.assertEqual(self.status("experienced", {"item": "X", "level": "deep", "recency": "current", "evidence": "self-taught"}), "LATENT_STRENGTH")

    def test_stale_beats_weak_evidence(self):
        # old and unproven needs a refresh, not a pat on the back
        self.assertEqual(self.status("moderate", {"item": "X", "level": "deep", "recency": "stale", "evidence": "self-taught"}), "STALE_THIN")

    def test_below_the_needed_level_is_thin_even_when_current(self):
        self.assertEqual(self.status("deep", {"item": "X", "level": "familiar", "recency": "current", "evidence": "certified"}), "STALE_THIN")

    def test_not_held_splits_on_whether_the_firm_can_teach_it(self):
        self.assertEqual(self.status("moderate", coverage="full"), "LEARNABLE")
        self.assertEqual(self.status("moderate", coverage="refresh"), "LEARNABLE")
        self.assertEqual(self.status("moderate", coverage="none"), "NO_CONTENT")
        self.assertEqual(self.status("moderate"), "NO_CONTENT", "no content record at all is a provision gap, not learnable")


class DiffMerging(unittest.TestCase):
    def test_a_capability_named_twice_keeps_the_higher_need(self):
        consultant = {"profile": [{"item": "Agile", "level": "moderate", "recency": "current", "evidence": "certified"}]}
        spec = {"raw": "", "parsed_stub": [
            {"item": "Agile", "type": "capability", "need_level": "familiar", "need_recency": "current"},
            {"item": "Agile", "type": "capability", "need_level": "deep", "need_recency": "current"},
        ]}
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)   # offline: use the stub, never the network
            rows, _ = engine.diff(consultant, spec, {})
        self.assertEqual(len(rows), 1, "two mentions are one requirement")
        self.assertEqual(rows[0]["req"]["need_level"], "deep")
        self.assertEqual(rows[0]["status"], "STALE_THIN", "judged against the higher need: moderate is below deep")


@unittest.skipUnless(shutil.which("node"), "needs node to run the dashboard's own function")
class DashboardParity(unittest.TestCase):
    """dashboard.jsx carries its own JavaScript copy of verdict(). The engine's was fixed
    to stop saying 'spec met' while a gap exists and the dashboard's was not, so the live
    page kept saying it. This runs the dashboard's function and checks it agrees with the
    engine for every combination of statuses."""

    STATUSES = ["MET", "LATENT_STRENGTH", "STALE_THIN", "LEARNABLE", "NO_CONTENT"]

    @classmethod
    def setUpClass(cls):
        src = (ROOT / "dashboard.jsx").read_text(encoding="utf-8")
        start = src.index("function verdict(spec, rows) {")
        end = src.index("\n}\n", start) + 3
        cls.js_fn = src[start:end]

    def js_title(self, statuses):
        rows = json.dumps([{"status": st} for st in statuses])
        code = ('const MAYA={profile:[{family:"banking"}]};' + self.js_fn +
                f'console.log(verdict({{domainFamily:"banking"}},{rows}).title)')
        out = subprocess.run(["node", "-e", code], capture_output=True, text=True, encoding="utf-8", check=True)
        return out.stdout.strip()

    def test_the_dashboard_and_the_engine_give_the_same_title_for_every_combination(self):
        consultant, spec = {"profile": [{"family": "banking"}], "ambitions": []}, {"domain_family": "banking"}
        checked = 0
        for n in (1, 2, 3):
            for combo in itertools.product(self.STATUSES, repeat=n):
                engine_title, _ = engine.verdict(consultant, spec, _rows(*combo))
                self.assertEqual(self.js_title(combo).casefold(), engine_title.casefold(), combo)
                checked += 1
        self.assertEqual(checked, 5 + 25 + 125)


class NonUtf8DefaultEncoding(unittest.TestCase):
    """The data files are UTF-8 and full of dashes and accents. The engine read them with the
    platform default, so on a machine whose default is not UTF-8 (ASCII here, a Windows code
    page there) it could not even load its own data. The console is kept UTF-8 so this
    isolates file reading from what is printed."""

    def test_the_engine_loads_its_data_under_an_ascii_default(self):
        env = {**os.environ, "LC_ALL": "C", "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0", "PYTHONIOENCODING": "utf-8"}
        probe = subprocess.run([sys.executable, "-c", "import locale; print(locale.getpreferredencoding(False))"],
                               env=env, capture_output=True, text=True)
        self.assertNotIn("utf", probe.stdout.lower(), "the test proves nothing if the default is UTF-8")
        r = subprocess.run([sys.executable, str(ROOT / "engine.py")], cwd=ROOT, env=env,
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr[-300:])
        self.assertIn("VERDICT", r.stdout)


if __name__ == "__main__":
    unittest.main()
