import datetime as dt
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from update_chapters import read_chapters, run

HTML_133 = """<html><body><h1>Kagurabachi</h1><p>New chapter coming in 7 days!</p>
<div>October 4, 2026 Ch. 133 FREE</div><div>September 27, 2026 Ch. 132 FREE</div>
<div>September 6, 2026 Ch. 131 FREE</div></body></html>"""
HTML_134 = HTML_133.replace(
    "<div>October 4", "<div>October 11, 2026 Ch. 134 FREE</div><div>October 4"
)
NOW_BEFORE = dt.datetime(2026, 10, 9, 20, tzinfo=dt.timezone.utc)
NOW_AFTER = dt.datetime(2026, 10, 11, 16, tzinfo=dt.timezone.utc)


class TestChapterFeed(unittest.TestCase):
    def test_expected_latest(self):
        self.assertEqual(read_chapters(HTML_133, NOW_BEFORE)[-1][1], "133")

    def test_dont_announce_future(self):
        self.assertEqual(read_chapters(HTML_134, NOW_BEFORE)[-1][1], "133")

    def test_baseline_then_once(self):
        original = os.getcwd()
        with tempfile.TemporaryDirectory() as folder:
            os.chdir(folder)
            try:
                self.assertIn("Initialized", run(HTML_133, NOW_BEFORE))
                self.assertNotIn("<item>", Path("chapters.xml").read_text())
                self.assertIn("Added 1", run(HTML_134, NOW_AFTER))
                self.assertIn("Chapter 134", Path("chapters.xml").read_text())
                self.assertIn("No new chapter", run(HTML_134, NOW_AFTER))
                self.assertEqual(Path("chapters.xml").read_text().count("<item>"), 1)
                self.assertEqual(json.loads(Path("state.json").read_text())["last_chapter"], "134")
            finally:
                os.chdir(original)

    def test_unparseable_page_does_not_change_state(self):
        original = os.getcwd()
        with tempfile.TemporaryDirectory() as folder:
            os.chdir(folder)
            try:
                with self.assertRaisesRegex(RuntimeError, "could not be parsed"):
                    run("<html>Access denied</html>", NOW_BEFORE)
                self.assertFalse(Path("state.json").exists())
            finally:
                os.chdir(original)


if __name__ == "__main__":
    unittest.main()
