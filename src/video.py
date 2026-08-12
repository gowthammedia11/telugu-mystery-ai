import csv
from pathlib import Path


TOPICS_FILE = "topics/topics.csv"


def get_voiced_topic():
    with open(TOPICS_FILE, "r", encoding="utf-8") as file:
        topics = list(csv.DictReader(file))

    for topic in topics:
        topic_id = topic["id"]
        audio_file = Path(f"audio/{topic_id}.mp3")
        script_file = Path(f"scripts/{topic_id}.txt")

        if (
            topic["status"].strip().lower() == "voiced"
            and audio_file.exists()
            and script_file.exists()
        ):
            return topic

    return None


topic = get_voiced_topic()

if not topic:
    print("NO VOICED TOPIC READY FOR VIDEO")
    exit(0)

topic_id = topic["id"]

print(f"VIDEO READY TO BUILD: {topic_id}")
print(f"SCRIPT: scripts/{topic_id}.txt")
print(f"AUDIO: audio/{topic_id}.mp3")

Path("videos").mkdir(exist_ok=True)

print("VIDEO ENGINE TEST PASSED")
