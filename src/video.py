import csv
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse, unquote

import requests


TOPICS_FILE = "topics/topics.csv"

HEADERS = {
    "User-Agent": "TeluguMysteryAI/1.0 (contact: gowthammed ia11@users.noreply.github.com)",
    "Accept": "image/avif,image/webp,image/apng,image/jpeg,image/png,*/*;q=0.8",
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


def get_wikimedia_images(query, count=10):

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
        "format": "json",
    }

    response = requests.get(
        url,
        params=params,
        headers=HEADERS,
        timeout=60,
    )

    print("WIKIMEDIA API STATUS:", response.status_code)

    response.raise_for_status()

    data = response.json()

    pages = data.get("query", {}).get("pages", {})

    images = []

    for page in pages.values():

        info = page.get("imageinfo", [])

        if not info:
            continue

        image_url = (
            info[0].get("thumburl")
            or info[0].get("url")
        )

        if image_url:
            images.append(image_url)

    return images


def download_image(url, output):

    max_attempts = 5

    for attempt in range(1, max_attempts + 1):

        try:

            print(
                f"DOWNLOAD ATTEMPT {attempt}/{max_attempts}: "
                f"{output.name}"
            )

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=90,
            )

            print(
                f"IMAGE STATUS: {response.status_code}"
            )

            if response.status_code == 200:

                content_type = response.headers.get(
                    "Content-Type",
                    ""
                )

                if (
                    "image" not in content_type.lower()
                    and len(response.content) < 10000
                ):
                    print("INVALID IMAGE RESPONSE")
                    return False

                output.write_bytes(response.content)

                print(
                    f"DOWNLOADED: {output}"
                )

                return True

            if response.status_code == 429:

                retry_after = response.headers.get(
                    "Retry-After"
                )

                if retry_after:

                    try:
                        wait_time = int(retry_after)
                    except ValueError:
                        wait_time = 15

                else:
                    wait_time = 15 * attempt

                print(
                    f"RATE LIMITED. WAITING {wait_time} SECONDS..."
                )

                time.sleep(wait_time)

                continue

            print(
                f"HTTP ERROR {response.status_code}"
            )

        except Exception as error:

            print(
                f"DOWNLOAD ERROR: {error}"
            )

        wait_time = 10 * attempt

        print(
            f"WAITING {wait_time} SECONDS BEFORE RETRY..."
        )

        time.sleep(wait_time)

    return False


topic = get_ready_topic()

if not topic:
    print("NO READY TOPIC")
    exit(0)


topic_id = topic["id"].strip()
title = topic["title"].strip()

audio = Path(
    f"audio/{topic_id}.mp3"
)

videos = Path("videos")
visuals = Path("visuals")

videos.mkdir(exist_ok=True)
visuals.mkdir(exist_ok=True)

print(
    f"CREATING VISUAL VIDEO: {title}"
)


# --------------------------------------------------
# SEARCH IMAGES
# --------------------------------------------------

images = get_wikimedia_images(
    title,
    10
)

print(
    f"FOUND {len(images)} IMAGE RESULTS"
)

if len(images) < 3:

    print(
        "NOT ENOUGH IMAGE RESULTS"
    )

    exit(1)


# --------------------------------------------------
# DOWNLOAD IMAGES
# --------------------------------------------------

downloaded = []

for index, image_url in enumerate(
    images,
    start=1
):

    if len(downloaded) >= 6:
        break

    output = visuals / (
        f"{topic_id}_{len(downloaded) + 1}.jpg"
    )

    success = download_image(
        image_url,
        output
    )

    if success:

        downloaded.append(
            output
        )

        print(
            f"SUCCESSFUL IMAGES: "
            f"{len(downloaded)}/6"
        )

    else:

        print(
            f"SKIPPED IMAGE {index}"
        )

    # IMPORTANT:
    # Do not hit Wikimedia CDN continuously.
    time.sleep(5)


if len(downloaded) < 3:

    print(
        "FAILED: LESS THAN 3 IMAGES DOWNLOADED"
    )

    exit(1)


print(
    f"TOTAL DOWNLOADED IMAGES: "
    f"{len(downloaded)}"
)


# --------------------------------------------------
# AUDIO DURATION
# --------------------------------------------------

probe = subprocess.run(
    [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio),
    ],
    capture_output=True,
    text=True,
    check=True,
)

duration = float(
    probe.stdout.strip()
)

scene_duration = (
    duration / len(downloaded)
)

print(
    f"AUDIO DURATION: "
    f"{duration:.2f} seconds"
)

print(
    f"SCENE DURATION: "
    f"{scene_duration:.2f} seconds"
)


# --------------------------------------------------
# CREATE VIDEO CLIPS
# --------------------------------------------------

clips = []

for index, image in enumerate(
    downloaded,
    start=1
):

    clip = visuals / (
        f"{topic_id}_clip_{index}.mp4"
    )

    print(
        f"CREATING CLIP {index}"
    )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(image),
            "-t",
            str(scene_duration),
            "-vf",
            (
                "scale=1920:1080:"
                "force_original_aspect_ratio=increase,"
                "crop=1920:1080"
            ),
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            str(clip),
        ],
        check=True,
    )

    clips.append(clip)


# --------------------------------------------------
# CONCAT
# --------------------------------------------------

concat_file = visuals / (
    f"{topic_id}_concat.txt"
)

with open(
    concat_file,
    "w",
    encoding="utf-8"
) as f:

    for clip in clips:

        f.write(
            f"file '{clip.resolve()}'\n"
        )


silent_video = visuals / (
    f"{topic_id}_silent.mp4"
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
        str(silent_video),
    ],
    check=True,
)


# --------------------------------------------------
# ADD TELUGU AUDIO
# --------------------------------------------------

output = videos / (
    f"{topic_id}.mp4"
)


subprocess.run(
    [
        "ffmpeg",
        "-y",
        "-i",
        str(silent_video),
        "-i",
        str(audio),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(output),
    ],
    check=True,
)


print(
    f"VIDEO CREATED SUCCESSFULLY: "
    f"{output}"
)
