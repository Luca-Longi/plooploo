import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from datetime import datetime
from unittest.mock import Mock, patch


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


posting = load("tweet_art")
records = load("save_tweet_record")


class PostingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.log = Path(self.directory.name) / "render_log.json"
        self.log.write_text(json.dumps({
            "video_count": 117,
            "last_render": "2026-11-09T00:38:00+00:00",
            "last_tweeted": {"video": 116},
        }))

    def check(self, instant, *flags):
        clock = Mock()
        clock.now.side_effect = lambda tz: datetime.fromisoformat(instant).astimezone(tz)
        clock.fromisoformat = datetime.fromisoformat
        output = io.StringIO()
        with patch.object(posting, "JSON_PATH", str(self.log)), patch.object(
            posting, "datetime", clock
        ), patch("sys.argv", ["tweet_art", "--check-only", *flags]), contextlib.redirect_stdout(output):
            try:
                posting.main()
            except SystemExit as error:
                self.assertEqual(error.code, 0)
        return output.getvalue()

    def test_target_and_midnight_catchup(self):
        self.assertIn("Waiting", self.check("2026-11-09T17:59:00+01:00"))
        self.assertIn("eligible", self.check("2026-11-09T18:00:00+01:00"))
        self.assertIn("eligible", self.check("2026-11-10T00:30:00+01:00"))

    def test_expiration_even_when_forced(self):
        self.assertIn("24 hours old", self.check("2026-11-10T01:38:00+01:00", "--force"))

    def test_legacy_and_current_duplicate_records(self):
        for record in [117, {"video": 117}]:
            data = json.loads(self.log.read_text())
            data["last_tweeted"] = record
            self.log.write_text(json.dumps(data))
            self.assertIn("already tweeted", self.check("2026-11-09T18:00:00+01:00"))

    def test_replaced_render_does_not_replay_missing_piece(self):
        data = json.loads(self.log.read_text())
        data.update(video_count=118, last_render="2026-11-10T00:38:00+00:00")
        self.log.write_text(json.dumps(data))
        output = self.check("2026-11-10T04:00:00+01:00")
        self.assertIn("Piece #118", output)
        self.assertIn("Waiting", output)

    def test_record_retries_preserve_concurrent_render(self):
        receipt = {"video": 117, "tweet_id": "123"}
        latest = {"video_count": 118, "last_render": "new", "last_tweeted": {"video": 116}}
        previous_directory = os.getcwd()
        self.addCleanup(os.chdir, previous_directory)
        os.chdir(self.directory.name)

        def git(*args):
            if args[0] == "reset":
                self.log.write_text(json.dumps(latest))
            return ""

        with patch.object(records, "git", side_effect=git), patch.object(
            records.subprocess, "run", side_effect=[Mock(returncode=1), Mock(returncode=0)]
        ) as push, patch.object(records.time, "sleep"):
            records.save_record(receipt)
        saved = json.loads(self.log.read_text())
        self.assertEqual(push.call_count, 2)
        self.assertEqual(saved["video_count"], 118)
        self.assertEqual(saved["last_render"], "new")
        self.assertEqual(saved["last_tweeted"], receipt)


if __name__ == "__main__":
    unittest.main()
