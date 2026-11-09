"""Save a confirmed X receipt without overwriting a concurrent render update."""

import json
import subprocess
import time
from pathlib import Path


def git(*arguments):
    return subprocess.check_output(["git", *arguments], text=True).strip()


def save_record(receipt, attempts=5):
    if not receipt.get("tweet_id"):
        raise ValueError("A confirmed X post ID is required")

    # This runs only in the disposable Actions checkout. Each attempt starts
    # from the latest main and changes only last_tweeted in its render log.
    for attempt in range(attempts):
        git("fetch", "--no-tags", "origin", "main")
        git("reset", "--hard", "FETCH_HEAD")
        path = Path("render_log.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        previous = data.get("last_tweeted")
        previous_number = previous.get("video", 0) if isinstance(previous, dict) else previous or 0
        if previous_number >= receipt["video"]:
            return
        data["last_tweeted"] = receipt
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        git("add", "render_log.json")
        git("commit", "-m", "chore: record tweet for daily render [skip ci]")
        result = subprocess.run(["git", "push", "origin", "HEAD:main"])
        if result.returncode == 0:
            return
        if attempt + 1 < attempts:
            time.sleep(5)
    raise RuntimeError("Could not save the tweet record. Recover the receipt artifact before retrying.")


if __name__ == "__main__":
    receipt_path = Path("tweet_receipt.json")
    if receipt_path.exists():
        save_record(json.loads(receipt_path.read_text(encoding="utf-8")))
