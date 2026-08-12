import csv
import asyncio
from pathlib import Path
import edge_tts


TOPICS_FILE = "topics/topics.csv"


def get_next_script():
    with open(TOPICS_FILE, "r", encoding="utf-8") as file:
        topics = list(csv.DictReader(file))

    for topic in topics:
        topic_id = topic["id"]
        script_file = Path(f"scripts/{topic_id}.txt")

        if script_file.exists() and topic["status"].strip().lower() == "pending":
            return topic

    return None


async def generate_voice(topic_id):
    script_file = Path(f"scripts/{topic_id}.txt")
    output_file = Path(f"audio/{topic_id}.mp3")

    text = script_file.read_text(encoding="utf-8").strip()

    if not text:
        raise Exception("Script is empty")

    Path("audio").mkdir(exist_ok=True)

    voice = "te-IN-MohanNeural"

    print(f"Generating Telugu voice for topic {topic_id}...")
    print(f"Voice: {voice}")

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate="+0%",
        volume="+0%"
    )

    await communicate.save(str(output_file))

    print(f"VOICE CREATED: {output_file}")


topic = get_next_script()

if not topic:
    print("NO SCRIPT READY FOR VOICE")
    exit(0)

topic_id = topic["id"]

asyncio.run(generate_voice(topic_id))
