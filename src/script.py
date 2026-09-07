import os
import csv
import requests
from pathlib import Path


TOPICS_FILE = Path("topics/topics.csv")
RESEARCH_DIR = Path("research")
SCRIPTS_DIR = Path("scripts")

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

    for topic in load_topics():

        if topic["id"].strip() == topic_id:
            return topic

    raise ValueError(
        f"Topic ID not found: {topic_id}"
    )


def generate_script(
    topic_id,
    topic_title,
    research
):

    api_key = os.environ.get(
        "OPENROUTER_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY secret is missing"
        )

    prompt = f"""
You are an expert Telugu YouTube documentary
scriptwriter.

Create a completely ORIGINAL Telugu narration
for a mystery/science YouTube channel.

TOPIC ID:
{topic_id}

TOPIC:
{topic_title}

============================================================
RESEARCH MATERIAL
============================================================

{research}

============================================================
SCRIPT REQUIREMENTS
============================================================

Write the script in natural, conversational Telugu.

The narration should sound like a professional
Telugu YouTube documentary.

IMPORTANT:

1. Use ONLY information supported by the research.
2. NEVER invent facts.
3. NEVER invent dates, measurements or discoveries.
4. Clearly distinguish confirmed facts from theories.
5. Never present speculation as confirmed fact.
6. Do not copy sentences from the research.
7. Rewrite everything in original language.
8. Do not mention AI.
9. Do not mention the research material.
10. Do not mention sources inside the narration.
11. Do not use scene directions.
12. Do not use timestamps.
13. Do not use headings.
14. Do not use bullet points.
15. Write ONLY the final narration.
16. Keep the language easy for a general Telugu audience.
17. Avoid unnecessary English words.

IMPORTANT:

Years must be written in natural Telugu words.

1990 → పంతొమ్మిది వందల తొంభై
2002 → రెండు వేల రెండు
2014 → రెండు వేల పద్నాలుగు
2016 → రెండు వేల పదహారు
2020 → రెండు వేల ఇరవై

DO NOT write years digit-by-digit.

For other important numbers,
write naturally in Telugu words whenever practical.

The narration should naturally contain:

Powerful opening hook.
Central mystery/question.
Background.
Confirmed scientific facts.
Scientific explanation.
Important discoveries.
Major evidence.
What scientists still don't know.
Theories clearly identified as theories.
Strong conclusion.

Do not explicitly label these sections.

Start with strong curiosity.
Use short and medium sentences.
Create natural pauses using punctuation.
Do not exaggerate beyond the evidence.
End with a memorable conclusion.

Write ONLY the Telugu narration.
"""

    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization":
                f"Bearer {api_key}",
            "Content-Type":
                "application/json",
            "HTTP-Referer":
                "https://github.com/",
            "X-Title":
                "Telugu Mystery AI",
        },
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content":
                        (
                            "You are a highly accurate Telugu "
                            "documentary scriptwriter. "
                            "Never invent factual information."
                        ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.55,
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

    script = (
        choices[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )

    if not script:
        raise RuntimeError(
            "OpenRouter returned empty script"
        )

    return script


def clean_script(script):

    script = script.replace(
        "```text",
        ""
    )

    script = script.replace(
        "```",
        ""
    )

    lines = []

    for line in script.splitlines():

        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            line = line.lstrip("#").strip()

        lines.append(line)

    return "\n".join(lines).strip()


def save_script(
    topic_id,
    script
):

    SCRIPTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        SCRIPTS_DIR /
        f"{topic_id}.txt"
    )

    output_file.write_text(
        script,
        encoding="utf-8"
    )

    return output_file


def run(topic_id):

    topic = get_topic_by_id(topic_id)

    topic_id = topic["id"].strip()
    topic_title = topic["title"].strip()

    research_file = (
        RESEARCH_DIR /
        f"{topic_id}.txt"
    )

    output_file = (
        SCRIPTS_DIR /
        f"{topic_id}.txt"
    )

    if not research_file.exists():
        raise RuntimeError(
            f"Research not found: {research_file}"
        )

    if output_file.exists() and output_file.stat().st_size >= 500:
        print(
            f"SCRIPT ALREADY EXISTS: {output_file}"
        )
        return output_file

    research = research_file.read_text(
        encoding="utf-8"
    ).strip()

    if not research:
        raise RuntimeError(
            "Research file is empty"
        )

    script = generate_script(
        topic_id,
        topic_title,
        research
    )

    script = clean_script(script)

    if len(script) < 500:
        raise RuntimeError(
            "Generated script is suspiciously short"
        )

    output_file = save_script(
        topic_id,
        script
    )

    print(
        f"SCRIPT CREATED: {output_file}"
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
