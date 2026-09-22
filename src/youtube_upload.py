import os
import sys
import json
import base64
from datetime import datetime, timezone, timedelta

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TOPICS_FILE = os.path.join(BASE_DIR, "topics", "topics.csv")
METADATA_DIR = os.path.join(BASE_DIR, "metadata")
VIDEOS_DIR = os.path.join(BASE_DIR, "videos")
UPLOADS_DIR = os.path.join(METADATA_DIR, "uploads")

YOUTUBE_TOKEN_B64 = os.environ.get("YOUTUBE_TOKEN_B64", "")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload"
]


def now_ist():
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S IST")


def ensure_directories():
    os.makedirs(UPLOADS_DIR, exist_ok=True)


def load_topics():
    import csv

    if not os.path.exists(TOPICS_FILE):
        raise RuntimeError(f"Topics file not found: {TOPICS_FILE}")

    with open(TOPICS_FILE, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def save_topics(topics):
    import csv

    fieldnames = ["id", "title", "status"]

    with open(TOPICS_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(topics)


def get_ready_topic(topics):
    for topic in topics:
        topic_id = str(topic["id"]).zfill(3)

        if topic.get("status") == "completed":
            continue

        long_video = os.path.join(
            VIDEOS_DIR,
            f"{topic_id}.mp4"
        )

        short_video = os.path.join(
            VIDEOS_DIR,
            f"{topic_id}_short.mp4"
        )

        long_metadata = os.path.join(
            METADATA_DIR,
            f"{topic_id}.txt"
        )

        short_metadata = os.path.join(
            METADATA_DIR,
            f"{topic_id}_short.txt"
        )

        if (
            os.path.exists(long_video)
            and os.path.exists(short_video)
            and os.path.exists(long_metadata)
            and os.path.exists(short_metadata)
        ):
            return topic

    return None


def read_metadata(path):
    if not os.path.exists(path):
        raise RuntimeError(f"Metadata file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


def get_credentials():
    if not YOUTUBE_TOKEN_B64:
        raise RuntimeError(
            "YOUTUBE_TOKEN_B64 environment variable is missing."
        )

    token_json = base64.b64decode(
        YOUTUBE_TOKEN_B64
    ).decode("utf-8")

    token_data = json.loads(token_json)

    credentials = Credentials.from_authorized_user_info(
        token_data,
        SCOPES
    )

    if credentials.expired and credentials.refresh_token:
        print("Refreshing expired YouTube token...")
        credentials.refresh(Request())

    if not credentials.valid:
        raise RuntimeError(
            "YouTube credentials are invalid or expired."
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
    metadata
):
    title = metadata.get("title", "")
    description = metadata.get("description", "")
    tags = metadata.get("tags", [])
    category_id = metadata.get("category_id", "27")

    if not isinstance(tags, list):
        tags = []

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
            "defaultLanguage": "te",
            "defaultAudioLanguage": "te"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None

    while response is None:
        status, response = request.next_chunk()

        if status:
            progress = int(status.progress() * 100)
            print(
                f"UPLOAD PROGRESS: {progress}%"
            )

    video_id = response.get("id")

    if not video_id:
        raise RuntimeError(
            "YouTube upload completed but no video ID was returned."
        )

    return video_id


def save_upload_record(
    topic_id,
    video_type,
    video_id,
    title
):
    if video_type == "long":
        filename = f"{topic_id}.json"
    else:
        filename = f"{topic_id}_short.json"

    path = os.path.join(
        UPLOADS_DIR,
        filename
    )

    record = {
        "topic_id": topic_id,
        "type": video_type,
        "video_id": video_id,
        "title": title,
        "uploaded_at": now_ist()
    }

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            record,
            f,
            ensure_ascii=False,
            indent=2
        )

    return path


def read_upload_record(
    topic_id,
    video_type
):
    if video_type == "long":
        filename = f"{topic_id}.json"
    else:
        filename = f"{topic_id}_short.json"

    path = os.path.join(
        UPLOADS_DIR,
        filename
    )

    if not os.path.exists(path):
        return None

    try:
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)
    except Exception:
        return None


def long_url(video_id):
    return f"https://www.youtube.com/watch?v={video_id}"


def short_url(video_id):
    return f"https://www.youtube.com/shorts/{video_id}"


def write_summary(
    topic_id,
    title,
    long_video_id,
    short_video_id
):
    summary_file = os.environ.get(
        "GITHUB_STEP_SUMMARY"
    )

    if not summary_file:
        return

    long_link = long_url(long_video_id)
    short_link = short_url(short_video_id)

    lines = [
        "# 🎬 YouTube Publish Successful",
        "",
        f"## Topic {topic_id}",
        "",
        f"**{title}**",
        "",
        "### 🎬 Long Video",
        "",
        f"**[▶️ WATCH LONG VIDEO]({long_link})**",
        "",
        f"`{long_link}`",
        "",
        "### 📱 YouTube Short",
        "",
        f"**[▶️ WATCH SHORT]({short_link})**",
        "",
        f"`{short_link}`",
        "",
        "### ✅ Status",
        "",
        "Long Video: **Uploaded**",
        "",
        "Short: **Uploaded**",
        "",
        f"Topic {topic_id}: **Completed**",
        ""
    ]

    with open(
        summary_file,
        "a",
        encoding="utf-8"
    ) as f:
        f.write("\n".join(lines))


def main():
    print("=" * 70)
    print("YOUTUBE PUBLISH")
    print("=" * 70)

    print(
        f"UPLOAD START TIME (IST): {now_ist()}"
    )

    ensure_directories()

    topics = load_topics()

    topic = get_ready_topic(topics)

    if not topic:
        print("NO READY TOPIC FOUND")
        return

    topic_id = str(topic["id"]).zfill(3)
    title = topic["title"]

    print(f"TOPIC: {topic_id}")
    print(f"TITLE: {title}")

    long_video_path = os.path.join(
        VIDEOS_DIR,
        f"{topic_id}.mp4"
    )

    short_video_path = os.path.join(
        VIDEOS_DIR,
        f"{topic_id}_short.mp4"
    )

    long_metadata_path = os.path.join(
        METADATA_DIR,
        f"{topic_id}.txt"
    )

    short_metadata_path = os.path.join(
        METADATA_DIR,
        f"{topic_id}_short.txt"
    )

    long_record = read_upload_record(
        topic_id,
        "long"
    )

    short_record = read_upload_record(
        topic_id,
        "short"
    )

    youtube = get_youtube_service()

    if long_record and long_record.get("video_id"):
        long_video_id = long_record["video_id"]

        print("LONG VIDEO ALREADY UPLOADED")
        print(
            f"VIDEO ID: {long_video_id}"
        )
    else:
        print("=" * 70)
        print("UPLOADING LONG VIDEO")
        print("=" * 70)

        long_metadata = read_metadata(
            long_metadata_path
        )

        long_video_id = upload_video(
            youtube,
            long_video_path,
            long_metadata
        )

        save_upload_record(
            topic_id,
            "long",
            long_video_id,
            long_metadata.get("title", title)
        )

        print("LONG VIDEO UPLOADED")
        print(
            f"VIDEO ID: {long_video_id}"
        )
        print(
            f"LONG VIDEO URL: {long_url(long_video_id)}"
        )

    if short_record and short_record.get("video_id"):
        short_video_id = short_record["video_id"]

        print("SHORT ALREADY UPLOADED")
        print(
            f"VIDEO ID: {short_video_id}"
        )
    else:
        print("=" * 70)
        print("UPLOADING SHORT")
        print("=" * 70)

        short_metadata = read_metadata(
            short_metadata_path
        )

        short_video_id = upload_video(
            youtube,
            short_video_path,
            short_metadata
        )

        save_upload_record(
            topic_id,
            "short",
            short_video_id,
            short_metadata.get("title", title)
        )

        print("SHORT UPLOADED")
        print(
            f"VIDEO ID: {short_video_id}"
        )
        print(
            f"SHORT VIDEO URL: {short_url(short_video_id)}"
        )

    long_record = read_upload_record(
        topic_id,
        "long"
    )

    short_record = read_upload_record(
        topic_id,
        "short"
    )

    if (
        long_record
        and long_record.get("video_id")
        and short_record
        and short_record.get("video_id")
    ):
        for current_topic in topics:
            current_id = str(
                current_topic["id"]
            ).zfill(3)

            if current_id == topic_id:
                current_topic["status"] = "completed"
                break

        save_topics(topics)

        final_long_id = long_record["video_id"]
        final_short_id = short_record["video_id"]

        print("=" * 70)
        print("BOTH VIDEOS UPLOADED SUCCESSFULLY")
        print("=" * 70)

        print(
            f"LONG VIDEO ID: {final_long_id}"
        )
        print(
            f"LONG VIDEO URL: {long_url(final_long_id)}"
        )

        print(
            f"SHORT VIDEO ID: {final_short_id}"
        )
        print(
            f"SHORT VIDEO URL: {short_url(final_short_id)}"
        )

        print(
            f"TOPIC {topic_id} COMPLETED"
        )

        write_summary(
            topic_id,
            title,
            final_long_id,
            final_short_id
        )

        print("=" * 70)

    else:
        raise RuntimeError(
            "Both Long and Short uploads were not completed."
        )


if __name__ == "__main__":
    main()
