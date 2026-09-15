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

MAX_CLIPS = 36
SCENE_SECONDS = 18

MIN_SOURCE_WIDTH = 1920
MIN_SOURCE_HEIGHT = 1080

MIN_SATURATION = 0.08
MIN_BRIGHTNESS = 0.12

MUSIC_DIR = Path("music")
MUSIC_VOLUME = 0.055


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


def read_script(script_file):

    with open(
        script_file,
        "r",
        encoding="utf-8"
    ) as file:

        return file.read()


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


def create_scene_queries(
    script_text,
    title=""
):

    queries = []

    title_lower = title.lower()

    # ========================================================
    # Topic-specific visual queries
    # ========================================================

    if (
        "yonaguni" in title_lower
        or "underwater" in title_lower
    ):

        queries.extend([
            "Yonaguni underwater ruins",
            "underwater stone ruins",
            "underwater archaeology",
            "underwater ancient ruins",
            "diver underwater ruins",
            "underwater rock formations",
            "deep ocean diver",
            "scuba diver underwater",
            "Japanese island ocean",
            "Ryukyu islands ocean",
            "underwater cliffs",
            "underwater stone structures",
        ])

    if "bloop" in title_lower:
        queries.extend([
            "deep ocean underwater",
            "deep sea research",
            "ocean hydrophone",
            "deep sea scientist",
            "underwater microphone",
            "ocean waves aerial",
            "deep blue ocean",
            "research vessel ocean",
        ])

    if "milky sea" in title_lower:
        queries.extend([
            "glowing ocean night",
            "bioluminescent ocean",
            "blue glowing water",
            "night ocean waves",
            "bioluminescence sea",
            "deep ocean night",
        ])

    if "brine" in title_lower:
        queries.extend([
            "deep sea brine pool",
            "underwater deep ocean",
            "deep sea floor",
            "ocean research submarine",
            "deep sea scientist",
            "underwater exploration",
        ])

    if "volcano" in title_lower:
        queries.extend([
            "underwater volcano",
            "volcanic ocean",
            "ocean volcano aerial",
            "lava ocean",
            "volcanic eruption ocean",
        ])

    if "antarctica" in title_lower:
        queries.extend([
            "Antarctica colorful landscape",
            "Antarctica glacier sunlight",
            "Antarctica blue ice",
            "Antarctica blue ocean",
            "Antarctica iceberg",
            "polar landscape sunlight",
        ])

    # ========================================================
    # Generic research visuals
    # ========================================================

    generic_queries = [
        "scientist research",
        "scientist laboratory",
        "scientific research",
        "research vessel ocean",
        "satellite Earth space",
        "Earth from space",
        "ocean aerial sunlight",
        "deep blue ocean",
        "dramatic ocean waves",
        "underwater exploration",
        "scuba diver underwater",
        "ocean documentary",
        "technology research",
        "scientific equipment",
        "map ocean",
        "globe Earth",
    ]

    keywords = [
        "ice",
        "glacier",
        "ocean",
        "underwater",
        "sea",
        "antarctica",
        "antarctic",
        "iceberg",
        "satellite",
        "scientist",
        "research",
        "snow",
        "climate",
        "water",
        "earth",
        "volcano",
        "island",
        "rock",
        "stone",
        "archaeology",
        "diver",
    ]

    lower_script = script_text.lower()

    detected = [
        keyword
        for keyword in keywords
        if keyword in lower_script
    ]

    for keyword in detected:

        if keyword in {
            "ocean",
            "sea"
        }:

            queries.extend([
                "deep blue ocean",
                "ocean waves sunlight",
                "ocean aerial",
            ])

        elif keyword == "underwater":

            queries.extend([
                "underwater exploration",
                "scuba diver underwater",
                "deep sea underwater",
            ])

        elif keyword in {
            "scientist",
            "research"
        }:

            queries.extend([
                "scientist research",
                "scientist laboratory",
                "research vessel",
            ])

        elif keyword == "satellite":

            queries.extend([
                "satellite Earth space",
                "Earth from space",
            ])

        elif keyword == "earth":

            queries.extend([
                "Earth from space",
                "planet Earth",
            ])

        elif keyword in {
            "ice",
            "glacier",
            "antarctica",
            "antarctic",
        }:

            queries.extend([
                "blue ice glacier",
                "glacier sunlight",
                "polar landscape",
            ])

        elif keyword == "volcano":

            queries.extend([
                "volcano eruption",
                "volcanic landscape",
            ])

        elif keyword in {
            "rock",
            "stone",
            "archaeology",
        }:

            queries.extend([
                "ancient stone ruins",
                "archaeological excavation",
                "ancient ruins",
            ])

    queries.extend(
        generic_queries
    )

    final_queries = []

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


def load_used_video_ids():

    history_file = Path(
        "visuals/used_pexels_ids.txt"
    )

    if not history_file.exists():
        return set()

    return {
        line.strip()
        for line
        in history_file.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    }


def save_used_video_ids(
    video_ids
):

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


def download_video(
    url,
    output
):

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

    return float(
        result.stdout.strip()
    )


def get_video_visual_stats(
    video_file
):

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
        text=True
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


def find_music_file():

    MUSIC_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    candidates = sorted(
        [
            p
            for p in MUSIC_DIR.iterdir()
            if (
                p.is_file()
                and p.suffix.lower()
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
            "NO BACKGROUND MUSIC FOUND"
        )

        print(
            "Video will be created with narration only."
        )

        return None

    state_file = (
        MUSIC_DIR
        / ".last_used.txt"
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

    print(
        f"SELECTED BACKGROUND MUSIC: "
        f"{selected}"
    )

    return selected


def get_media_duration(
    media_file
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
            str(media_file),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    return float(
        result.stdout.strip()
    )


def create_exact_clip(
    input_video,
    output_video,
    duration
):

    create_clip(
        input_video,
        output_video,
        duration
    )

    actual = get_media_duration(
        output_video
    )

    if actual + 0.05 < duration:

        raise RuntimeError(
            f"Generated clip is too short: "
            f"{actual:.3f}s < "
            f"{duration:.3f}s"
        )

    return actual


def ensure_visual_duration(
    visual_file,
    required_duration
):

    actual = get_media_duration(
        visual_file
    )

    if actual + 0.10 >= required_duration:
        return actual

    extended = visual_file.with_name(
        visual_file.stem
        + "_extended.mp4"
    )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(visual_file),
            "-t",
            f"{required_duration:.3f}",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(extended),
        ],
        check=True
    )

    extended.replace(
        visual_file
    )

    return get_media_duration(
        visual_file
    )


def add_narration_and_music_exact(
    video,
    narration,
    output,
    narration_duration
):

    music = find_music_file()

    if music is None:

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-i",
            str(narration),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-t",
            f"{narration_duration:.3f}",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output),
        ]

    else:

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-i",
            str(narration),
            "-stream_loop",
            "-1",
            "-i",
            str(music),
            "-filter_complex",
            (
                "[1:a]"
                "aresample=48000,"
                "aformat="
                "sample_fmts=fltp:"
                "sample_rates=48000:"
                "channel_layouts=stereo,"
                "volume=1.0[narr];"

                "[2:a]"
                "aresample=48000,"
                "aformat="
                "sample_fmts=fltp:"
                "sample_rates=48000:"
                "channel_layouts=stereo,"
                f"volume={MUSIC_VOLUME}[music];"

                "[narr][music]"
                "amix="
                "inputs=2:"
                "duration=first:"
                "dropout_transition=2:"
                "normalize=0[mix]"
            ),
            "-map",
            "0:v:0",
            "-map",
            "[mix]",
            "-t",
            f"{narration_duration:.3f}",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output),
        ]

    subprocess.run(
        command,
        check=True
    )


def run(topic_id=None):

    if topic_id:

        topic = None

        with open(
            TOPICS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            topics = list(
                csv.DictReader(file)
            )

        for item in topics:

            if (
                item.get(
                    "id",
                    ""
                ).strip()
                == str(topic_id).strip()
            ):

                topic = item
                break

        if not topic:

            raise RuntimeError(
                f"Topic {topic_id} not found"
            )

    else:

        topic = get_ready_topic()

    if not topic:

        print(
            "NO SCRIPT + AUDIO READY"
        )

        return

    topic_id = topic["id"].strip()
    title = topic["title"].strip()

    script_file = Path(
        f"scripts/{topic_id}.txt"
    )

    audio_file = Path(
        f"audio/{topic_id}.mp3"
    )

    visuals_dir = Path("visuals")
    downloads_dir = (
        visuals_dir / "downloads"
    )
    clips_dir = (
        visuals_dir / "clips"
    )
    videos_dir = Path("videos")

    visuals_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    downloads_dir.mkdir(
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

    script_text = clean_script(
        read_script(script_file)
    )

    audio_duration = get_audio_duration(
        audio_file
    )

    print("=" * 70)
    print("CREATING ROBUST HIGH QUALITY VIDEO")
    print("=" * 70)
    print(f"TOPIC: {title}")
    print(
        f"AUDIO DURATION: "
        f"{audio_duration:.2f}s"
    )

    # ========================================================
    # 7–8 MINUTE PROTECTION
    # ========================================================

    if audio_duration < 390:

        raise RuntimeError(
            f"Long narration is shorter than 6.5 minutes: "
            f"{audio_duration:.2f}s"
        )

    if audio_duration > 510:

        raise RuntimeError(
            f"Long narration is longer than 8.5 minutes: "
            f"{audio_duration:.2f}s"
        )

    target_duration = (
        audio_duration + 2.0
    )

    scene_duration = 18.0

    required_clips = (
        int(
            target_duration
            / scene_duration
        )
        + 1
    )

    required_clips = min(
        required_clips,
        MAX_CLIPS
    )

    print(
        f"REQUIRED CLIPS: "
        f"{required_clips}"
    )

    search_queries = (
        create_scene_queries(
            script_text,
            title
        )
    )

    used_video_ids = (
        load_used_video_ids()
    )

    run_video_ids = set()
    videos = []

    for query in search_queries:

        if len(videos) >= MAX_CLIPS * 5:
            break

        print(
            f"PEXELS SEARCH: {query}"
        )

        try:

            results = get_pexels_videos(
                query
            )

            for result in results:

                video_id = result.get(
                    "id"
                )

                if not video_id:
                    continue

                video_id = str(
                    video_id
                )

                if (
                    video_id
                    in used_video_ids
                    or video_id
                    in run_video_ids
                ):
                    continue

                videos.append(
                    result
                )

                run_video_ids.add(
                    video_id
                )

                if (
                    len(videos)
                    >= MAX_CLIPS * 5
                ):
                    break

        except Exception as error:

            print(
                f"Search failed: {error}"
            )

        time.sleep(0.5)

    if len(videos) < 3:

        raise RuntimeError(
            "NOT ENOUGH NEW HIGH QUALITY VIDEOS FOUND"
        )

    accepted = []
    accepted_ids = []

    for index, video in enumerate(
        videos,
        start=1
    ):

        if (
            len(accepted)
            >= required_clips
        ):
            break

        video_id = str(
            video.get("id")
        )

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

            if not is_colourful_enough(
                output_file
            ):

                output_file.unlink(
                    missing_ok=True
                )

                continue

            accepted.append(
                output_file
            )

            accepted_ids.append(
                video_id
            )

            print(
                f"ACCEPTED CLIPS: "
                f"{len(accepted)}/"
                f"{required_clips}"
            )

        except Exception as error:

            print(
                f"Download failed: {error}"
            )

            output_file.unlink(
                missing_ok=True
            )

        time.sleep(0.5)

    if len(accepted) < 3:

        raise RuntimeError(
            "FAILED: LESS THAN 3 "
            "COLOURFUL HIGH QUALITY CLIPS"
        )

    save_used_video_ids(
        accepted_ids
    )

    # ========================================================
    # PREPARE ENOUGH VISUAL DURATION
    # ========================================================

    prepared = []
    actual_total = 0.0
    index = 0

    while (
        actual_total
        < target_duration
    ):

        if len(prepared) >= MAX_CLIPS:

            raise RuntimeError(
                "MAX_CLIPS reached before "
                "visual duration was sufficient"
            )

        source = accepted[
            index % len(accepted)
        ]

        index += 1

        clip_path = (
            clips_dir
            / f"{topic_id}_clip_"
            f"{len(prepared) + 1}.mp4"
        )

        duration = create_exact_clip(
            source,
            clip_path,
            scene_duration
        )

        prepared.append(
            clip_path
        )

        actual_total += duration

        print(
            f"VISUAL DURATION: "
            f"{actual_total:.2f}/"
            f"{target_duration:.2f}s"
        )

    if (
        actual_total + 0.1
        < audio_duration
    ):

        raise RuntimeError(
            f"VIDEO CLIPS ARE SHORTER "
            f"THAN AUDIO: "
            f"{actual_total:.2f}s < "
            f"{audio_duration:.2f}s"
        )

    silent_video = (
        visuals_dir
        / f"{topic_id}_moving_silent.mp4"
    )

    combine_clips(
        prepared,
        silent_video
    )

    ensure_visual_duration(
        silent_video,
        audio_duration + 0.5
    )

    final_video = (
        videos_dir
        / f"{topic_id}.mp4"
    )

    add_narration_and_music_exact(
        silent_video,
        audio_file,
        final_video,
        audio_duration
    )

    final_duration = (
        get_media_duration(
            final_video
        )
    )

    if (
        final_duration + 0.20
        < audio_duration
    ):

        raise RuntimeError(
            f"FINAL VIDEO IS SHORTER "
            f"THAN NARRATION: "
            f"{final_duration:.2f}s < "
            f"{audio_duration:.2f}s"
        )

    print("=" * 70)
    print("VIDEO CREATED SUCCESSFULLY")
    print("=" * 70)
    print(f"OUTPUT: {final_video}")
    print(
        f"FINAL DURATION: "
        f"{final_duration:.2f}s"
    )
    print("RESOLUTION: 1920x1080")
    print("FORMAT: 16:9")
    print("TELUGU NARRATION: YES")
    print("BACKGROUND MUSIC: VERY LOW")
    print("=" * 70)


if __name__ == "__main__":
    run()
