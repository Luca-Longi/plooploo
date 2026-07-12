import cv2
import json
import os
import sys
import tweepy

JSON_PATH = "render_log.json"
VIDEO_PATH = "assets/daily_loop.webm"
TEMP_IMAGE_PATH = "temp_preview.png"

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
post_text = f"plooploo #{current_number} new #digitalart everyday. See full animation here: https://plooploo.com"

try:
    response = client_v2.create_tweet(text=post_text, media_ids=[media_id])
    print(f"Successfully posted Piece #{current_number} with its video snapshot card!")
finally:
    # Clean up the local runner workspace by deleting the temporary file
    if os.path.exists(TEMP_IMAGE_PATH):
        os.remove(TEMP_IMAGE_PATH)