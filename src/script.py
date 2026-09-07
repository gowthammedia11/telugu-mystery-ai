import os
import csv
import time
import requests
from pathlib import Path


TOPICS_FILE = Path("topics/topics.csv")
RESEARCH_DIR = Path("research")
SCRIPTS_DIR = Path("scripts")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openrouter/free"

MIN_SCRIPT_LENGTH = 1000
MAX_SCRIPT_ATTEMPTS = 3


# ============================================================
# LOAD TOPICS
# ============================================================

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

        return list(
            csv.DictReader(file)
        )


# ============================================================
# GET EXACT TOPIC
# ============================================================

def get_topic_by_id(topic_id):

    topic_id = str(topic_id).strip()

    topics = load_topics()

    for topic in topics:

        if topic["id"].strip() == topic_id:
            return topic

    raise ValueError(
        f"Topic ID not found: {topic_id}"
    )


# ============================================================
# GENERATE SCRIPT
# ============================================================

def generate_script(
    topic_id,
    topic_title,
    research,
    attempt=1
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
for a Telugu mystery and science YouTube channel.

TOPIC ID:
{topic_id}

TOPIC:
{topic_title}

============================================================
RESEARCH MATERIAL
============================================================

{research}

============================================================
STRICT FACTUAL RULES
============================================================

1. Use ONLY information supported by the research.
2. NEVER invent facts.
3. NEVER invent dates.
4. NEVER invent measurements.
5. NEVER invent scientific discoveries.
6. Clearly distinguish facts from theories.
7. Never present speculation as confirmed fact.
8. Do not exaggerate the mystery.
9. Do not create fictional events.
10. Do not create fake quotations.
11. Do not create fake sources.
12. Do not mention AI.
13. Do not mention this research material.
14. Do not mention these instructions.

============================================================
TELUGU STYLE
============================================================

Write natural conversational Telugu.

The narration should sound like a professional
Telugu YouTube documentary.

Use easy Telugu that a general audience can understand.

Scientific terms may use natural Telugu pronunciation
when a direct Telugu translation sounds unnatural.

Avoid unnecessary English words.

============================================================
YEAR AND NUMBER RULES
============================================================

Years must be written naturally in Telugu words.

Examples:

1990 → పంతొమ్మిది వందల తొంభై

1995 → పంతొమ్మిది వందల తొంభై ఐదు

2002 → రెండు వేల రెండు

2014 → రెండు వేల పద్నాలుగు

2016 → రెండు వేల పదహారు

2020 → రెండు వేల ఇరవై

2026 → రెండు వేల ఇరవై ఆరు

Never pronounce years digit by digit.

For important numbers, use natural Telugu words
whenever practical.

============================================================
STORY FLOW
============================================================

Write ONE continuous narration.

Do not use headings.

Do not use bullet points.

Do not use numbered sections.

Do not use scene directions.

Do not use timestamps.

The narration should naturally include:

1. A powerful curiosity-driven opening.
2. The central mystery or question.
3. Background information.
4. Confirmed facts.
5. Important dates.
6. Important measurements and evidence.
7. Scientific explanation.
8. Major discoveries.
9. Popular theories, clearly identified as theories.
10. What scientists actually know.
11. What remains unknown.
12. A strong memorable conclusion.

============================================================
LENGTH REQUIREMENT
============================================================

IMPORTANT:

Write a FULL-LENGTH YouTube documentary narration.

The script must NOT be a short summary.

Target approximately 1800 to 3000 Telugu words
when the research supports that amount.

Include enough detail to create a substantial
YouTube video.

Do not stop after the introduction.

Do not return a brief answer.

Write the entire narration from beginning to conclusion.

ONLY return the final Telugu narration.
"""

    print("=" * 70)
    print(
        f"SCRIPT GENERATION ATTEMPT: {attempt}"
    )
    print("=" * 70)

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
                    "content": (
                        "You are a professional Telugu "
                        "documentary writer. "
                        "Return a long, detailed, "
                        "factually accurate narration. "
                        "Never invent information."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],

            "temperature": 0.45,

            # Important:
            # Give the model enough output budget.
            "max_tokens": 4000,
        },

        timeout=240,
    )

    response.raise_for_status()

    result = response.json()

    choices = result.get(
        "choices",
        []
    )

    if not choices:

        raise RuntimeError(
            "OpenRouter returned no choices"
        )

    message = choices[0].get(
        "message",
        {}
    )

    script = message.get(
        "content",
        ""
    )

    if not script:

        raise RuntimeError(
            "OpenRouter returned empty script"
        )

    script = script.strip()

    print(
        f"GENERATED SCRIPT CHARACTERS: "
        f"{len(script)}"
    )

    return script


# ============================================================
# CLEAN SCRIPT
# ============================================================

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

        # Remove accidental markdown headings.
        if line.startswith("#"):

            line = line.lstrip(
                "#"
            ).strip()

        # Remove accidental section markers.
        if line in {
            "HOOK",
            "MYSTERY",
            "BACKGROUND",
            "FACTS",
            "EXPLANATION",
            "DISCOVERIES",
            "UNKNOWN",
            "UNKNOWNS",
            "CONCLUSION",
        }:
            continue

        lines.append(line)

    return "\n".join(
        lines
    ).strip()


# ============================================================
# SAVE SCRIPT
# ============================================================

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


# ============================================================
# MAIN PIPELINE STEP
# ============================================================

def run(topic_id):

    topic = get_topic_by_id(
        topic_id
    )

    topic_id = topic["id"].strip()
    topic_title = topic["title"].strip()

    research_file = (
        RESEARCH_DIR /
        f"{topic_id}.txt"
    )

    script_file = (
        SCRIPTS_DIR /
        f"{topic_id}.txt"
    )

    print("=" * 70)
    print("TELUGU MYSTERY AI - SCRIPT")
    print("=" * 70)

    print(
        f"TOPIC ID: {topic_id}"
    )

    print(
        f"TOPIC TITLE: {topic_title}"
    )

    print(
        f"RESEARCH FILE: {research_file}"
    )

    print(
        f"SCRIPT FILE: {script_file}"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # EXISTING VALID SCRIPT
    # --------------------------------------------------------

    if (
        script_file.exists()
        and script_file.stat().st_size >= MIN_SCRIPT_LENGTH
    ):

        print(
            "VALID SCRIPT ALREADY EXISTS."
        )

        print(
            f"Using existing script: {script_file}"
        )

        return script_file

    # --------------------------------------------------------
    # RESEARCH REQUIRED
    # --------------------------------------------------------

    if not research_file.exists():

        raise RuntimeError(
            f"Research file not found: "
            f"{research_file}"
        )

    research = research_file.read_text(
        encoding="utf-8"
    ).strip()

    if not research:

        raise RuntimeError(
            "Research file is empty"
        )

    print(
        f"RESEARCH CHARACTERS: "
        f"{len(research)}"
    )

    # --------------------------------------------------------
    # GENERATE WITH RETRIES
    # --------------------------------------------------------

    last_error = None

    for attempt in range(
        1,
        MAX_SCRIPT_ATTEMPTS + 1
    ):

        try:

            script = generate_script(
                topic_id,
                topic_title,
                research,
                attempt
            )

            script = clean_script(
                script
            )

            print(
                f"CLEAN SCRIPT CHARACTERS: "
                f"{len(script)}"
            )

            # ------------------------------------------------
            # LENGTH VALIDATION
            # ------------------------------------------------

            if len(script) < MIN_SCRIPT_LENGTH:

                last_error = (
                    "Generated script is too short: "
                    f"{len(script)} characters"
                )

                print(
                    last_error
                )

                if attempt < MAX_SCRIPT_ATTEMPTS:

                    print(
                        "Retrying script generation..."
                    )

                    time.sleep(3)

                    continue

                raise RuntimeError(
                    last_error
                )

            # ------------------------------------------------
            # SAVE
            # ------------------------------------------------

            output_file = save_script(
                topic_id,
                script
            )

            # ------------------------------------------------
            # VERIFY
            # ------------------------------------------------

            if not output_file.exists():

                raise RuntimeError(
                    "Script file was not created"
                )

            file_size = (
                output_file.stat().st_size
            )

            if file_size < 1000:

                raise RuntimeError(
                    "Saved script file is too small"
                )

            print("=" * 70)
            print("TELUGU SCRIPT CREATED SUCCESSFULLY")
            print("=" * 70)

            print(
                f"FILE: {output_file}"
            )

            print(
                f"CHARACTERS: {len(script)}"
            )

            print(
                f"SIZE: {file_size} bytes"
            )

            print("=" * 70)

            return output_file

        except Exception as error:

            last_error = error

            print(
                f"SCRIPT ATTEMPT {attempt} FAILED:"
            )

            print(
                f"{error}"
            )

            if attempt < MAX_SCRIPT_ATTEMPTS:

                print(
                    "Retrying..."
                )

                time.sleep(3)

            else:

                raise RuntimeError(
                    f"Script generation failed after "
                    f"{MAX_SCRIPT_ATTEMPTS} attempts: "
                    f"{last_error}"
                )


if __name__ == "__main__":

    topic_id = os.environ.get(
        "PIPELINE_TOPIC_ID"
    )

    if not topic_id:

        raise SystemExit(
            "PIPELINE_TOPIC_ID is required"
        )

    run(topic_id)
