import base64
import csv
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


TOPICS_FILE = Path("topics/topics.csv")

METADATA_DIR = Path("metadata")
VIDEOS_DIR = Path("videos")
UPLOADS_DIR = METADATA_DIR / "uploads"

YOUTUBE_TOKEN_ENV = "YOUTUBE_TOKEN_B64"

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload"
]

YOUTUBE_PRIVACY_STATUS = "public"

IST = ZoneInfo("Asia/Kolkata")


def load_topics():

    with TOPICS_FILE.open(
        "r",
        encoding="utf-8",
        newline=""
    ) as file:
        return list(
            csv.DictReader(file)
        )


def save_topics(topics):

    with TOPICS_FILE.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as file:

        fieldnames = [
            "id",
            "title",
            "status"
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(topics)


def valid_file(path):

    return (
        path.exists()
        and path.is_file()
        and path.stat().st_size > 0
    )


def get_ready_topic():

    topics = load_topics()

    candidates = []

    for topic in topics:

        topic_id = topic.get(
            "id",
            ""
        ).strip()

        status = topic.get(
            "status",
            ""
        ).strip().lower()

        if not topic_id:
            continue

        if status == "completed":
            continue

        long_video = (
            VIDEOS_DIR
            / f"{topic_id}.mp4"
        )

        short_video = (
            VIDEOS_DIR
            / f"{topic_id}_short.mp4"
        )

        long_metadata = (
            METADATA_DIR
            / f"{topic_id}.txt"
        )

        short_metadata = (
            METADATA_DIR
            / f"{topic_id}_short.txt"
        )

        if (
            valid_file(long_video)
            and valid_file(short_video)
            and valid_file(long_metadata)
            and valid_file(short_metadata)
        ):

            candidates.append(
                topic
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda topic: int(
            topic["id"].strip()
        )
    )

    return candidates[0]


def read_metadata(path):

    text = path.read_text(
        encoding="utf-8"
    )

    title = ""
    description_lines = []
    tags = ""
    hashtags = ""

    current = None

    for line in text.splitlines():

        stripped = line.strip()

        upper = stripped.upper()

        if upper.startswith("TITLE:"):

            title = stripped[6:].strip()
            current = "title"
            continue

        if upper.startswith("DESCRIPTION:"):

            description_lines = [
                stripped[12:].strip()
            ]

            current = "description"
            continue

        if upper.startswith("TAGS:"):

            tags = stripped[5:].strip()
            current = "tags"
            continue

        if upper.startswith("HASHTAGS:"):

            hashtags = stripped[9:].strip()
            current = "hashtags"
            continue

        if current == "description":
            description_lines.append(
                stripped
            )

    description = "\n".join(
        line
        for line in description_lines
        if line
    ).strip()

    if hashtags:

        description = (
            description
            + "\n\n"
            + hashtags
        ).strip()

    tag_list = [
        tag.strip()
        for tag in tags.split(",")
        if tag.strip()
    ]

    return {
        "title": title[:100],
        "description": description,
        "tags": tag_list,
    }


def get_credentials():

    token_b64 = os.getenv(
        YOUTUBE_TOKEN_ENV,
        ""
    ).strip()

    if not token_b64:

        raise RuntimeError(
            f"{YOUTUBE_TOKEN_ENV} environment variable is missing"
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

    except Exception as exc:

        raise RuntimeError(
            f"Unable to decode YouTube token: {exc}"
        )

    credentials = Credentials.from_authorized_user_info(
        token_data,
        YOUTUBE_SCOPES
    )

    if credentials.expired and credentials.refresh_token:

        print(
            "Refreshing expired YouTube token..."
        )

        credentials.refresh(
            Request()
        )

    if not credentials.valid:

        raise RuntimeError(
            "YouTube credentials are not valid"
        )

    return credentials


def get_youtube_service():

    credentials = get_credentials()

    return build(
        "youtube",
        "v3",
        credentials=credentials
    )


def upload_video(
    youtube,
    video_path,
    metadata,
    is_short=False
):

    body = {
        "snippet": {
            "title": metadata["title"],
            "description": metadata["description"],
            "tags": metadata["tags"],
            "categoryId": "27",
            "defaultLanguage": "te",
            "defaultAudioLanguage": "te",
        },
        "status": {
            "privacyStatus": YOUTUBE_PRIVACY_STATUS,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=8 * 1024 * 1024
    )

    print("=" * 70)

    if is_short:
        print("UPLOADING YOUTUBE SHORT")
    else:
        print("UPLOADING YOUTUBE LONG VIDEO")

    print(
        f"FILE: {video_path}"
    )

    print(
        f"TITLE: {metadata['title']}"
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
                f"UPLOAD PROGRESS: "
                f"{int(status.progress() * 100)}%"
            )

    if not response:

        raise RuntimeError(
            "YouTube upload returned no response"
        )

    video_id = response.get(
        "id"
    )

    if not video_id:

        raise RuntimeError(
            f"YouTube upload did not return video ID: {response}"
        )

    print(
        f"YOUTUBE VIDEO ID: {video_id}"
    )

    return response


def record_path(
    topic_id,
    is_short=False
):

    suffix = "_short" if is_short else ""

    return (
        UPLOADS_DIR
        / f"{topic_id}{suffix}.json"
    )


def read_upload_record(
    topic_id,
    is_short=False
):

    path = record_path(
        topic_id,
        is_short
    )

    if not path.exists():
        return None

    try:

        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if data.get("video_id"):
            return data

    except Exception:
        return None

    return None


def save_upload_record(
    topic_id,
    response,
    is_short=False
):

    UPLOADS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    path = record_path(
        topic_id,
        is_short
    )

    data = {
        "topic_id": topic_id,
        "video_id": response.get("id"),
        "uploaded_at_ist": datetime.now(
            IST
        ).strftime(
            "%Y-%m-%d %H:%M:%S IST"
        ),
        "privacy_status": YOUTUBE_PRIVACY_STATUS,
        "type": "short" if is_short else "long",
    }

    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        f"UPLOAD RECORD SAVED: {path}"
    )


def mark_topic_completed(
    topic_id
):

    topics = load_topics()

    for topic in topics:

        if topic.get(
            "id",
            ""
        ).strip() == topic_id:

            topic["status"] = "completed"
            break

    save_topics(
        topics
    )

    print(
        f"TOPIC MARKED COMPLETED: {topic_id}"
    )


def main():

    current_ist = datetime.now(
        IST
    )

    print(
        f"UPLOAD START TIME (IST): "
        f"{current_ist.strftime('%Y-%m-%d %H:%M:%S IST')}"
    )

    topic = get_ready_topic()

    if not topic:

        print(
            "NO TOPIC READY FOR YOUTUBE UPLOAD"
        )

        return

    topic_id = topic[
        "id"
    ].strip()

    topic_title = topic[
        "title"
    ].strip()

    print("=" * 70)
    print("YOUTUBE PUBLISH")
    print("=" * 70)
    print(
        f"TOPIC: {topic_id}"
    )
    print(
        f"TITLE: {topic_title}"
    )
    print("=" * 70)

    long_video = (
        VIDEOS_DIR
        / f"{topic_id}.mp4"
    )

    short_video = (
        VIDEOS_DIR
        / f"{topic_id}_short.mp4"
    )

    long_metadata_file = (
        METADATA_DIR
        / f"{topic_id}.txt"
    )

    short_metadata_file = (
        METADATA_DIR
        / f"{topic_id}_short.txt"
    )

    for path in (
        long_video,
        short_video,
        long_metadata_file,
        short_metadata_file,
    ):

        if not valid_file(path):

            raise RuntimeError(
                f"Required upload file missing: {path}"
            )

    youtube = get_youtube_service()

    long_record = read_upload_record(
        topic_id,
        False
    )

    if long_record:

        print(
            "LONG VIDEO ALREADY UPLOADED"
        )

        print(
            f"VIDEO ID: {long_record['video_id']}"
        )

    else:

        long_metadata = read_metadata(
            long_metadata_file
        )

        long_response = upload_video(
            youtube,
            long_video,
            long_metadata,
            False
        )

        save_upload_record(
            topic_id,
            long_response,
            False
        )

    short_record = read_upload_record(
        topic_id,
        True
    )

    if short_record:

        print(
            "SHORT ALREADY UPLOADED"
        )

        print(
            f"VIDEO ID: {short_record['video_id']}"
        )

    else:

        short_metadata = read_metadata(
            short_metadata_file
        )

        short_response = upload_video(
            youtube,
            short_video,
            short_metadata,
            True
        )

        save_upload_record(
            topic_id,
            short_response,
            True
        )

    final_long_record = read_upload_record(
        topic_id,
        False
    )

    final_short_record = read_upload_record(
        topic_id,
        True
    )

    if (
        final_long_record
        and final_short_record
    ):

        mark_topic_completed(
            topic_id
        )

        print("=" * 70)
        print("BOTH VIDEOS UPLOADED SUCCESSFULLY")
        print(
            f"LONG VIDEO ID: "
            f"{final_long_record['video_id']}"
        )
        print(
            f"SHORT VIDEO ID: "
            f"{final_short_record['video_id']}"
        )
        print(
            f"TOPIC {topic_id} COMPLETED"
        )
        print("=" * 70)

    else:

        raise RuntimeError(
            "Both uploads were not completed. "
            "Topic remains incomplete."
        )


if __name__ == "__main__":
    main()
