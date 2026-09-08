import os
import re
import math
import random
import shutil
import subprocess
from pathlib import Path

import requests


# ============================================================
# CONFIG
# ============================================================

PEXELS_API_URL = "https://api.pexels.com/videos/search"

WIDTH = 1920
HEIGHT = 1080
FPS = 30

SCENE_SECONDS = 15
MIN_CLIPS = 8
MAX_CLIPS = 80

VISUAL_SAFETY_SECONDS = 2.0

MIN_SOURCE_WIDTH = 1920
MIN_SOURCE_HEIGHT = 1080

PEXELS_HISTORY = Path(
    "visuals/used_pexels_ids.txt"
)


# ============================================================
# HELPERS
# ============================================================

def run_command(command):

    print(
        "RUNNING:",
        " ".join(str(x) for x in command)
    )

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:

        print(result.stderr[-4000:])

        raise RuntimeError(
            f"Command failed: {result.returncode}"
        )

    return result


def get_media_duration(file_path):

    result = run_command([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(file_path)
    ])

    try:

        duration = float(
            result.stdout.strip()
        )

    except ValueError:

        raise RuntimeError(
            f"Could not read duration: {file_path}"
        )

    return duration


def load_history():

    if not PEXELS_HISTORY.exists():
        return set()

    ids = set()

    for line in PEXELS_HISTORY.read_text(
        encoding="utf-8"
    ).splitlines():

        value = line.strip()

        if value:
            ids.add(value)

    return ids


def save_history(video_id):

    PEXELS_HISTORY.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with PEXELS_HISTORY.open(
        "a",
        encoding="utf-8"
    ) as file:

        file.write(
            f"{video_id}\n"
        )


# ============================================================
# SEARCH QUERIES
# ============================================================

def build_queries(title, script):

    text = (
        f"{title} {script}"
    ).lower()

    queries = []

    groups = [

        (
            "mariana",
            [
                "Mariana Trench ocean",
                "deep ocean underwater",
                "deep sea exploration",
                "ocean depth",
                "deep sea submarine",
            ]
        ),

        (
            "bermuda",
            [
                "Bermuda Triangle ocean",
                "Atlantic ocean storm",
                "ship ocean aerial",
                "aircraft ocean",
                "deep ocean",
            ]
        ),

        (
            "baltic",
            [
                "Baltic Sea aerial",
                "underwater ocean",
                "underwater exploration",
                "sea anomaly",
            ]
        ),

        (
            "antarctica",
            [
                "Antarctica ice",
                "Antarctica glacier",
                "Antarctica aerial",
                "ice shelf ocean",
                "polar ocean",
            ]
        ),

        (
            "space",
            [
                "deep space",
                "galaxy stars",
                "planet space",
                "Earth from space",
                "astronaut space",
            ]
        ),

        (
            "volcano",
            [
                "volcano eruption",
                "lava volcano",
                "volcanic mountain",
                "smoke volcano",
            ]
        ),

        (
            "pyramid",
            [
                "Egypt pyramids",
                "ancient Egypt",
                "pyramid aerial",
                "ancient ruins",
            ]
        ),
    ]

    for keyword, group in groups:

        if keyword in text:

            queries.extend(group)

    generic = [
        "mystery documentary",
        "scientific research",
        "ocean aerial",
        "nature documentary",
        "science laboratory",
        "satellite Earth",
        "mountains aerial",
        "underwater exploration",
        "dramatic landscape",
        "historical ruins",
    ]

    queries.extend(generic)

    # Remove duplicates.
    result = []
    seen = set()

    for query in queries:

        key = query.lower()

        if key not in seen:

            seen.add(key)
            result.append(query)

    return result


# ============================================================
# PEXELS SEARCH
# ============================================================

def search_pexels(
    query,
    api_key,
    per_page=80
):

    response = requests.get(
        PEXELS_API_URL,
        headers={
            "Authorization": api_key
        },
        params={
            "query": query,
            "per_page": per_page,
            "orientation": "landscape"
        },
        timeout=60
    )

    if response.status_code != 200:

        print(
            f"Pexels error {response.status_code}: "
            f"{response.text[:500]}"
        )

        return []

    data = response.json()

    return data.get(
        "videos",
        []
    )


# ============================================================
# CHOOSE VIDEO
# ============================================================

def choose_video_file(video):

    files = video.get(
        "video_files",
        []
    )

    candidates = []

    for item in files:

        width = item.get(
            "width",
            0
        )

        height = item.get(
            "height",
            0
        )

        link = item.get(
            "link"
        )

        if not link:
            continue

        if (
            width >= MIN_SOURCE_WIDTH
            and height >= MIN_SOURCE_HEIGHT
        ):

            candidates.append(
                item
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            item.get("width", 0)
            * item.get("height", 0)
        ),
        reverse=True
    )

    return candidates[0]


# ============================================================
# DOWNLOAD
# ============================================================

def download_video(
    url,
    output_file
):

    response = requests.get(
        url,
        stream=True,
        timeout=120
    )

    if response.status_code != 200:

        raise RuntimeError(
            f"Download failed: {response.status_code}"
        )

    with open(
        output_file,
        "wb"
    ) as file:

        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):

            if chunk:
                file.write(chunk)


# ============================================================
# CREATE CLIP
# ============================================================

def create_clip(
    source,
    output_file,
    duration=SCENE_SECONDS
):

    run_command([
        "ffmpeg",
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        str(source),
        "-t",
        str(duration),
        "-vf",
        (
            f"scale={WIDTH}:{HEIGHT}:"
            "force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},"
            f"fps={FPS}"
        ),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        str(output_file)
    ])

    actual_duration = get_media_duration(
        output_file
    )

    return actual_duration


# ============================================================
# CONCAT
# ============================================================

def combine_clips(
    clips,
    output_file,
    concat_file
):

    with concat_file.open(
        "w",
        encoding="utf-8"
    ) as file:

        for clip in clips:

            file.write(
                f"file '{clip.resolve()}'\n"
            )

    run_command([
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        str(output_file)
    ])

    return get_media_duration(
        output_file
    )


# ============================================================
# ENSURE VISUAL LENGTH
# ============================================================

def ensure_visual_long_enough(
    visual_file,
    required_duration,
    temp_dir
):

    current_duration = get_media_duration(
        visual_file
    )

    if current_duration >= required_duration:
        return visual_file

    print(
        f"Visual duration short: "
        f"{current_duration:.2f}s"
    )

    print(
        f"Required: "
        f"{required_duration:.2f}s"
    )

    extended_file = (
        temp_dir /
        "visual_extended.mp4"
    )

    loop_count = math.ceil(
        required_duration /
        max(current_duration, 0.1)
    )

    run_command([
        "ffmpeg",
        "-y",
        "-stream_loop",
        str(loop_count),
        "-i",
        str(visual_file),
        "-t",
        str(required_duration),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        str(extended_file)
    ])

    return extended_file


# ============================================================
# MUSIC
# ============================================================

def find_music():

    music_dir = Path("music")

    if not music_dir.exists():
        return None

    files = []

    for extension in [
        "*.mp3",
        "*.wav",
        "*.m4a"
    ]:

        files.extend(
            music_dir.glob(extension)
        )

    if not files:
        return None

    return random.choice(files)


# ============================================================
# FINAL VIDEO
# ============================================================

def create_final_video(
    visual_file,
    voice_file,
    output_file
):

    voice_duration = get_media_duration(
        voice_file
    )

    music_file = find_music()

    if music_file:

        run_command([
            "ffmpeg",
            "-y",
            "-i",
            str(visual_file),
            "-i",
            str(voice_file),
            "-stream_loop",
            "-1",
            "-i",
            str(music_file),
            "-filter_complex",
            (
                "[2:a]"
                "volume=0.055,"
                f"atrim=0:{voice_duration},"
                "asetpts=N/SR/TB"
                "[music];"
                "[1:a][music]"
                "amix=inputs=2:"
                "duration=first:"
                "dropout_transition=2"
                "[audio]"
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
            "-movflags",
            "+faststart",
            str(output_file)
        ])

    else:

        run_command([
            "ffmpeg",
            "-y",
            "-i",
            str(visual_file),
            "-i",
            str(voice_file),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-t",
            str(voice_duration),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output_file)
        ])

    final_duration = get_media_duration(
        output_file
    )

    print("=" * 70)
    print("FINAL VIDEO DURATION CHECK")
    print(
        f"VOICE: {voice_duration:.2f}s"
    )
    print(
        f"VIDEO: {final_duration:.2f}s"
    )
    print("=" * 70)

    if final_duration + 0.15 < voice_duration:

        raise RuntimeError(
            "FINAL VIDEO IS SHORTER THAN AUDIO"
        )

    return output_file


# ============================================================
# MAIN
# ============================================================

def generate_video(topic_id):

    topic_id = str(topic_id).strip()

    api_key = os.environ.get(
        "PEXELS_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "PEXELS_API_KEY is not set"
        )

    script_file = Path(
        f"scripts/{topic_id}.txt"
    )

    voice_file = Path(
        f"audio/{topic_id}.mp3"
    )

    if not script_file.exists():

        raise RuntimeError(
            f"Script not found: {script_file}"
        )

    if not voice_file.exists():

        raise RuntimeError(
            f"Voice not found: {voice_file}"
        )

    voice_duration = get_media_duration(
        voice_file
    )

    required_visual_duration = (
        voice_duration +
        VISUAL_SAFETY_SECONDS
    )

    required_clips = max(
        MIN_CLIPS,
        math.ceil(
            required_visual_duration /
            SCENE_SECONDS
        ) + 1
    )

    required_clips = min(
        required_clips,
        MAX_CLIPS
    )

    print("=" * 70)
    print("VIDEO GENERATION")
    print(f"TOPIC ID: {topic_id}")
    print(
        f"AUDIO DURATION: "
        f"{voice_duration:.2f}s"
    )
    print(
        f"REQUIRED VISUAL: "
        f"{required_visual_duration:.2f}s"
    )
    print(
        f"TARGET CLIPS: "
        f"{required_clips}"
    )
    print("=" * 70)

    temp_dir = Path(
        f"visuals/temp_{topic_id}"
    )

    temp_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    final_output = Path(
        f"videos/{topic_id}.mp4"
    )

    final_output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    history = load_history()

    queries = build_queries(
        script_file.read_text(
            encoding="utf-8"
        )[:8000],
        script_file.read_text(
            encoding="utf-8"
        )[:8000]
    )

    clips = []
    clip_durations = []
    selected_ids = []

    try:

        # ----------------------------------------------------
        # SEARCH UNIQUE CLIPS
        # ----------------------------------------------------

        for query in queries:

            if (
                sum(clip_durations)
                >= required_visual_duration
            ):
                break

            print("=" * 70)
            print(
                f"PEXELS SEARCH: {query}"
            )
            print("=" * 70)

            videos = search_pexels(
                query,
                api_key
            )

            random.shuffle(videos)

            for video in videos:

                if (
                    sum(clip_durations)
                    >= required_visual_duration
                ):
                    break

                video_id = str(
                    video.get("id", "")
                )

                if not video_id:
                    continue

                if video_id in history:
                    continue

                source_info = choose_video_file(
                    video
                )

                if not source_info:
                    continue

                source_url = source_info.get(
                    "link"
                )

                source_file = (
                    temp_dir /
                    f"source_{video_id}.mp4"
                )

                clip_file = (
                    temp_dir /
                    f"clip_{video_id}.mp4"
                )

                try:

                    print(
                        f"Downloading Pexels ID: "
                        f"{video_id}"
                    )

                    download_video(
                        source_url,
                        source_file
                    )

                    duration = create_clip(
                        source_file,
                        clip_file,
                        SCENE_SECONDS
                    )

                    if duration < 1:

                        continue

                    clips.append(
                        clip_file
                    )

                    clip_durations.append(
                        duration
                    )

                    selected_ids.append(
                        video_id
                    )

                    history.add(
                        video_id
                    )

                    print(
                        f"ACCEPTED CLIP: "
                        f"{duration:.2f}s"
                    )

                except Exception as error:

                    print(
                        f"Skipping video "
                        f"{video_id}: {error}"
                    )

        # ----------------------------------------------------
        # IF UNIQUE CLIPS ARE NOT ENOUGH,
        # REPEAT ACCEPTED CLIPS
        # ----------------------------------------------------

        if not clips:

            raise RuntimeError(
                "No usable Pexels clips found"
            )

        current_duration = sum(
            clip_durations
        )

        print(
            f"UNIQUE VISUAL DURATION: "
            f"{current_duration:.2f}s"
        )

        if current_duration < required_visual_duration:

            original_clips = list(clips)

            index = 0

            while (
                current_duration
                < required_visual_duration
            ):

                clip = original_clips[
                    index % len(original_clips)
                ]

                clips.append(
                    clip
                )

                duration = get_media_duration(
                    clip
                )

                clip_durations.append(
                    duration
                )

                current_duration += duration

                index += 1

            print(
                f"EXTENDED VISUAL DURATION: "
                f"{current_duration:.2f}s"
            )

        # ----------------------------------------------------
        # CONCAT
        # ----------------------------------------------------

        concat_file = (
            temp_dir /
            "concat.txt"
        )

        visual_file = (
            temp_dir /
            "visual.mp4"
        )

        combined_duration = combine_clips(
            clips,
            visual_file,
            concat_file
        )

        print(
            f"COMBINED VISUAL: "
            f"{combined_duration:.2f}s"
        )

        # ----------------------------------------------------
        # ENSURE FINAL VISUAL IS LONG ENOUGH
        # ----------------------------------------------------

        visual_ready = ensure_visual_long_enough(
            visual_file,
            required_visual_duration,
            temp_dir
        )

        # ----------------------------------------------------
        # FINAL MUX
        # ----------------------------------------------------

        create_final_video(
            visual_ready,
            voice_file,
            final_output
        )

        if not final_output.exists():

            raise RuntimeError(
                "Final video was not created"
            )

        if final_output.stat().st_size < 100000:

            raise RuntimeError(
                "Final video file is too small"
            )

        # ----------------------------------------------------
        # SAVE HISTORY ONLY AFTER SUCCESS
        # ----------------------------------------------------

        for video_id in selected_ids:

            save_history(
                video_id
            )

        print("=" * 70)
        print("VIDEO CREATED SUCCESSFULLY")
        print(f"FILE: {final_output}")
        print(
            f"DURATION: "
            f"{get_media_duration(final_output):.2f}s"
        )
        print("=" * 70)

        return final_output

    finally:

        if temp_dir.exists():

            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":

    topic_id = os.environ.get(
        "PIPELINE_TOPIC_ID"
    )

    if not topic_id:

        raise SystemExit(
            "PIPELINE_TOPIC_ID is required"
        )

    generate_video(
        topic_id
    )
