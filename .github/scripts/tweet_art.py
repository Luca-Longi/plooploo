import cv2
import json
import os
import random
import sys
import tweepy

JSON_PATH = "render_log.json"
VIDEO_PATH = "assets/daily_loop.webm"
TEMP_IMAGE_PATH = "temp_preview.png"

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

# 1. Parse your JSON configuration
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

# 2. Extract a snapshot frame from the .webm video file
print(f"Opening video source: {VIDEO_PATH}")
vidcap = cv2.VideoCapture(VIDEO_PATH)
success, frame = vidcap.read()
vidcap.release()

if not success:
    print(f"Error: Failed to extract a frame from {VIDEO_PATH}. Check if file is valid.")
    sys.exit(1)

# Save the single frame as a temporary static PNG image
cv2.imwrite(TEMP_IMAGE_PATH, frame)
print(f"Extracted preview image saved to {TEMP_IMAGE_PATH}")

# 3. Setup API v1.1 for raw media upload processing
auth = tweepy.OAuth1UserHandler(
    os.environ["X_CONSUMER_KEY"], os.environ["X_CONSUMER_SECRET"],
    os.environ["X_ACCESS_TOKEN"], os.environ["X_ACCESS_TOKEN_SECRET"]
)
api_v1 = tweepy.API(auth)

# Setup API v2 for modern text publishing
client_v2 = tweepy.Client(
    consumer_key=os.environ["X_CONSUMER_KEY"],
    consumer_secret=os.environ["X_CONSUMER_SECRET"],
    access_token=os.environ["X_ACCESS_TOKEN"],
    access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"]
)

# 4. Upload the extracted preview image to X
print("Uploading frame preview to X...")
try:
    media = api_v1.media_upload(filename=TEMP_IMAGE_PATH)
    media_id = media.media_id_string
    print(f"Media uploaded to X infrastructure successfully. ID: {media_id}")
except Exception as e:
    print(f"Failed to upload frame file to X: {e}")
    if os.path.exists(TEMP_IMAGE_PATH): os.remove(TEMP_IMAGE_PATH)
    sys.exit(1)

# 5. Build presentation text and execute tweet publish step
intro_text = random.choice(TEXT_VARIATIONS)
chosen_hashtags = random.sample(HASHTAG_POOL, 2) + ["#plooploo"]
hashtags_str = " ".join(chosen_hashtags)

post_text = (
    f"{intro_text}\n"
    f"Today's piece: #{current_number}\n"
    f"🔗 visit plooploo website for the full animation\n\n"
    f"{hashtags_str}"
)
print(f"Generated post text:\n---\n{post_text}\n---")
try:
    response = client_v2.create_tweet(text=post_text, media_ids=[media_id])
    print(f"Successfully posted Piece #{current_number} with its video snapshot card!")
finally:
    # Clean up the local runner workspace by deleting the temporary file
    if os.path.exists(TEMP_IMAGE_PATH):
        os.remove(TEMP_IMAGE_PATH)