import os
import csv
import requests
from pathlib import Path

TOPICS_FILE = "topics/topics.csv"


def get_next_topic():
    with open(TOPICS_FILE, "r", encoding="utf-8") as file:
        topics = list(csv.DictReader(file))

    for topic in topics:
        if topic["status"].strip().lower() == "pending":
            return topic

    return None


topic = get_next_topic()

if not topic:
    print("NO PENDING TOPICS")
    exit(0)

topic_id = topic["id"]
topic_title = topic["title"]

print(f"RESEARCHING: {topic_id} - {topic_title}")

api_key = os.environ["OPENROUTER_API_KEY"]

prompt = f"""
You are a factual research assistant for a Telugu YouTube channel.

Research this topic:
{topic_title}

Provide:

1. Confirmed scientific facts
2. Important dates, measurements and numbers
3. Scientific explanations
4. Popular theories
5. What is actually unknown
6. Reliable sources for verification

Rules:
- Do not invent facts.
- Separate confirmed facts from theories.
- If information is uncertain, clearly say so.
- Prefer scientific institutions, universities, government sources,
  research papers and reputable publications.
- This research will later be converted into an original Telugu
  YouTube script.
"""

response = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    },
    json={
        "model": "openrouter/free",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    },
    timeout=120
)

response.raise_for_status()

result = response.json()
answer = result["choices"][0]["message"]["content"]

Path("research").mkdir(exist_ok=True)

output_file = f"research/{topic_id}.txt"

with open(output_file, "w", encoding="utf-8") as file:
    file.write(f"TOPIC: {topic_title}\n\n")
    file.write(answer)

print(f"RESEARCH SAVED: {output_file}")
