import csv
import json
import os
import re
import requests
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

TOPICS_FILE = Path("topics/topics.csv")
RESEARCH_DIR = Path("research")
SCRIPTS_DIR = Path("scripts")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openrouter/free"

MIN_SCRIPT_LENGTH = 1000
MAX_SCRIPT_ATTEMPTS = 3

SCRIPT_RULES_VERSION = "2026-09-08-v3"


# ============================================================
# HELPERS
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

        return list(csv.DictReader(file))


def get_topic_by_id(topic_id):

    topic_id = str(topic_id).strip()

    for topic in load_topics():

        if topic.get("id", "").strip() == topic_id:
            return topic

    raise RuntimeError(
        f"Topic not found: {topic_id}"
    )


def clean_script(text):

    if not text:
        return ""

    text = text.replace("```text", "")
    text = text.replace("```", "")

    text = re.sub(
        r"^\s*#+\s*.*$",
        "",
        text,
        flags=re.MULTILINE
    )

    text = re.sub(
        r"^\s*(HOOK|INTRO|BACKGROUND|FACTS|CONCLUSION|ENDING)\s*:?\s*$",
        "",
        text,
        flags=re.IGNORECASE | re.MULTILINE
    )

    text = text.replace("**", "")
    text = text.replace("__", "")

    text = re.sub(
        r"^\s*[-*•]\s+",
        "",
        text,
        flags=re.MULTILINE
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# VALIDATION
# ============================================================

def validate_script(text):

    if not text:
        return False, "EMPTY SCRIPT"

    if len(text) < MIN_SCRIPT_LENGTH:
        return False, "SCRIPT TOO SHORT"

    # No miles.
    forbidden_miles = [
        "mile",
        "miles",
        " mi ",
        "మైలు",
        "మైల్స్"
    ]

    lower_text = f" {text.lower()} "

    for word in forbidden_miles:

        if word in lower_text:
            return False, f"MILES FOUND: {word}"

    # Detect digit-style years.
    # They are allowed in research, but final narration should
    # convert them later in voice.py.
    # This is only a soft validation.

    # Ending should not look like an unfinished fragment.
    stripped = text.rstrip()

    if len(stripped) < 100:
        return False, "ENDING TOO SHORT"

    # Reject obvious unfinished endings.
    unfinished_endings = [
        "...",
        "…",
        ":",
        "-",
        "మరి",
        "కానీ",
        "అయితే",
        "అందుకే"
    ]

    last_line = stripped.splitlines()[-1].strip()

    if last_line.endswith(tuple(unfinished_endings)):
        return False, "ABRUPT / UNFINISHED ENDING"

    return True, "VALID"


# ============================================================
# PROMPT
# ============================================================

def build_prompt(topic_title, research_text):

    return f"""
మీరు Telugu Mystery YouTube documentary writer.

TOPIC:
{topic_title}

RESEARCH:
{research_text}

ఈ research ఆధారంగా పూర్తిగా సహజంగా వినిపించే తెలుగు documentary narration తయారు చేయాలి.

ముఖ్యమైన RULES:

1. మొత్తం narration తెలుగులో ఉండాలి.
2. అవసరమైన scientific names మాత్రమే English terminologyగా ఉండవచ్చు.
3. Headings, bullets, numbering, markdown ఏవీ ఉండకూడదు.
4. "Hook", "Introduction", "Conclusion" వంటి labels రాయకూడదు.
5. కథలా కాకుండా factual documentary styleలో రాయాలి.
6. ప్రతి claim research ఆధారంగా ఉండాలి.
7. ఊహాజనిత facts తయారు చేయకూడదు.
8. Mystery ఉంటే mysteryగా explain చేయాలి; fake answer ఇవ్వకూడదు.
9. Script చివరలో natural, complete conclusion ఉండాలి.
10. చివరి 4-6 sentences ఒక పూర్తి ముగింపులా ఉండాలి.
11. చివరి sentence మధ్యలో ఆగినట్టు లేదా rhetorical fragmentలా ఉండకూడదు.
12. "ఇదే ఆ రహస్యం", "కానీ అసలు విషయం..." అంటూ abruptగా ముగించకూడదు.
13. "Subscribe చేయండి", "Like చేయండి" వంటి YouTube requests narrationలో పెట్టకూడదు.
14. Miles ఎక్కడ ఉన్నా వాటిని kilometersగా మార్చాలి.
15. Final narrationలో miles / miles అనే unit ఉండకూడదు.
16. Decimal numbersలో unnecessary trailing zeros వద్దు.
   ఉదాహరణ:
   69.900 → 69.9
   10.000 → 10
17. సంవత్సరాలను సహజమైన పూర్తి తెలుగు రూపంలో చెప్పాలి.
   ఉదాహరణ:
   1990 → వెయ్యి తొమ్మిది వందల తొంభై
   1995 → వెయ్యి తొమ్మిది వందల తొంభై ఐదు
   1969 → వెయ్యి తొమ్మిది వందల అరవై తొమ్మిది
   2005 → రెండు వేల ఐదు
   2020 → రెండు వేల ఇరవై
18. 1900s years కోసం "పంతొమ్మిది వందల..." అనే రూపం ఉపయోగించకూడదు.
19. 1800s, 1700s కూడా పూర్తి సహజ తెలుగు year formatలో ఉండాలి.
20. Numbers చదివేటప్పుడు TTSకి సహజంగా వినిపించేలా రాయాలి.
21. అవసరమైతే చిన్న sentences ఉపయోగించాలి.
22. Narration engagingగా ఉండాలి.
23. Repetition తగ్గించాలి.
24. Final paragraphలో mystery/topicకి meaningful closure ఇవ్వాలి.

Length:
సుమారు 1800-3000 తెలుగు పదాల documentary narration ఇవ్వాలి.

IMPORTANT:
Final outputలో narration మాత్రమే ఇవ్వాలి.
ఏ explanation ఇవ్వకూడదు.
ఏ heading ఇవ్వకూడదు.
ఏ bullet points ఇవ్వకూడదు.
"""


# ============================================================
# OPENROUTER
# ============================================================

def call_openrouter(prompt):

    api_key = os.environ.get(
        "OPENROUTER_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set"
        )

    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/",
            "X-Title": "Telugu Mystery AI"
        },
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an expert Telugu documentary "
                        "script writer. Follow every formatting "
                        "and pronunciation-related instruction exactly."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 6000
        },
        timeout=180
    )

    if response.status_code != 200:

        raise RuntimeError(
            f"OpenRouter error "
            f"{response.status_code}: "
            f"{response.text[:1000]}"
        )

    data = response.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):

        raise RuntimeError(
            "Invalid OpenRouter response"
        )

    return clean_script(content)


# ============================================================
# SCRIPT VERSION
# ============================================================

def get_version_file(topic_id):

    return (
        SCRIPTS_DIR /
        f"{topic_id}.version"
    )


def is_current_script(topic_id, script_file):

    version_file = get_version_file(topic_id)

    if not script_file.exists():
        return False

    if script_file.stat().st_size < MIN_SCRIPT_LENGTH:
        return False

    if not version_file.exists():
        return False

    try:

        version = version_file.read_text(
            encoding="utf-8"
        ).strip()

    except Exception:
        return False

    return version == SCRIPT_RULES_VERSION


# ============================================================
# GENERATE SCRIPT
# ============================================================

def generate_script(topic_id):

    topic = get_topic_by_id(topic_id)

    title = topic.get(
        "title",
        ""
    ).strip()

    research_file = (
        RESEARCH_DIR /
        f"{topic_id}.txt"
    )

    script_file = (
        SCRIPTS_DIR /
        f"{topic_id}.txt"
    )

    version_file = get_version_file(topic_id)

    if not research_file.exists():

        raise RuntimeError(
            f"Research file not found: {research_file}"
        )

    research_text = research_file.read_text(
        encoding="utf-8"
    ).strip()

    if not research_text:

        raise RuntimeError(
            f"Research file is empty: {research_file}"
        )

    SCRIPTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Reuse only if it was generated with current rules.
    if is_current_script(
        topic_id,
        script_file
    ):

        existing = script_file.read_text(
            encoding="utf-8"
        ).strip()

        valid, reason = validate_script(existing)

        if valid:

            print("=" * 70)
            print("SCRIPT ALREADY EXISTS")
            print(f"TOPIC ID: {topic_id}")
            print(f"RULE VERSION: {SCRIPT_RULES_VERSION}")
            print("=" * 70)

            return script_file

        print(
            f"Existing script invalid: {reason}"
        )

    prompt = build_prompt(
        title,
        research_text
    )

    last_error = None

    for attempt in range(
        1,
        MAX_SCRIPT_ATTEMPTS + 1
    ):

        print("=" * 70)
        print("SCRIPT GENERATION")
        print(f"ATTEMPT: {attempt}/{MAX_SCRIPT_ATTEMPTS}")
        print(f"TOPIC: {title}")
        print("=" * 70)

        try:

            generated = call_openrouter(
                prompt
            )

            valid, reason = validate_script(
                generated
            )

            if not valid:

                print(
                    f"SCRIPT VALIDATION FAILED: {reason}"
                )

                last_error = reason
                continue

            script_file.write_text(
                generated,
                encoding="utf-8"
            )

            version_file.write_text(
                SCRIPT_RULES_VERSION,
                encoding="utf-8"
            )

            print("=" * 70)
            print("SCRIPT CREATED SUCCESSFULLY")
            print(f"FILE: {script_file}")
            print(f"CHARACTERS: {len(generated)}")
            print(f"RULE VERSION: {SCRIPT_RULES_VERSION}")
            print("=" * 70)

            return script_file

        except Exception as error:

            last_error = str(error)

            print(
                f"SCRIPT GENERATION ERROR: {error}"
            )

    raise RuntimeError(
        f"Script generation failed: {last_error}"
    )


# ============================================================
# RUN
# ============================================================

def run(topic_id):

    return generate_script(
        str(topic_id).strip()
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
