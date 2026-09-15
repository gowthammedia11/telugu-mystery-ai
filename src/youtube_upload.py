import base64
import csv
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


TOPICS_FILE = Path(
    "topics/topics.csv"
)

METADATA_DIR = Path(
    "metadata"
)

VIDEOS_DIR = Path(
    "videos"
)

UPLOADS_DIR = (
    METADATA_DIR / "uploads"
)

YOUTUBE_TOKEN_ENV = (
    "YOUTUBE_TOKEN_B64"
)

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload"
]

YOUTUBE_PRIVACY_STATUS = "public"

IST = ZoneInfo(
    "Asia/Kolkata"
)


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

    fieldnames = [
        "id",
        "title",
        "status"
    ]

    with TOPICS_FILE.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            topics
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
            "pending"
        ).strip().lower()

        if (
            not topic_id
            or status == "completed"
        ):
            continue

        long_video = (
            VIDEOS_DIR
            / f"{topic_id}.mp4"
        )

        long_metadata = (
            METADATA_DIR
            / f"{topic_id}.txt"
        )

        short_video = (
            VIDEOS_DIR
            / f"{topic_id}_short.mp4"
        )

        short_metadata = (
            METADATA_DIR
            / f"{topic_id}_short.txt"
        )

        if (
            long_video.exists()
            and long_metadata.exists()
            and short_video.exists()
            and short_metadata.exists()
        ):

            candidates.append(
                topic
            )

    candidates.sort(
        key=lambda topic:
        int(
            topic["id"].strip()
        )
    )

    return (
        candidates[0]
        if candidates
        else None
    )


def read_metadata(
    metadata_file
):

    text = metadata_file.read_text(
        encoding="utf-8"
    )

    title = ""
    description = ""
    tags = []
    hashtags = []

    for line in text.splitlines():

        if line.startswith(
            "TITLE:"
        ):

            title = line[
                len("TITLE:"):
            ].strip()

        elif line.startswith(
            "DESCRIPTION:"
        ):

            description = line[
                len("DESCRIPTION:"):
            ].strip()

        elif line.startswith(
            "TAGS:"
        ):

            raw_tags = line[
                len("TAGS:"):
            ].strip()

            tags = [
                item.strip()
                for item in raw_tags.split(",")
                if item.strip()
            ]

        elif line.startswith(
            "HASHTAGS:"
        ):

            raw_hashtags = line[
                len("HASHTAGS:"):
            ].strip()

            hashtags = [
                item.strip()
                for item
                in raw_hashtags.split()
                if item.strip()
            ]

    if not title:
        raise RuntimeError(
            f"TITLE missing in {metadata_file}"
        )

    if not description:
        raise RuntimeError(
            f"DESCRIPTION missing in {metadata_file}"
        )

    if hashtags:

        hashtag_text = " ".join(
            hashtags
        )

        if hashtag_text not in description:

            description = (
                description
                + "\n\n"
                + hashtag_text
            )

    return (
        title,
        description,
        tags
    )


def get_credentials():

    token_b64 = os.environ.get(
        YOUTUBE_TOKEN_ENV
    )

    if not token_b64:

        raise RuntimeError(
            "YOUTUBE_TOKEN_B64 secret is missing"
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

    credentials = Credentials.from_authorized_user_info(
        token_data,
        YOUTUBE_SCOPES
    )

    return credentials


def get_youtube():

    credentials = get_credentials()

    return build(
        "youtube",
        "v3",
        credentials=credentials
    )


def upload_video(
    youtube,
    video_file,
    metadata_file,
    is_short=False
):

    title, description, tags = (
        read_metadata(
            metadata_file
        )
    )

    if is_short:

        if "#Shorts" not in title:

            title = (
                title
                + " #Shorts"
            )

        if "#Shorts" not in description:

            description = (
                description
                + "\n\n#Shorts"
            )

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
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
        str(video_file),
        chunksize=1024 * 1024 * 8,
        resumable=True
    )

    print("=" * 70)

    if is_short:
        print("YOUTUBE SHORT UPLOAD")
    else:
        print("YOUTUBE LONG VIDEO UPLOAD")

    print("=" * 70)
    print(f"FILE: {video_file}")
    print(f"TITLE: {title}")
    print("PRIVACY: public")

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None

    while response is None:

        status, response = (
            request.next_chunk()
        )

        if status:

            print(
                f"UPLOAD PROGRESS: "
                f"{int(status.progress() * 100)}%"
            )

    video_id = response.get(
        "id"
    )

    if not video_id:

        raise RuntimeError(
            "YouTube upload completed "
            "without returning video ID"
        )

    print(
        f"YOUTUBE VIDEO ID: {video_id}"
    )

    return video_id


def upload_record_file(
    topic_id,
    suffix
):

    if suffix == "":

        return (
            UPLOADS_DIR
            / f"{topic_id}.json"
        )

    return (
        UPLOADS_DIR
        / f"{topic_id}_{suffix}.json"
    )


def save_upload_record(
    topic_id,
    video_id,
    video_file,
    is_short
):

    UPLOADS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    suffix = (
        "short"
        if is_short
        else ""
    )

    record_file = upload_record_file(
        topic_id,
        suffix
    )

    record = {
        "topic_id": topic_id,
        "youtube_video_id": video_id,
        "video_file": str(video_file),
        "type": (
            "short"
            if is_short
            else "long"
        ),
        "privacy_status": "public",
        "uploaded": True,
    }

    record_file.write_text(
        json.dumps(
            record,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        f"UPLOAD RECORD SAVED: "
        f"{record_file}"
    )


def existing_upload_id(
    topic_id,
    is_short
):

    suffix = (
        "short"
        if is_short
        else ""
    )

    record_file = upload_record_file(
        topic_id,
        suffix
    )

    if not record_file.exists():
        return None

    try:

        data = json.loads(
            record_file.read_text(
                encoding="utf-8"
            )
        )

        if data.get(
            "uploaded"
        ):

            return data.get(
                "youtube_video_id"
            )

    except Exception:

        return None

    return None


def mark_topic_completed(
    topic_id
):

    topics = load_topics()

    long_id = existing_upload_id(
        topic_id,
        False
    )

    short_id = existing_upload_id(
        topic_id,
        True
    )

    if not long_id:
        raise RuntimeError(
            "Cannot mark completed: "
            "long video upload record missing"
        )

    if not short_id:
        raise RuntimeError(
            "Cannot mark completed: "
            "Short upload record missing"
        )

    found = False

    for topic in topics:

        if (
            topic.get(
                "id",
                ""
            ).strip()
            == topic_id
        ):

            topic["status"] = (
                "completed"
            )

            found = True

            break

    if not found:

        raise RuntimeError(
            f"Topic {topic_id} not found "
            "while marking completed"
        )

    save_topics(
        topics
    )

    print(
        f"TOPIC {topic_id} MARKED COMPLETED"
    )


def upload_one_if_needed(
    youtube,
    topic_id,
    video_file,
    metadata_file,
    is_short
):

    existing_id = existing_upload_id(
        topic_id,
        is_short
    )

    if existing_id:

        print("=" * 70)

        if is_short:
            print("SHORT ALREADY UPLOADED")
        else:
            print("LONG VIDEO ALREADY UPLOADED")

        print(
            f"YOUTUBE VIDEO ID: {existing_id}"
        )

        print("=" * 70)

        return existing_id

    if not video_file.exists():

        raise RuntimeError(
            f"Video file missing: {video_file}"
        )

    if not metadata_file.exists():

        raise RuntimeError(
            f"Metadata file missing: {metadata_file}"
        )

    video_id = upload_video(
        youtube,
        video_file,
        metadata_file,
        is_short=is_short
    )

    save_upload_record(
        topic_id,
        video_id,
        video_file,
        is_short
    )

    return video_id


def main():

    print("=" * 70)
    print("TELUGU MYSTERY AI — YOUTUBE UPLOAD")
    print("=" * 70)

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

    long_video = (
        VIDEOS_DIR
        / f"{topic_id}.mp4"
    )

    long_metadata = (
        METADATA_DIR
        / f"{topic_id}.txt"
    )

    short_video = (
        VIDEOS_DIR
        / f"{topic_id}_short.mp4"
    )

    short_metadata = (
        METADATA_DIR
        / f"{topic_id}_short.txt"
    )

    print(
        f"TOPIC: {topic_id}"
    )

    print(
        f"TITLE: {topic_title}"
    )

    print(
        "CURRENT IST:",
        __import__("datetime").datetime.now(
            IST
        ).strftime(
            "%Y-%m-%d %H:%M:%S IST"
        )
    )

    # ========================================================
    # Validate all files BEFORE uploading
    # ========================================================

    required_files = [
        long_video,
        long_metadata,
        short_video,
        short_metadata,
    ]

    for file in required_files:

        if not file.exists():

            raise RuntimeError(
                f"Required file missing: {file}"
            )

        if file.stat().st_size <= 0:

            raise RuntimeError(
                f"Required file is empty: {file}"
            )

    youtube = get_youtube()

    # ========================================================
    # LONG VIDEO
    # ========================================================

    long_video_id = upload_one_if_needed(
        youtube,
        topic_id,
        long_video,
        long_metadata,
        is_short=False
    )

    print(
        f"LONG VIDEO READY: "
        f"{long_video_id}"
    )

    # ========================================================
    # SHORT
    # ========================================================

    short_video_id = upload_one_if_needed(
        youtube,
        topic_id,
        short_video,
        short_metadata,
        is_short=True
    )

    print(
        f"SHORT READY: "
        f"{short_video_id}"
    )

    # ========================================================
    # ONLY NOW COMPLETED
    # ========================================================

    mark_topic_completed(
        topic_id
    )

    print("=" * 70)
    print("BOTH VIDEOS UPLOADED SUCCESSFULLY")
    print("=" * 70)
    print(
        f"LONG VIDEO ID: "
        f"{long_video_id}"
    )
    print(
        f"SHORT VIDEO ID: "
        f"{short_video_id}"
    )
    print(
        f"TOPIC: {topic_id}"
    )
    print(
        "STATUS: completed"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
