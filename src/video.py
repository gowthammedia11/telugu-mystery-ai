import csv
import subprocess
from pathlib import Path


TOPICS_FILE = "topics/topics.csv"


def get_voiced_topic():
    with open(TOPICS_FILE, "r", encoding="utf-8") as file:
        topics = list(csv.DictReader(file))

    for topic in topics:
        topic_id = topic["id"]

        audio_file = Path(f"audio/{topic_id}.mp3")
        script_file = Path(f"scripts/{topic_id}.txt")

        if (
            topic["status"].strip().lower() == "voiced"
            and audio_file.exists()
            and script_file.exists()
        ):
            return topic

    return None


topic = get_voiced_topic()

if not topic:
    print("NO VOICED TOPIC READY FOR VIDEO")
    exit(0)


topic_id = topic["id"]
title = topic["title"]

audio_file = Path(f"audio/{topic_id}.mp3")
output_file = Path(f"videos/{topic_id}.mp4")

Path("videos").mkdir(exist_ok=True)

print(f"BUILDING VIDEO: {title}")
print(f"AUDIO: {audio_file}")
print(f"OUTPUT: {output_file}")


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


# Create a simple video background and combine it with narration.
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

print(f"VIDEO CREATED: {output_file}")
