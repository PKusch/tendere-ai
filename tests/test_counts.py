import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
UNITS = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]


class ReadmeQuotesTheRealTestCount(unittest.TestCase):
    """The README gives the count in words ("Forty-five tests pin...") and it was
    edited by hand after every new test."""

    def test_the_count_in_words_matches_the_suite(self):
        # a fresh loader, so counting does not disturb the run that is counting
        n = unittest.TestLoader().discover(str(ROOT / "tests"), top_level_dir=str(ROOT / "tests")).countTestCases()
        m = re.search(r"^([A-Z][a-z]+(?:-[a-z]+)?) tests pin", (ROOT / "README.md").read_text(encoding="utf-8"), re.M)
        self.assertIsNotNone(m, 'README has no "<Number> tests pin" line')
        tens, _, units = m.group(1).lower().partition("-")
        self.assertIn(tens, TENS, f"cannot read {m.group(1)!r} as a number")
        self.assertIn(units, UNITS, f"cannot read {m.group(1)!r} as a number")
        self.assertEqual(TENS[tens] + UNITS.index(units), n, f"README says {m.group(1)}; the suite has {n}")


if __name__ == "__main__":
    unittest.main()
