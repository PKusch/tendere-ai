"""A <button> does not inherit its text colour, so a button class that never sets
one draws black text on the dark page. That is how the role titles in the
dashboard once went unreadable. This checks that every class used on a button
sets a colour, so the mistake cannot come back unseen."""
import re
import unittest
from pathlib import Path

JSX = (Path(__file__).resolve().parent.parent / "dashboard.jsx").read_text(encoding="utf-8")


def button_classes():
    return set(re.findall(r'<button[^>]*className="([^"]+)"', JSX))


def rule(selector):
    # The rule ends at a "}" that finishes the line; a "}" inside ${...} does not.
    m = re.search(r"\n\s*%s\s*\{(.*?)\}[ \t]*\n" % re.escape(selector), JSX, re.S)
    return m.group(1) if m else None


class ButtonColours(unittest.TestCase):
    def test_there_are_button_classes_to_check(self):
        self.assertIn("bc-tab", button_classes())

    def test_every_button_class_sets_a_text_colour(self):
        for cls in sorted(button_classes()):
            body = rule("." + cls)
            self.assertIsNotNone(body, f".{cls} is used on a button but has no style rule")
            self.assertRegex(body, r"(^|[;\s])color\s*:", f".{cls} sets no text colour, so its text will be black")


if __name__ == "__main__":
    unittest.main()
