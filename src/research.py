import os
import csv
import requests
from pathlib import Path


TOPICS_FILE = Path("topics/topics.csv")
RESEARCH_DIR = Path("research")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openrouter/free"


def load_topics():
    if not TOPICS_FILE.exists():
        raise FileNotFoundError(
            f"Topics file not found: {TOPICS_FILE}"
        )

    with TOPICS_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        return list(csv.DictReader(file))


def get_topic_by_id(topic_id):
    topic_id = str(topic_id).strip()

    topics = load_topics()

    for topic in topics:
        if topic["id"].strip() == topic_id:
            return topic

    raise ValueError(
        f"Topic ID not found: {topic_id}"
    )


def research_topic(topic_id, topic_title):

    api_key = os.environ.get(
        "OPENROUTER_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY secret is missing"
        )

    prompt = f"""
You are a professional factual research assistant
for a Telugu mystery and science YouTube channel.

TOPIC ID:
{topic_id}

TOPIC:
{topic_title}

Research this topic deeply and accurately.

The research will later be converted into an
original Telugu YouTube documentary script.

IMPORTANT RULES:

1. NEVER invent facts.
2. NEVER fabricate dates, measurements,
   scientific findings or quotations.
3. Clearly distinguish:
   CONFIRMED FACTS
   SCIENTIFIC EXPLANATIONS
   THEORIES / HYPOTHESES
   WHAT REMAINS UNKNOWN
4. If a claim is disputed or uncertain,
   explicitly say that it is uncertain.
5. Prefer authoritative sources and scientific
   institutions.
6. Include exact dates when relevant.
7. Include important measurements and numbers.
8. Explain scientific concepts simply.
9. Do not write a fictional story.
10. Do not exaggerate the mystery.
11. Do not present theories as facts.
12. Do not create fake sources.

STRUCTURE THE RESEARCH AS:

TITLE

1. OVERVIEW

2. CONFIRMED FACTS

3. IMPORTANT DATES

4. IMPORTANT NUMBERS AND MEASUREMENTS

5. SCIENTIFIC EXPLANATION

6. MAJOR DISCOVERIES

7. POPULAR THEORIES

8. WHAT SCIENTISTS ACTUALLY KNOW

9. WHAT REMAINS UNKNOWN

10. POSSIBLE EXPLANATIONS

11. SOURCE / VERIFICATION NOTES

For every important factual claim,
include enough information to allow later verification.

This is research material only.
Do not write the final YouTube script.
"""

    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/",
            "X-Title": "Telugu Mystery AI",
        },
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a careful factual research "
                        "assistant. Accuracy is more important "
                        "than creativity."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.2,
        },
        timeout=180,
    )

    response.raise_for_status()

    result = response.json()

    choices = result.get("choices", [])

    if not choices:
        raise RuntimeError(
            "OpenRouter returned no choices"
        )

    answer = (
        choices[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )

    if not answer:
        raise RuntimeError(
            "OpenRouter returned empty research"
        )

    return answer


def save_research(
    topic_id,
    topic_title,
    research
):

    RESEARCH_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        RESEARCH_DIR /
        f"{topic_id}.txt"
    )

    content = (
        f"TOPIC ID: {topic_id}\n"
        f"TOPIC: {topic_title}\n"
        f"RESEARCH STATUS: COMPLETED\n"
        f"{'=' * 70}\n\n"
        f"{research}\n"
    )

    output_file.write_text(
        content,
        encoding="utf-8"
    )

    return output_file


def run(topic_id):

    topic = get_topic_by_id(topic_id)

    topic_id = topic["id"].strip()
    topic_title = topic["title"].strip()

    output_file = (
        RESEARCH_DIR /
        f"{topic_id}.txt"
    )

    print("=" * 70)
    print("RESEARCH STEP")
    print(f"TOPIC: {topic_id}")
    print(f"TITLE: {topic_title}")
    print("=" * 70)

    # Resume protection
    if output_file.exists() and output_file.stat().st_size >= 500:
        print(
            f"RESEARCH ALREADY EXISTS: {output_file}"
        )
        return output_file

    research = research_topic(
        topic_id,
        topic_title
    )

    output_file = save_research(
        topic_id,
        topic_title,
        research
    )

    if output_file.stat().st_size < 500:
        raise RuntimeError(
            "Research file is suspiciously small"
        )

    print(
        f"RESEARCH CREATED: {output_file}"
    )

    return output_file


if __name__ == "__main__":

    topic_id = os.environ.get(
        "PIPELINE_TOPIC_ID"
    )

    if not topic_id:
        raise SystemExit(
            "PIPELINE_TOPIC_ID is required"
        )

    run(topic_id)
