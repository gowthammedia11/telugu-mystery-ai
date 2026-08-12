import os
import csv
import requests
from pathlib import Path

TOPICS_FILE = "topics/topics.csv"


def get_latest_researched_topic():
    with open(TOPICS_FILE, "r", encoding="utf-8") as file:
        topics = list(csv.DictReader(file))

    for topic in topics:
        research_file = Path(f"research/{topic['id']}.txt")

        if research_file.exists() and topic["status"].strip().lower() == "pending":
            return topic

    return None


topic = get_latest_researched_topic()

if not topic:
    print("NO RESEARCHED PENDING TOPIC FOUND")
    exit(0)

topic_id = topic["id"]
topic_title = topic["title"]

research = Path(f"research/{topic_id}.txt").read_text(encoding="utf-8")

api_key = os.environ["OPENROUTER_API_KEY"]

prompt = f"""
You are an expert Telugu YouTube scriptwriter.

Create an ORIGINAL Telugu script about:

{topic_title}

Use ONLY the research provided below.

RESEARCH:
{research}

SCRIPT REQUIREMENTS:

- Simple, natural Telugu.
- Interesting enough for YouTube viewers.
- Strong curiosity hook in the first 15 seconds.
- Explain difficult scientific concepts in simple language.
- Clearly distinguish confirmed facts from theories.
- Never present speculation as fact.
- Do not copy sentences from the research.
- Do not mention that AI was used.
- Do not use unnecessary English words.
- Avoid complicated Telugu vocabulary.
- Make the narration smooth and conversational.

Structure:

1. Powerful opening hook
2. Mystery/question
3. Background
4. Scientific facts
5. Main explanation
6. Interesting discoveries
7. What scientists still don't know
8. Final conclusion

Write only the narration.
Do not add scene directions.
Do not add timestamps.
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
script = result["choices"][0]["message"]["content"]

Path("scripts").mkdir(exist_ok=True)

output_file = f"scripts/{topic_id}.txt"

with open(output_file, "w", encoding="utf-8") as file:
    file.write(script)

print(f"SCRIPT SAVED: {output_file}")
