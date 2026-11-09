import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    CET_TZ = ZoneInfo("Europe/Paris")
except Exception:
    CET_TZ = timezone(timedelta(hours=1))

JSON_PATH = "render_log.json"
VIDEO_PATH = "assets/daily_loop.webm"
TEMP_IMAGE_PATH = "temp_preview.png"
RECEIPT_PATH = "tweet_receipt.json"

# Schedule of rotating posting hours in Rome time, between 04:00 and 18:00.
# Each piece rotates to a different hour to cover different global timezones.
TARGET_HOURS_SCHEDULE = [
    (15, "EU Afternoon / US East Morning"),       # 15:00 CET (09:00 EST)
    (7,  "EU Morning / Asia-Pacific Afternoon"),  # 07:00 CET (15:00 Tokyo)
    (17, "Europe Late Afternoon / US Morning"),
    (12, "Europe Midday / Lunch"),                # 12:00 CET (16:30 India)
    (18, "Europe Evening / US Midday"),           # 18:00 CET (12:00 EST)
    (5,  "Asia-Pacific Morning / Australia"),     # 05:00 CET (13:00 Tokyo / 15:00 Sydney)
    (16, "Europe Afternoon / US Morning"),
    (10, "Europe Morning / Asia Evening"),        # 10:00 CET (18:00 Tokyo)
    (16, "US East Start / Europe Late Work"),     # 16:00 CET (10:00 EST)
    (18, "Europe Evening / US Midday"),
    (8,  "Europe Commute / Asia Dinner"),         # 08:00 CET (16:00 Tokyo)
    (14, "Europe Afternoon / US East Wake"),      # 14:00 CET (08:00 EST)
    (15, "Europe Afternoon / US East Morning"),
    (6,  "Japan & Australia Prime / Dawn EU"),    # 06:00 CET (14:00 Tokyo / 16:00 Sydney)
    (13, "Europe Lunch / South Asia Evening"),    # 13:00 CET (17:30 India)
    (17, "Europe Transition / US East Noon"),     # 17:00 CET (11:00 EST)
    (11, "Europe Late Morning"),                  # 11:00 CET
    (4,  "Asia-Pacific Business Start"),          # 04:00 CET (12:00 Tokyo)
]

TEXT_VARIATIONS = [
    "A new 3D loop procedurally generated every single day.",
    "Another animation is online for today only.",
    "A new render is ready. No AI, old-fashioned 3D render.",
    "A new animation loop is ready.",
    "Fresh daily 3D render dropped!",
    "New day, new procedural 3D loop.",
    "Today's procedural loop is live!",
    "A brand new procedural animation is live.",
    "Another unique 3D loop procedurally generated today.",
]

HASHTAG_POOL = [
    "#proceduralart",
    "#everydays",
    "#digitalart",
    "#generativeart",
    "#creativecoding",
    "#3dart",
    "#3danimation",
    "#loopinganimation",
    "#dailyart",
]


def get_target_hour_cet(piece_number: int) -> tuple[int, str]:
    """Returns (target_hour_cet, target_timezone_description) for a given piece number."""
    return TARGET_HOURS_SCHEDULE[piece_number % len(TARGET_HOURS_SCHEDULE)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tweet daily procedural 3D render")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Publish immediately (bypasses target hour, preserves duplicate protection)",
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Display the upcoming posting schedule and exit",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Check eligibility without posting; write should_post to GITHUB_OUTPUT",
    )
    return parser.parse_args()


def print_schedule(current_piece: int) -> None:
    print("\n--- Upcoming Posting Schedule (Rome time) ---")
    for offset in range(len(TARGET_HOURS_SCHEDULE)):
        piece = current_piece + offset
        hour, focus = get_target_hour_cet(piece)
        marker = " (Next)" if offset == 1 else (" (Current)" if offset == 0 else "")
        print(f"  Piece #{piece:3d}: {hour:02d}:00  --  {focus}{marker}")
    print("-----------------------------------------------------------------\n")


def main() -> None:
    args = parse_args()
    if args.check_only and os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write("should_post=false\n")

    # 1. Parse JSON configuration
    try:
        with open(JSON_PATH, "r") as f:
            log_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {JSON_PATH} not found.")
        sys.exit(1)

    current_number = log_data.get("video_count")
    if current_number is None:
        print("Error: 'video_count' key missing from JSON.")
        sys.exit(1)

    if args.schedule:
        print_schedule(current_number)
        sys.exit(0)

    # 2. Duplicate check: has this piece already been posted?
    last_tweeted = log_data.get("last_tweeted")
    last_tweeted_video = (
        last_tweeted.get("video") if isinstance(last_tweeted, dict) else last_tweeted
    )

    if last_tweeted_video == current_number:
        tweeted_at = (
            last_tweeted.get("tweeted_at", "an earlier run")
            if isinstance(last_tweeted, dict)
            else "an earlier run"
        )
        print(
            f"Piece #{current_number} was already tweeted ({tweeted_at}). Skipping."
        )
        sys.exit(0)

    # 3. Anchor the target hour to the render date so delayed runs can cross midnight.
    target_hour, target_audience = get_target_hour_cet(current_number)
    now_cet = datetime.now(CET_TZ)
    rendered_at = datetime.fromisoformat(log_data["last_render"])
    expires_at = rendered_at.astimezone(timezone.utc) + timedelta(hours=24)
    target_at = rendered_at.astimezone(CET_TZ).replace(
        hour=target_hour, minute=0, second=0, microsecond=0
    )

    if now_cet >= expires_at:
        print(f"Piece #{current_number} is more than 24 hours old. Skipping.")
        return

    if not args.force and now_cet < target_at:
        print(
            f"[Schedule Check] Piece #{current_number} is scheduled for {target_at:%Y-%m-%d %H:%M %Z} "
            f"({target_audience}). Current time: {now_cet:%Y-%m-%d %H:%M %Z}. "
            f"Waiting for scheduled hour."
        )
        sys.exit(0)

    print(
        f"[Publishing] Piece #{current_number} is due at {target_at:%Y-%m-%d %H:%M %Z} "
        f"({target_audience}). Current time: {now_cet:%Y-%m-%d %H:%M %Z}. "
        f"Proceeding with broadcast."
    )

    # 4. Check-only runs never import dependencies or contact X.
    if args.check_only:
        print(f"Piece #{current_number} is eligible for posting.")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as output:
                output.write("should_post=true\n")
        return

    # Import heavy third-party dependencies only when posting
    import cv2
    import random
    import tweepy

    # 5. Extract a snapshot frame from the .webm video file
    print(f"Opening video source: {VIDEO_PATH}")
    if not os.path.exists(VIDEO_PATH):
        print(f"Error: Video file {VIDEO_PATH} not found.")
        sys.exit(1)

    vidcap = cv2.VideoCapture(VIDEO_PATH)
    success, frame = vidcap.read()
    vidcap.release()

    if not success or frame is None:
        print(f"Error: Failed to extract a frame from {VIDEO_PATH}. Check if file is valid.")
        sys.exit(1)

    # Save the single frame as a temporary static PNG image
    if not cv2.imwrite(TEMP_IMAGE_PATH, frame):
        sys.exit("Error: Failed to save the preview image.")
    print(f"Extracted preview image saved to {TEMP_IMAGE_PATH}")

    # Validate required credentials
    required_env = [
        "X_CONSUMER_KEY",
        "X_CONSUMER_SECRET",
        "X_ACCESS_TOKEN",
        "X_ACCESS_TOKEN_SECRET",
    ]
    missing_env = [k for k in required_env if not os.environ.get(k)]
    if missing_env:
        print(f"Error: Missing required environment variables: {', '.join(missing_env)}")
        if os.path.exists(TEMP_IMAGE_PATH):
            os.remove(TEMP_IMAGE_PATH)
        sys.exit(1)

    try:
        # 6. Setup API v1.1 for raw media upload processing
        auth = tweepy.OAuth1UserHandler(
            os.environ["X_CONSUMER_KEY"],
            os.environ["X_CONSUMER_SECRET"],
            os.environ["X_ACCESS_TOKEN"],
            os.environ["X_ACCESS_TOKEN_SECRET"],
        )
        api_v1 = tweepy.API(auth)

        # Setup API v2 for modern text publishing
        client_v2 = tweepy.Client(
            consumer_key=os.environ["X_CONSUMER_KEY"],
            consumer_secret=os.environ["X_CONSUMER_SECRET"],
            access_token=os.environ["X_ACCESS_TOKEN"],
            access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
        )

        # 7. Upload the extracted preview image to X
        print("Uploading frame preview to X...")
        media = api_v1.media_upload(filename=TEMP_IMAGE_PATH)
        media_id = media.media_id_string
        print(f"Media uploaded to X infrastructure successfully. ID: {media_id}")

        # 8. Build presentation text and execute tweet publish step
        # Keep retry content stable for the same piece.
        selection = random.Random(current_number)
        intro_text = selection.choice(TEXT_VARIATIONS)
        chosen_hashtags = selection.sample(HASHTAG_POOL, 2) + ["#plooploo"]
        hashtags_str = " ".join(chosen_hashtags)

        post_text = (
            f"{intro_text}\n"
            f"Today's piece: #{current_number}\n"
            f"🔗 visit plooploo website for the full animation\n\n"
            f"{hashtags_str}"
        )
        print(f"Generated post text:\n---\n{post_text}\n---")

        if os.environ.get("GITHUB_ACTIONS") == "true":
            subprocess.run(["git", "fetch", "--no-tags", "origin", "main"], check=True)
            latest_log = json.loads(
                subprocess.check_output(["git", "show", f"FETCH_HEAD:{JSON_PATH}"])
            )
            if (latest_log["video_count"], latest_log["last_render"]) != (
                current_number, log_data["last_render"]
            ):
                print(f"Piece #{current_number} was replaced by a newer render. Skipping.")
                return

        if datetime.now(timezone.utc) >= expires_at:
            print(f"Piece #{current_number} expired before publishing. Skipping.")
            return

        response = client_v2.create_tweet(text=post_text, media_ids=[media_id])
        tweet_id = (getattr(response, "data", None) or {}).get("id")
        if not tweet_id:
            raise RuntimeError("X returned no post ID. Check X before retrying this run.")
        print(f"Successfully posted Piece #{current_number}! Tweet ID: {tweet_id}")

        # 9. Update render_log.json with the tweet timestamp and ID
        now_iso = datetime.now(timezone.utc).isoformat()
        receipt = {
            "video": current_number,
            "tweeted_at": now_iso,
            "tweet_id": str(tweet_id) if tweet_id else None,
            "posted_hour_cet": now_cet.hour,
        }
        with open(RECEIPT_PATH, "w") as f:
            json.dump(receipt, f, indent=2)
        log_data["last_tweeted"] = receipt
        with open(JSON_PATH, "w") as f:
            json.dump(log_data, f, indent=2)
        print(f"Updated {JSON_PATH} with tweet record for Piece #{current_number}.")

    except Exception as e:
        print(f"Failed to publish tweet to X: {e}")
        sys.exit(1)
    finally:
        # Clean up the local runner workspace by deleting the temporary file
        if os.path.exists(TEMP_IMAGE_PATH):
            os.remove(TEMP_IMAGE_PATH)


if __name__ == "__main__":
    main()
