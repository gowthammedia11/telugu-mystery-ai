import base64
import csv
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


# ============================================================
# CONFIG
# ============================================================

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload"
]

VIDEO_DIR = Path("videos")
METADATA_DIR = Path("metadata")
UPLOAD_DIR = Path("metadata/uploads")

IST = ZoneInfo(
    "Asia/Kolkata"
)

TARGET_HOUR = 17
TARGET_MINUTE = 30


# ============================================================
# TOKEN
# ============================================================

def load_credentials():

    token_b64 = os.environ.get(
        "YOUTUBE_TOKEN_B64"
    )

    if not token_b64:

        raise RuntimeError(
            "YOUTUBE_TOKEN_B64 is not set"
        )

    try:

        token_json = base64.b64decode(
            token_b64
        ).decode(
            "utf-8"
        )

        token_data = json.loads(
            token_json
        )

    except Exception as error:

        raise RuntimeError(
            f"Invalid YOUTUBE_TOKEN_B64: {error}"
        )

    return Credentials.from_authorized_user_info(
        token_data,
        SCOPES
    )


# ============================================================
# METADATA
# ============================================================

def parse_metadata(topic_id):

    metadata_file = (
        METADATA_DIR /
        f"{topic_id}.txt"
    )

    if not metadata_file.exists():

        raise RuntimeError(
            f"Metadata not found: {metadata_file}"
        )

    text = metadata_file.read_text(
        encoding="utf-8"
    )

    title = ""
    description = ""
    tags = []

    sections = {
        "TITLE:": "title",
        "DESCRIPTION:": "description",
        "TAGS:": "tags",
        "HASHTAGS:": "hashtags",
    }

    current = None
    values = {
        "title": [],
        "description": [],
        "tags": [],
        "hashtags": [],
    }

    for line in text.splitlines():

        stripped = line.strip()

        if stripped in sections:

            current = sections[stripped]
            continue

        if current:

            values[current].append(
                line
            )

    title = "\n".join(
        values["title"]
    ).strip()

    description = "\n".join(
        values["description"]
    ).strip()

    tags_text = "\n".join(
        values["tags"]
    ).strip()

    hashtags_text = "\n".join(
        values["hashtags"]
    ).strip()

    if tags_text:

        tags = [
            tag.strip()
            for tag in tags_text.split(",")
            if tag.strip()
        ]

    # Add hashtags to description.
    if hashtags_text:

        description = (
            f"{description}\n\n"
            f"{hashtags_text}"
        )

    if not title:

        raise RuntimeError(
            "YouTube title is empty"
        )

    return {
        "title": title[:100],
        "description": description[:5000],
        "tags": tags[:45]
    }


# ============================================================
# NEXT 5:30 PM IST
# ============================================================

def get_next_publish_time():

    now_ist = datetime.now(
        IST
    )

    target = now_ist.replace(
        hour=TARGET_HOUR,
        minute=TARGET_MINUTE,
        second=0,
        microsecond=0
    )

    # If workflow starts after today's 5:30 PM,
    # schedule for tomorrow.
    if now_ist >= target:

        target += timedelta(
            days=1
        )

    return target


def to_utc_iso(dt):

    utc_dt = dt.astimezone(
        timezone.utc
    )

    return (
        utc_dt.strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    )


# ============================================================
# UPLOAD
# ============================================================

def upload_video(
    topic_id,
    video_file,
    metadata
):

    credentials = load_credentials()

    youtube = build(
        "youtube",
        "v3",
        credentials=credentials
    )

    publish_time_ist = (
        get_next_publish_time()
    )

    publish_at = to_utc_iso(
        publish_time_ist
    )

    body = {
        "snippet": {
            "title": metadata["title"],
            "description": metadata["description"],
            "tags": metadata["tags"],
            "categoryId": "24",
        },

        "status": {
            "privacyStatus": "private",
            "publishAt": publish_at,
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(
        str(video_file),
        mimetype="video/mp4",
        resumable=True,
        chunksize=8 * 1024 * 1024
    )

    print("=" * 70)
    print("YOUTUBE UPLOAD")
    print("=" * 70)
    print(f"FILE: {video_file}")
    print(f"TITLE: {metadata['title']}")
    print(
        f"PUBLISH TIME IST: "
        f"{publish_time_ist.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print(
        f"PUBLISH TIME UTC: "
        f"{publish_at}"
    )
    print("=" * 70)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None

    while response is None:

        status, response = request.next_chunk()

        if status:

            print(
                f"UPLOAD: "
                f"{int(status.progress() * 100)}%"
            )

    video_id = response.get(
        "id"
    )

    if not video_id:

        raise RuntimeError(
            "YouTube upload did not return video ID"
        )

    print("=" * 70)
    print("YOUTUBE VIDEO SCHEDULED")
    print(f"VIDEO ID: {video_id}")
    print(
        f"PUBLISH AT IST: "
        f"{publish_time_ist.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print("=" * 70)

    return {
        "video_id": video_id,
        "publish_at_ist": (
            publish_time_ist.isoformat()
        ),
        "publish_at_utc": publish_at,
        "title": metadata["title"]
    }


# ============================================================
# SAVE UPLOAD RECORD
# ============================================================

def save_upload_record(
    topic_id,
    result
):

    UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    record_file = (
        UPLOAD_DIR /
        f"{topic_id}.json"
    )

    record_file.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return record_file


# ============================================================
# RUN
# ============================================================

def run(topic_id):

    topic_id = str(
        topic_id
    ).strip()

    video_file = (
        VIDEO_DIR /
        f"{topic_id}.mp4"
    )

    if not video_file.exists():

        raise RuntimeError(
            f"Video not found: {video_file}"
        )

    metadata = parse_metadata(
        topic_id
    )

    result = upload_video(
        topic_id,
        video_file,
        metadata
    )

    record_file = save_upload_record(
        topic_id,
        result
    )

    print(
        f"UPLOAD RECORD: {record_file}"
    )

    return result


if __name__ == "__main__":

    topic_id = os.environ.get(
        "PIPELINE_TOPIC_ID"
    )

    if not topic_id:

        raise SystemExit(
            "PIPELINE_TOPIC_ID is required"
        )

    run(topic_id)
