import csv
import json
import os
import re
import subprocess
import time
from pathlib import Path

import requests


# ============================================================
# CONFIG
# ============================================================

TOPICS_FILE = "topics/topics.csv"
PEXELS_API_URL = "https://api.pexels.com/videos/search"

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080

MAX_CLIPS = 24
SCENE_SECONDS = 18

MIN_SOURCE_WIDTH = 1920
MIN_SOURCE_HEIGHT = 1080

MIN_SATURATION = 0.08
MIN_BRIGHTNESS = 0.12

# ============================================================
# BACKGROUND MUSIC CONFIG
# ============================================================

MUSIC_CONFIG_FILE = Path("music/music-config.json")

DEFAULT_MUSIC_CATEGORY = "mystery"
DEFAULT_MUSIC_VOLUME = 0.055


# ============================================================
# TOPIC
# ============================================================

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


# ============================================================
# SCRIPT
# ============================================================

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


# ============================================================
# PEXELS SEARCH QUERIES
# ============================================================

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

    detected = [
        keyword
        for keyword in keywords
        if keyword in lower_script
    ]

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


# ============================================================
# PEXELS
# ============================================================

def get_pexels_videos(query):

    api_key = os.environ.get("PEXELS_API_KEY")

    if not api_key:
        raise Exception(
            "PEXELS_API_KEY secret is missing"
        )

    response = requests.get(
        PEXELS_API_URL,
        headers={
            "Authorization": api_key
        },
        params={
            "query": query,
            "orientation": "landscape",
            "size": "large",
            "per_page": 15,
        },
        timeout=60,
    )

    print(
        "PEXELS API STATUS:",
        response.status_code
    )

    response.raise_for_status()

    return response.json().get(
        "videos",
        []
    )


# ============================================================
# USED PEXELS HISTORY
# ============================================================

def load_used_video_ids():

    history_file = Path(
        "visuals/used_pexels_ids.txt"
    )

    if not history_file.exists():
        return set()

    return {
        line.strip()
        for line in history_file.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    }


def save_used_video_ids(video_ids):

    history_file = Path(
        "visuals/used_pexels_ids.txt"
    )

    history_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with history_file.open(
        "a",
        encoding="utf-8"
    ) as file:

        for video_id in video_ids:
            file.write(
                f"{video_id}\n"
            )


# ============================================================
# SOURCE VIDEO
# ============================================================

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

        if not link or not width or not height:
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
        key=lambda item:
        item.get("width", 0)
        * item.get("height", 0),
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

    print(
        f"Downloading: {output.name}"
    )

    response = requests.get(
        url,
        headers={
            "User-Agent":
            "TeluguMysteryAI/1.0"
        },
        stream=True,
        timeout=180,
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


# ============================================================
# AUDIO
# ============================================================

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
            str(audio_file),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    return float(
        result.stdout.strip()
    )


# ============================================================
# VISUAL QUALITY
# ============================================================

def get_video_visual_stats(video_file):

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
        "-",
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    output = (
        result.stdout
        + result.stderr
    )

    saturation_values = []
    brightness_values = []

    for line in output.splitlines():

        if (
            "lavfi.signalstats.SATAVG="
            in line
        ):

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

        if (
            "lavfi.signalstats.YAVG="
            in line
        ):

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

    if saturation is None:

        print(
            "COLOUR CHECK: unable to analyse"
        )

        return True

    normalized_saturation = (
        saturation / 255.0
    )

    normalized_brightness = (
        brightness / 255.0
        if brightness is not None
        else 0
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


# ============================================================
# CREATE VIDEO CLIP
# ============================================================

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
            "eq=saturation=1.08:"
            "contrast=1.03:"
            "brightness=0.02,"
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

        str(output_video),
    ]

    subprocess.run(
        command,
        check=True
    )


# ============================================================
# COMBINE CLIPS
# ============================================================

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

            "-c:v",
            "libx264",

            "-preset",
            "medium",

            "-crf",
            "18",

            "-pix_fmt",
            "yuv420p",

            "-an",

            str(output),
        ],
        check=True
    )


# ============================================================
# MUSIC CONFIG
# ============================================================

def load_music_config():

    if not MUSIC_CONFIG_FILE.exists():

        print(
            "MUSIC CONFIG NOT FOUND"
        )

        return {
            "defaultCategory":
                DEFAULT_MUSIC_CATEGORY,

            "categories": {},

            "output": {}
        }

    try:

        with MUSIC_CONFIG_FILE.open(
            "r",
            encoding="utf-8"
        ) as file:

            config = json.load(
                file
            )

        print(
            "MUSIC CONFIG LOADED"
        )

        return config

    except Exception as error:

        print(
            f"MUSIC CONFIG ERROR: {error}"
        )

        return {
            "defaultCategory":
                DEFAULT_MUSIC_CATEGORY,

            "categories": {},

            "output": {}
        }


# ============================================================
# MUSIC CATEGORY DETECTION
# ============================================================

def detect_music_category(
    topic_title,
    script_text
):

    text = (
        f"{topic_title} "
        f"{script_text}"
    ).lower()

    category_keywords = {

        "dark": [
            "dark",
            "death",
            "dead",
            "killer",
            "horror",
            "danger",
            "evil",
            "disappearance",
            "murder",
        ],

        "suspense": [
            "mystery",
            "unknown",
            "secret",
            "missing",
            "strange",
            "unexplained",
            "hidden",
            "mysterious",
        ],

        "science": [
            "science",
            "scientist",
            "research",
            "experiment",
            "laboratory",
            "space",
            "earth",
            "physics",
            "technology",
            "antarctica",
            "ocean",
            "ice",
        ],

        "emotional": [
            "emotional",
            "loss",
            "lost",
            "tragedy",
            "survivor",
            "victim",
            "family",
            "hope",
        ],
    }

    scores = {
       
