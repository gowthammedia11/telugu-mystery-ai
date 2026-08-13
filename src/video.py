import csv
import os
import re
import subprocess
import time
from pathlib import Path

import requests


TOPICS_FILE = "topics/topics.csv"

PEXELS_API_URL = "https://api.pexels.com/videos/search"

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080

# More frequent visual changes
MAX_CLIPS = 24

# Each visual scene approximately this long
SCENE_SECONDS = 18


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


def read_script(script_file):
    with open(script_file, "r", encoding="utf-8") as file:
        return file.read()


def clean_script(text):
    """
    Remove obvious section headings and blank lines.
    Keep the actual narration.
    """

    lines = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        # Remove markdown headings
        line = re.sub(r"^#+\s*", "", line)

        # Ignore common structural headings
        lower = line.lower()

        ignored = [
            "hook",
            "mystery",
            "background",
            "facts",
            "explanation",
            "discoveries",
            "unknowns",
            "conclusion",
        ]

        if lower.rstrip(":") in ignored:
            continue

        lines.append(line)

    return "\n".join(lines)


def create_scene_queries(script_text):
    """
    Create visual search topics based on important words
    appearing in the actual script.

    Pexels works better with simple English visual concepts.
    """

    queries = [
        "Antarctica",
        "Antarctica glacier",
        "Antarctica ice",
        "Antarctic ocean",
        "iceberg Antarctica",
        "melting glacier",
        "ice shelf",
        "polar ice",
        "snow mountains",
        "ocean waves Antarctica",
        "scientist research Antarctica",
        "satellite Earth",
        "Earth from space",
        "ice core science",
        "glacier aerial",
        "polar landscape",
        "frozen ocean",
        "deep ocean",
        "scientific research",
        "climate science",
        "ice cracking",
        "glacier aerial view",
        "snow storm",
        "Antarctic landscape",
    ]

    # Use script keywords to slightly prioritize relevant searches
    keywords = [
        "ice",
        "glacier",
        "ocean",
        "antarctica",
        "antarctic",
        "iceberg",
        "shelf",
        "satellite",
        "scientist",
        "research",
        "snow",
        "climate",
        "water",
        "earth",
    ]

    lower_script = script_text.lower()

    detected = []

    for keyword in keywords:
        if keyword in lower_script:
            detected.append(keyword)

    # Add useful queries first
    final_queries = []

    for item in detected:
        if item == "ice":
            final_queries.extend([
                "Antarctica ice",
                "glacier ice",
            ])
        elif item == "glacier":
            final_queries.extend([
                "Antarctica glacier",
                "glacier aerial",
            ])
        elif item == "ocean":
            final_queries.extend([
                "Antarctic ocean",
                "deep ocean",
            ])
        elif item == "iceberg":
            final_queries.extend([
                "Antarctica iceberg",
                "iceberg ocean",
            ])
        elif item == "scientist":
            final_queries.append(
                "scientist research"
            )
        elif item == "satellite":
            final_queries.append(
                "satellite Earth"
            )
        elif item == "earth":
            final_queries.append(
                "Earth from space"
            )

    for query in queries:
        if query not in final_queries:
            final_queries.append(query)

    return final_queries


def get_pexels_videos(query):
    api_key = os.environ.get("PEXELS_API_KEY")

    if not api_key:
        raise Exception(
            "PEXELS_API_KEY secret is missing"
        )

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

    print(
        "PEXELS API STATUS:",
        response.status_code
    )

    response.raise_for_status()

    data = response.json()

    return data.get("videos", [])


def choose_video_file(video):
    files = video.get(
        "video_files",
        []
    )

    suitable = []

    for video_file in files:

        width = video_file.get("width")
        height = video_file.get("height")
        link = video_file.get("link")

        if not link or not width or not height:
            continue

        if (
            width >= 1280
            and height >= 720
        ):
            suitable.append(
                video_file
            )

    if not suitable:
        return None

    # Prefer HD/Full HD instead of extremely large files
    suitable.sort(
        key=lambda item: (
            abs(
                item.get("width", 0)
                - VIDEO_WIDTH
            )
        )
    )

    return suitable[0]["link"]


def download_video(url, output):
    headers = {
        "User-Agent": "TeluguMysteryAI/1.0"
    }

    print(
        f"Downloading: {output.name}"
    )

    response = requests.get(
        url,
        headers=headers,
        stream=True,
        timeout=120
    )

    response.raise_for_status()

    with open(
        output,
        "wb"
    ) as file:

        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):

            if chunk:
                file.write(chunk)

    print(
        f"Downloaded: {output}"
    )

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

    return float(
        result.stdout.strip()
    )


def create_clip(
    input_video,
    output_video,
    duration
):

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

        "-crf",
        "22",

        "-pix_fmt",
        "yuv420p",

        str(output_video)
    ]

    subprocess.run(
        command,
        check=True
    )


def combine_clips(
    clips,
    output
):

    concat_file = (
        output.parent
        / "concat.txt"
    )

    with open(
        concat_file,
        "w",
        encoding="utf-8"
    ) as file:

        for clip in clips:

            file.write(
                "file '"
                f"{clip.resolve()}"
                "'\n"
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

            "-c:v",
            "libx264",

            "-preset",
            "veryfast",

            "-crf",
            "22",

            "-pix_fmt",
            "yuv420p",

            "-an",

            str(output)
        ],
        check=True
    )


def add_narration(
    video,
    audio,
    output
):

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


# ==================================================
# START
# ==================================================

topic = get_ready_topic()

if not topic:

    print(
        "NO SCRIPT + AUDIO READY"
    )

    exit(0)


topic_id = topic["id"].strip()

title = topic["title"].strip()


script_file = Path(
    f"scripts/{topic_id}.txt"
)

audio_file = Path(
    f"audio/{topic_id}.mp3"
)


visuals_dir = Path(
    "visuals"
)

downloads_dir = (
    visuals_dir
    / "downloads"
)

clips_dir = (
    visuals_dir
    / "clips"
)

videos_dir = Path(
    "videos"
)


visuals_dir.mkdir(
    exist_ok=True
)

downloads_dir.mkdir(
    exist_ok=True
)

clips_dir.mkdir(
    exist_ok=True
)

videos_dir.mkdir(
    exist_ok=True
)


print("=" * 70)
print("CREATING REAL MOVING VIDEO")
print("=" * 70)

print(
    f"TOPIC: {title}"
)

print(
    f"SCRIPT: {script_file}"
)

print(
    f"AUDIO: {audio_file}"
)


# ==================================================
# READ SCRIPT
# ==================================================

script_text = read_script(
    script_file
)

script_text = clean_script(
    script_text
)

print(
    f"SCRIPT CHARACTERS: "
    f"{len(script_text)}"
)


# ==================================================
# AUDIO DURATION
# ==================================================

audio_duration = get_audio_duration(
    audio_file
)

print(
    f"AUDIO DURATION: "
    f"{audio_duration:.2f} seconds"
)


# ==================================================
# CALCULATE NUMBER OF SCENES
# ==================================================

required_clips = int(
    audio_duration / SCENE_SECONDS
) + 1

required_clips = min(
    required_clips,
    MAX_CLIPS
)

print(
    f"TARGET VISUAL CLIPS: "
    f"{required_clips}"
)


# ==================================================
# SEARCH PEXELS
# ==================================================

search_queries = create_scene_queries(
    script_text
)

print("=" * 70)
print("SEARCHING FOR MOVING FOOTAGE")
print("=" * 70)


videos = []

used_video_ids = set()


for query in search_queries:

    if len(videos) >= MAX_CLIPS:
        break

    print(
        f"Searching Pexels: "
        f"{query}"
    )

    try:

        results = get_pexels_videos(
            query
        )

        print(
            f"Found "
            f"{len(results)} videos"
        )

        for result in results:

            video_id = result.get(
                "id"
            )

            if (
                video_id
                and video_id
                in used_video_ids
            ):
                continue

            videos.append(
                result
            )

            if video_id:
                used_video_ids.add(
                    video_id
                )

            if len(videos) >= MAX_CLIPS:
                break

    except Exception as error:

        print(
            f"Search failed: "
            f"{error}"
        )

    time.sleep(0.5)


if len(videos) < 3:

    print(
        "NOT ENOUGH PEXELS "
        "VIDEOS FOUND"
    )

    exit(1)


print(
    f"TOTAL UNIQUE VIDEO SOURCES: "
    f"{len(videos)}"
)


# ==================================================
# DOWNLOAD MOVING FOOTAGE
# ==================================================

downloaded = []


for index, video in enumerate(
    videos,
    start=1
):

    if (
        len(downloaded)
        >= required_clips
    ):
        break

    video_url = choose_video_file(
        video
    )

    if not video_url:
        print(
            f"Clip {index}: "
            "No suitable HD file"
        )

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
            f"Download failed: "
            f"{error}"
        )

    time.sleep(0.5)


if len(downloaded) < 3:

    print(
        "FAILED: LESS THAN 3 "
        "MOVING VIDEO CLIPS"
    )

    exit(1)


print(
    f"DOWNLOADED MOVING CLIPS: "
    f"{len(downloaded)}"
)


# ==================================================
# SCENE DURATION
# ==================================================

scene_duration = (
    audio_duration
    / len(downloaded)
)

print(
    f"AVERAGE SCENE DURATION: "
    f"{scene_duration:.2f} seconds"
)


# ==================================================
# PREPARE EACH MOVING CLIP
# ==================================================

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
        "=" * 50
    )

    print(
        f"PREPARING MOVING CLIP "
        f"{index}/{len(downloaded)}"
    )

    print(
        f"SOURCE: {source.name}"
    )

    create_clip(
        source,
        prepared,
        scene_duration
    )

    prepared_clips.append(
        prepared
    )


# ==================================================
# JOIN MOVING CLIPS
# ==================================================

silent_video = (
    visuals_dir
    / f"{topic_id}_moving_silent.mp4"
)

print("=" * 70)

print(
    "JOINING ALL MOVING FOOTAGE..."
)

combine_clips(
    prepared_clips,
    silent_video
)


# ==================================================
# ADD TELUGU NARRATION
# ==================================================

final_video = (
    videos_dir
    / f"{topic_id}.mp4"
)

print("=" * 70)

print(
    "ADDING TELUGU NARRATION..."
)

add_narration(
    silent_video,
    audio_file,
    final_video
)


# ==================================================
# VERIFY FINAL VIDEO
# ==================================================

print("=" * 70)

print(
    "VERIFYING FINAL VIDEO..."
)

subprocess.run(
    [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-show_entries",
        "stream=codec_type",
        "-of",
        "default=noprint_wrappers=1",
        str(final_video)
    ],
    check=True
)


print("=" * 70)
print("VIDEO CREATED SUCCESSFULLY")
print("=" * 70)

print(
    f"OUTPUT: {final_video}"
)

print(
    "FORMAT: 1920x1080"
)

print(
    "ASPECT RATIO: 16:9"
)

print(
    f"MOVING CLIPS: "
    f"{len(prepared_clips)}"
)

print(
    "TELUGU NARRATION: YES"
)

print(
    "SCRIPT USED FOR VISUAL SEARCH: YES"
)

print("=" * 70)
