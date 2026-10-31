"""The weekly schedule: short role-critical items first, the long track spread out."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import engine  # noqa: E402


def action(kind, item, *hours):
    return {"kind": kind, "item": item,
            "content": [{"title": f"{item} {i}", "hours": h} for i, h in enumerate(hours, 1)]}


class ScheduleWeeks(unittest.TestCase):
    def test_every_week_exists_even_when_nothing_is_planned(self):
        self.assertEqual(engine.schedule_weeks([], 3, 5), {1: [], 2: [], 3: []})

    def test_items_fill_a_week_then_move_to_the_next(self):
        weeks = engine.schedule_weeks([action("REFRESH", "Cloud", 3, 3, 3)], 4, 5)
        self.assertEqual([len(weeks[w]) for w in (1, 2, 3, 4)], [1, 1, 1, 0])

    def test_two_short_items_share_a_week(self):
        weeks = engine.schedule_weeks([action("BUILD", "Data", 2, 2)], 2, 5)
        self.assertEqual(len(weeks[1]), 2)
        self.assertEqual(weeks[2], [])

    def test_the_last_week_takes_what_is_left_instead_of_dropping_it(self):
        weeks = engine.schedule_weeks([action("REFRESH", "Cloud", 4, 4, 4)], 2, 5)
        self.assertEqual(sum(len(v) for v in weeks.values()), 3)
        self.assertEqual(len(weeks[2]), 2)

    def test_the_long_track_appears_in_every_week_with_its_share_of_hours(self):
        weeks = engine.schedule_weeks([action("EVIDENCE_LATENT", "GenAI", 12)], 4, 5)
        for w in (1, 2, 3, 4):
            self.assertEqual(len(weeks[w]), 1)
            self.assertIn("~3.0h", weeks[w][0])

    def test_an_evidence_action_with_no_content_adds_nothing(self):
        weeks = engine.schedule_weeks([{"kind": "EVIDENCE_LATENT", "item": "X", "content": []}], 2, 5)
        self.assertEqual(weeks, {1: [], 2: []})


class WorkdayEffects(unittest.TestCase):
    def test_each_kind_says_what_changes_when_it_is_done(self):
        plan = {"actions": [action("REFRESH", "Cloud"), action("BUILD", "Data"),
                            action("EVIDENCE_LATENT", "GenAI"), action("NO_FIRM_CONTENT", "Quantum")]}
        fx = engine.workday_effects(plan)
        self.assertEqual(len(fx), 4)
        self.assertIn("stale -> CURRENT", fx[0])
        self.assertIn("added to profile", fx[1])
        self.assertIn("EVIDENCED", fx[2])
        self.assertIn("FIRM PROVISION GAP", fx[3])

    def test_an_unknown_kind_is_skipped(self):
        self.assertEqual(engine.workday_effects({"actions": [action("MYSTERY", "X")]}), [])


def row(item, status):
    return {"req": {"item": item}, "status": status}


class BuildPlan(unittest.TestCase):
    consultant = {"roll_off_weeks": 4, "weekly_learning_hours": 5}
    content = {
        "Cloud": {"items": [{"title": "Cloud refresher", "hours": 3}]},
        "GenAI": {"items": [{"title": "GenAI capstone", "hours": 8, "verifiable": True},
                            {"title": "GenAI reading", "hours": 2}], "evidence_path": "Ship the capstone."},
        "Quantum": {"fragments": [{"title": "Vendor webinar", "hours": 1}], "workaround": "Ask the vendor."},
        "Data": {"items": [{"title": "Data basics", "hours": 6}]},
    }

    def plan(self, *rows):
        return engine.build_plan(self.consultant, list(rows), self.content, {"GenAI": {"capability": "GenAI"}})

    def test_met_rows_need_no_action(self):
        self.assertEqual(self.plan(row("Cloud", "MET"))["actions"], [])

    def test_each_status_becomes_its_own_kind_of_action(self):
        p = self.plan(row("Cloud", "STALE_THIN"), row("Quantum", "NO_CONTENT"),
                      row("GenAI", "LATENT_STRENGTH"), row("Data", "LEARNABLE"))
        kinds = {a["item"]: a["kind"] for a in p["actions"]}
        self.assertEqual(kinds, {"Cloud": "REFRESH", "Quantum": "NO_FIRM_CONTENT",
                                 "GenAI": "EVIDENCE_LATENT", "Data": "BUILD"})

    def test_actions_come_out_in_priority_order(self):
        p = self.plan(row("GenAI", "LATENT_STRENGTH"), row("Data", "LEARNABLE"), row("Cloud", "STALE_THIN"))
        self.assertEqual([a["kind"] for a in p["actions"]], ["REFRESH", "BUILD", "EVIDENCE_LATENT"])

    def test_a_latent_strength_keeps_only_the_verifiable_content(self):
        a = self.plan(row("GenAI", "LATENT_STRENGTH"))["actions"][0]
        self.assertEqual([c["title"] for c in a["content"]], ["GenAI capstone"])
        self.assertEqual(a["hours"], 8)
        self.assertTrue(a["future_demand_push"])

    def test_a_missing_course_is_flagged_as_a_provision_gap_with_its_workaround(self):
        a = self.plan(row("Quantum", "NO_CONTENT"))["actions"][0]
        self.assertTrue(a["provision_gap"])
        self.assertEqual(a["workaround"], "Ask the vendor.")

    def test_the_runway_is_the_roll_off_weeks_and_at_least_one(self):
        self.assertEqual(self.plan()["runway"], 4)
        short = dict(self.consultant, roll_off_weeks=0)
        self.assertEqual(engine.build_plan(short, [], {}, {})["runway"], 1)


if __name__ == "__main__":
    unittest.main()
