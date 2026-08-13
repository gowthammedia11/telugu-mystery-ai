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

MAX_CLIPS = 24
SCENE_SECONDS = 18

# Visual quality settings
MIN_SOURCE_WIDTH = 1920
MIN_SOURCE_HEIGHT = 1080

# Colour preference
MIN_SATURATION = 0.08
MIN_BRIGHTNESS = 0.12


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
    lines = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        line = re.sub(r"^#+\s*", "", line)

        lower = line.lower().rstrip(":")

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

        if lower in ignored:
            continue

        lines.append(line)

    return "\n".join(lines)


def create_scene_queries(script_text):

    queries = [
        "Antarctica colorful landscape",
        "Antarctica glacier sunlight",
        "Antarctica blue ice",
        "Antarctica blue ocean",
        "Antarctica iceberg blue water",
        "colorful glacier",
        "glacier sunlight",
        "ice shelf ocean",
        "polar landscape sunlight",
        "blue iceberg ocean",
        "snow mountains sunlight",
        "ocean waves sunlight",
        "scientist research Antarctica",
        "scientist laboratory research",
        "satellite Earth space",
        "Earth from space",
        "ice core science",
        "glacier aerial sunlight",
        "polar landscape",
        "frozen ocean sunlight",
        "deep blue ocean",
        "scientific research",
        "climate science",
        "ice cracking glacier",
        "Antarctic landscape sunlight",
        "dramatic glacier landscape",
        "ocean iceberg cinematic",
        "blue ice glacier",
    ]

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

    final_queries = []

    for item in detected:

        if item == "ice":
            final_queries.extend([
                "Antarctica blue ice",
                "colorful glacier sunlight",
            ])

        elif item == "glacier":
            final_queries.extend([
                "Antarctica glacier sunlight",
                "glacier aerial sunlight",
            ])

        elif item == "ocean":
            final_queries.extend([
                "Antarctica blue ocean",
                "deep blue ocean",
            ])

        elif item == "iceberg":
            final_queries.extend([
                "blue iceberg ocean",
                "Antarctica iceberg sunlight",
            ])

        elif item == "scientist":
            final_queries.extend([
                "scientist research Antarctica",
                "scientist laboratory research",
            ])

        elif item == "satellite":
            final_queries.extend([
                "satellite Earth space",
                "Earth from space",
            ])

        elif item == "earth":
            final_queries.extend([
                "Earth from space",
                "colorful planet Earth",
            ])

    for query in queries:
        if query not in final_queries:
            final_queries.append(query)

    return final_queries


def get_pexels_videos(query):

    api_key = os.environ.get(
        "PEXELS_API_KEY"
    )

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

    return data.get(
        "videos",
        []
    )


def choose_video_file(video):

    files = video.get(
        "video_files",
        []
    )

    suitable = []

    for video_file in files:

        width = video_file.get(
            "width"
        )

        height = video_file.get(
            "height"
        )

        link = video_file.get(
            "link"
        )

        if (
            not link
            or not width
            or not height
        ):
            continue

        if (
            width >= MIN_SOURCE_WIDTH
            and height >= MIN_SOURCE_HEIGHT
        ):
            suitable.append(
                video_file
            )

    if not suitable:
        return None

    suitable.sort(
        key=lambda item: (
            item.get("width", 0)
            * item.get("height", 0)
        ),
        reverse=True
    )

    selected = suitable[0]

    print(
        "SELECTED SOURCE:",
        selected.get("width"),
        "x",
        selected.get("height")
    )

    return selected["link"]


def download_video(url, output):

    headers = {
        "User-Agent":
        "TeluguMysteryAI/1.0"
    }

    print(
        f"Downloading: {output.name}"
    )

    response = requests.get(
        url,
        headers=headers,
        stream=True,
        timeout=180
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


def get_video_visual_stats(video_file):

    """
    Returns approximate average saturation and brightness
    using FFmpeg signal statistics.

    This is used only to reject extremely dull/dark footage.
    """

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "info",
        "-ss",
        "2",
        "-i",
        str(video_file),
        "-t",
        "3",
        "-vf",
        "signalstats",
        "-f",
        "null",
        "-"
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    output = (
        result.stdout
        + result.stderr
    )

    saturation_values = []
    brightness_values = []

    for line in output.splitlines():

        if "lavfi.signalstats.SATAVG=" in line:
            try:
                value = float(
                    line.split(
                        "lavfi.signalstats.SATAVG="
                    )[1].split()[0]
                )

                saturation_values.append(
                    value
                )
            except Exception:
                pass

        if "lavfi.signalstats.YAVG=" in line:
            try:
                value = float(
                    line.split(
                        "lavfi.signalstats.YAVG="
                    )[1].split()[0]
                )

                brightness_values.append(
                    value
                )
            except Exception:
                pass

    if not saturation_values:
        return None, None

    saturation = (
        sum(saturation_values)
        / len(saturation_values)
    )

    brightness = None

    if brightness_values:
        brightness = (
            sum(brightness_values)
            / len(brightness_values)
        )

    return saturation, brightness


def is_colourful_enough(video_file):

    saturation, brightness = (
        get_video_visual_stats(
            video_file
        )
    )

    # If FFmpeg cannot calculate statistics,
    # don't reject the clip.
    if saturation is None:
        print(
            "COLOUR CHECK: unable to analyse"
        )

        return True

    normalized_saturation = (
        saturation / 255.0
    )

    normalized_brightness = 0

    if brightness is not None:
        normalized_brightness = (
            brightness / 255.0
        )

    print(
        f"COLOUR CHECK: "
        f"saturation={normalized_saturation:.3f}, "
        f"brightness={normalized_brightness:.3f}"
    )

    if (
        normalized_saturation
        < MIN_SATURATION
    ):
        print(
            "REJECTED: TOO DESATURATED"
        )

        return False

    if (
        brightness is not None
        and normalized_brightness
        < MIN_BRIGHTNESS
    ):
        print(
            "REJECTED: TOO DARK"
        )

        return False

    print(
        "ACCEPTED: GOOD COLOUR"
    )

    return True


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
            "eq=saturation=1.08:contrast=1.03:brightness=0.02,"
            "setsar=1"
        ),

        "-r",
        "30",

        "-an",

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-crf",
        "18",

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
            "medium",

            "-crf",
            "18",

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


topic_id = topic[
    "id"
].strip()

title = topic[
    "title"
].strip()


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
print("CREATING HIGH QUALITY COLOURFUL MOVING VIDEO")
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
# CALCULATE CLIPS
# ==================================================

required_clips = int(
    audio_duration
    / SCENE_SECONDS
) + 1

required_clips = min(
    required_clips,
    MAX_CLIPS
)

print(
    f"TARGET CLIPS: "
    f"{required_clips}"
)


# ==================================================
# SEARCH PEXELS
# ==================================================

search_queries = create_scene_queries(
    script_text
)

print("=" * 70)
print("SEARCHING COLOURFUL HIGH QUALITY FOOTAGE")
print("=" * 70)


videos = []

used_video_ids = set()


for query in search_queries:

    if len(videos) >= MAX_CLIPS * 3:
        break

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

            if len(videos) >= MAX_CLIPS * 3:
                break

    except Exception as error:

        print(
            f"Search failed: {error}"
        )

    time.sleep(0.5)


if len(videos) < 3:

    print(
        "NOT ENOUGH HIGH QUALITY "
        "VIDEOS FOUND"
    )

    exit(1)


print(
    f"TOTAL CANDIDATE SOURCES: "
    f"{len(videos)}"
)


# ==================================================
# DOWNLOAD + COLOUR FILTER
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
            f"Candidate {index}: "
            "No 1080p/4K source"
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

        if not is_colourful_enough(
            output_file
        ):

            print(
                f"Removing dull clip: "
                f"{output_file.name}"
            )

            try:
                output_file.unlink()
            except Exception:
                pass

            continue

        downloaded.append(
            output_file
        )

        print(
            f"ACCEPTED CLIPS: "
            f"{len(downloaded)}/"
            f"{required_clips}"
        )

    except Exception as error:

        print(
            f"Download failed: "
            f"{error}"
        )

        try:
            if output_file.exists():
                output_file.unlink()
        except Exception:
            pass

    time.sleep(0.5)


if len(downloaded) < 3:

    print(
        "FAILED: LESS THAN 3 "
        "COLOURFUL HIGH QUALITY CLIPS"
    )

    exit(1)


print(
    f"FINAL ACCEPTED CLIPS: "
    f"{len(downloaded)}"
)


# ==================================================
# SCENE LENGTH
# ==================================================

scene_duration = (
    audio_duration
    / len(downloaded)
)

print(
    f"SCENE DURATION: "
    f"{scene_duration:.2f} seconds"
)


# ==================================================
# PREPARE CLIPS
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
        f"PROCESSING CLIP "
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
# JOIN
# ==================================================

silent_video = (
    visuals_dir
    / f"{topic_id}_moving_silent.mp4"
)

print("=" * 70)

print(
    "JOINING COLOURFUL HIGH QUALITY CLIPS..."
)

combine_clips(
    prepared_clips,
    silent_video
)


# ==================================================
# ADD AUDIO
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
# VERIFY
# ==================================================

print("=" * 70)
print("VERIFYING FINAL VIDEO")
print("=" * 70)


subprocess.run(
    [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "stream=codec_type,width,height",
        "-show_entries",
        "format=duration",
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
    "RESOLUTION: 1920x1080"
)

print(
    "QUALITY: CRF 18"
)

print(
    f"MOVING CLIPS: "
    f"{len(prepared_clips)}"
)

print(
    "COLOURFUL FOOTAGE: PRIORITIZED"
)

print(
    "DULL/DARK FOOTAGE: FILTERED"
)

print(
    "TELUGU NARRATION: YES"
)

print(
    "HIGH QUALITY SOURCE: 1080P/4K"
)

print("=" * 70)
