import os
import re
import time
from pathlib import Path

import requests


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openrouter/free"

SCRIPTS_DIR = Path("scripts")

MIN_CHARS = 4600
TARGET_MIN_CHARS = 5000
TARGET_MAX_CHARS = 5700
MAX_CHARS = 6000

MAX_ATTEMPTS = 6
REQUEST_TIMEOUT = 240


ALLOWED_ENGLISH_WORDS = {
    "YouTube",
    "Yonaguni",
    "Monument",
    "Japan",
    "Pacific",
    "Asia",
    "UNESCO",
}


def load_research(topic_id):
    topic_id = str(topic_id).zfill(3)

    research_file = (
        Path("research") / f"{topic_id}.txt"
    )

    if not research_file.exists():
        raise FileNotFoundError(
            f"Research file not found: {research_file}"
        )

    content = research_file.read_text(
        encoding="utf-8"
    ).strip()

    if not content:
        raise RuntimeError(
            f"Research file is empty: {research_file}"
        )

    return content


def remove_urls(text):
    text = re.sub(
        r"https?://\S+",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"www\.\S+",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return text


def clean_text(text):
    if not text:
        return ""

    text = text.replace("\r", "\n")

    text = text.replace("```text", "")
    text = text.replace("```", "")

    text = remove_urls(text)

    # Remove geographic coordinates.
    text = re.sub(
        r"\b\d+(?:\.\d+)?\s*[°º]\s*[NSWE]\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\b\d+(?:\.\d+)?\s*°",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove latitude / longitude wording.
    text = re.sub(
        r"\blatitude\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\blongitude\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\bcoordinates?\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove miles / feet.
    text = re.sub(
        r"\b\d+(?:\.\d+)?\s*(?:miles?|mi)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\b\d+(?:\.\d+)?\s*(?:feet|ft)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove Markdown headings.
    text = re.sub(
        r"(?m)^\s*#{1,6}\s*",
        "",
        text,
    )

    # Remove bullets.
    text = re.sub(
        r"(?m)^\s*[-*•]\s+",
        "",
        text,
    )

    # Remove horizontal separators.
    text = re.sub(
        r"(?m)^\s*[-_=]{3,}\s*$",
        "",
        text,
    )

    text = text.replace("—", " ")
    text = text.replace("–", " ")

    text = re.sub(
        r"\.{3,}",
        ".",
        text,
    )

    text = re.sub(
        r"!{2,}",
        "!",
        text,
    )

    text = re.sub(
        r"\?{2,}",
        "?",
        text,
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    lines = []

    for line in text.splitlines():
        line = line.strip()

        if line:
            lines.append(line)

    text = " ".join(lines)

    text = re.sub(
        r"\s+([,.!?])",
        r"\1",
        text,
    )

    text = re.sub(
        r"([.!?])\s+",
        r"\1 ",
        text,
    )

    return text.strip()


def split_sentences(text):
    if not text:
        return []

    return [
        part.strip()
        for part in re.split(
            r"(?<=[.!?])\s+",
            text,
        )
        if part.strip()
    ]


def normalize_sentence(text):
    text = text.lower()

    text = re.sub(
        r"[^ఀ-౿a-z0-9 ]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def has_repeated_sentences(text):
    sentences = split_sentences(text)

    if len(sentences) < 10:
        return False

    seen = set()

    for sentence in sentences:
        normalized = normalize_sentence(sentence)

        if len(normalized) < 40:
            continue

        if normalized in seen:
            return True

        seen.add(normalized)

    # Detect repeated 3-sentence blocks.
    blocks = set()

    for index in range(
        0,
        len(sentences) - 2,
    ):
        block = " ".join(
            normalize_sentence(sentence)
            for sentence in sentences[
                index:index + 3
            ]
        )

        if len(block) < 100:
            continue

        if block in blocks:
            return True

        blocks.add(block)

    return False


def has_excessive_repetition(text):
    words = normalize_sentence(text).split()

    if len(words) < 100:
        return False

    window_size = 12

    windows = {}

    for index in range(
        0,
        len(words) - window_size + 1,
    ):
        window = " ".join(
            words[
                index:index + window_size
            ]
        )

        windows[window] = (
            windows.get(window, 0) + 1
        )

        if windows[window] >= 3:
            return True

    return False


def contains_meta_text(text):
    lowered = text.lower()

    forbidden = [
        "మీ కోసం",
        "ఇదిగో",
        "ఈ స్క్రిప్ట్",
        "ఈ నారేషన్",
        "ఈ narration",
        "script",
        "narration script",
        "ఇక్కడ మీకు",
        "ప్రశ్నలకు సమాధానం కోసం",
        "ఇలా రాయాలి",
        "మీరు ఒక తెలుగు",
    ]

    for item in forbidden:
        if item.lower() in lowered:
            return True

    return False


def contains_forbidden_content(text):
    patterns = [
        r"\blatitude\b",
        r"\blongitude\b",
        r"\bcoordinates?\b",
        r"\b\d+(?:\.\d+)?\s*[°º]\s*[NSWE]\b",
        r"\b\d+(?:\.\d+)?\s*(?:miles?|mi)\b",
        r"\b\d+(?:\.\d+)?\s*(?:feet|ft)\b",
        r"\bhttps?://",
        r"\bwww\.",
    ]

    for pattern in patterns:
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            return True

    return False


def find_unwanted_english(text):
    words = re.findall(
        r"\b[A-Za-z]{2,}\b",
        text,
    )

    unwanted = []

    for word in words:
        if word not in ALLOWED_ENGLISH_WORDS:
            unwanted.append(word)

    return sorted(set(unwanted))


def validate_script(text):
    if not text:
        return False, "EMPTY SCRIPT"

    count = len(text)

    if count < MIN_CHARS:
        return False, (
            f"SCRIPT TOO SHORT: {count} chars"
        )

    if count > MAX_CHARS:
        return False, (
            f"SCRIPT TOO LONG: {count} chars"
        )

    if has_repeated_sentences(text):
        return False, (
            "REPEATED SENTENCES DETECTED"
        )

    if has_excessive_repetition(text):
        return False, (
            "EXCESSIVE REPETITION DETECTED"
        )

    if contains_meta_text(text):
        return False, "META TEXT DETECTED"

    if contains_forbidden_content(text):
        return False, (
            "FORBIDDEN CONTENT DETECTED"
        )

    unwanted_english = find_unwanted_english(
        text
    )

    if unwanted_english:
        return False, (
            "UNNECESSARY ENGLISH WORDS: "
            + ", ".join(
                unwanted_english[:15]
            )
        )

    return True, "VALID"


def build_prompt(
    topic_id,
    topic_title,
    research,
    retry_reason=None,
):
    retry_text = ""

    if retry_reason:
        retry_text = f"""

IMPORTANT: A PREVIOUS ATTEMPT FAILED.

Failure reason:
{retry_reason}

Ignore the previous generated answer completely.

Generate a brand-new complete narration.

Do not explain the failure.
Do not apologize.
Do not give a short answer.
Do not give instructions.
Return only the full narration.
"""

    return f"""
ROLE:
You are a professional Telugu documentary narrator.

TOPIC:
{topic_title}

TOPIC ID:
{topic_id}

YOUR TASK:
Convert the research below into one complete natural Telugu
documentary narration.

The final narration must be approximately 7 to 8 minutes long.

TARGET LENGTH:
5000 to 5700 characters.

HARD LIMIT:
4600 minimum.
6000 maximum.

RESEARCH:
{research}

VERY IMPORTANT:

The research above contains tables, URLs, source names,
coordinates, English words, measurements and structured notes.

DO NOT copy the research format.

DO NOT output tables.

DO NOT output URLs.

DO NOT output source lists.

DO NOT output coordinates.

DO NOT output latitude or longitude.

DO NOT output miles or feet.

Convert the useful factual information into natural spoken Telugu.

NARRATION STRUCTURE:

Start with a strong mystery hook.

Then naturally explain where the Yonaguni formation is
without using coordinates.

Explain when it was discovered and how the mystery began.

Describe what divers actually see there.

Explain why the geometric shapes look unusual.

Explain the natural geological explanation.

Explain the artificial-origin theory and what its supporters
point to.

Explain the important evidence against definite human construction.

Explain what is still unknown.

End with a balanced, natural conclusion about why the
Yonaguni Monument remains an interesting mystery.

WRITING RULES:

Write ONLY the narration.

No title.

No headings.

No bullet points.

No numbered lists.

No Markdown.

No tables.

No "---".

No URLs.

No citations inside the narration.

No source list.

No meta commentary.

Do not say "ఈ స్క్రిప్ట్".

Do not say "ఈ వీడియోలో".

Do not say "మీ కోసం".

Do not say "ఇదిగో".

Do not discuss how the script was generated.

Do not mention AI.

Do not mention artificial intelligence.

Do not mention coordinates.

Do not mention latitude.

Do not mention longitude.

Do not mention miles.

Do not mention feet.

Use kilometers when a distance is genuinely useful.

Avoid unnecessary numerical precision.

Use natural Telugu.

The narration should sound like a real Telugu documentary,
not like a translated table or academic report.

Every paragraph must move the story forward.

Never repeat the same fact.

Never repeat the same sentence.

Never repeat a paragraph.

Do not invent facts that are not supported by the research.

Do not claim that the monument is definitely man-made.

Do not claim that the monument is definitely natural.

Present the competing explanations accurately.

The final ending must feel complete and intentional.

CRITICAL LENGTH RULE:

Write enough content to reach approximately 5000-5700
characters.

Do not stop after a few paragraphs.

Do not return a summary.

Do not return an outline.

Do not return only an introduction.

Return the COMPLETE narration.

{retry_text}
"""


def request_script(
    api_key,
    topic_id,
    topic_title,
    research,
    retry_reason=None,
):
    prompt = build_prompt(
        topic_id,
        topic_title,
        research,
        retry_reason,
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": (
            "https://github.com/"
            "gowthammedia11/telugu-mystery-ai"
        ),
        "X-Title": "Telugu Mystery AI",
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Generate only the complete Telugu "
                    "documentary narration requested by "
                    "the user. Never return a short reply. "
                    "Never return an explanation."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.25,
        "max_tokens": 4000,
    }

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
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

    choices = data.get("choices", [])

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
        content = " ".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict)
        )

    content = str(content).strip()

    if not content:
        raise RuntimeError(
            "OpenRouter returned empty content"
        )

    print(
        "OPENROUTER SCRIPT CONTENT RECEIVED"
    )

    return content


def generate_script(
    topic_id,
    topic_title,
    research,
):
    api_key = os.environ.get(
        "OPENROUTER_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY secret is missing"
        )

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
            raw = request_script(
                api_key,
                topic_id,
                topic_title,
                research,
                retry_reason=last_error,
            )

            cleaned = clean_text(raw)

            valid, reason = validate_script(
                cleaned
            )

            print(
                f"SCRIPT VALIDATION: {reason}"
            )

            print(
                f"SCRIPT CHARACTERS: "
                f"{len(cleaned)}"
            )

            if valid:
                print(
                    "SCRIPT VALIDATION PASSED"
                )

                return cleaned

            last_error = reason

        except requests.RequestException as exc:
            last_error = (
                f"REQUEST ERROR: {exc}"
            )

            print(last_error)

        except Exception as exc:
            last_error = str(exc)

            print(
                f"SCRIPT GENERATION ERROR: "
                f"{last_error}"
            )

        if attempt < MAX_ATTEMPTS:
            print(
                "REQUESTING A FRESH COMPLETE "
                "NARRATION"
            )
            time.sleep(3)

    raise RuntimeError(
        "Script generation failed after "
        f"{MAX_ATTEMPTS} attempts: "
        f"{last_error}"
    )


def save_script(
    topic_id,
    script,
):
    SCRIPTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    topic_id = str(topic_id).zfill(3)

    output = (
        SCRIPTS_DIR
        / f"{topic_id}.txt"
    )

    content = clean_text(script)

    valid, reason = validate_script(
        content
    )

    if not valid:
        raise RuntimeError(
            "Refusing to save invalid script: "
            f"{reason}"
        )

    output.write_text(
        content,
        encoding="utf-8",
    )

    print("=" * 70)
    print("SCRIPT SAVED")
    print("=" * 70)
    print(f"FILE: {output}")
    print(
        f"CHARACTERS: {len(content)}"
    )
    print("=" * 70)

    return output


def main():
    topic_id = os.environ.get(
        "TOPIC_ID"
    )

    if not topic_id:
        raise RuntimeError(
            "TOPIC_ID environment variable is required"
        )

    topic_title = os.environ.get(
        "TOPIC_TITLE",
        "",
    ).strip()

    if not topic_title:
        raise RuntimeError(
            "TOPIC_TITLE environment variable is required"
        )

    research = load_research(
        topic_id
    )

    script = generate_script(
        topic_id,
        topic_title,
        research,
    )

    save_script(
        topic_id,
        script,
    )


if __name__ == "__main__":
    main()
