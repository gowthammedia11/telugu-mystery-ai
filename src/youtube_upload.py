import base64
import csv
import json
import os
import re
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


TOPICS_FILE = Path("topics/topics.csv")
METADATA_DIR = Path("metadata")
VIDEOS_DIR = Path("videos")
UPLOAD_RECORDS_DIR = Path("metadata/uploads")

YOUTUBE_TOKEN_ENV = "YOUTUBE_TOKEN_B64"

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload"
]

MAX_TITLE_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 5000
MAX_TAGS = 45
MAX_TOTAL_TAG_LENGTH = 480

YOUTUBE_CATEGORY_ID = "27"
YOUTUBE_PRIVACY_STATUS = "public"


def get_topic_by_id(topic_id):

    if not TOPICS_FILE.exists():
        raise RuntimeError(
            f"Topics file not found: {TOPICS_FILE}"
        )

    with TOPICS_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        topics = list(csv.DictReader(file))

    for topic in topics:

        if topic["id"].strip() == topic_id:
            return topic

    raise RuntimeError(
        f"Topic {topic_id} not found"
    )


def read_metadata(topic_id):

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

    title_match = re.search(
        r"TITLE:\s*\n(.*?)(?=\n\nDESCRIPTION:)",
        text,
        flags=re.DOTALL
    )

    description_match = re.search(
        r"DESCRIPTION:\s*\n(.*?)(?=\n\nTAGS:)",
        text,
        flags=re.DOTALL
    )

    tags_match = re.search(
        r"TAGS:\s*\n(.*?)(?=\n\nHASHTAGS:)",
        text,
        flags=re.DOTALL
    )

    hashtags_match = re.search(
        r"HASHTAGS:\s*\n(.*)$",
        text,
        flags=re.DOTALL
    )

    if not title_match:
        raise RuntimeError(
            "TITLE not found in metadata"
        )

    if not description_match:
        raise RuntimeError(
            "DESCRIPTION not found in metadata"
        )

    title = title_match.group(1).strip()

    description = (
        description_match.group(1).strip()
    )

    tags_text = (
        tags_match.group(1).strip()
        if tags_match
        else ""
    )

    hashtags_text = (
        hashtags_match.group(1).strip()
        if hashtags_match
        else ""
    )

    tags = [
        tag.strip()
        for tag in tags_text.split(",")
        if tag.strip()
    ]

    if hashtags_text:
        description += (
            "\n\n" +
            hashtags_text
        )

    return {
        "title": title,
        "description": description,
        "tags": tags,
    }


def prepare_title(title):

    title = re.sub(
        r"\s+",
        " ",
        title.strip()
    )

    if len(title) > MAX_TITLE_LENGTH:
        title = (
            title[:MAX_TITLE_LENGTH - 3]
            + "..."
        )

    return title


def prepare_description(description):

    description = description.strip()

    description = re.sub(
        r"\n{4,}",
        "\n\n\n",
        description
    )

    if len(description) > MAX_DESCRIPTION_LENGTH:
        description = (
            description[
                :MAX_DESCRIPTION_LENGTH - 3
            ]
            + "..."
        )

    return description


def prepare_tags(tags):

    final_tags = []
    seen = set()
    total_length = 0

    for tag in tags:

        tag = re.sub(
            r"\s+",
            " ",
            tag
        ).strip()

        if not tag:
            continue

        key = tag.lower()

        if key in seen:
            continue

        extra = len(tag) + 1

        if (
            total_length + extra
            > MAX_TOTAL_TAG_LENGTH
        ):
            break

        seen.add(key)
        final_tags.append(tag)
        total_length += extra

        if len(final_tags) >= MAX_TAGS:
            break

    return final_tags


def get_existing_upload_record(topic_id):

    record_file = (
        UPLOAD_RECORDS_DIR /
        f"{topic_id}.json"
    )

    if not record_file.exists():
        return None

    try:

        record = json.loads(
            record_file.read_text(
                encoding="utf-8"
            )
        )

        if record.get("video_id"):
            return record

    except Exception as error:

        print(
            f"WARNING: invalid upload record: {error}"
        )

    return None


def load_youtube_credentials():

    token_b64 = os.environ.get(
        YOUTUBE_TOKEN_ENV
    )

    if not token_b64:
        raise RuntimeError(
            "YOUTUBE_TOKEN_B64 GitHub Secret is missing"
        )

    try:

        token_json = base64.b64decode(
            token_b64.strip()
        ).decode(
            "utf-8"
        )

        token_data = json.loads(
            token_json
        )

    except Exception as error:

        raise RuntimeError(
            f"Invalid YouTube token: {error}"
        )

    required = [
        "client_id",
        "client_secret",
        "refresh_token",
    ]

    missing = [
        field
        for field in required
        if not token_data.get(field)
    ]

    if missing:
        raise RuntimeError(
            "YouTube token missing: "
            + ", ".join(missing)
        )

    return Credentials.from_authorized_user_info(
        token_data,
        YOUTUBE_SCOPES
    )


def get_youtube_client():

    credentials = (
        load_youtube_credentials()
    )

    return build(
        "youtube",
        "v3",
        credentials=credentials
    )


def validate_video_file(video_file):

    if not video_file.exists():
        raise RuntimeError(
            f"Video not found: {video_file}"
        )

    if video_file.stat().st_size < 100000:
        raise RuntimeError(
            "Video file is too small"
        )


def upload_video(
    youtube,
    video_file,
    metadata
):

    title = prepare_title(
        metadata["title"]
    )

    description = prepare_description(
        metadata["description"]
    )

    tags = prepare_tags(
        metadata["tags"]
    )

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId":
                YOUTUBE_CATEGORY_ID,
            "defaultLanguage":
                "te",
            "defaultAudioLanguage":
                "te",
        },
        "status": {
            "privacyStatus":
                YOUTUBE_PRIVACY_STATUS,
            "selfDeclaredMadeForKids":
                False,
        },
    }

    media = MediaFileUpload(
        str(video_file),
        mimetype="video/mp4",
        resumable=True,
        chunksize=8 * 1024 * 1024,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None

    print(
        "STARTING YOUTUBE UPLOAD..."
    )

    while response is None:

        status, response = (
            request.next_chunk()
        )

        if status:

            progress = int(
                status.progress() * 100
            )

            print(
                f"UPLOAD PROGRESS: {progress}%"
            )

    video_id = response.get("id")

    if not video_id:
        raise RuntimeError(
            "YouTube video ID was not returned"
        )

    return video_id


def mark_topic_completed(topic_id):

    with TOPICS_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        topics = list(reader)

    found = False

    for topic in topics:

        if topic["id"].strip() == topic_id:

            topic["status"] = "completed"
            found = True
            break

    if not found:
        raise RuntimeError(
            f"Topic {topic_id} not found"
        )

    temp_file = (
        TOPICS_FILE.parent /
        "topics.tmp.csv"
    )

    with temp_file.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(topics)

    temp_file.replace(
        TOPICS_FILE
    )


def save_upload_record(
    topic_id,
    video_id,
    title
):

    UPLOAD_RECORDS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    youtube_url = (
        f"https://www.youtube.com/watch?v={video_id}"
    )

    record = {
        "topic_id": topic_id,
        "video_id": video_id,
        "title": title,
        "youtube_url": youtube_url,
    }

    record_file = (
        UPLOAD_RECORDS_DIR /
        f"{topic_id}.json"
    )

    record_file.write_text(
        json.dumps(
            record,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def run(topic_id):

    topic = get_topic_by_id(
        topic_id
    )

    video_file = (
        VIDEOS_DIR /
        f"{topic_id}.mp4"
    )

    metadata_file = (
        METADATA_DIR /
        f"{topic_id}.txt"
    )

    print("=" * 70)
    print("YOUTUBE UPLOAD")
    print(f"TOPIC: {topic_id}")
    print(f"TITLE: {topic['title']}")
    print("=" * 70)

    validate_video_file(
        video_file
    )

    if not metadata_file.exists():
        raise RuntimeError(
            f"Metadata missing: {metadata_file}"
        )

    existing_record = (
        get_existing_upload_record(
            topic_id
        )
    )

    if existing_record:

        print(
            "UPLOAD RECORD ALREADY EXISTS"
        )

        mark_topic_completed(
            topic_id
        )

        return existing_record["video_id"]

    metadata = read_metadata(
        topic_id
    )

    youtube = get_youtube_client()

    video_id = upload_video(
        youtube,
        video_file,
        metadata
    )

    save_upload_record(
        topic_id,
        video_id,
        metadata["title"]
    )

    mark_topic_completed(
        topic_id
    )

    print("=" * 70)
    print("YOUTUBE UPLOAD SUCCESSFUL")
    print(f"TOPIC: {topic_id}")
    print(f"VIDEO ID: {video_id}")
    print(
        f"URL: https://www.youtube.com/watch?v={video_id}"
    )
    print("=" * 70)

    return video_id


if __name__ == "__main__":

    topic_id = os.environ.get(
        "PIPELINE_TOPIC_ID"
    )

    if not topic_id:
        raise SystemExit(
            "PIPELINE_TOPIC_ID is required"
        )

    run(topic_id)
