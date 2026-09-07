import csv
import json
import math
import os
import re
import subprocess
from pathlib import Path

import requests


# ============================================================
# CONFIG
# ============================================================

TOPICS_FILE = Path("topics/topics.csv")

PEXELS_API_URL = (
    "https://api.pexels.com/videos/search"
)

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080

# Each accepted clip contributes this much visual duration.
SCENE_SECONDS = 15

# Safety limits.
MIN_CLIPS = 8
MAX_CLIPS = 80

MIN_SOURCE_WIDTH = 1920
MIN_SOURCE_HEIGHT = 1080

MIN_SATURATION = 0.08
MIN_BRIGHTNESS = 0.12


# ============================================================
# BACKGROUND MUSIC
# ============================================================

MUSIC_CONFIG_FILE = Path(
    "music/music-config.json"
)

DEFAULT_MUSIC_CATEGORY = "mystery"
DEFAULT_MUSIC_VOLUME = 0.055


# ============================================================
# TOPIC
# ============================================================

def get_topic_by_id(topic_id):

    topic_id = str(topic_id).strip()

    if not TOPICS_FILE.exists():
        raise RuntimeError(
            f"Topics file not found: {TOPICS_FILE}"
        )

    with TOPICS_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        topics = list(
            csv.DictReader(file)
        )

    for topic in topics:

        if topic["id"].strip() == topic_id:
            return topic

    raise RuntimeError(
        f"Topic not found: {topic_id}"
    )


# ============================================================
# SCRIPT
# ============================================================

def read_script(topic_id):

    script_file = Path(
        f"scripts/{topic_id}.txt"
    )

    if not script_file.exists():
        raise RuntimeError(
            f"Script not found: {script_file}"
        )

    return script_file.read_text(
        encoding="utf-8"
    )


def clean_script(text):

    if not text:
        return ""

    lines = []

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

        lines.append(line)

    return "\n".join(lines)


# ============================================================
# PEXELS QUERY GENERATION
# ============================================================

def create_scene_queries(
    topic_title,
    script_text
):

    text = (
        f"{topic_title} "
        f"{script_text}"
    ).lower()

    queries = []

    # --------------------------------------------------------
    # MAIN TOPIC
    # --------------------------------------------------------

    queries.extend([
        topic_title,
    ])

    # --------------------------------------------------------
    # TOPIC-SPECIFIC GROUPS
    # --------------------------------------------------------

    keyword_groups = [

        (
            [
                "mariana",
                "trench",
                "deep ocean",
                "deep sea",
            ],
            [
                "Mariana Trench",
                "Mariana Trench ocean",
                "deep ocean",
                "deep sea underwater",
                "ocean depth",
                "underwater trench",
                "deep sea expedition",
                "submarine deep ocean",
            ],
        ),

        (
            [
                "bermuda",
                "triangle",
            ],
            [
                "Bermuda Triangle",
                "Bermuda ocean",
                "Atlantic Ocean",
                "mysterious ocean",
                "ship ocean",
                "aircraft ocean",
                "ocean storm",
                "deep Atlantic",
            ],
        ),

        (
            [
                "baltic",
                "anomaly",
            ],
            [
                "Baltic Sea",
                "Baltic Sea underwater",
                "underwater anomaly",
                "underwater object",
                "deep sea object",
                "ocean anomaly",
                "underwater exploration",
            ],
        ),

        (
            [
                "antarctica",
                "antarctic",
            ],
            [
                "Antarctica",
                "Antarctica glacier",
                "Antarctica ice",
                "Antarctica ocean",
                "polar landscape",
                "iceberg ocean",
                "Antarctic research",
            ],
        ),

        (
            [
                "death valley",
                "moving rocks",
                "sailing stones",
            ],
            [
                "Death Valley",
                "Death Valley desert",
                "moving rocks",
                "sailing stones",
                "desert landscape",
                "desert stones",
            ],
        ),

        (
            [
                "space",
                "planet",
                "earth",
                "universe",
                "cosmos",
                "black hole",
            ],
            [
                "outer space",
                "Earth from space",
                "planet Earth",
                "galaxy",
                "deep space",
                "space telescope",
                "stars universe",
            ],
        ),

        (
            [
                "volcano",
                "volcanic",
                "eruption",
            ],
            [
                "volcano",
                "volcanic eruption",
                "lava",
                "volcano aerial",
                "volcanic landscape",
            ],
        ),

        (
            [
                "pyramid",
                "egypt",
            ],
            [
                "Egypt pyramids",
                "ancient Egypt",
                "pyramid desert",
                "Egypt ancient ruins",
                "Giza pyramids",
            ],
        ),
    ]

    for keywords, group_queries in keyword_groups:

        if any(
            keyword in text
            for keyword in keywords
        ):

            queries.extend(
                group_queries
            )

    # --------------------------------------------------------
    # GENERIC VISUAL CONCEPTS
    # --------------------------------------------------------

    generic_map = {

        "ocean": [
            "ocean waves",
            "deep ocean",
            "underwater ocean",
            "ocean aerial",
        ],

        "ice": [
            "glacier",
            "blue ice",
            "iceberg",
            "ice ocean",
        ],

        "scientist": [
            "scientist research",
            "scientist laboratory",
            "scientific research",
        ],

        "satellite": [
            "satellite Earth",
            "Earth satellite",
            "space satellite",
        ],

        "desert": [
            "desert landscape",
            "desert aerial",
            "desert cinematic",
        ],

        "forest": [
            "forest aerial",
            "forest landscape",
            "dense forest",
        ],

        "mountain": [
            "mountains aerial",
            "mountain landscape",
            "mountain cinematic",
        ],

        "river": [
            "river aerial",
            "river landscape",
            "river water",
        ],

        "ship": [
            "ship ocean",
            "cargo ship",
            "ship at sea",
        ],

        "aircraft": [
            "airplane sky",
            "aircraft flying",
            "airplane ocean",
        ],

        "submarine": [
            "submarine underwater",
            "submarine ocean",
            "deep sea submarine",
        ],

        "underwater": [
            "underwater exploration",
            "deep underwater",
            "underwater ocean",
        ],
    }

    for keyword, group_queries in generic_map.items():

        if keyword in text:

            queries.extend(
                group_queries
            )

    # --------------------------------------------------------
    # TOPIC VARIATIONS
    # --------------------------------------------------------

    queries.extend([
        f"{topic_title} documentary",
        f"{topic_title} cinematic",
        f"{topic_title} aerial",
        f"{topic_title} nature",
        f"{topic_title} exploration",
        f"{topic_title} science",
    ])

    # --------------------------------------------------------
    # UNIQUE QUERIES
    # --------------------------------------------------------

    final_queries = []

    seen = set()

    for query in queries:

        query = query.strip()

        if not query:
            continue

        key = query.lower()

        if key in seen:
            continue

        seen.add(key)

        final_queries.append(
            query
        )

    return final_queries


# ============================================================
# PEXELS SEARCH
# ============================================================

def get_pexels_videos(query):

    api_key = os.environ.get(
        "PEXELS_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
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
        f"PEXELS API STATUS: "
        f"{response.status_code}"
    )

    response.raise_for_status()

    return response.json().get(
        "videos",
        []
    )


# ============================================================
# PEXELS USED HISTORY
# ============================================================

def get_history_file():

    return Path(
        "visuals/used_pexels_ids.txt"
    )


def load_used_video_ids():

    history_file = get_history_file()

    if not history_file.exists():
        return set()

    return {
        line.strip()
        for line in history_file.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    }


def save_used_video_ids(
    video_ids
):

    if not video_ids:
        return

    history_file = get_history_file()

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
# CHOOSE BEST SOURCE
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
        (
            item.get("width", 0)
            *
            item.get("height", 0)
        ),
        reverse=True
    )

    return suitable[0]["link"]


# ============================================================
# DOWNLOAD
# ============================================================

def download_video(
    url,
    output
):

    print(
        f"DOWNLOADING: {output.name}"
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

    with output.open(
        "wb"
    ) as file:

        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):

            if chunk:
                file.write(chunk)

    if not output.exists():
        raise RuntimeError(
            f"Download failed: {output}"
        )

    return output


# ============================================================
# AUDIO DURATION
# ============================================================

def get_audio_duration(
    audio_file
):

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

    output = result.stdout.strip()

    if not output:
        raise RuntimeError(
            "Could not determine audio duration"
        )

    return float(output)


# ============================================================
# VIDEO VISUAL STATS
# ============================================================

def get_video_visual_stats(
    video_file
):

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "info",
        "-ss",
        "1",
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
        result.stdout +
        result.stderr
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
        /
        len(saturation_values)
    )

    brightness = None

    if brightness_values:

        brightness = (
            sum(brightness_values)
            /
            len(brightness_values)
        )

    return saturation, brightness


# ============================================================
# VISUAL QUALITY
# ============================================================

def is_colourful_enough(
    video_file
):

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
        "ACCEPTED: GOOD VISUAL"
    )

    return True


# ============================================================
# CREATE CLIP
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
            "eq="
            "saturation=1.08:"
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

    if not clips:
        raise RuntimeError(
            "No clips available for combination"
        )

    concat_file = (
        output.parent /
        "concat.txt"
    )

    with concat_file.open(
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

        return {
            "defaultCategory":
                DEFAULT_MUSIC_CATEGORY,
            "categories": {},
        }

    try:

        return json.loads(
            MUSIC_CONFIG_FILE.read_text(
                encoding="utf-8"
            )
        )

    except Exception as error:

        print(
            f"MUSIC CONFIG ERROR: {error}"
        )

        return {
            "defaultCategory":
                DEFAULT_MUSIC_CATEGORY,
            "categories": {},
        }


# ============================================================
# MUSIC CATEGORY
# ============================================================

def detect_music_category(
    topic_title,
    script_text
):

    text = (
        f"{topic_title} "
        f"{script_text}"
    ).lower()

    scores = {
        "mystery": 0,
        "dark": 0,
        "suspense": 0,
        "science": 0,
        "emotional": 0,
    }

    groups = {

        "dark": [
            "dark",
            "death",
            "dead",
            "killer",
            "horror",
            "danger",
            "murder",
        ],

        "suspense": [
            "mystery",
            "unknown",
            "secret",
            "missing",
            "unexplained",
            "hidden",
            "strange",
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
            "ocean",
            "ice",
        ],

        "emotional": [
            "loss",
            "lost",
            "tragedy",
            "survivor",
            "victim",
            "family",
            "hope",
        ],
    }

    for category, keywords in groups.items():

        for keyword in keywords:

            if keyword in text:
                scores[category] += 1

    selected = max(
        scores,
        key=scores.get
    )

    if scores[selected] == 0:

        selected = DEFAULT_MUSIC_CATEGORY

    print("=" * 60)
    print("MUSIC CATEGORY ANALYSIS")
    print(f"SCORES: {scores}")
    print(
        f"SELECTED CATEGORY: {selected}"
    )
    print("=" * 60)

    return selected


# ============================================================
# FIND MUSIC
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

    category_config = (
        categories.get(category)
    )

    if not category_config:

        category = config.get(
            "defaultCategory",
            DEFAULT_MUSIC_CATEGORY
        )

        category_config = (
            categories.get(category)
        )

    if not category_config:

        return (
            None,
            DEFAULT_MUSIC_VOLUME
        )

    folder = Path(
        category_config.get(
            "folder",
            f"music/tracks/{category}"
        )
    )

    try:

        volume = float(
            category_config.get(
                "volume",
                DEFAULT_MUSIC_VOLUME
            )
        )

    except Exception:

        volume = DEFAULT_MUSIC_VOLUME

    volume = min(
        max(volume, 0.01),
        0.15
    )

    if not folder.exists():

        print(
            f"MUSIC FOLDER NOT FOUND: {folder}"
        )

        return None, volume

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

        return None, volume

    state_file = (
        folder /
        ".last_used.txt"
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
    print(f"CATEGORY: {category}")
    print(f"FILE: {selected}")
    print(f"VOLUME: {volume}")
    print("=" * 60)

    return selected, volume


# ============================================================
# MUSIC VALIDATION
# ============================================================

def validate_music_file(
    music_file
):

    if not music_file:
        return False

    if not music_file.exists():
        return False

    try:

        duration = get_audio_duration(
            music_file
        )

        return duration >= 5

    except Exception:

        return False


# ============================================================
# FINAL VIDEO
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

    if (
        music_file
        and validate_music_file(music_file)
    ):

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

def run(topic_id):

    topic_id = str(
        topic_id
    ).strip()

    topic = get_topic_by_id(
        topic_id
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

    videos_dir = Path(
        "videos"
    )

    visuals_dir = Path(
        "visuals"
    )

    clips_dir = (
        visuals_dir /
        topic_id
    )

    videos_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    clips_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    if not script_file.exists():
        raise RuntimeError(
            f"Script not found: {script_file}"
        )

    if not audio_file.exists():
        raise RuntimeError(
            f"Audio not found: {audio_file}"
        )

    final_video = (
        videos_dir /
        f"{topic_id}.mp4"
    )

    # --------------------------------------------------------
    # EXISTING FINAL VIDEO
    # --------------------------------------------------------

    if (
        final_video.exists()
        and final_video.stat().st_size >= 100000
    ):

        print("=" * 70)
        print(
            f"VALID FINAL VIDEO ALREADY EXISTS: "
            f"{final_video}"
        )
        print("=" * 70)

        return final_video

    # --------------------------------------------------------
    # READ SCRIPT + AUDIO
    # --------------------------------------------------------

    script_text = clean_script(
        read_script(
            topic_id
        )
    )

    audio_duration = (
        get_audio_duration(
            audio_file
        )
    )

    # --------------------------------------------------------
    # DYNAMIC CLIP COUNT
    # --------------------------------------------------------

    required_clips = int(
        math.ceil(
            audio_duration /
            SCENE_SECONDS
        )
    ) + 2

    required_clips = max(
        required_clips,
        MIN_CLIPS
    )

    required_clips = min(
        required_clips,
        MAX_CLIPS
    )

    print("=" * 70)
    print("VIDEO GENERATION")
    print("=" * 70)

    print(
        f"TOPIC ID: {topic_id}"
    )

    print(
        f"TOPIC TITLE: {topic_title}"
    )

    print(
        f"AUDIO DURATION: "
        f"{audio_duration:.2f} seconds"
    )

    print(
        f"CLIP DURATION: "
        f"{SCENE_SECONDS} seconds"
    )

    print(
        f"REQUIRED CLIPS: "
        f"{required_clips}"
    )

    print(
        f"EXPECTED VISUAL DURATION: "
        f"{required_clips * SCENE_SECONDS} seconds"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # SEARCH QUERIES
    # --------------------------------------------------------

    queries = create_scene_queries(
        topic_title,
        script_text
    )

    print("=" * 70)
    print("PEXELS SEARCH")
    print("=" * 70)

    print(
        f"TOTAL QUERIES: {len(queries)}"
    )

    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    used_ids = load_used_video_ids()

    selected_videos = []
    selected_ids = set()

    # --------------------------------------------------------
    # COLLECT ENOUGH VIDEOS
    # --------------------------------------------------------

    for query in queries:

        if (
            len(selected_videos)
            >= required_clips
        ):
            break

        print(
            f"PEXELS SEARCH: {query}"
        )

        try:

            videos = get_pexels_videos(
                query
            )

        except Exception as error:

            print(
                f"PEXELS SEARCH ERROR: {error}"
            )

            continue

        for video in videos:

            if (
                len(selected_videos)
                >= required_clips
            ):
                break

            video_id = str(
                video.get(
                    "id",
                    ""
                )
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
                    "query": query,
                }
            )

            selected_ids.add(
                video_id
            )

            print(
                f"SELECTED PEXELS VIDEO: "
                f"{video_id}"
            )

    print("=" * 70)
    print(
        f"TOTAL SELECTED VIDEOS: "
        f"{len(selected_videos)}"
    )
    print("=" * 70)

    if len(selected_videos) < MIN_CLIPS:

        raise RuntimeError(
            "NOT ENOUGH UNIQUE PEXELS VIDEOS FOUND"
        )

    # --------------------------------------------------------
    # CREATE CLIPS
    # --------------------------------------------------------

    clips = []
    accepted_video_ids = []

    total_duration = 0.0

    for index, item in enumerate(
        selected_videos,
        start=1
    ):

        if (
            total_duration
            >= audio_duration + 5
        ):
            break

        raw_file = (
            clips_dir /
            f"raw_{index:02d}.mp4"
        )

        clip_file = (
            clips_dir /
            f"clip_{index:02d}.mp4"
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
                    f"REJECTED VISUAL: "
                    f"{item['id']}"
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

            if not clip_file.exists():

                raise RuntimeError(
                    "Clip was not created"
                )

            clips.append(
                clip_file
            )

            accepted_video_ids.append(
                item["id"]
            )

            total_duration += (
                SCENE_SECONDS
            )

            print("=" * 60)
            print(
                f"CLIP {len(clips)} READY"
            )

            print(
                f"TOTAL VISUAL DURATION: "
                f"{total_duration:.2f}s"
            )

            print("=" * 60)

            raw_file.unlink(
                missing_ok=True
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

    # --------------------------------------------------------
    # FINAL DURATION CHECK
    # --------------------------------------------------------

    if not clips:

        raise RuntimeError(
            "NO VIDEO CLIPS CREATED"
        )

    if total_duration < audio_duration:

        raise RuntimeError(
            "VIDEO CLIPS ARE SHORTER THAN AUDIO"
        )

    print("=" * 70)
    print("VISUAL DURATION CHECK PASSED")
    print(
        f"VISUAL: {total_duration:.2f}s"
    )
    print(
        f"AUDIO: {audio_duration:.2f}s"
    )
    print("=" * 70)

    # --------------------------------------------------------
    # SAVE ONLY ACTUALLY USED PEXELS IDs
    # --------------------------------------------------------

    save_used_video_ids(
        accepted_video_ids
    )

    # --------------------------------------------------------
    # COMBINE
    # --------------------------------------------------------

    visual_video = (
        videos_dir /
        f"{topic_id}_visual.mp4"
    )

    print("=" * 70)
    print("COMBINING VISUAL CLIPS")
    print("=" * 70)

    combine_clips(
        clips,
        visual_video
    )

    # --------------------------------------------------------
    # MUSIC
    # --------------------------------------------------------

    music_file, music_volume = (
        find_music_file(
            topic_title,
            script_text
        )
    )

    # --------------------------------------------------------
    # CREATE FINAL
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # VERIFY
    # --------------------------------------------------------

    if not final_video.exists():

        raise RuntimeError(
            "FINAL VIDEO WAS NOT CREATED"
        )

    final_size = (
        final_video.stat().st_size
    )

    if final_size < 100000:

        raise RuntimeError(
            "FINAL VIDEO FILE IS TOO SMALL"
        )

    # --------------------------------------------------------
    # REMOVE TEMP VISUAL VIDEO
    # --------------------------------------------------------

    visual_video.unlink(
        missing_ok=True
    )

    print("=" * 70)
    print("VIDEO CREATED SUCCESSFULLY")
    print("=" * 70)

    print(
        f"FILE: {final_video}"
    )

    print(
        f"SIZE: "
        f"{final_size} bytes"
    )

    print(
        f"AUDIO DURATION: "
        f"{audio_duration:.2f}s"
    )

    print(
        f"VISUAL DURATION: "
        f"{total_duration:.2f}s"
    )

    print(
        f"CLIPS USED: "
        f"{len(clips)}"
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

    return final_video


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    topic_id = os.environ.get(
        "PIPELINE_TOPIC_ID"
    )

    if not topic_id:

        raise SystemExit(
            "PIPELINE_TOPIC_ID is required"
        )

    run(topic_id)
