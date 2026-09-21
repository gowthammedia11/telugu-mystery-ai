import base64
import csv
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


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
        return list(csv.DictReader(file))


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
        writer.writerows(topics)


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

        if not topic_id or status == "completed":
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
            candidates.append(topic)

    candidates.sort(
        key=lambda topic: int(
            topic["id"].strip()
        )
    )

    return (
        candidates[0]
        if candidates
        else None
    )


def read_metadata(metadata_file):
    """
    Supports both metadata formats.

    Format 1 - multiline:
        TITLE:
        Title here

        DESCRIPTION:
        Description line 1
        Description line 2

        TAGS:
        tag1, tag2

        HASHTAGS:
        #Shorts #Telugu

    Format 2 - inline:
        TITLE: Title here
        DESCRIPTION: Description here

        TAGS: tag1, tag2
        HASHTAGS: #Shorts #Telugu
    """

    text = metadata_file.read_text(
        encoding="utf-8"
    ).strip()

    if not text:
        raise RuntimeError(
            f"Metadata file is empty: "
            f"{metadata_file}"
        )

    title = ""
    description_lines = []
    tags = []
    hashtags = []

    lines = text.splitlines()

    section = None

    for line in lines:

        stripped = line.strip()

        # ====================================================
        # EMPTY LINE
        # ====================================================

        if not stripped:

            if section == "description":
                description_lines.append("")

            continue

        # ====================================================
        # TITLE
        # Supports:
        # TITLE:
        # TITLE: actual title
        # ====================================================

        title_match = re_match_header(
            stripped,
            "TITLE"
        )

        if title_match is not None:

            value = title_match

            if value:
                title = value
                section = None
            else:
                section = "title"

            continue

        # ====================================================
        # DESCRIPTION
        # Supports multiline description
        # ====================================================

        description_match = re_match_header(
            stripped,
            "DESCRIPTION"
        )

        if description_match is not None:

            value = description_match

            if value:
                description_lines.append(value)

            section = "description"

            continue

        # ====================================================
        # TAGS
        # ====================================================

        tags_match = re_match_header(
            stripped,
            "TAGS"
        )

        if tags_match is not None:

            value = tags_match

            if value:
                tags = [
                    item.strip()
                    for item in value.split(",")
                    if item.strip()
                ]

            section = None

            continue

        # ====================================================
        # HASHTAGS
        # ====================================================

        hashtags_match = re_match_header(
            stripped,
            "HASHTAGS"
        )

        if hashtags_match is not None:

            value = hashtags_match

            if value:
                hashtags = [
                    item.strip()
                    for item in value.split()
                    if item.strip()
                ]

            section = None

            continue

        # ====================================================
        # SECTION CONTENT
        # ====================================================

        if section == "title":

            if stripped:
                title = stripped
                section = None

            continue

        if section == "description":

            description_lines.append(
                line.rstrip()
            )

            continue

        if section == "tags":

            if stripped:
                tags = [
                    item.strip()
                    for item in stripped.split(",")
                    if item.strip()
                ]

            section = None
            continue

        if section == "hashtags":

            if stripped:
                hashtags = [
                    item.strip()
                    for item in stripped.split()
                    if item.strip()
                ]

            section = None
            continue

    # ========================================================
    # DESCRIPTION CLEANUP
    # ========================================================

    description = "\n".join(
        description_lines
    ).strip()

    description = "\n".join(
        line.rstrip()
        for line in description.splitlines()
    ).strip()

    # ========================================================
    # VALIDATION
    # ========================================================

    if not title:
        raise RuntimeError(
            f"TITLE missing in {metadata_file}"
        )

    if not description:
        raise RuntimeError(
            f"DESCRIPTION missing in {metadata_file}"
        )

    # ========================================================
    # ADD HASHTAGS TO DESCRIPTION
    # ========================================================

    if hashtags:

        hashtag_text = " ".join(
            hashtags
        )

        existing_description_lower = (
            description.lower()
        )

        missing_hashtags = []

        for hashtag in hashtags:

            if hashtag.lower() not in existing_description_lower:
                missing_hashtags.append(hashtag)

        if missing_hashtags:

            description = (
                description
                + "\n\n"
                + " ".join(missing_hashtags)
            )

    return (
        title,
        description,
        tags
    )


def re_match_header(
    line,
    header
):
    """
    Returns:
        None  -> line is not this header
        ""    -> exact header such as TITLE:
        value -> inline value such as TITLE: My Title
    """

    pattern = (
        rf"^{header}\s*:\s*(.*)$"
    )

    match = __import__("re").match(
        pattern,
        line,
        flags=__import__("re").IGNORECASE
    )

    if not match:
        return None

    return match.group(1).strip()


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
        ).decode("utf-8")

        token_data = json.loads(
            token_json
        )

    except Exception as error:

        raise RuntimeError(
            f"Invalid YOUTUBE_TOKEN_B64: {error}"
        )

    credentials = (
        Credentials.from_authorized_user_info(
            token_data,
            YOUTUBE_SCOPES
        )
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

    # ========================================================
    # SHORT HANDLING
    # ========================================================

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

    # ========================================================
    # YOUTUBE BODY
    # ========================================================

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

            "privacyStatus":
                YOUTUBE_PRIVACY_STATUS,

            "selfDeclaredMadeForKids":
                False,
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

    print(
        f"FILE: {video_file}"
    )

    print(
        f"METADATA: {metadata_file}"
    )

    print(
        f"TITLE: {title}"
    )

    print("PRIVACY: public")

    print(
        f"FILE SIZE: "
        f"{video_file.stat().st_size / (1024 * 1024):.2f} MB"
    )

    # ========================================================
    # UPLOAD REQUEST
    # ========================================================

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
                f"UPLOAD PROGRESS: "
                f"{progress}%"
            )

    # ========================================================
    # VIDEO ID
    # ========================================================

    video_id = response.get("id")

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

    record_file = (
        upload_record_file(
            topic_id,
            suffix
        )
    )

    record = {

        "topic_id":
            topic_id,

        "youtube_video_id":
            video_id,

        "video_file":
            str(video_file),

        "type":
            (
                "short"
                if is_short
                else "long"
            ),

        "privacy_status":
            "public",

        "uploaded":
            True,

        "uploaded_at_ist":
            datetime.now(
                IST
            ).strftime(
                "%Y-%m-%d %H:%M:%S IST"
            ),
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

    record_file = (
        upload_record_file(
            topic_id,
            suffix
        )
    )

    if not record_file.exists():
        return None

    try:

        data = json.loads(
            record_file.read_text(
                encoding="utf-8"
            )
        )

        if data.get("uploaded"):
            return data.get(
                "youtube_video_id"
            )

    except Exception as error:

        print(
            f"WARNING: Unable to read "
            f"upload record {record_file}: "
            f"{error}"
        )

        return None

    return None


def mark_topic_completed(
    topic_id
):

    topics = load_topics()

    long_id = (
        existing_upload_id(
            topic_id,
            False
        )
    )

    short_id = (
        existing_upload_id(
            topic_id,
            True
        )
    )

    # ========================================================
    # BOTH UPLOADS REQUIRED
    # ========================================================

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

            topic["status"] = "completed"

            found = True

            break

    if not found:
        raise RuntimeError(
            f"Topic {topic_id} not found "
            "while marking completed"
        )

    save_topics(topics)

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

    existing_id = (
        existing_upload_id(
            topic_id,
            is_short
        )
    )

    # ========================================================
    # ALREADY UPLOADED
    # ========================================================

    if existing_id:

        print("=" * 70)

        if is_short:
            print("SHORT ALREADY UPLOADED")
        else:
            print("LONG VIDEO ALREADY UPLOADED")

        print(
            f"YOUTUBE VIDEO ID: "
            f"{existing_id}"
        )

        print("=" * 70)

        return existing_id

    # ========================================================
    # FILE VALIDATION
    # ========================================================

    if not video_file.exists():
        raise RuntimeError(
            f"Video file missing: "
            f"{video_file}"
        )

    if video_file.stat().st_size <= 0:
        raise RuntimeError(
            f"Video file is empty: "
            f"{video_file}"
        )

    if not metadata_file.exists():
        raise RuntimeError(
            f"Metadata file missing: "
            f"{metadata_file}"
        )

    if metadata_file.stat().st_size <= 0:
        raise RuntimeError(
            f"Metadata file is empty: "
            f"{metadata_file}"
        )

    # ========================================================
    # UPLOAD
    # ========================================================

    video_id = upload_video(
        youtube,
        video_file,
        metadata_file,
        is_short=is_short
    )

    # ========================================================
    # SAVE RECORD IMMEDIATELY
    # ========================================================

    save_upload_record(
        topic_id,
        video_id,
        video_file,
        is_short
    )

    return video_id


def main():

    print("=" * 70)
    print(
        "TELUGU MYSTERY AI — YOUTUBE UPLOAD"
    )
    print("=" * 70)

    topic = get_ready_topic()

    if not topic:

        print(
            "NO TOPIC READY FOR YOUTUBE UPLOAD"
        )

        return

    topic_id = (
        topic["id"].strip()
    )

    topic_title = (
        topic["title"].strip()
    )

    print(
        f"TOPIC: {topic_id}"
    )

    print(
        f"TITLE: {topic_title}"
    )

    print(
        "CURRENT IST:",
        datetime.now(
            IST
        ).strftime(
            "%Y-%m-%d %H:%M:%S IST"
        )
    )

    # ========================================================
    # FILE PATHS
    # ========================================================

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

    # ========================================================
    # VALIDATE ALL REQUIRED FILES
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
                f"Required file missing: "
                f"{file}"
            )

        if file.stat().st_size <= 0:
            raise RuntimeError(
                f"Required file is empty: "
                f"{file}"
            )

    # ========================================================
    # VALIDATE LONG METADATA
    # ========================================================

    print("=" * 70)
    print("VALIDATING LONG METADATA")
    print("=" * 70)

    long_title, long_description, long_tags = (
        read_metadata(
            long_metadata
        )
    )

    print(
        f"LONG TITLE: {long_title}"
    )

    print(
        f"LONG DESCRIPTION CHARACTERS: "
        f"{len(long_description)}"
    )

    print(
        f"LONG TAGS: {len(long_tags)}"
    )

    # ========================================================
    # VALIDATE SHORT METADATA
    # ========================================================

    print("=" * 70)
    print("VALIDATING SHORT METADATA")
    print("=" * 70)

    short_title, short_description, short_tags = (
        read_metadata(
            short_metadata
        )
    )

    print(
        f"SHORT TITLE: {short_title}"
    )

    print(
        f"SHORT DESCRIPTION CHARACTERS: "
        f"{len(short_description)}"
    )

    print(
        f"SHORT TAGS: {len(short_tags)}"
    )

    # ========================================================
    # YOUTUBE CLIENT
    # ========================================================

    youtube = get_youtube()

    # ========================================================
    # LONG VIDEO
    # ========================================================

    print("=" * 70)
    print("STARTING LONG VIDEO UPLOAD")
    print("=" * 70)

    long_video_id = (
        upload_one_if_needed(
            youtube,
            topic_id,
            long_video,
            long_metadata,
            is_short=False
        )
    )

    print(
        f"LONG VIDEO READY: "
        f"{long_video_id}"
    )

    # ========================================================
    # SHORT
    # ========================================================

    print("=" * 70)
    print("STARTING SHORT UPLOAD")
    print("=" * 70)

    short_video_id = (
        upload_one_if_needed(
            youtube,
            topic_id,
            short_video,
            short_metadata,
            is_short=True
        )
    )

    print(
        f"SHORT READY: "
        f"{short_video_id}"
    )

    # ========================================================
    # MARK COMPLETED ONLY AFTER BOTH
    # ========================================================

    mark_topic_completed(
        topic_id
    )

    # ========================================================
    # FINAL
    # ========================================================

    print("=" * 70)
    print("BOTH VIDEOS UPLOADED SUCCESSFULLY")
    print("=" * 70)

    print(
        f"TOPIC: {topic_id}"
    )

    print(
        f"LONG VIDEO ID: "
        f"{long_video_id}"
    )

    print(
        f"SHORT VIDEO ID: "
        f"{short_video_id}"
    )

    print("LONG PRIVACY: public")
    print("SHORT PRIVACY: public")
    print("STATUS: completed")

    print("=" * 70)


if __name__ == "__main__":
    main()
