import csv
import subprocess
from pathlib import Path


TOPICS_FILE = "topics/topics.csv"


def get_ready_topic():
    with open(TOPICS_FILE, "r", encoding="utf-8") as file:
        topics = list(csv.DictReader(file))

    # Find the first topic that already has both
    # Telugu script and generated audio.
    for topic in topics:
        topic_id = topic["id"].strip()

        script_file = Path(f"scripts/{topic_id}.txt")
        audio_file = Path(f"audio/{topic_id}.mp3")

        if script_file.exists() and audio_file.exists():
            return topic

    return None


topic = get_ready_topic()

if not topic:
    print("NO SCRIPT + AUDIO READY FOR VIDEO")
    exit(0)


topic_id = topic["id"].strip()
title = topic["title"].strip()

audio_file = Path(f"audio/{topic_id}.mp3")
output_file = Path(f"videos/{topic_id}.mp4")

Path("videos").mkdir(exist_ok=True)

print(f"BUILDING VIDEO: {title}")
print(f"AUDIO FILE: {audio_file}")
print(f"OUTPUT FILE: {output_file}")


# Get audio duration
probe = subprocess.run(
    [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_file)
    ],
    capture_output=True,
    text=True,
    check=True
)

duration = float(probe.stdout.strip())

print(f"AUDIO DURATION: {duration:.2f} seconds")


# Create 16:9 Full HD video with narration.
command = [
    "ffmpeg",
    "-y",
    "-f",
    "lavfi",
    "-i",
    "color=c=black:s=1920x1080:r=30",
    "-i",
    str(audio_file),
    "-t",
    str(duration),
    "-c:v",
    "libx264",
    "-preset",
    "veryfast",
    "-pix_fmt",
    "yuv420p",
    "-c:a",
    "aac",
    "-b:a",
    "192k",
    "-shortest",
    str(output_file)
]

subprocess.run(command, check=True)

print(f"VIDEO CREATED SUCCESSFULLY: {output_file}")
