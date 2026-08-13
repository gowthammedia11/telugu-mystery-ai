import os
import json
import base64
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


# ============================================================
# GET TOPIC
# ============================================================

TOPIC_ID = os.environ.get("TOPIC_ID", "003")

VIDEO_FILE = Path(
    f"videos/{TOPIC_ID}.mp4"
)

THUMBNAIL_FILE = Path(
    f"thumbnails/{TOPIC_ID}.jpg"
)

TITLE = os.environ.get(
    "YOUTUBE_TITLE",
    f"Antarctica Ice Mystery | Telugu Mystery"
)

DESCRIPTION = os.environ.get(
    "YOUTUBE_DESCRIPTION",
    """Antarctica Ice Mystery

Antarctica gurinchi scientifically verified facts, mysteries and unknowns ni ee video lo telusukundam.

#Antarctica #Mystery #Telugu #TeluguMystery #Science"""
)

TAGS = [
    "Telugu Mystery",
    "Antarctica",
    "Antarctica Mystery",
    "Mystery",
    "Science",
    "Telugu",
    "Telugu Science",
    "Mystery Telugu",
    "Antarctica Telugu"
]


# ============================================================
# CHECK VIDEO
# ============================================================

if not VIDEO_FILE.exists():

    raise Exception(
        f"VIDEO NOT FOUND: {VIDEO_FILE}"
    )

print("=" * 70)
print("YOUTUBE UPLOAD")
print("=" * 70)

print(
    f"VIDEO: {VIDEO_FILE}"
)

print(
    f"TITLE: {TITLE}"
)


# ============================================================
# YOUTUBE TOKEN
# ============================================================

TOKEN_B64 = os.environ[
    "YOUTUBE_TOKEN_B64"
]

token_json = base64.b64decode(
    TOKEN_B64
).decode("utf-8")

token_data = json.loads(
    token_json
)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload"
]

credentials = (
    Credentials.from_authorized_user_info(
        token_data,
        SCOPES
    )
)

youtube = build(
    "youtube",
    "v3",
    credentials=credentials
)


# ============================================================
# VIDEO METADATA
# ============================================================

body = {

    "snippet": {

        "title": TITLE,

        "description": DESCRIPTION,

        "tags": TAGS,

        "categoryId": "27",

        "defaultLanguage": "te",

        "defaultAudioLanguage": "te"
    },

    "status": {

        # PUBLIC
        "privacyStatus": "public",

        "selfDeclaredMadeForKids": False,

        "license": "youtube"
    }
}


# ============================================================
# UPLOAD VIDEO
# ============================================================

media = MediaFileUpload(
    str(VIDEO_FILE),
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

    status, response = (
        request.next_chunk()
    )

    if status:

        print(
            "UPLOAD PROGRESS:",
            f"{int(status.progress() * 100)}%"
        )


# ============================================================
# VERIFY
# ============================================================

video_id = response["id"]

print("=" * 70)
print("VIDEO UPLOAD SUCCESS")
print("=" * 70)

print(
    "VIDEO ID:",
    video_id
)

print(
    "VIDEO URL:",
    f"https://www.youtube.com/watch?v={video_id}"
)

print(
    "PRIVACY:",
    response["status"]["privacyStatus"]
)


# ============================================================
# THUMBNAIL
# ============================================================

if THUMBNAIL_FILE.exists():

    print("=" * 70)
    print("UPLOADING THUMBNAIL")
    print("=" * 70)

    thumbnail_media = MediaFileUpload(
        str(THUMBNAIL_FILE),
        mimetype="image/jpeg"
    )

    thumbnail_response = (
        youtube.thumbnails()
        .set(
            videoId=video_id,
            media_body=thumbnail_media
        )
        .execute()
    )

    print(
        "THUMBNAIL UPLOADED SUCCESSFULLY"
    )

else:

    print(
        "THUMBNAIL NOT FOUND:"
        f" {THUMBNAIL_FILE}"
    )

    print(
        "VIDEO WILL REMAIN WITHOUT CUSTOM THUMBNAIL"
    )


print("=" * 70)
print("YOUTUBE PUBLISHING COMPLETE")
print("=" * 70)
