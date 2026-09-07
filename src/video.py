import csv
import json
import os
import re
import subprocess
from pathlib import Path

import requests


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

MUSIC_CONFIG_FILE = Path(
    "music/music-config.json"
)

DEFAULT_MUSIC_CATEGORY = "mystery"
DEFAULT_MUSIC_VOLUME = 0.055


def get_topic_by_id(topic_id):

    with open(
        TOPICS_FILE,
        "r",
        encoding="utf-8-sig"
    ) as file:
        topics = list(csv.DictReader(file))

    for topic in topics:

        if topic["id"].strip() == topic_id:
            return topic

    raise RuntimeError(
        f"Topic not found: {topic_id}"
    )


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


def create_scene_queries(
    topic_title,
    script_text
):
    """
    Generates topic-specific Pexels queries.
    No fixed Antarctica queries.
    """

    text = (
        f"{topic_title} "
        f"{script_text}"
    ).lower()

    queries = []

    # Topic title itself first.
    queries.append(topic_title)

    # Strong topic combinations.
    keyword_groups = [
        (
            [
                "mariana",
                "trench",
                "deep ocean",
                "deep sea",
                "underwater"
            ],
            [
                "Mariana Trench",
                "deep ocean",
                "deep sea underwater",
                "ocean depth",
                "underwater ocean"
            ]
        ),
        (
            [
                "bermuda",
                "triangle"
            ],
            [
                "Bermuda Triangle",
                "Atlantic Ocean",
                "mysterious ocean",
                "ship ocean",
                "aircraft ocean"
            ]
        ),
        (
            [
                "baltic",
                "anomaly"
            ],
            [
                "Baltic Sea",
                "underwater anomaly",
                "underwater discovery",
                "deep sea object",
                "ocean anomaly"
            ]
        ),
        (
            [
                "death valley",
                "moving rocks",
                "sailing stones"
            ],
            [
                "Death Valley",
                "moving rocks",
                "desert landscape",
                "desert stones",
                "Sailing Stones"
            ]
        ),
        (
            [
                "antarctica",
                "antarctic"
            ],
            [
                "Antarctica",
                "Antarctica glacier",
                "Antarctica ice",
                "Antarctica ocean",
                "polar landscape"
            ]
        ),
        (
            [
                "space",
                "planet",
                "earth",
                "cosmos",
                "universe",
                "black hole"
            ],
            [
                "outer space",
                "Earth from space",
                "galaxy",
                "planet",
                "deep space"
            ]
        ),
        (
            [
                "volcano",
                "volcanic",
                "eruption"
            ],
            [
                "volcano",
                "volcanic eruption",
                "lava",
                "volcano aerial"
            ]
        ),
        (
            [
                "pyramid",
                "egypt"
            ],
            [
                "Egypt pyramids",
                "ancient Egypt",
                "pyramid",
                "Egypt desert"
            ]
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

    # Generic detected concepts.
    generic_map = {
        "ocean": [
            "ocean waves",
            "deep ocean",
            "underwater ocean"
        ],
        "ice": [
            "glacier",
            "blue ice",
            "iceberg"
        ],
        "scientist": [
            "scientist research",
            "scientist laboratory"
        ],
        "satellite": [
            "satellite Earth",
            "Earth satellite"
        ],
        "desert": [
            "desert landscape",
            "desert aerial"
        ],
        "forest": [
            "forest aerial",
            "forest landscape"
        ],
        "mountain": [
            "mountains aerial",
            "mountain landscape"
        ],
        "river": [
            "river aerial",
            "river landscape"
        ],
        "ship": [
            "ship ocean",
            "cargo ship"
        ],
        "aircraft": [
            "airplane sky",
            "aircraft flying"
        ],
    }

    for keyword, group_queries in generic_map.items():

        if keyword in text:
            queries.extend(group_queries)

    # Add broad topic + visual combinations.
    queries.extend([
        f"{topic_title} documentary",
        f"{topic_title} landscape",
        f"{topic_title} aerial",
        f"{topic_title} cinematic",
        f"{topic_title} nature",
    ])

    # Unique while preserving order.
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
        final_queries.append(query)

    return final_queries


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

    response.raise_for_status()

    return response.json().get(
        "videos",
        []
    )


def load_used_video_ids():

    file = Path(
        "visuals/used_pexels_ids.txt"
    )

    if not file.exists():
        return set()

    return {
        line.strip()
        for line in file.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    }


def save_used_video_ids(video_ids):

    file = Path(
        "visuals/used_pexels_ids.txt"
    )

    file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with file.open(
        "a",
        encoding="utf-8"
    ) as handle:

        for video_id in video_ids:
            handle.write(
                f"{video_id}\n"
            )


def choose_video_file(video):

    suitable = []

    for item in video.get(
        "video_files",
        []
    ):

        width = item.get("width")
        height = item.get("height")
        link = item.get("link")

        if not link or not width or not height:
            continue

        if (
            width >= MIN_SOURCE_WIDTH
            and height >= MIN_SOURCE_HEIGHT
        ):
            suitable.append(item)

    if not suitable:
        return None

    suitable.sort(
        key=lambda item:
        item.get("width", 0) *
        item.get("height", 0),
        reverse=True
    )

    return suitable[0]["link"]


def download_video(url, output):

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
        result.stdout +
        result.stderr
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

                saturation_values.append(value)

            except Exception:
                pass

        if "lavfi.signalstats.YAVG=" in line:

            try:
                value = float(
                    line.split(
                        "lavfi.signalstats.YAVG="
                    )[1].split()[0]
                )

                brightness_values.append(value)

            except Exception:
                pass

    if not saturation_values:
        return None, None

    saturation = (
        sum(saturation_values) /
        len(saturation_values)
    )

    brightness = None

    if brightness_values:
        brightness = (
            sum(brightness_values) /
            len(brightness_values)
        )

    return saturation, brightness


def is_colourful_enough(video_file):

    saturation, brightness = (
        get_video_visual_stats(
            video_file
        )
    )

    if saturation is None:
        return True

    normalized_saturation = (
        saturation / 255.0
    )

    normalized_brightness = (
        brightness / 255.0
        if brightness is not None
        else 0
    )

    if (
        normalized_saturation <
        MIN_SATURATION
    ):
        return False

    if (
        brightness is not None
        and normalized_brightness <
        MIN_BRIGHTNESS
    ):
        return False

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


def combine_clips(
    clips,
    output
):

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


def load_music_config():

    if not MUSIC_CONFIG_FILE.exists():

        return {
            "defaultCategory":
                DEFAULT_MUSIC_CATEGORY,
            "categories": {}
        }

    try:
        return json.loads(
            MUSIC_CONFIG_FILE.read_text(
                encoding="utf-8"
            )
        )

    except Exception:
        return {
            "defaultCategory":
                DEFAULT_MUSIC_CATEGORY,
            "categories": {}
        }


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

    return selected


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
        return None, DEFAULT_MUSIC_VOLUME

    folder = Path(
        category_config.get(
            "folder",
            f"music/tracks/{category}"
        )
    )

    volume = float(
        category_config.get(
            "volume",
            DEFAULT_MUSIC_VOLUME
        )
    )

    volume = min(
        max(volume, 0.01),
        0.15
    )

    if not folder.exists():
        return None, volume

    candidates = sorted(
        [
            path
            for path in folder.iterdir()
            if (
                path.is_file()
                and path.suffix.lower()
                in {".mp3", ".wav", ".m4a"}
            )
        ]
    )

    if not candidates:
        return None, volume

    state_file = folder / ".last_used.txt"

    last_used = ""

    if state_file.exists():
        last_used = state_file.read_text(
            encoding="utf-8"
        ).strip()

    selected = candidates[0]

    for candidate in candidates:

        if candidate.name != last_used:
            selected = candidate
            break

    state_file.write_text(
        selected.name,
        encoding="utf-8"
    )

    return selected, volume


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


def create_final_video(
    visual_video,
    voice_audio,
    music_file,
    music_volume,
    output_video
):

    voice_duration = get_audio_duration(
        voice_audio
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
                f"[2:a]volume={music_volume},"
                f"afade=t=in:st=0:d=0.8,"
                f"afade=t=out:"
                f"st={max(0, voice_duration - 2):.2f}:"
                f"d=2[music];"
                f"[1:a]volume=1.0[voice];"
                "[voice][music]"
                "amix=inputs=2:"
                "duration=first:"
                "dropout_transition=2:"
                "normalize=0[audio]"
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


def run(topic_id):

    topic = get_topic_by_id(topic_id)

    topic_title = topic["title"].strip()

    script_file = Path(
        f"scripts/{topic_id}.txt"
    )

    audio_file = Path(
        f"audio/{topic_id}.mp3"
    )

    if not script_file.exists():
        raise RuntimeError(
            f"Script not found: {script_file}"
        )

    if not audio_file.exists():
        raise RuntimeError(
            f"Audio not found: {audio_file}"
        )

    script_text = clean_script(
        read_script(topic_id)
    )

    audio_duration = get_audio_duration(
        audio_file
    )

    visuals_dir = Path("visuals")
    clips_dir = visuals_dir / topic_id
    videos_dir = Path("videos")

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

    final_video = (
        videos_dir /
        f"{topic_id}.mp4"
    )

    # Resume protection
    if (
        final_video.exists()
        and final_video.stat().st_size > 100000
    ):
        print(
            f"VIDEO ALREADY EXISTS: {final_video}"
        )
        return final_video

    queries = create_scene_queries(
        topic_title,
        script_text
    )

    used_ids = load_used_video_ids()

    selected_videos = []
    selected_ids = set()

    for query in queries:

        if len(selected_videos) >= MAX_CLIPS:
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
                f"PEXELS ERROR: {error}"
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

            source_url = choose_video_file(
                video
            )

            if not source_url:
                continue

            selected_videos.append(
                {
                    "id": video_id,
                    "url": source_url
                }
            )

            selected_ids.add(
                video_id
            )

    if not selected_videos:
        raise RuntimeError(
            "NO SUITABLE PEXELS VIDEOS FOUND"
        )

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
        raise RuntimeError(
            "NO VIDEO CLIPS CREATED"
        )

    if total_duration < audio_duration:
        raise RuntimeError(
            "VIDEO CLIPS ARE SHORTER THAN AUDIO"
        )

    save_used_video_ids(
        [
            item["id"]
            for item in selected_videos
        ]
    )

    visual_video = (
        videos_dir /
        f"{topic_id}_visual.mp4"
    )

    combine_clips(
        clips,
        visual_video
    )

    music_file, music_volume = (
        find_music_file(
            topic_title,
            script_text
        )
    )

    create_final_video(
        visual_video,
        audio_file,
        music_file,
        music_volume,
        final_video
    )

    if not final_video.exists():
        raise RuntimeError(
            "FINAL VIDEO WAS NOT CREATED"
        )

    if final_video.stat().st_size < 100000:
        raise RuntimeError(
            "FINAL VIDEO FILE IS TOO SMALL"
        )

    visual_video.unlink(
        missing_ok=True
    )

    print(
        f"VIDEO CREATED SUCCESSFULLY: {final_video}"
    )

    return final_video


if __name__ == "__main__":

    topic_id = os.environ.get(
        "PIPELINE_TOPIC_ID"
    )

    if not topic_id:
        raise SystemExit(
            "PIPELINE_TOPIC_ID is required"
        )

    run(topic_id)
