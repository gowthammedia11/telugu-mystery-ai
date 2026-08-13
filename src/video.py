import csv
import os
import subprocess
import time
from pathlib import Path

import requests


TOPICS_FILE = "topics/topics.csv"

PEXELS_API_URL = "https://api.pexels.com/videos/search"

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080

MAX_CLIPS = 8


def get_ready_topic():
    with open(TOPICS_FILE, "r", encoding="utf-8") as file:
        topics = list(csv.DictReader(file))

    for topic in topics:
        topic_id = topic["id"].strip()

        script_file = Path(f"scripts/{topic_id}.txt")
        audio_file = Path(f"audio/{topic_id}.mp3")

        if script_file.exists() and audio_file.exists():
            return topic

    return None


def get_pexels_videos(query):
    api_key = os.environ.get("PEXELS_API_KEY")

    if not api_key:
        raise Exception("PEXELS_API_KEY secret is missing")

    headers = {
        "Authorization": api_key
    }

    params = {
        "query": query,
        "orientation": "landscape",
        "size": "large",
        "per_page": 15
    }

    response = requests.get(
        PEXELS_API_URL,
        headers=headers,
        params=params,
        timeout=60
    )

    print("PEXELS API STATUS:", response.status_code)

    response.raise_for_status()

    data = response.json()

    return data.get("videos", [])


def choose_video_file(video):
    files = video.get("video_files", [])

    suitable = []

    for video_file in files:
        width = video_file.get("width")
        height = video_file.get("height")
        link = video_file.get("link")

        if not link or not width or not height:
            continue

        if width >= 1280 and height >= 720:
            suitable.append(video_file)

    if not suitable:
        return None

    suitable.sort(
        key=lambda item: item.get("width", 0),
        reverse=True
    )

    return suitable[0]["link"]


def download_video(url, output):
    headers = {
        "User-Agent": "TeluguMysteryAI/1.0"
    }

    print(f"Downloading: {output.name}")

    response = requests.get(
        url,
        headers=headers,
        stream=True,
        timeout=120
    )

    response.raise_for_status()

    with open(output, "wb") as file:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                file.write(chunk)

    print(f"Downloaded: {output}")

    return True


def get_audio_duration(audio_file):
    result = subprocess.run(
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

    return float(result.stdout.strip())


def create_clip(input_video, output_video, duration):
    command = [
        "ffmpeg",
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        str(input_video),
        "-t",
        str(duration),
        "-vf",
        (
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
            "force_original_aspect_ratio=increase,"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
            "setsar=1"
        ),
        "-r",
        "30",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        str(output_video)
    ]

    subprocess.run(command, check=True)


def combine_clips(clips, output):
    concat_file = output.parent / "concat.txt"

    with open(concat_file, "w", encoding="utf-8") as file:
        for clip in clips:
            file.write(
                f"file '{clip.resolve()}'\n"
            )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            str(output)
        ],
        check=True
    )


def add_narration(video, audio, output):
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output)
        ],
        check=True
    )


# --------------------------------------------------
# START
# --------------------------------------------------

topic = get_ready_topic()

if not topic:
    print("NO SCRIPT + AUDIO READY")
    exit(0)

topic_id = topic["id"].strip()
title = topic["title"].strip()

audio_file = Path(
    f"audio/{topic_id}.mp3"
)

visuals_dir = Path("visuals")
downloads_dir = visuals_dir / "downloads"
clips_dir = visuals_dir / "clips"
videos_dir = Path("videos")

visuals_dir.mkdir(exist_ok=True)
downloads_dir.mkdir(exist_ok=True)
clips_dir.mkdir(exist_ok=True)
videos_dir.mkdir(exist_ok=True)

print("=" * 60)
print("CREATING REAL VIDEO")
print("=" * 60)
print(f"TOPIC: {title}")
print(f"AUDIO: {audio_file}")

audio_duration = get_audio_duration(
    audio_file
)

print(
    f"AUDIO DURATION: "
    f"{audio_duration:.2f} seconds"
)


# --------------------------------------------------
# SEARCH FOR MOVING FOOTAGE
# --------------------------------------------------

search_queries = [
    title,
    "Antarctica ice",
    "Antarctica glacier",
    "Antarctic ocean",
    "iceberg",
    "polar ice",
    "snow mountains",
    "scientific research Antarctica"
]

videos = []

for query in search_queries:

    print(
        f"Searching Pexels: {query}"
    )

    try:

        results = get_pexels_videos(
            query
        )

        print(
            f"Found {len(results)} videos"
        )

        for result in results:

            if result not in videos:
                videos.append(result)

            if len(videos) >= MAX_CLIPS:
                break

    except Exception as error:

        print(
            f"Search failed for "
            f"{query}: {error}"
        )

    if len(videos) >= MAX_CLIPS:
        break


if len(videos) < 3:

    print(
        "NOT ENOUGH PEXELS VIDEOS FOUND"
    )

    exit(1)


print(
    f"TOTAL VIDEO SOURCES: "
    f"{len(videos)}"
)


# --------------------------------------------------
# DOWNLOAD MOVING FOOTAGE
# --------------------------------------------------

downloaded = []

for index, video in enumerate(
    videos,
    start=1
):

    if len(downloaded) >= MAX_CLIPS:
        break

    video_url = choose_video_file(
        video
    )

    if not video_url:
        continue

    output_file = (
        downloads_dir
        / f"{topic_id}_{index}.mp4"
    )

    try:

        download_video(
            video_url,
            output_file
        )

        downloaded.append(
            output_file
        )

    except Exception as error:

        print(
            f"Download failed: {error}"
        )

    time.sleep(1)


if len(downloaded) < 3:

    print(
        "FAILED: LESS THAN 3 MOVING "
        "VIDEO CLIPS DOWNLOADED"
    )

    exit(1)


print(
    f"DOWNLOADED MOVING CLIPS: "
    f"{len(downloaded)}"
)


# --------------------------------------------------
# CALCULATE SCENE LENGTH
# --------------------------------------------------

scene_duration = (
    audio_duration / len(downloaded)
)

print(
    f"SCENE DURATION: "
    f"{scene_duration:.2f} seconds"
)


# --------------------------------------------------
# CONVERT EACH CLIP TO 16:9
# --------------------------------------------------

prepared_clips = []

for index, source in enumerate(
    downloaded,
    start=1
):

    prepared = (
        clips_dir
        / f"{topic_id}_clip_{index}.mp4"
    )

    print(
        f"Preparing clip {index}: "
        f"{source.name}"
    )

    create_clip(
        source,
        prepared,
        scene_duration
    )

    prepared_clips.append(
        prepared
    )


# --------------------------------------------------
# JOIN ALL MOVING CLIPS
# --------------------------------------------------

silent_video = (
    visuals_dir
    / f"{topic_id}_moving_silent.mp4"
)

print("Joining moving footage...")

combine_clips(
    prepared_clips,
    silent_video
)


# --------------------------------------------------
# ADD TELUGU NARRATION
# --------------------------------------------------

final_video = (
    videos_dir
    / f"{topic_id}.mp4"
)

print("Adding Telugu narration...")

add_narration(
    silent_video,
    audio_file,
    final_video
)


print("=" * 60)
print("VIDEO CREATED SUCCESSFULLY")
print("=" * 60)
print(f"OUTPUT: {final_video}")
print("FORMAT: 1920x1080")
print("ASPECT RATIO: 16:9")
print("MOVING FOOTAGE: YES")
print("TELUGU NARRATION: YES")
print("=" * 60)
