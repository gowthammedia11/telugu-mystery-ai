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

    with open(
        TOPICS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        topics = list(
            csv.DictReader(file)
        )

    for topic in topics:

        topic_id = topic["id"].strip()

        script_file = Path(
            f"scripts/{topic_id}.txt"
        )

        audio_file = Path(
            f"audio/{topic_id}.mp3"
        )

        if (
            script_file.exists()
            and audio_file.exists()
        ):
            return topic

    return None


# ============================================================
# SCRIPT
# ============================================================

def read_script(script_file):

    with open(
        script_file,
        "r",
        encoding="utf-8"
    ) as file:

        return file.read()


def clean_script(text):

    lines = []

    ignored = {
        "hook",
        "mystery",
        "background",
        "facts",
        "explanation",
        "discoveries",
        "unknowns",
        "conclusion",
    }

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        line = re.sub(
            r"^#+\s*",
            "",
            line
        )

        line = line.replace(
            "**",
            ""
        )

        line = line.replace(
            "__",
            ""
        )

        line = line.replace(
            "*",
            ""
        )

        lower = (
            line
            .lower()
            .rstrip(":")
            .strip()
        )

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

    api_key = os.environ.get(
        "PEXELS_API_KEY"
    )

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
        "mystery": 0,
        "dark": 0,
        "suspense": 0,
        "science": 0,
        "emotional": 0
    }

    for category, keywords in (
        category_keywords.items()
    ):

        for keyword in keywords:

            if keyword in text:

                scores[category] += 1

    selected_category = max(
        scores,
        key=scores.get
    )

    if scores[selected_category] == 0:

        selected_category = (
            DEFAULT_MUSIC_CATEGORY
        )

    print("=" * 60)
    print("MUSIC CATEGORY ANALYSIS")
    print(f"SCORES: {scores}")
    print(
        f"SELECTED CATEGORY: "
        f"{selected_category}"
    )
    print("=" * 60)

    return selected_category


# ============================================================
# FIND MUSIC FILE
# ============================================================

def find_music_file(
    topic_title,
    script_text
):

    config = load_music_config()

    categories = config.get(
        "categories",
        {}
    )

    category = detect_music_category(
        topic_title,
        script_text
    )

    category_config = categories.get(
        category
    )

    if not category_config:

        category = config.get(
            "defaultCategory",
            DEFAULT_MUSIC_CATEGORY
        )

        category_config = categories.get(
            category
        )

    if not category_config:

        print(
            "NO VALID MUSIC CATEGORY CONFIGURED"
        )

        return None, DEFAULT_MUSIC_VOLUME

    folder = Path(
        category_config.get(
            "folder",
            f"music/tracks/{category}"
        )
    )

    configured_volume = float(
        category_config.get(
            "volume",
            DEFAULT_MUSIC_VOLUME
        )
    )

    music_volume = min(
        max(
            configured_volume,
            0.01
        ),
        0.15
    )

    if not folder.exists():

        print(
            f"MUSIC FOLDER NOT FOUND: "
            f"{folder}"
        )

        return None, music_volume

    candidates = sorted(
        [
            path
            for path in folder.iterdir()
            if (
                path.is_file()
                and path.suffix.lower()
                in {
                    ".mp3",
                    ".wav",
                    ".m4a"
                }
            )
        ]
    )

    if not candidates:

        print(
            f"NO MUSIC FOUND IN: {folder}"
        )

        return None, music_volume

    # --------------------------------------------------------
    # ROTATE MUSIC TRACKS
    # --------------------------------------------------------

    state_file = (
        folder / ".last_used.txt"
    )

    last_used = ""

    if state_file.exists():

        last_used = (
            state_file.read_text(
                encoding="utf-8"
            ).strip()
        )

    selected = candidates[0]

    for candidate in candidates:

        if candidate.name != last_used:

            selected = candidate
            break

    state_file.write_text(
        selected.name,
        encoding="utf-8"
    )

    print("=" * 60)
    print("BACKGROUND MUSIC SELECTED")
    print(
        f"CATEGORY: {category}"
    )
    print(
        f"FILE: {selected}"
    )
    print(
        f"VOLUME: {music_volume}"
    )
    print("=" * 60)

    return selected, music_volume


# ============================================================
# VALIDATE MUSIC
# ============================================================

def validate_music_file(
    music_file
):

    if not music_file:
        return False

    if not music_file.exists():

        print(
            "MUSIC VALIDATION FAILED: "
            "FILE NOT FOUND"
        )

        return False

    try:

        duration = get_audio_duration(
            music_file
        )

        print(
            f"MUSIC DURATION: "
            f"{duration:.2f} seconds"
        )

        if duration < 5:

            print(
                "MUSIC REJECTED: TOO SHORT"
            )

            return False

        return True

    except Exception as error:

        print(
            f"MUSIC VALIDATION ERROR: "
            f"{error}"
        )

        return False


# ============================================================
# MIX VOICE + MUSIC
# ============================================================

def create_final_video(
    visual_video,
    voice_audio,
    music_file,
    music_volume,
    output_video
):

    voice_duration = (
        get_audio_duration(
            voice_audio
        )
    )

    print(
        f"VOICE DURATION: "
        f"{voice_duration:.2f} seconds"
    )

    if music_file and validate_music_file(
        music_file
    ):

        print(
            "CREATING VIDEO WITH "
            "BACKGROUND MUSIC"
        )

        command = [
            "ffmpeg",
            "-y",

            "-i",
            str(visual_video),

            "-i",
            str(voice_audio),

            "-stream_loop",
            "-1",

            "-i",
            str(music_file),

            "-filter_complex",
            (
                f"[2:a]"
                f"volume={music_volume},"
                f"afade=t=in:"
                f"st=0:d=0.8,"
                f"afade=t=out:"
                f"st={max(0, voice_duration - 2):.2f}:"
                f"d=2"
                f"[music];"
                f"[1:a]"
                f"volume=1.0"
                f"[voice];"
                f"[voice][music]"
                f"amix=inputs=2:"
                f"duration=first:"
                f"dropout_transition=2:"
                f"normalize=0"
                f"[audio]"
            ),

            "-map",
            "0:v:0",

            "-map",
            "[audio]",

            "-t",
            str(voice_duration),

            "-c:v",
            "copy",

            "-c:a",
            "aac",

            "-b:a",
            "192k",

            "-shortest",

            "-movflags",
            "+faststart",

            str(output_video),
        ]

    else:

        print(
            "NO VALID MUSIC FOUND"
        )

        print(
            "CREATING VIDEO WITH VOICE ONLY"
        )

        command = [
            "ffmpeg",
            "-y",

            "-i",
            str(visual_video),

            "-i",
            str(voice_audio),

            "-t",
            str(voice_duration),

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

            str(output_video),
        ]

    subprocess.run(
        command,
        check=True
    )


# ============================================================
# MAIN VIDEO GENERATION
# ============================================================

def main():

    topic = get_ready_topic()

    if not topic:

        print(
            "NO READY TOPIC FOUND"
        )

        return

    topic_id = (
        topic["id"].strip()
    )

    topic_title = (
        topic["title"].strip()
    )

    script_file = Path(
        f"scripts/{topic_id}.txt"
    )

    audio_file = Path(
        f"audio/{topic_id}.mp3"
    )

    print("=" * 70)
    print("VIDEO GENERATION STARTED")
    print("=" * 70)

    print(
        f"TOPIC ID: {topic_id}"
    )

    print(
        f"TITLE: {topic_title}"
    )

    print(
        f"SCRIPT: {script_file}"
    )

    print(
        f"AUDIO: {audio_file}"
    )

    print("=" * 70)

    script_text = clean_script(
        read_script(
            script_file
        )
    )

    audio_duration = (
        get_audio_duration(
            audio_file
        )
    )

    print(
        f"AUDIO DURATION: "
        f"{audio_duration:.2f} seconds"
    )

    # ========================================================
    # PREPARE DIRECTORIES
    # ========================================================

    visuals_dir = Path(
        "visuals"
    )

    clips_dir = (
        visuals_dir
        / topic_id
    )

    videos_dir = Path(
        "videos"
    )

    visuals_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    clips_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    videos_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # ========================================================
    # SEARCH PEXELS
    # ========================================================

    queries = create_scene_queries(
        script_text
    )

    print("=" * 70)
    print("PEXELS SEARCH")
    print("=" * 70)

    print(
        f"TOTAL QUERIES: {len(queries)}"
    )

    used_ids = (
        load_used_video_ids()
    )

    selected_videos = []
    selected_ids = set()

    # ========================================================
    # COLLECT VIDEOS
    # ========================================================

    for query in queries:

        if len(selected_videos) >= MAX_CLIPS:
            break

        print(
            f"SEARCHING: {query}"
        )

        try:

            videos = get_pexels_videos(
                query
            )

        except Exception as error:

            print(
                f"SEARCH ERROR: {error}"
            )

            continue

        for video in videos:

            if len(selected_videos) >= MAX_CLIPS:
                break

            video_id = str(
                video.get("id", "")
            )

            if not video_id:
                continue

            if video_id in used_ids:
                continue

            if video_id in selected_ids:
                continue

            source_url = (
                choose_video_file(
                    video
                )
            )

            if not source_url:
                continue

            selected_videos.append(
                {
                    "id": video_id,
                    "url": source_url,
                    "query": query
                }
            )

            selected_ids.add(
                video_id
            )

            print(
                f"SELECTED PEXELS VIDEO: "
                f"{video_id}"
            )

    if not selected_videos:

        raise Exception(
            "NO SUITABLE PEXELS VIDEOS FOUND"
        )

    print("=" * 70)
    print(
        f"TOTAL SELECTED VIDEOS: "
        f"{len(selected_videos)}"
    )
    print("=" * 70)

    # ========================================================
    # CREATE CLIPS
    # ========================================================

    clips = []

    required_duration = (
        audio_duration + 5
    )

    total_duration = 0

    for index, item in enumerate(
        selected_videos,
        start=1
    ):

        if total_duration >= required_duration:
            break

        raw_file = (
            clips_dir
            / f"raw_{index:02d}.mp4"
        )

        clip_file = (
            clips_dir
            / f"clip_{index:02d}.mp4"
        )

        try:

            download_video(
                item["url"],
                raw_file
            )

            if not is_colourful_enough(
                raw_file
            ):

                print(
                    "SKIPPING LOW QUALITY "
                    "VISUAL"
                )

                raw_file.unlink(
                    missing_ok=True
                )

                continue

            create_clip(
                raw_file,
                clip_file,
                SCENE_SECONDS
            )

            clips.append(
                clip_file
            )

            total_duration += (
                SCENE_SECONDS
            )

            print(
                f"CLIP {index} READY"
            )

        except Exception as error:

            print(
                f"CLIP ERROR: {error}"
            )

            raw_file.unlink(
                missing_ok=True
            )

            clip_file.unlink(
                missing_ok=True
            )

    if not clips:

        raise Exception(
            "NO VIDEO CLIPS CREATED"
        )

    if total_duration < audio_duration:

        raise Exception(
            "VIDEO CLIPS ARE SHORTER "
            "THAN VOICE AUDIO"
        )

    # ========================================================
    # SAVE PEXELS HISTORY
    # ========================================================

    save_used_video_ids(
        [
            item["id"]
            for item in selected_videos
        ]
    )

    # ========================================================
    # COMBINE VISUAL CLIPS
    # ========================================================

    visual_video = (
        videos_dir
        / f"{topic_id}_visual.mp4"
    )

    print("=" * 70)
    print("COMBINING VISUAL CLIPS")
    print("=" * 70)

    combine_clips(
        clips,
        visual_video
    )

    # ========================================================
    # BACKGROUND MUSIC
    # ========================================================

    music_file, music_volume = (
        find_music_file(
            topic_title,
            script_text
        )
    )

    # ========================================================
    # FINAL VIDEO
    # ========================================================

    final_video = (
        videos_dir
        / f"{topic_id}.mp4"
    )

    print("=" * 70)
    print("CREATING FINAL VIDEO")
    print("=" * 70)

    create_final_video(
        visual_video,
        audio_file,
        music_file,
        music_volume,
        final_video
    )

    # ========================================================
    # VERIFY FINAL VIDEO
    # ========================================================

    if not final_video.exists():

        raise Exception(
            "FINAL VIDEO WAS NOT CREATED"
        )

    final_size = (
        final_video.stat().st_size
    )

    if final_size < 100000:

        raise Exception(
            "FINAL VIDEO FILE IS TOO SMALL"
        )

    print("=" * 70)
    print("VIDEO CREATED SUCCESSFULLY")
    print("=" * 70)

    print(
        f"FILE: {final_video}"
    )

    print(
        f"SIZE: {final_size} bytes"
    )

    print(
        f"VOICE DURATION: "
        f"{audio_duration:.2f}s"
    )

    print(
        f"VISUAL CLIPS: {len(clips)}"
    )

    print(
        f"MUSIC: "
        f"{music_file if music_file else 'NONE'}"
    )

    print(
        f"MUSIC VOLUME: "
        f"{music_volume}"
    )

    print("=" * 70)

    # ========================================================
    # REMOVE TEMP VISUAL VIDEO
    # ========================================================

    try:

        visual_video.unlink(
            missing_ok=True
        )

    except Exception:
        pass

    print(
        "TEMPORARY VISUAL VIDEO REMOVED"
    )

    print(
        "PIPELINE VIDEO STEP COMPLETED"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
