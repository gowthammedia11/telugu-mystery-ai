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

TOPICS_FILE = Path("topics/topics.csv")
METADATA_DIR = Path("metadata")
VIDEOS_DIR = Path("videos")
UPLOAD_RECORDS_DIR = Path("metadata/uploads")

YOUTUBE_TOKEN_ENV = "YOUTUBE_TOKEN_B64"

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload"
]

# YouTube limits
MAX_TITLE_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 5000
MAX_TAGS = 45
MAX_TOTAL_TAG_LENGTH = 480

# Education category
YOUTUBE_CATEGORY_ID = "27"

# Public upload
YOUTUBE_PRIVACY_STATUS = "public"


# ============================================================
# GET READY TOPIC
# ============================================================

def get_ready_topic():

    if not TOPICS_FILE.exists():

        raise Exception(
            f"Topics file not found: {TOPICS_FILE}"
        )

    with TOPICS_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        topics = list(
            csv.DictReader(file)
        )

    for topic in topics:

        topic_id = topic.get(
            "id",
            ""
        ).strip()

        status = topic.get(
            "status",
            "pending"
        ).strip().lower()

        if not topic_id:
            continue

        # ----------------------------------------------------
        # IMPORTANT
        # Only pending topics should reach YouTube upload.
        # Completed topics must never be uploaded again.
        # ----------------------------------------------------

        if status != "pending":
            continue

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

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    title_match = re.search(
        r"TITLE:\s*\n(.*?)(?=\n\nDESCRIPTION:)",
        text,
        flags=re.DOTALL
    )

    # --------------------------------------------------------
    # DESCRIPTION
    # --------------------------------------------------------

    description_match = re.search(
        r"DESCRIPTION:\s*\n(.*?)(?=\n\nTAGS:)",
        text,
        flags=re.DOTALL
    )

    # --------------------------------------------------------
    # TAGS
    # --------------------------------------------------------

    tags_match = re.search(
        r"TAGS:\s*\n(.*?)(?=\n\nHASHTAGS:)",
        text,
        flags=re.DOTALL
    )

    # --------------------------------------------------------
    # HASHTAGS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # ADD HASHTAGS TO DESCRIPTION
    # --------------------------------------------------------

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
# CLEAN TITLE
# ============================================================

def prepare_title(title):

    title = title.strip()

    # Remove unnecessary line breaks
    title = re.sub(
        r"\s+",
        " ",
        title
    )

    # YouTube title limit
    if len(title) > MAX_TITLE_LENGTH:

        title = (
            title[:MAX_TITLE_LENGTH - 3]
            + "..."
        )

    return title


# ============================================================
# CLEAN DESCRIPTION
# ============================================================

def prepare_description(description):

    description = description.strip()

    # Normalize excessive blank lines
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


# ============================================================
# CLEAN TAGS
# ============================================================

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

        # ----------------------------------------------------
        # YouTube tags total length safety
        # ----------------------------------------------------

        additional_length = (
            len(tag) + 1
        )

        if (
            total_length
            + additional_length
            > MAX_TOTAL_TAG_LENGTH
        ):
            break

        seen.add(key)

        final_tags.append(tag)

        total_length += additional_length

        if len(final_tags) >= MAX_TAGS:
            break

    return final_tags


# ============================================================
# CHECK EXISTING UPLOAD RECORD
# ============================================================

def get_existing_upload_record(topic_id):

    record_file = (
        UPLOAD_RECORDS_DIR
        / f"{topic_id}.json"
    )

    if not record_file.exists():
        return None

    try:

        record = json.loads(
            record_file.read_text(
                encoding="utf-8"
            )
        )

        video_id = record.get(
            "video_id"
        )

        if video_id:
            return record

    except Exception as error:

        print(
            f"WARNING: Could not read upload record: {error}"
        )

    return None


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

    token_b64 = token_b64.strip()

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

    if not isinstance(
        token_data,
        dict
    ):

        raise Exception(
            "YOUTUBE_TOKEN_B64 does not contain valid token JSON"
        )

    required_token_fields = [
        "client_id",
        "client_secret",
        "refresh_token",
    ]

    missing_fields = [
        field
        for field in required_token_fields
        if not token_data.get(field)
    ]

    if missing_fields:

        raise Exception(
            "YouTube token is missing required fields: "
            + ", ".join(missing_fields)
        )

    credentials = (
        Credentials.from_authorized_user_info(
            token_data,
            YOUTUBE_SCOPES
        )
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
# VALIDATE VIDEO
# ============================================================

def validate_video_file(video_file):

    if not video_file.exists():

        raise Exception(
            f"Video not found: {video_file}"
        )

    if not video_file.is_file():

        raise Exception(
            f"Video path is not a file: {video_file}"
        )

    file_size = video_file.stat().st_size

    if file_size < 1000:

        raise Exception(
            f"Video file is too small: {file_size} bytes"
        )

    print(
        f"VIDEO FILE SIZE: "
        f"{file_size / (1024 * 1024):.2f} MB"
    )


# ============================================================
# UPLOAD VIDEO
# ============================================================

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

    # --------------------------------------------------------
    # YOUTUBE UPLOAD BODY
    # --------------------------------------------------------

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
        f"TITLE LENGTH: {len(title)}"
    )

    print(
        f"DESCRIPTION LENGTH: {len(description)}"
    )

    print(
        f"TAGS: {len(tags)}"
    )

    print(
        f"CATEGORY ID: {YOUTUBE_CATEGORY_ID}"
    )

    print(
        f"PRIVACY: {YOUTUBE_PRIVACY_STATUS.upper()}"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # MEDIA UPLOAD
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # RESUMABLE UPLOAD
    # --------------------------------------------------------

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

    youtube_url = (
        f"https://www.youtube.com/watch?v={video_id}"
    )

    print("=" * 70)
    print("YOUTUBE UPLOAD SUCCESSFUL")
    print("=" * 70)

    print(
        f"VIDEO ID: {video_id}"
    )

    print(
        f"YOUTUBE URL: {youtube_url}"
    )

    print("=" * 70)

    return video_id


# ============================================================
# UPDATE TOPIC STATUS
# ============================================================

def mark_topic_completed(topic_id):

    if not TOPICS_FILE.exists():

        raise Exception(
            f"Topics file not found: {TOPICS_FILE}"
        )

    with TOPICS_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        fieldnames = (
            reader.fieldnames
        )

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

        current_id = (
            topic.get(
                "id",
                ""
            ).strip()
        )

        if current_id == topic_id:

            topic["status"] = (
                "completed"
            )

            found = True

            break

    if not found:

        raise Exception(
            f"Topic {topic_id} not found in topics.csv"
        )

    # --------------------------------------------------------
    # Temporary file
    # --------------------------------------------------------

    temp_file = (
        TOPICS_FILE.parent
        / "topics.tmp.csv"
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

        writer.writerows(
            topics
        )

    # --------------------------------------------------------
    # Replace original
    # --------------------------------------------------------

    temp_file.replace(
        TOPICS_FILE
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

    UPLOAD_RECORDS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    record_file = (
        UPLOAD_RECORDS_DIR
        / f"{topic_id}.json"
    )

    youtube_url = (
        f"https://www.youtube.com/watch?v={video_id}"
    )

    record = {

        "topic_id":
            topic_id,

        "video_id":
            video_id,

        "title":
            title,

        "youtube_url":
            youtube_url,
    }

    record_file.write_text(
        json.dumps(
            record,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("=" * 70)
    print("UPLOAD RECORD SAVED")
    print("=" * 70)

    print(
        f"FILE: {record_file}"
    )

    print(
        f"VIDEO ID: {video_id}"
    )

    print(
        f"URL: {youtube_url}"
    )

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("TELUGU MYSTERY AI — YOUTUBE UPLOADER")
    print("=" * 70)

    # --------------------------------------------------------
    # GET TOPIC
    # --------------------------------------------------------

    topic = get_ready_topic()

    if not topic:

        print(
            "NO PENDING VIDEO + METADATA READY FOR YOUTUBE"
        )

        return

    topic_id = (
        topic["id"].strip()
    )

    topic_title = (
        topic["title"].strip()
    )

    video_file = (
        VIDEOS_DIR
        / f"{topic_id}.mp4"
    )

    metadata_file = (
        METADATA_DIR
        / f"{topic_id}.txt"
    )

    print(
        f"SELECTED TOPIC: {topic_id}"
    )

    print(
        f"TOPIC TITLE: {topic_title}"
    )

    print(
        f"VIDEO: {video_file}"
    )

    print(
        f"METADATA: {metadata_file}"
    )

    print(
        f"STATUS: {topic.get('status', 'pending')}"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # VALIDATE VIDEO
    # --------------------------------------------------------

    validate_video_file(
        video_file
    )

    # --------------------------------------------------------
    # CHECK DUPLICATE UPLOAD
    # --------------------------------------------------------

    existing_record = (
        get_existing_upload_record(
            topic_id
        )
    )

    if existing_record:

        existing_video_id = (
            existing_record["video_id"]
        )

        existing_url = (
            existing_record.get(
                "youtube_url",
                ""
            )
        )

        print("=" * 70)
        print("UPLOAD RECORD ALREADY EXISTS")
        print("=" * 70)

        print(
            f"TOPIC: {topic_id}"
        )

        print(
            f"VIDEO ID: {existing_video_id}"
        )

        print(
            f"URL: {existing_url}"
        )

        print(
            "UPLOAD CANCELLED TO PREVENT DUPLICATE VIDEO."
        )

        print("=" * 70)

        # ----------------------------------------------------
        # If upload record exists but CSV is still pending,
        # mark it completed instead of uploading again.
        # ----------------------------------------------------

        if (
            topic.get(
                "status",
                ""
            ).strip().lower()
            != "completed"
        ):

            print(
                "Synchronizing topics.csv status..."
            )

            mark_topic_completed(
                topic_id
            )

        return

    # --------------------------------------------------------
    # READ METADATA
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # YOUTUBE CLIENT
    # --------------------------------------------------------

    youtube = (
        get_youtube_client()
    )

    # --------------------------------------------------------
    # UPLOAD
    # --------------------------------------------------------

    # IMPORTANT:
    # If upload fails here, execution stops.
    #
    # Therefore:
    # - upload record is NOT created
    # - status is NOT changed to completed
    #
    # This prevents false completion.

    video_id = upload_video(
        youtube,
        video_file,
        metadata
    )

    # --------------------------------------------------------
    # SAVE UPLOAD RECORD
    # --------------------------------------------------------

    save_upload_record(
        topic_id,
        video_id,
        metadata["title"]
    )

    # --------------------------------------------------------
    # MARK COMPLETED
    # --------------------------------------------------------

    mark_topic_completed(
        topic_id
    )

    # --------------------------------------------------------
    # COMPLETE
    # --------------------------------------------------------

    youtube_url = (
        f"https://www.youtube.com/watch?v={video_id}"
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
        f"YOUTUBE URL = {youtube_url}"
    )

    print(
        "NEXT TOPIC CAN BE PROCESSED."
    )

    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
