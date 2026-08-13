import csv
import subprocess
from pathlib import Path
import requests


TOPICS_FILE = "topics/topics.csv"

HEADERS = {
    "User-Agent": "TeluguMysteryAI/1.0 (GitHub Actions video generator)"
}


def get_ready_topic():
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        topics = list(csv.DictReader(f))

    for topic in topics:
        topic_id = topic["id"].strip()

        if (
            Path(f"scripts/{topic_id}.txt").exists()
            and Path(f"audio/{topic_id}.mp3").exists()
        ):
            return topic

    return None


def get_wikimedia_images(query, count=6):

    url = "https://commons.wikimedia.org/w/api.php"

    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsrlimit": count,
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": "1920",
        "format": "json"
    }

    response = requests.get(
        url,
        params=params,
        headers=HEADERS,
        timeout=60
    )

    print("WIKIMEDIA STATUS:", response.status_code)

    response.raise_for_status()

    data = response.json()

    pages = data.get("query", {}).get("pages", {})

    images = []

    for page in pages.values():

        info = page.get("imageinfo", [])

        if info:

            image_url = (
                info[0].get("thumburl")
                or info[0].get("url")
            )

            if image_url:
                images.append(image_url)

    return images[:count]


topic = get_ready_topic()

if not topic:
    print("NO READY TOPIC")
    exit(0)


topic_id = topic["id"].strip()
title = topic["title"].strip()

audio = Path(f"audio/{topic_id}.mp3")

videos = Path("videos")
visuals = Path("visuals")

videos.mkdir(exist_ok=True)
visuals.mkdir(exist_ok=True)

print(f"CREATING VISUAL VIDEO: {title}")


# Search Wikimedia
images = get_wikimedia_images(title, 6)

if len(images) < 3:
    print("NOT ENOUGH IMAGES FOUND")
    print("Images found:", len(images))
    exit(1)


print(f"FOUND {len(images)} IMAGES")


# Download images
downloaded = []

for index, image_url in enumerate(images, start=1):

    output = visuals / f"{topic_id}_{index}.jpg"

    print(f"DOWNLOADING IMAGE {index}")

    r = requests.get(
        image_url,
        headers=HEADERS,
        timeout=60
    )

    r.raise_for_status()

    output.write_bytes(r.content)

    downloaded.append(output)


# Audio duration
probe = subprocess.run(
    [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio)
    ],
    capture_output=True,
    text=True,
    check=True
)

duration = float(probe.stdout.strip())

scene_duration = duration / len(downloaded)

print(f"AUDIO DURATION: {duration:.2f} seconds")
print(f"SCENE DURATION: {scene_duration:.2f} seconds")


# Create clips
clips = []

for index, image in enumerate(downloaded, start=1):

    clip = visuals / f"{topic_id}_clip_{index}.mp4"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-i", str(image),
            "-t", str(scene_duration),
            "-vf",
            "scale=1920:1080:force_original_aspect_ratio=increase,"
            "crop=1920:1080",
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            str(clip)
        ],
        check=True
    )

    clips.append(clip)


# Concat file
concat_file = visuals / f"{topic_id}_concat.txt"

with open(concat_file, "w", encoding="utf-8") as f:

    for clip in clips:
        f.write(f"file '{clip.resolve()}'\n")


silent_video = visuals / f"{topic_id}_silent.mp4"


# Combine clips
subprocess.run(
    [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(silent_video)
    ],
    check=True
)


# Add Telugu narration
output = videos / f"{topic_id}.mp4"

subprocess.run(
    [
        "ffmpeg",
        "-y",
        "-i", str(silent_video),
        "-i", str(audio),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output)
    ],
    check=True
)


print(f"VIDEO CREATED: {output}")
