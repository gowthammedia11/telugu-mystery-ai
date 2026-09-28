import os
import re
import time
from pathlib import Path

import requests


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openrouter/free"

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
RESEARCH_DIR = BASE_DIR / "research"

MIN_CHARS = 4500
TARGET_MIN_CHARS = 5000
TARGET_MAX_CHARS = 5500
HARD_MAX_CHARS = 5700

MAX_ATTEMPTS = 6
REQUEST_TIMEOUT = 240


def load_research(topic_id):
    path = RESEARCH_DIR / f"{topic_id}.txt"

    if not path.exists():
        raise FileNotFoundError(
            f"Research file not found: {path}"
        )

    text = path.read_text(
        encoding="utf-8"
    ).strip()

    if not text:
        raise RuntimeError(
            f"Research file is empty: {path}"
        )

    return text


def remove_urls(text):
    text = re.sub(
        r"https?://\S+",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"www\.\S+",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    return text


def remove_coordinates(text):
    patterns = [
        r"\b\d{1,3}\s*°\s*\d{1,2}\s*[′']\s*\d{1,2}(?:\.\d+)?\s*[″\"]?\s*[NS]\b",
        r"\b\d{1,3}\s*°\s*\d{1,2}\s*[′']\s*\d{1,2}(?:\.\d+)?\s*[″\"]?\s*[EW]\b",
        r"\b\d{1,3}(?:\.\d+)?\s*[NS]\b",
        r"\b\d{1,3}(?:\.\d+)?\s*[EW]\b",
        r"\blatitude\b",
        r"\blongitude\b",
        r"\bcoordinates?\b",
    ]

    for pattern in patterns:
        text = re.sub(
            pattern,
            " ",
            text,
            flags=re.IGNORECASE,
        )

    return text


def remove_forbidden_measurements(text):
    # Convert common imperial measurements into safe
    # metric wording instead of leaving forbidden words.

    replacements = [
        (
            r"(\d+(?:\.\d+)?)\s*(?:miles?|mi)\b",
            lambda m: f"{float(m.group(1)) * 1.60934:.1f} kilometres",
        ),
        (
            r"(\d+(?:\.\d+)?)\s*(?:feet|foot|ft)\b",
            lambda m: f"{float(m.group(1)) * 0.3048:.1f} metres",
        ),
    ]

    for pattern, replacement in replacements:
        text = re.sub(
            pattern,
            replacement,
            text,
            flags=re.IGNORECASE,
        )

    return text


def clean_text(text):
    if not text:
        return ""

    text = text.replace(
        "\r",
        "\n",
    )

    text = remove_urls(text)
    text = remove_coordinates()
    text = remove_forbidden_measurements(text)

    text = re.sub(
        r"```.*?```",
        " ",
        text,
        flags=re.DOTALL,
    )

    text = re.sub(
        r"^\s*#{1,6}\s*",
        "",
        text,
        flags=re.MULTILINE,
    )

    text = re.sub(
        r"^\s*[-*•]\s*",
        "",
        text,
        flags=re.MULTILINE,
    )

    text = re.sub(
        r"^(?:title|heading|section|part|introduction|conclusion)\s*[:\-].*$",
        " ",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def split_sentences(text):
    return [
        sentence.strip()
        for sentence in re.split(
            r"(?<=[.!?।])\s+",
            text,
        )
        if sentence.strip()
    ]


def normalize_sentence(sentence):
    sentence = sentence.lower()

    sentence = re.sub(
        r"\s+",
        " ",
        sentence,
    )

    sentence = re.sub(
        r"[^\w\s]",
        "",
        sentence,
        flags=re.UNICODE,
    )

    return sentence.strip()


def has_repeated_sentences(text):
    sentences = split_sentences(text)

    seen = set()

    for sentence in sentences:
        normalized = normalize_sentence(
            sentence
        )

        if len(normalized) < 35:
            continue

        if normalized in seen:
            return True

        seen.add(normalized)

    return False


def has_excessive_repetition(text):
    words = re.findall(
        r"\S+",
        text.lower(),
    )

    if len(words) < 100:
        return False

    counts = {}

    for word in words:
        word = re.sub(
            r"[^\w\u0C00-\u0C7F]",
            "",
            word,
        )

        if len(word) < 4:
            continue

        counts[word] = (
            counts.get(word, 0) + 1
        )

    for count in counts.values():
        if count / len(words) > 0.10:
            return True

    return False


def contains_meta_text(text):
    lower = text.lower()

    forbidden = [
        "as an ai",
        "i cannot",
        "here is the script",
        "here's the script",
        "below is",
        "according to the prompt",
        "i have written",
        "this narration",
        "script begins",
        "script ends",
    ]

    return any(
        item in lower
        for item in forbidden
    )


def contains_forbidden_content(text):
    lower = text.lower()

    forbidden = [
        "http://",
        "https://",
        "www.",
        "latitude",
        "longitude",
        "coordinates",
        "miles",
        "feet",
        "foot",
    ]

    return [
        item
        for item in forbidden
        if item in lower
    ]


def sanitize_final_script(text):
    """
    Final safety cleanup.

    Removes URLs, coordinates and imperial
    measurements before final validation.
    """

    text = remove_urls(text)
    text = remove_coordinates(text)
    text = remove_forbidden_measurements(text)

    # Catch any standalone forbidden words that
    # may have survived the measurement cleanup.
    text = re.sub(
        r"\b(?:miles?|mi)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\b(?:feet|foot|ft)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def trim_to_target(text):
    text = clean_text(text)
    text = sanitize_final_script(text)

    if len(text) <= TARGET_MAX_CHARS:
        return text

    sentences = split_sentences(text)

    result = []
    current_length = 0

    for sentence in sentences:
        extra = len(sentence)

        if result:
            extra += 1

        if (
            current_length + extra
            > TARGET_MAX_CHARS
        ):
            break

        result.append(sentence)
        current_length += extra

    trimmed = " ".join(result).strip()

    return trimmed


def validate_script(text):
    if not text:
        return "SCRIPT EMPTY"

    length = len(text)

    if length < MIN_CHARS:
        return (
            f"SCRIPT TOO SHORT: "
            f"{length} chars"
        )

    if length > HARD_MAX_CHARS:
        return (
            f"SCRIPT TOO LONG: "
            f"{length} chars"
        )

    if contains_meta_text(text):
        return "SCRIPT CONTAINS META TEXT"

    forbidden = contains_forbidden_content(
        text
    )

    if forbidden:
        return (
            "SCRIPT CONTAINS FORBIDDEN CONTENT: "
            + ", ".join(forbidden)
        )

    if has_repeated_sentences(text):
        return (
            "SCRIPT CONTAINS REPEATED SENTENCES"
        )

    if has_excessive_repetition(text):
        return (
            "SCRIPT HAS EXCESSIVE WORD REPETITION"
        )

    return None


def build_prompt(
    topic_id,
    title,
    research,
):
    research = clean_text(research)

    if len(research) > 18000:
        research = research[:18000]

    return f"""
Create a natural Telugu documentary narration
for a YouTube mystery/science video.

TOPIC ID: {topic_id}
TOPIC: {title}

Write a complete documentary narration.

The final narration should normally be around
5000 to 5500 Telugu characters.

CONTENT:

- Natural conversational Telugu.
- Documentary storytelling style.
- Facts only.
- Do not invent facts.
- Explain the mystery clearly.
- Explain scientific evidence.
- Explain competing explanations fairly.
- Separate confirmed facts from theories.
- Give a complete natural ending.
- Do not repeat the same information.
- Do not add generic filler.

FORMAT:

- Narration only.
- No headings.
- No bullets.
- No numbered lists.
- No markdown.
- No URLs.
- No source list.
- No citations.
- No prompt explanation.
- No AI mention.

LANGUAGE:

- Mostly natural spoken Telugu.
- Avoid unnecessary English.
- English proper names are allowed when necessary.
- Never use miles.
- Never use feet.
- Prefer kilometres and metres.
- Never mention latitude.
- Never mention longitude.
- Never mention coordinates.
- Never reproduce coordinate values.

RESEARCH:

{research}

Write only the complete Telugu
documentary narration.
"""


def request_script(
    topic_id,
    title,
    research,
):
    api_key = os.getenv(
        "OPENROUTER_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set"
        )

    prompt = build_prompt(
        topic_id,
        title,
        research,
    )

    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": (
                f"Bearer {api_key}"
            ),
            "Content-Type": (
                "application/json"
            ),
        },
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Generate only the complete "
                        "Telugu documentary narration. "
                        "Do not explain anything."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.45,
            "max_tokens": 5000,
        },
        timeout=REQUEST_TIMEOUT,
    )

    print(
        f"OPENROUTER HTTP STATUS: "
        f"{response.status_code}"
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"OpenRouter HTTP "
            f"{response.status_code}: "
            f"{response.text[:1000]}"
        )

    data = response.json()

    choices = data.get(
        "choices",
        [],
    )

    if not choices:
        raise RuntimeError(
            "OpenRouter returned no choices"
        )

    message = choices[0].get(
        "message",
        {},
    )

    content = message.get(
        "content",
        "",
    )

    if isinstance(content, list):
        content = "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict)
        )

    return clean_text(
        str(content or "")
    )


def generate_script(
    topic_id,
    title,
    research_text,
):
    print("=" * 70)
    print("GENERATING LONG SCRIPT")
    print("=" * 70)

    last_error = None

    for attempt in range(
        1,
        MAX_ATTEMPTS + 1,
    ):
        print(
            f"OPENROUTER SCRIPT ATTEMPT "
            f"{attempt}/{MAX_ATTEMPTS}"
        )

        try:
            raw_script = request_script(
                topic_id,
                title,
                research_text,
            )

            print(
                "OPENROUTER SCRIPT CONTENT RECEIVED"
            )

            print(
                f"RAW SCRIPT CHARACTERS: "
                f"{len(raw_script)}"
            )

            # Empty/very short model responses
            # need another request.
            if len(raw_script) < MIN_CHARS:
                last_error = (
                    f"SCRIPT TOO SHORT: "
                    f"{len(raw_script)} chars"
                )

                print(
                    f"SCRIPT VALIDATION: "
                    f"{last_error}"
                )

                time.sleep(1)
                continue

            # IMPORTANT:
            # Long model output is NOT an error.
            # Trim it automatically.
            script = trim_to_target(
                raw_script
            )

            print(
                f"TRIMMED SCRIPT CHARACTERS: "
                f"{len(script)}"
            )

            # Final cleanup AFTER trimming.
            script = sanitize_final_script(
                script
            )

            print(
                f"FINAL CLEAN SCRIPT CHARACTERS: "
                f"{len(script)}"
            )

            error = validate_script(
                script
            )

            if error:
                print(
                    f"SCRIPT VALIDATION: "
                    f"{error}"
                )

                last_error = error

                time.sleep(1)
                continue

            print("=" * 70)
            print(
                "LONG SCRIPT GENERATION "
                "SUCCESSFUL"
            )
            print(
                f"FINAL SCRIPT LENGTH: "
                f"{len(script)} characters"
            )
            print("=" * 70)

            return script

        except Exception as exc:
            last_error = str(exc)

            print(
                f"SCRIPT GENERATION ERROR: "
                f"{last_error}"
            )

            time.sleep(2)

    raise RuntimeError(
        f"Script generation failed after "
        f"{MAX_ATTEMPTS} attempts: "
        f"{last_error}"
    )


def save_script(
    topic_id,
    script_text,
):
    SCRIPTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    script_text = clean_text(
        script_text
    )

    script_text = sanitize_final_script(
        script_text
    )

    script_text = trim_to_target(
        script_text
    )

    script_text = sanitize_final_script(
        script_text
    )

    error = validate_script(
        script_text
    )

    if error:
        raise RuntimeError(
            f"Cannot save invalid script: "
            f"{error}"
        )

    path = (
        SCRIPTS_DIR
        / f"{topic_id}.txt"
    )

    path.write_text(
        script_text,
        encoding="utf-8",
    )

    print(
        f"SCRIPT SAVED: {path}"
    )

    print(
        f"SAVED SCRIPT CHARACTERS: "
        f"{len(script_text)}"
    )


def main():
    import sys

    if len(sys.argv) < 3:
        print(
            "Usage: python src/script.py "
            "<topic_id> <title>"
        )
        sys.exit(1)

    topic_id = sys.argv[1]
    title = sys.argv[2]

    research = load_research(
        topic_id
    )

    script = generate_script(
        topic_id,
        title,
        research,
    )

    save_script(
        topic_id,
        script,
    )


if __name__ == "__main__":
    main()
