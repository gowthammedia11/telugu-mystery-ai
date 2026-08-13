import base64
import csv
import json
import os
import re
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


# ============================================================
# CONFIG
# ============================================================

TOPICS_FILE = "topics/topics.csv"
METADATA_DIR = Path("metadata")
VIDEOS_DIR = Path("videos")

YOUTUBE_TOKEN_ENV = "YOUTUBE_TOKEN_B64"

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload"
]


# ============================================================
# GET READY TOPIC
# ============================================================

def get_ready_topic():

    if not Path(TOPICS_FILE).exists():
        raise Exception(
            f"Topics file not found: {TOPICS_FILE}"
        )

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

        video_file = (
            VIDEOS_DIR
            / f"{topic_id}.mp4"
        )

        metadata_file = (
            METADATA_DIR
            / f"{topic_id}.txt"
        )

        if (
            video_file.exists()
            and metadata_file.exists()
        ):

            return topic

    return None


# ============================================================
# READ METADATA
# ============================================================

def read_metadata(topic_id):

    metadata_file = (
        METADATA_DIR
        / f"{topic_id}.txt"
    )

    if not metadata_file.exists():

        raise Exception(
            f"Metadata file not found: {metadata_file}"
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
        raise Exception(
            "TITLE not found in metadata"
        )

    if not description_match:
        raise Exception(
            "DESCRIPTION not found in metadata"
        )

    title = title_match.group(1).strip()

    description = (
        description_match
        .group(1)
        .strip()
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

    # Add hashtags to description.
    if hashtags_text:

        description = (
            description
            + "\n\n"
            + hashtags_text
        )

    return {
        "title": title,
        "description": description,
        "tags": tags,
    }


# ============================================================
# LOAD YOUTUBE TOKEN
# ============================================================

def load_youtube_credentials():

    token_b64 = os.environ.get(
        YOUTUBE_TOKEN_ENV
    )

    if not token_b64:

        raise Exception(
            "YOUTUBE_TOKEN_B64 GitHub Secret is missing"
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

        raise Exception(
            f"Invalid YOUTUBE_TOKEN_B64: {error}"
        )

    credentials = Credentials.from_authorized_user_info(
        token_data,
        YOUTUBE_SCOPES
    )

    return credentials


# ============================================================
# BUILD YOUTUBE CLIENT
# ============================================================

def get_youtube_client():

    credentials = (
        load_youtube_credentials()
    )

    youtube = build(
        "youtube",
        "v3",
        credentials=credentials
    )

    return youtube


# ============================================================
# UPLOAD VIDEO
# ============================================================

def upload_video(
    youtube,
    video_file,
    metadata
):

    title = metadata["title"]
    description = metadata["description"]
    tags = metadata["tags"]

    # --------------------------------------------------------
    # YouTube title safety
    # --------------------------------------------------------

    title = title.strip()

    if len(title) > 100:

        title = title[:97] + "..."

    # --------------------------------------------------------
    # Description safety
    # --------------------------------------------------------

    description = description.strip()

    if len(description) > 5000:

        description = (
            description[:4997]
            + "..."
        )

    # --------------------------------------------------------
    # YouTube upload body
    # --------------------------------------------------------

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
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        }
    }

    print("=" * 70)
    print("YOUTUBE UPLOAD")
    print("=" * 70)

    print(
        f"VIDEO: {video_file}"
    )

    print(
        f"TITLE: {title}"
    )

    print(
        f"TAGS: {len(tags)}"
    )

    print(
        f"CATEGORY ID: 27"
    )

    print(
        "PRIVACY: PUBLIC"
    )

    print("=" * 70)

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

    video_id = response.get(
        "id"
    )

    if not video_id:

        raise Exception(
            "YouTube upload completed but video ID was not returned"
        )

    print("=" * 70)
    print("YOUTUBE UPLOAD SUCCESSFUL")
    print("=" * 70)

    print(
        f"VIDEO ID: {video_id}"
    )

    print(
        f"https://www.youtube.com/watch?v={video_id}"
    )

    print("=" * 70)

    return video_id


# ============================================================
# UPDATE TOPIC STATUS
# ============================================================

def mark_topic_completed(topic_id):

    topics_path = Path(
        TOPICS_FILE
    )

    with open(
        topics_path,
        "r",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        fieldnames = reader.fieldnames

        topics = list(reader)

    if not fieldnames:

        raise Exception(
            "topics.csv has no header"
        )

    # --------------------------------------------------------
    # Add status column if missing
    # --------------------------------------------------------

    if "status" not in fieldnames:

        fieldnames.append(
            "status"
        )

    found = False

    for topic in topics:

        if (
            topic["id"].strip()
            == topic_id
        ):

            topic["status"] = (
                "completed"
            )

            found = True

            break

    if not found:

        raise Exception(
            f"Topic {topic_id} not found in topics.csv"
        )

    temp_file = (
        topics_path.parent
        / "topics.tmp.csv"
    )

    with open(
        temp_file,
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

    temp_file.replace(
        topics_path
    )

    print("=" * 70)
    print("TOPIC STATUS UPDATED")
    print("=" * 70)

    print(
        f"TOPIC: {topic_id}"
    )

    print(
        "STATUS: completed"
    )

    print("=" * 70)


# ============================================================
# SAVE UPLOAD RECORD
# ============================================================

def save_upload_record(
    topic_id,
    video_id,
    title
):

    records_dir = Path(
        "metadata/uploads"
    )

    records_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    record_file = (
        records_dir
        / f"{topic_id}.json"
    )

    record = {
        "topic_id": topic_id,
        "video_id": video_id,
        "title": title,
        "youtube_url":
            f"https://www.youtube.com/watch?v={video_id}"
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
        f"UPLOAD RECORD: {record_file}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("TELUGU MYSTERY AI — YOUTUBE UPLOADER")
    print("=" * 70)

    topic = get_ready_topic()

    if not topic:

        print(
            "NO VIDEO + METADATA READY FOR YOUTUBE"
        )

        return

    topic_id = topic[
        "id"
    ].strip()

    topic_title = topic[
        "title"
    ].strip()

    video_file = (
        VIDEOS_DIR
        / f"{topic_id}.mp4"
    )

    print(
        f"SELECTED TOPIC: {topic_id}"
    )

    print(
        f"TITLE: {topic_title}"
    )

    print(
        f"VIDEO: {video_file}"
    )

    if not video_file.exists():

        raise Exception(
            f"Video not found: {video_file}"
        )

    metadata = read_metadata(
        topic_id
    )

    print("=" * 70)
    print("METADATA LOADED")
    print("=" * 70)

    print(
        f"YOUTUBE TITLE: "
        f"{metadata['title']}"
    )

    print(
        f"TAGS: "
        f"{len(metadata['tags'])}"
    )

    print("=" * 70)

    youtube = (
        get_youtube_client()
    )

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
    print("PIPELINE YOUTUBE STEP COMPLETE")
    print("=" * 70)

    print(
        f"TOPIC {topic_id} = COMPLETED"
    )

    print(
        f"YOUTUBE VIDEO ID = {video_id}"
    )

    print(
        "NEXT TOPIC CAN BE PROCESSED."
    )

    print("=" * 70)


if __name__ == "__main__":
    main()
