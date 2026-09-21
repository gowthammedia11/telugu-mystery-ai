from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


ROOT = Path(__file__).resolve().parent.parent
TOPICS_FILE = ROOT / "topics" / "topics.csv"
RESEARCH_DIR = ROOT / "research"
SCRIPTS_DIR = ROOT / "scripts"

MODEL = "openrouter/free"
REQUEST_TIMEOUT = 240

MIN_SCRIPT_CHARACTERS = 4500
TARGET_SCRIPT_CHARACTERS = 4500
MAX_SCRIPT_CHARACTERS = 6500
STOP_NEAR_TARGET_CHARACTERS = 4300

CHUNK_TARGET_CHARACTERS = 950
CHUNK_MIN_CHARACTERS = 450
CHUNK_MAX_ACCEPTED_CHARACTERS = 2200

MAX_CHUNKS = 7
MAX_RETRIES_PER_CHUNK = 3

CHUNK_TOKEN_LIMITS = [700, 600, 500]
RETRY_DELAYS = [5, 8, 10]

TELUGU_YEAR_REPLACEMENTS = {
    "2026": "రెండు వేల ఇరవై ఆరు",
    "2025": "రెండు వేల ఇరవై ఐదు",
    "2024": "రెండు వేల ఇరవై నాలుగు",
    "2023": "రెండు వేల ఇరవై మూడు",
    "2022": "రెండు వేల ఇరవై రెండు",
    "2021": "రెండు వేల ఇరవై ఒకటి",
    "2020": "రెండు వేల ఇరవై",
    "2019": "రెండు వేల పంతొమ్మిది",
    "2018": "రెండు వేల పద్దెనిమిది",
    "2017": "రెండు వేల పదిహేడు",
    "2016": "రెండు వేల పదహారు",
    "2015": "రెండు వేల పదిహేను",
    "2014": "రెండు వేల పద్నాలుగు",
    "2013": "రెండు వేల పదమూడు",
    "2012": "రెండు వేల పన్నెండు",
    "2011": "రెండు వేల పదకొండు",
    "2010": "రెండు వేల పది",
}

PROMPT_ECHO_MARKERS = [
    "we need to",
    "write only",
    "current narration",
    "do not write",
    "no english words",
    "characters",
    "openrouter",
    "generate a",
    "the topic is",
    "research material",
    "continue the narration",
    "previous narration",
    "instructions",
    "must be",
    "should be",
]


def log(message: str) -> None:
    print(f"[SCRIPT] {message}", flush=True)


def get_api_key() -> str:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()

    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set.")

    return key


def load_topics() -> List[Dict[str, str]]:
    if not TOPICS_FILE.exists():
        raise FileNotFoundError(f"Topics file not found: {TOPICS_FILE}")

    with TOPICS_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        rows = []

        for row in reader:
            rows.append(
                {
                    "id": (row.get("id") or "").strip(),
                    "title": (row.get("title") or "").strip(),
                    "status": (row.get("status") or "").strip().lower(),
                }
            )

    return rows


def find_next_topic() -> Dict[str, str]:
    topics = load_topics()

    for topic in topics:
        topic_id = topic["id"]
        status = topic["status"]

        if not topic_id:
            continue

        research_file = RESEARCH_DIR / f"{topic_id}.txt"

        if status == "researched" and research_file.exists():
            return topic

    raise RuntimeError(
        "No researched topic is available for script generation."
    )


def load_research(topic_id: str) -> str:
    research_file = RESEARCH_DIR / f"{topic_id}.txt"

    if not research_file.exists():
        raise FileNotFoundError(
            f"Research file not found: {research_file}"
        )

    text = research_file.read_text(encoding="utf-8").strip()

    if not text:
        raise RuntimeError(
            f"Research file is empty: {research_file}"
        )

    # Keep prompts reasonably small.
    if len(text) > 8000:
        text = (
            text[:4000]
            + "\n\n[మధ్యలోని పరిశోధన వివరాలు సంక్షిప్తంగా వదిలివేయబడ్డాయి]\n\n"
            + text[-4000:]
        )

    return text


def normalize_years(text: str) -> str:
    for year, telugu in TELUGU_YEAR_REPLACEMENTS.items():
        text = re.sub(rf"\b{year}\b", telugu, text)

    return text


def normalize_miles(text: str) -> str:
    text = re.sub(
        r"(\d+(?:\.\d+)?)\s*(?:miles?|mi)\b",
        r"\1 కిలోమీటర్లు",
        text,
        flags=re.IGNORECASE,
    )

    return text


def clean_script(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    text = re.sub(r"```(?:text|telugu|markdown)?", "", text, flags=re.I)
    text = text.replace("```", "")

    lines = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        # Remove accidental markdown headings.
        line = re.sub(r"^#{1,6}\s*", "", line)

        lines.append(line)

    text = " ".join(lines)

    text = re.sub(r"\s+", " ", text).strip()

    text = normalize_years(text)
    text = normalize_miles(text)

    return text


def looks_like_prompt_echo(text: str) -> bool:
    if not text:
        return True

    lower = text.lower()

    marker_count = 0

    for marker in PROMPT_ECHO_MARKERS:
        if marker in lower:
            marker_count += 1

    # English-heavy output is usually a failed prompt echo.
    english_words = re.findall(
        r"\b(?:the|and|or|we|need|write|only|must|should|topic|research|"
        r"narration|characters|continue|previous|instructions)\b",
        lower,
    )

    telugu_chars = len(re.findall(r"[\u0C00-\u0C7F]", text))

    if marker_count >= 2 and telugu_chars < 150:
        return True

    if len(english_words) >= 5 and telugu_chars < 250:
        return True

    return False


def has_reasonable_telugu(text: str) -> bool:
    telugu_chars = len(re.findall(r"[\u0C00-\u0C7F]", text))

    if telugu_chars < 100:
        return False

    if len(text) < 200:
        return False

    return True


def validate_narration_chunk(text: str) -> bool:
    text = clean_script(text)

    if not text:
        return False

    if looks_like_prompt_echo(text):
        log("Rejected: model returned prompt/instructions instead of narration.")
        return False

    if not has_reasonable_telugu(text):
        log("Rejected: insufficient Telugu narration.")
        return False

    return True


def trim_to_sentence_boundary(
    text: str,
    max_chars: int,
) -> str:
    text = text.strip()

    if len(text) <= max_chars:
        return text

    candidate = text[:max_chars]

    positions = [
        candidate.rfind("।"),
        candidate.rfind("."),
        candidate.rfind("?"),
        candidate.rfind("!"),
    ]

    cut = max(positions)

    if cut >= int(max_chars * 0.55):
        return candidate[: cut + 1].strip()

    return candidate.strip()


def extract_script_from_response(data: Dict[str, Any]) -> str:
    choices = data.get("choices")

    if not choices:
        return ""

    choice = choices[0] or {}

    message = choice.get("message") or {}
    content = message.get("content")

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []

        for item in content:
            if isinstance(item, str):
                parts.append(item)

            elif isinstance(item, dict):
                text = item.get("text")

                if isinstance(text, str):
                    parts.append(text)

        return "\n".join(parts).strip()

    return ""


def call_openrouter(
    prompt: str,
    token_limit: int,
) -> Dict[str, Any]:

    api_key = get_api_key()

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/gowthammedia11/telugu-mystery-ai",
        "X-Title": "Telugu Mystery AI",
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "నువ్వు తెలుగు డాక్యుమెంటరీ నరేషన్ రచయితవి. "
                    "నీ పని ఇచ్చిన పరిశోధన ఆధారంగా సహజమైన తెలుగు వాయిస్ ఓవర్ "
                    "నరేషన్ మాత్రమే రాయడం. సూచనలు, వివరణలు, ఇంగ్లీష్ "
                    "మెటా టెక్స్ట్ లేదా markdown ఇవ్వకూడదు."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.45,
        "max_tokens": token_limit,
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    return response.json()


def build_chunk_prompt(
    title: str,
    research: str,
    previous_script: str,
    chunk_number: int,
) -> str:

    if previous_script:
        continuation = (
            "ఇప్పటివరకు తయారైన నరేషన్:\n"
            f"{previous_script[-2200:]}\n\n"
            "దీనిని పదే పదే రాయకుండా, సహజంగా తర్వాతి భాగాన్ని కొనసాగించు."
        )
    else:
        continuation = (
            "ఇది నరేషన్ యొక్క మొదటి భాగం. "
            "మొదట ప్రేక్షకుడిలో ఆసక్తి కలిగించే విధంగా ప్రారంభించు."
        )

    return f"""
విషయం: {title}

పరిశోధన సమాచారం:
{research}

{continuation}

ఇది భాగం {chunk_number}.

ఈ భాగంలో సుమారు {CHUNK_TARGET_CHARACTERS} అక్షరాల తెలుగు వాయిస్ ఓవర్ నరేషన్ రాయాలి.

కచ్చితమైన నియమాలు:

1. నరేషన్ మాత్రమే ఇవ్వాలి.
2. తెలుగులో సహజంగా మాట్లాడుతున్నట్టు ఉండాలి.
3. డాక్యుమెంటరీ శైలి ఉండాలి.
4. పరిశోధనలో ఉన్న వాస్తవాలనే ఉపయోగించాలి.
5. ఊహలు లేదా కల్పిత విషయాలు జోడించకూడదు.
6. "ఈ వీడియోలో", "ఇప్పుడు మనం", "మనం తెలుసుకున్నాం" వంటి పదాలను అవసరం లేకుండా పదే పదే వాడకూడదు.
7. headings, bullet points, numbering ఇవ్వకూడదు.
8. markdown ఇవ్వకూడదు.
9. ఇంగ్లీష్ సూచనలు లేదా meta commentary ఇవ్వకూడదు.
10. పరిశోధనకు సంబంధం లేని విషయం రాయకూడదు.
11. చివరలో సహజమైన sentence boundary వద్ద ఆపాలి.
12. ఈ prompt గురించి ఏమీ చెప్పకూడదు.
13. output లో narration తప్ప మరేమీ ఉండకూడదు.
""".strip()


def request_script_chunk(
    title: str,
    research: str,
    previous_script: str,
    chunk_number: int,
) -> Optional[str]:

    for attempt in range(MAX_RETRIES_PER_CHUNK):
        token_limit = CHUNK_TOKEN_LIMITS[
            min(attempt, len(CHUNK_TOKEN_LIMITS) - 1)
        ]

        prompt = build_chunk_prompt(
            title=title,
            research=research,
            previous_script=previous_script,
            chunk_number=chunk_number,
        )

        log(
            f"Generating chunk {chunk_number}, "
            f"attempt {attempt + 1}/{MAX_RETRIES_PER_CHUNK}, "
            f"max_tokens={token_limit}"
        )

        try:
            data = call_openrouter(
                prompt=prompt,
                token_limit=token_limit,
            )

            choice = {}

            if data.get("choices"):
                choice = data["choices"][0] or {}

            finish_reason = choice.get("finish_reason")

            content = extract_script_from_response(data)

            if not content:
                log(
                    "OpenRouter returned empty content"
                    + (
                        f" (finish_reason={finish_reason})"
                        if finish_reason
                        else ""
                    )
                )

                if attempt < MAX_RETRIES_PER_CHUNK - 1:
                    time.sleep(RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)])

                continue

            content = clean_script(content)

            if looks_like_prompt_echo(content):
                log("Rejected prompt echo.")

                if attempt < MAX_RETRIES_PER_CHUNK - 1:
                    time.sleep(RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)])

                continue

            if not has_reasonable_telugu(content):
                log("Rejected output because Telugu content is too low.")

                if attempt < MAX_RETRIES_PER_CHUNK - 1:
                    time.sleep(RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)])

                continue

            # Free routed models can ignore max_tokens.
            # Accept valid narration and trim locally.
            if len(content) > CHUNK_MAX_ACCEPTED_CHARACTERS:
                log(
                    f"Chunk returned {len(content)} chars. "
                    f"Trimming locally."
                )

                content = trim_to_sentence_boundary(
                    content,
                    CHUNK_MAX_ACCEPTED_CHARACTERS,
                )

            if len(content) < CHUNK_MIN_CHARACTERS:
                log(
                    f"Chunk too short: {len(content)} chars."
                )

                if attempt < MAX_RETRIES_PER_CHUNK - 1:
                    time.sleep(RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)])

                continue

            log(
                f"Chunk {chunk_number} accepted: "
                f"{len(content)} chars"
                + (
                    f", finish_reason={finish_reason}"
                    if finish_reason
                    else ""
                )
            )

            return content

        except requests.RequestException as exc:
            log(f"OpenRouter request failed: {exc}")

        except Exception as exc:
            log(f"Chunk generation error: {exc}")

        if attempt < MAX_RETRIES_PER_CHUNK - 1:
            time.sleep(RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)])

    return None


def update_topic_status(topic_id: str, new_status: str) -> None:
    topics = load_topics()

    for topic in topics:
        if topic["id"] == topic_id:
            topic["status"] = new_status
            break
    else:
        raise RuntimeError(
            f"Topic {topic_id} not found in topics.csv"
        )

    fieldnames = ["id", "title", "status"]

    with TOPICS_FILE.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for topic in topics:
            writer.writerow(
                {
                    "id": topic["id"],
                    "title": topic["title"],
                    "status": topic["status"],
                }
            )


def save_script(topic_id: str, script: str) -> Path:
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    output_file = SCRIPTS_DIR / f"{topic_id}.txt"

    output_file.write_text(
        script.strip() + "\n",
        encoding="utf-8",
    )

    return output_file


def generate_script(
    topic: Optional[Dict[str, str]] = None,
    research: Optional[str] = None,
    *args: Any,
    **kwargs: Any,
) -> str:

    if topic is None:
        topic = find_next_topic()

    topic_id = topic["id"]
    title = topic["title"]

    if research is None:
        research = load_research(topic_id)

    log(f"Topic: {topic_id} - {title}")
    log(f"Research length: {len(research)} chars")

    update_topic_status(topic_id, "script_processing")

    chunks: List[str] = []
    combined = ""

    try:
        for chunk_number in range(1, MAX_CHUNKS + 1):

            if len(combined) >= STOP_NEAR_TARGET_CHARACTERS:
                break

            chunk = request_script_chunk(
                title=title,
                research=research,
                previous_script=combined,
                chunk_number=chunk_number,
            )

            if not chunk:
                raise RuntimeError(
                    f"Failed to generate valid narration chunk "
                    f"{chunk_number}."
                )

            chunks.append(chunk)

            combined = " ".join(chunks)
            combined = clean_script(combined)

            log(
                f"Total narration: {len(combined)} chars"
            )

        if len(combined) > MAX_SCRIPT_CHARACTERS:
            combined = trim_to_sentence_boundary(
                combined,
                MAX_SCRIPT_CHARACTERS,
            )

        if len(combined) < MIN_SCRIPT_CHARACTERS:
            raise RuntimeError(
                f"Final script too short: {len(combined)} chars. "
                f"Minimum required: {MIN_SCRIPT_CHARACTERS}"
            )

        if not has_reasonable_telugu(combined):
            raise RuntimeError(
                "Final script does not contain enough Telugu narration."
            )

        if looks_like_prompt_echo(combined):
            raise RuntimeError(
                "Final script looks like prompt/instruction text."
            )

        output_file = save_script(
            topic_id=topic_id,
            script=combined,
        )

        update_topic_status(
            topic_id,
            "script_ready",
        )

        log(
            f"Script saved: {output_file}"
        )

        log(
            f"Final script length: {len(combined)} chars"
        )

        return combined

    except Exception:
        try:
            update_topic_status(
                topic_id,
                "researched",
            )
        except Exception as status_error:
            log(
                f"Could not restore topic status: {status_error}"
            )

        raise


def main() -> None:
    try:
        topic = find_next_topic()

        log(
            f"Next topic: {topic['id']} - {topic['title']}"
        )

        script = generate_script(
            topic=topic,
        )

        print(
            json.dumps(
                {
                    "topic_id": topic["id"],
                    "title": topic["title"],
                    "characters": len(script),
                    "status": "success",
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    except Exception as exc:
        print(
            f"[SCRIPT] ERROR: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise


if __name__ == "__main__":
    main()
