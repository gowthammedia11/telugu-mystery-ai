import csv
import subprocess
from pathlib import Path


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


topic = get_next_script()

if not topic:
    print("NO SCRIPT READY FOR VOICE")
    exit(0)

topic_id = topic["id"]
script_file = Path(f"scripts/{topic_id}.txt")
text = script_file.read_text(encoding="utf-8")

Path("audio").mkdir(exist_ok=True)

text_file = Path(f"audio/{topic_id}_text.txt")
text_file.write_text(text, encoding="utf-8")

output_file = Path(f"audio/{topic_id}.wav")

print(f"VOICE GENERATION STARTED: {topic_id}")

# Temporary test command.
# Actual Telugu TTS engine will be installed in the workflow next.
subprocess.run(
    [
        "python",
        "-c",
        "print('Telugu TTS test started successfully')"
    ],
    check=True
)

print(f"VOICE TARGET: {output_file}")
