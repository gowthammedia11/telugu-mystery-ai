import os
import json
import base64

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


VIDEO_FILE = "videos/003.mp4"

TITLE = "Antarctica Ice Mystery | Telugu Mystery"
DESCRIPTION = """Antarctica Ice Mystery

Antarctica gurinchi scientifically verified facts, mysteries and unknowns ni ee video lo telusukundam.

#Antarctica #Mystery #Telugu #TeluguMystery #Science"""

TOKEN_B64 = os.environ["YOUTUBE_TOKEN_B64"]

token_json = base64.b64decode(TOKEN_B64).decode("utf-8")
token_data = json.loads(token_json)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

credentials = Credentials.from_authorized_user_info(
    token_data,
    SCOPES
)

youtube = build("youtube", "v3", credentials=credentials)

body = {
    "snippet": {
        "title": TITLE,
        "description": DESCRIPTION,
        "tags": [
            "Telugu Mystery",
            "Antarctica",
            "Mystery",
            "Science",
            "Telugu"
        ],
        "categoryId": "27"
    },
    "status": {
        "privacyStatus": "private",
        "selfDeclaredMadeForKids": False
    }
}

media = MediaFileUpload(
    VIDEO_FILE,
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
        print(
            f"UPLOAD PROGRESS: {int(status.progress() * 100)}%"
        )

print("YOUTUBE UPLOAD SUCCESS")
print("VIDEO ID:", response["id"])
print("VIDEO URL:", f"https://www.youtube.com/watch?v={response['id']}")
