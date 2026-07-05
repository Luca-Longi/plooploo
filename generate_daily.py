"""
Blender internal script — run headlessly via:
  blender -b plooploo.blend -P generate_daily.py

1. Reads render_log.json to determine the next 120-frame window.
2. Renders those frames as WebM to assets/daily_loop.webm.
3. Updates render_log.json.
4. Git-commits and pushes both files to GitHub Pages.
"""

import bpy
import os
import json
import subprocess
from datetime import datetime, timezone

# ── Paths ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
LOG_PATH    = os.path.join(SCRIPT_DIR, "render_log.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "assets", "daily_loop.webm")

# ── Determine next frame window ───────────────────────────────────────────────

if os.path.exists(LOG_PATH):
    with open(LOG_PATH, "r") as f:
        log = json.load(f)
    frame_start = log["last_frame_end"] + 1
else:
    log = {}
    frame_start = 1

frame_end   = frame_start + 119          # always exactly 120 frames
video_index = log.get("video_count", 0) + 1

print(f"[generate_daily] Rendering video #{video_index}  frames {frame_start}–{frame_end}")

# ── Frame range ───────────────────────────────────────────────────────────────

scene = bpy.context.scene
scene.frame_start = frame_start
scene.frame_end   = frame_end

# ── Render settings ───────────────────────────────────────────────────────────

scene.render.film_transparent = True     # preserve alpha channel

render = scene.render
render.image_settings.file_format  = "FFMPEG"
render.ffmpeg.format               = "WEBM"
render.ffmpeg.codec                = "WEBM"   # VP8; switch to "VP9" if your Blender build supports it
render.ffmpeg.constant_rate_factor = "HIGH"
render.ffmpeg.ffmpeg_preset        = "GOOD"
render.ffmpeg.color_mode           = "RGBA"

# ── Output path ───────────────────────────────────────────────────────────────

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

# Remove stale file so Blender doesn't append a version suffix
if os.path.exists(OUTPUT_PATH):
    os.remove(OUTPUT_PATH)

render.filepath = OUTPUT_PATH

# ── Render ────────────────────────────────────────────────────────────────────

bpy.ops.render.render(animation=True, write_still=False)
print(f"[generate_daily] Render complete → {OUTPUT_PATH}")

# ── Update log ────────────────────────────────────────────────────────────────

now_iso = datetime.now(timezone.utc).isoformat()
log.update({
    "video_count":    video_index,
    "last_frame_end": frame_end,
    "last_render":    now_iso,
    "history": log.get("history", []) + [{
        "video":       video_index,
        "frame_start": frame_start,
        "frame_end":   frame_end,
        "rendered_at": now_iso,
    }],
})

with open(LOG_PATH, "w") as f:
    json.dump(log, f, indent=2)

print(f"[generate_daily] Log updated → {LOG_PATH}")

# ── Git: commit and push ──────────────────────────────────────────────────────

def git(args: list[str]) -> None:
    result = subprocess.run(
        ["git"] + args,
        cwd=SCRIPT_DIR,
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")

today = datetime.now().strftime("%Y-%m-%d")

git(["add", "assets/daily_loop.webm", "render_log.json"])
git(["commit", "-m", f"daily loop — {today}"])
git(["push", "origin", "main"])

print(f"[generate_daily] Pushed to GitHub Pages — done.")
