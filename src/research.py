import csv
import os
import time
from pathlib import Path

import requests

TOPICS_FILE = Path("topics/topics.csv")
RESEARCH_DIR = Path("research")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openrouter/free"


def load_topics():
    if not TOPICS_FILE.exists():
        raise FileNotFoundError(f"Topics file not found: {TOPICS_FILE}")
    with TOPICS_FILE.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def save_research(topic_id, topic_title, research):
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    output = RESEARCH_DIR / f"{topic_id}.txt"
    content = research.strip()
    if not content:
        raise RuntimeError("Research result is empty")
    output.write_text(content, encoding="utf-8")
    print(f"RESEARCH SAVED: {output}")
    return output


def research_topic(topic_id, topic_title):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY secret is missing")

    prompt = f"""
You are a rigorous factual research assistant for a Telugu mystery/science YouTube channel.

TOPIC ID: {topic_id}
TOPIC: {topic_title}

Create a detailed research brief for a later Telugu scriptwriter.

Rules:
1. Use only well-established, defensible factual information.
2. Never invent facts, dates, measurements, discoveries, quotes, people, or statistics.
3. Clearly separate confirmed facts from hypotheses, disputed claims, legends, or speculation.
4. Include important dates and measurements when they are genuinely relevant.
5. Explain the scientific mechanism in simple language.
6. Include the strongest evidence and what remains unknown.
7. If a popular claim is false or unsupported, explicitly say so.
8. Do not write a YouTube script.
9. Do not use dramatic filler.
10. Do not cite imaginary sources.
11. Prefer primary scientific institutions, peer-reviewed research, government agencies, universities, and established reference material when naming sources.
12. End with a short list of useful source names/URLs that a human can verify.

Return a structured research brief with these sections:
- Topic overview
- Confirmed facts
- Timeline / important dates
- Measurements / numbers
- Scientific explanation
- Evidence
- Competing theories or explanations
- What is still unknown
- Common myths / misinformation
- Sources to verify
""".strip()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "Telugu Mystery AI Research",
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a careful factual research assistant. "
                    "Never fabricate information. Clearly label uncertainty."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    last_error = None
    for attempt in range(1, 4):
        try:
            print(f"RESEARCH API ATTEMPT: {attempt}/3")
            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=240,
            )
            response.raise_for_status()
            result = response.json()
            choices = result.get("choices") or []
            if not choices:
                raise RuntimeError("OpenRouter returned no research choices")

            content = (choices[0].get("message") or {}).get("content", "")
            if not content or not content.strip():
                raise RuntimeError("OpenRouter returned empty research")

            return content.strip()
        except Exception as error:
            last_error = error
            print(f"RESEARCH ATTEMPT FAILED: {error}")
            if attempt < 3:
                time.sleep(5 * attempt)

    raise RuntimeError(f"Research failed after 3 attempts: {last_error}")


if __name__ == "__main__":
    topics = load_topics()
    candidates = [t for t in topics if t.get("status", "").strip().lower() != "completed"]
    candidates.sort(key=lambda t: int(t["id"].strip()))
    if not candidates:
        raise SystemExit("NO TOPICS AVAILABLE")
    topic = candidates[0]
    research = research_topic(topic["id"].strip(), topic["title"].strip())
    save_research(topic["id"].strip(), topic["title"].strip(), research)
