````python
from __future__ import annotations

import csv
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


# ============================================================
# CONFIG
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

TOPICS_FILE = ROOT / "topics" / "topics.csv"
RESEARCH_DIR = ROOT / "research"
SCRIPTS_DIR = ROOT / "scripts"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openrouter/free"
REQUEST_TIMEOUT = 240

# Long-video narration target.
# Do NOT make this too large because the free routed model can
# become unstable with large generations.
MIN_SCRIPT_CHARACTERS = 4500
TARGET_SCRIPT_CHARACTERS = 4500
MAX_SCRIPT_CHARACTERS = 6500
STOP_NEAR_TARGET_CHARACTERS = 4300

# Chunk settings.
CHUNK_TARGET_CHARACTERS = 950
CHUNK_MIN_CHARACTERS = 450

# Provider output is NOT trusted to respect token limits.
# We therefore validate and locally trim the returned text.
CHUNK_MAX_ACCEPTED_CHARACTERS = 2200

MAX_CHUNKS = 7
MAX_RETRIES_PER_CHUNK = 3

# Smaller limits are more reliable with openrouter/free.
CHUNK_TOKEN_LIMITS = [700, 600, 500]

# Delay between retries.
RETRY_DELAYS = [5, 8, 10]


# ============================================================
# BASIC HELPERS
# ============================================================

def log_line(message: str = "") -> None:
    print(message, flush=True)


def separator() -> None:
    log_line("=" * 70)


def get_openrouter_key() -> str:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()

    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY environment variable is missing."
        )

    return key


def ensure_directories() -> None:
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# TOPIC / CSV
# ============================================================

def load_topics() -> List[Dict[str, str]]:
    if not TOPICS_FILE.exists():
        raise FileNotFoundError(
            f"Topics file not found: {TOPICS_FILE}"
        )

    with TOPICS_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    return rows


def save_topics(rows: List[Dict[str, str]]) -> None:
    if not rows:
        return

    fieldnames = list(rows[0].keys())

    with TOPICS_FILE.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def find_next_topic() -> Dict[str, str]:
    rows = load_topics()

    for row in rows:
        topic_id = str(row.get("id", "")).strip()
        status = str(row.get("status", "")).strip().lower()

        if not topic_id:
            continue

        research_file = RESEARCH_DIR / f"{topic_id}.txt"

        # Script generation starts only after research exists.
        if status == "researched" and research_file.exists():
            return row

    raise RuntimeError(
        "No researched topic is available for script generation."
    )


def update_topic_status(topic_id: str, status: str) -> None:
    rows = load_topics()

    changed = False

    for row in rows:
        if str(row.get("id", "")).strip() == str(topic_id).strip():
            row["status"] = status
            changed = True
            break

    if changed:
        save_topics(rows)


# ============================================================
# RESEARCH
# ============================================================

def load_research(topic_id: str) -> str:
    research_file = RESEARCH_DIR / f"{topic_id}.txt"

    if not research_file.exists():
        raise FileNotFoundError(
            f"Research file not found: {research_file}"
        )

    research = research_file.read_text(
        encoding="utf-8",
        errors="ignore",
    ).strip()

    if not research:
        raise RuntimeError(
            f"Research file is empty: {research_file}"
        )

    return research


def compact_research(research: str, max_chars: int = 8000) -> str:
    """
    Keep prompts reasonably small.

    The beginning usually contains the topic/background and the end
    usually contains evidence/uncertainty/conclusion. Keeping both
    is safer than simply taking the first N characters.
    """
    research = research.strip()

    if len(research) <= max_chars:
        return research

    half = max_chars // 2

    return (
        research[:half]
        + "\n\n[RESEARCH MIDDLE OMITTED FOR CONTEXT SIZE]\n\n"
        + research[-half:]
    )


# ============================================================
# SCRIPT NORMALIZATION
# ============================================================

TELUGU_DIGITS = {
    "0": "౦",
    "1": "౧",
    "2": "౨",
    "3": "౩",
    "4": "౪",
    "5": "౫",
    "6": "౬",
    "7": "౭",
    "8": "౮",
    "9": "౯",
}


TELUGU_NUMBER_WORDS = {
    0: "సున్నా",
    1: "ఒకటి",
    2: "రెండు",
    3: "మూడు",
    4: "నాలుగు",
    5: "ఐదు",
    6: "ఆరు",
    7: "ఏడు",
    8: "ఎనిమిది",
    9: "తొమ్మిది",
    10: "పది",
    11: "పదకొండు",
    12: "పన్నెండు",
    13: "పదమూడు",
    14: "పద్నాలుగు",
    15: "పదిహేను",
    16: "పదహారు",
    17: "పదిహేడు",
    18: "పద్దెనిమిది",
    19: "పందొమ్మిది",
    20: "ఇరవై",
    30: "ముప్పై",
    40: "నలభై",
    50: "యాభై",
    60: "అరవై",
    70: "డెబ్బై",
    80: "ఎనభై",
    90: "తొంభై",
    100: "వంద",
    1000: "వెయ్యి",
}


def number_to_telugu_words(number: int) -> str:
    if number in TELUGU_NUMBER_WORDS:
        return TELUGU_NUMBER_WORDS[number]

    if number < 100:
        tens = (number // 10) * 10
        ones = number % 10

        if ones == 0:
            return TELUGU_NUMBER_WORDS.get(number, str(number))

        return (
            TELUGU_NUMBER_WORDS.get(tens, str(tens))
            + " "
            + TELUGU_NUMBER_WORDS.get(ones, str(ones))
        )

    if number < 1000:
        hundreds = number // 100
        remainder = number % 100

        result = (
            TELUGU_NUMBER_WORDS.get(hundreds, str(hundreds))
            + " వంద"
        )

        if remainder:
            result += " " + number_to_telugu_words(remainder)

        return result

    if number < 100000:
        thousands = number // 1000
        remainder = number % 1000

        if thousands == 1:
            result = "వెయ్యి"
        else:
            result = number_to_telugu_words(thousands) + " వేల"

        if remainder:
            result += " " + number_to_telugu_words(remainder)

        return result

    return str(number)


def normalize_years(text: str) -> str:
    def replace_year(match: re.Match[str]) -> str:
        year = int(match.group(0))

        if 1800 <= year <= 2099:
            return number_to_telugu_words(year)

        return match.group(0)

    return re.sub(r"\b(?:18|19|20)\d{2}\b", replace_year, text)


def normalize_kilometers(text: str) -> str:
    """
    Convert miles to kilometers.
    Do not leave miles in the final narration.
    """

    def replace_miles(match: re.Match[str]) -> str:
        value = float(match.group(1))
        km = value * 1.60934

        if abs(km - round(km)) < 0.01:
            km_text = str(int(round(km)))
        else:
            km_text = f"{km:.1f}".rstrip("0").rstrip(".")

        return f"{km_text} kilometers"

    text = re.sub(
        r"(?i)\b(\d+(?:\.\d+)?)\s*(?:miles|mile|mi)\b",
        replace_miles,
        text,
    )

    return text


def normalize_decimal_zeroes(text: str) -> str:
    return re.sub(
        r"(\d+)\.0+\b",
        r"\1",
        text,
    )


def clean_script(text: str) -> str:
    if not text:
        return ""

    text = text.strip()

    # Remove markdown/code fences if a provider accidentally adds them.
    text = re.sub(r"```(?:text|telugu|te)?", "", text, flags=re.I)
    text = text.replace("```", "")

    # Remove obvious heading markers only.
    text = re.sub(r"^\s*#+\s*", "", text)

    # Remove accidental leading/trailing quotes.
    text = text.strip().strip('"').strip("'").strip()

    # Normalize whitespace without destroying paragraphs.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    text = normalize_kilometers(text)
    text = normalize_decimal_zeroes(text)
    text = normalize_years(text)

    return text.strip()


# ============================================================
# PROVIDER OUTPUT VALIDATION
# ============================================================

PROMPT_ECHO_MARKERS = [
    "we need to produce",
    "we need to",
    "write only",
    "write a telugu",
    "write the script",
    "current narration",
    "research:",
    "task:",
    "instructions:",
    "must be",
    "must include",
    "do not write",
    "do not mention",
    "no english words",
    "no conclusion",
    "end naturally",
    "start with",
    "then introduce",
    "characters",
    "target chunk characters",
    "max output tokens",
    "openrouter",
    "finish reason",
    "ensure that",
    "you are",
    "your task",
    "generate a",
    "generate only",
    "return only",
    "avoid repetition",
    "scene directions",
    "================================================",
]


def looks_like_prompt_echo(text: str) -> bool:
    if not text:
        return True

    lowered = text.lower()

    marker_hits = 0

    for marker in PROMPT_ECHO_MARKERS:
        if marker in lowered:
            marker_hits += 1

    # One marker alone can occasionally occur naturally.
    # Multiple instructional markers are a strong sign that the
    # provider returned our prompt instead of narration.
    if marker_hits >= 2:
        return True

    if "===" in text:
        return True

    # Count obvious English instruction words.
    english_instruction_words = [
        "write",
        "return",
        "must",
        "should",
        "include",
        "avoid",
        "characters",
        "research",
        "current",
        "narration",
        "prompt",
        "instruction",
        "task",
        "generate",
        "ensure",
        "topic",
    ]

    hits = 0

    for word in english_instruction_words:
        if re.search(
            rf"\b{re.escape(word)}\b",
            lowered,
        ):
            hits += 1

    if hits >= 4:
        return True

    return False


def has_reasonable_telugu(text: str) -> bool:
    """
    We do NOT demand 100% Telugu because scientific names and
    unavoidable proper nouns can contain English characters.

    But a normal Telugu narration should contain a meaningful
    amount of Telugu Unicode characters.
    """
    if not text:
        return False

    telugu_chars = len(
        re.findall(r"[\u0C00-\u0C7F]", text)
    )

    letters = len(
        re.findall(r"[A-Za-z\u0C00-\u0C7F]", text)
    )

    if letters == 0:
        return False

    ratio = telugu_chars / letters

    return ratio >= 0.25


def validate_narration_chunk(text: str) -> Tuple[bool, str]:
    if not text:
        return False, "empty provider content"

    if looks_like_prompt_echo(text):
        return False, "provider returned prompt/instruction echo"

    if not has_reasonable_telugu(text):
        return False, "provider output does not look like Telugu narration"

    # Extremely large output from openrouter/free is often a prompt
    # echo or runaway generation. It must not enter TTS.
    if len(text) > CHUNK_MAX_ACCEPTED_CHARACTERS:
        return (
            False,
            (
                f"chunk returned {len(text)} characters, "
                f"above safety limit {CHUNK_MAX_ACCEPTED_CHARACTERS}"
            ),
        )

    return True, ""


# ============================================================
# SENTENCE-BOUNDARY TRIMMING
# ============================================================

def trim_to_sentence_boundary(
    text: str,
    max_chars: int,
    preferred_min_chars: int = 600,
) -> str:
    if len(text) <= max_chars:
        return text.strip()

    candidate = text[:max_chars]

    # Telugu full stop, normal punctuation, question/exclamation.
    punctuation_positions = []

    for mark in ["।", ".", "!", "?", "…"]:
        punctuation_positions.extend(
            [m.start() + 1 for m in re.finditer(re.escape(mark), candidate)]
        )

    punctuation_positions = sorted(
        set(punctuation_positions)
    )

    suitable = [
        pos
        for pos in punctuation_positions
        if pos >= preferred_min_chars
    ]

    if suitable:
        return candidate[: suitable[-1]].strip()

    # If no suitable sentence boundary exists, cut at the last
    # whitespace so TTS doesn't get a broken word.
    whitespace_positions = [
        m.start()
        for m in re.finditer(r"\s", candidate)
    ]

    suitable_spaces = [
        pos
        for pos in whitespace_positions
        if pos >= preferred_min_chars
    ]

    if suitable_spaces:
        return candidate[: suitable_spaces[-1]].strip()

    return candidate.strip()


# ============================================================
# OPENROUTER RESPONSE EXTRACTION
# ============================================================

def extract_script_from_response(data: Dict[str, Any]) -> str:
    choices = data.get("choices")

    if not choices:
        raise RuntimeError(
            "OpenRouter returned no choices."
        )

    choice = choices[0] or {}

    message = choice.get("message") or {}
    content = message.get("content")

    # Some providers can return content as a list.
    if isinstance(content, list):
        pieces: List[str] = []

        for item in content:
            if isinstance(item, dict):
                value = item.get("text")
                if value:
                    pieces.append(str(value))
            elif item:
                pieces.append(str(item))

        content = "".join(pieces)

    if content is None:
        provider = choice.get("provider")
        finish_reason = choice.get("finish_reason")

        raise RuntimeError(
            "OpenRouter returned null script content "
            f"(provider={provider}, finish_reason={finish_reason})"
        )

    content = str(content).strip()

    if not content:
        provider = choice.get("provider")
        finish_reason = choice.get("finish_reason")

        raise RuntimeError(
            "OpenRouter returned empty script content "
            f"(provider={provider}, finish_reason={finish_reason})"
        )

    return content


# ============================================================
# PROMPTS
# ============================================================

def common_script_rules() -> str:
    return """
You are writing narration for a Telugu mystery documentary.

Return ONLY the narration that a Telugu narrator should speak.

IMPORTANT:
- Write naturally in Telugu.
- Use conversational documentary Telugu.
- Facts only.
- Use only information supported by the supplied research.
- Do not invent facts.
- Do not mention AI, prompts, instructions, research files, models, or sources.
- Do not write headings.
- Do not write bullet points.
- Do not write scene directions.
- Do not write English instructions.
- Do not explain what you are doing.
- Do not repeat the prompt.
- Do not repeat the same fact again and again.
- Keep scientific names, place names and necessary proper names natural.
- Avoid unnecessary English words.
- Distances must be expressed in kilometers, not miles.
- Years should be spoken naturally in Telugu words.
- End naturally when the supplied material reaches its logical point.
- Never end abruptly in the middle of a sentence.
"""


def build_initial_prompt(
    title: str,
    research: str,
) -> str:
    return f"""
{common_script_rules()}

TOPIC:
{title}

RESEARCH:
{research}

Write the FIRST part of the narration.

Length target: approximately {CHUNK_TARGET_CHARACTERS} Telugu characters.

Start with an interesting documentary-style hook about the mystery.
Then naturally introduce the place, object or phenomenon and the main question.

Return ONLY the Telugu narration.

Do not return the instructions above.
Do not return the research text.
Do not write labels such as "INTRODUCTION" or "SCRIPT".
"""


def build_continuation_prompt(
    title: str,
    research: str,
    current_script: str,
    is_final: bool,
) -> str:
    current_tail = current_script[-1800:]

    if is_final:
        ending_instruction = """
This is the FINAL part.

Add the remaining important facts or evidence and bring the story
to a natural documentary ending.

Do not leave the narration unfinished.
Do not add a generic "like and subscribe" ending.
"""
    else:
        ending_instruction = """
This is a CONTINUATION.

Continue the story naturally with new information.
Do not repeat facts already covered in the previous narration.
Do not conclude the mystery yet unless the research itself requires it.
"""

    return f"""
{common_script_rules()}

TOPIC:
{title}

RESEARCH:
{research}

THE END OF THE PREVIOUS NARRATION:
{current_tail}

{ending_instruction}

Write approximately {CHUNK_TARGET_CHARACTERS} Telugu characters.

Return ONLY the new Telugu narration.
Do not repeat the previous narration.
Do not return instructions.
Do not return research.
Do not write headings or labels.
"""


# ============================================================
# OPENROUTER REQUEST
# ============================================================

def request_script_chunk(
    prompt: str,
    chunk_number: int,
) -> str:
    api_key = get_openrouter_key()

    last_error: Optional[str] = None

    for attempt in range(1, MAX_RETRIES_PER_CHUNK + 1):
        token_limit = CHUNK_TOKEN_LIMITS[
            min(attempt - 1, len(CHUNK_TOKEN_LIMITS) - 1)
        ]

        separator()

        log_line(
            f"OPENROUTER CHUNK {chunk_number} ATTEMPT: "
            f"{attempt}/{MAX_RETRIES_PER_CHUNK}"
        )
        log_line(f"MODEL: {MODEL}")
        log_line(
            f"TARGET CHUNK CHARACTERS: "
            f"{CHUNK_TARGET_CHARACTERS}"
        )
        log_line(
            f"MAX OUTPUT TOKENS: {token_limit}"
        )

        payload = {
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return only the requested Telugu documentary "
                        "narration. Never return the prompt or instructions."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "max_tokens": token_limit,
            "temperature": 0.45,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/gowthammedia11/telugu-mystery-ai",
            "X-Title": "Telugu Mystery AI",
        }

        try:
            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )

            log_line(
                f"OPENROUTER HTTP STATUS: {response.status_code}"
            )

            if response.status_code != 200:
                body_preview = response.text[:1000]

                raise RuntimeError(
                    f"OpenRouter HTTP {response.status_code}: "
                    f"{body_preview}"
                )

            try:
                data = response.json()
            except Exception as exc:
                raise RuntimeError(
                    f"OpenRouter returned invalid JSON: {exc}"
                ) from exc

            choices = data.get("choices") or []

            if choices:
                finish_reason = choices[0].get(
                    "finish_reason"
                )
            else:
                finish_reason = None

            # ------------------------------------------------
            # NULL CONTENT
            # ------------------------------------------------
            try:
                raw_content = extract_script_from_response(data)
            except RuntimeError as exc:
                last_error = str(exc)

                separator()
                log_line(
                    f"OPENROUTER CHUNK {chunk_number} "
                    f"ATTEMPT {attempt} FAILED"
                )
                log_line(f"ERROR: {last_error}")
                separator()

                if attempt < MAX_RETRIES_PER_CHUNK:
                    delay = RETRY_DELAYS[
                        min(attempt - 1, len(RETRY_DELAYS) - 1)
                    ]

                    log_line(
                        f"RETRYING WITH LOWER OUTPUT LIMIT "
                        f"IN {delay} SECONDS..."
                    )

                    time.sleep(delay)
                    continue

                break

            cleaned = clean_script(raw_content)

            log_line(
                f"OPENROUTER CHUNK {chunk_number} "
                f"CHARACTERS: {len(cleaned)}"
            )
            log_line(
                f"OPENROUTER CHUNK {chunk_number} "
                f"FINISH REASON: {finish_reason}"
            )

            # ------------------------------------------------
            # VALIDATE BEFORE TRIMMING
            # ------------------------------------------------
            valid, validation_error = validate_narration_chunk(
                cleaned
            )

            if not valid:

                # Special handling:
                # If the provider returned a legitimate Telugu
                # narration that is simply longer than our safe
                # chunk size, trim it instead of rejecting it.
                if (
                    "above safety limit" in validation_error
                    and not looks_like_prompt_echo(cleaned)
                    and has_reasonable_telugu(cleaned)
                ):
                    trimmed = trim_to_sentence_boundary(
                        cleaned,
                        CHUNK_MAX_ACCEPTED_CHARACTERS,
                        preferred_min_chars=700,
                    )

                    if len(trimmed) >= CHUNK_MIN_CHARACTERS:
                        log_line(
                            f"CHUNK {chunk_number} IS LONGER THAN "
                            f"TARGET BUT VALID TELUGU WAS RETURNED."
                        )
                        log_line(
                            f"TRIMMING TO "
                            f"{len(trimmed)} CHARACTERS AT "
                            f"A SENTENCE BOUNDARY."
                        )

                        return trimmed

                last_error = validation_error

                separator()
                log_line(
                    f"OPENROUTER CHUNK {chunk_number} "
                    f"ATTEMPT {attempt} FAILED"
                )
                log_line(
                    f"ERROR: {validation_error}"
                )
                separator()

                if attempt < MAX_RETRIES_PER_CHUNK:
                    delay = RETRY_DELAYS[
                        min(attempt - 1, len(RETRY_DELAYS) - 1)
                    ]

                    log_line(
                        f"RETRYING WITH LOWER OUTPUT LIMIT "
                        f"IN {delay} SECONDS..."
                    )

                    time.sleep(delay)
                    continue

                break

            # ------------------------------------------------
            # SHORT VALID CONTENT
            # ------------------------------------------------
            if len(cleaned) < CHUNK_MIN_CHARACTERS:
                last_error = (
                    f"Chunk {chunk_number} returned only "
                    f"{len(cleaned)} characters. "
                    f"Minimum required is {CHUNK_MIN_CHARACTERS}."
                )

                separator()
                log_line(
                    f"OPENROUTER CHUNK {chunk_number} "
                    f"ATTEMPT {attempt} FAILED"
                )
                log_line(
                    f"ERROR: {last_error}"
                )
                separator()

                if attempt < MAX_RETRIES_PER_CHUNK:
                    delay = RETRY_DELAYS[
                        min(attempt - 1, len(RETRY_DELAYS) - 1)
                    ]

                    time.sleep(delay)
                    continue

                break

            # ------------------------------------------------
            # SUCCESS
            # ------------------------------------------------
            separator()
            log_line(
                f"OPENROUTER CHUNK {chunk_number} "
                f"ACCEPTED: {len(cleaned)} CHARACTERS"
            )
            separator()

            return cleaned

        except requests.RequestException as exc:
            last_error = (
                f"OpenRouter request failed: {exc}"
            )

            separator()
            log_line(
                f"OPENROUTER CHUNK {chunk_number} "
                f"ATTEMPT {attempt} FAILED"
            )
            log_line(f"ERROR: {last_error}")
            separator()

            if attempt < MAX_RETRIES_PER_CHUNK:
                delay = RETRY_DELAYS[
                    min(attempt - 1, len(RETRY_DELAYS) - 1)
                ]

                time.sleep(delay)
                continue

        except Exception as exc:
            last_error = str(exc)

            separator()
            log_line(
                f"OPENROUTER CHUNK {chunk_number} "
                f"ATTEMPT {attempt} FAILED"
            )
            log_line(f"ERROR: {last_error}")
            separator()

            if attempt < MAX_RETRIES_PER_CHUNK:
                delay = RETRY_DELAYS[
                    min(attempt - 1, len(RETRY_DELAYS) - 1)
                ]

                time.sleep(delay)
                continue

    raise RuntimeError(
        f"OpenRouter chunk {chunk_number} generation failed "
        f"after {MAX_RETRIES_PER_CHUNK} attempts. "
        f"Last error: {last_error}"
    )


# ============================================================
# SCRIPT GENERATION
# ============================================================

def generate_script(
    topic_id: str,
    title: str,
    research: str,
    *args: Any,
    **kwargs: Any,
) -> str:
    """
    Generate the long Telugu narration.

    *args / **kwargs are intentionally accepted so this remains
    compatible with the existing build_pipeline.py even if it
    passes an additional optional argument.
    """

    ensure_directories()

    separator()
    log_line("GENERATING LONG TELUGU SCRIPT IN CHUNKS")
    separator()

    if not research.strip():
        raise RuntimeError(
            f"Research is empty for topic {topic_id}."
        )

    research_context = compact_research(
        research,
        max_chars=8000,
    )

    update_topic_status(
        topic_id,
        "script_processing",
    )

    chunks: List[str] = []
    current_script = ""

    try:
        # ----------------------------------------------------
        # CHUNK 1
        # ----------------------------------------------------
        prompt = build_initial_prompt(
            title=title,
            research=research_context,
        )

        chunk = request_script_chunk(
            prompt,
            chunk_number=1,
        )

        chunks.append(chunk)
        current_script = "\n\n".join(chunks)

        log_line(
            f"TOTAL SCRIPT CHARACTERS AFTER CHUNK 1: "
            f"{len(current_script)}"
        )

        # ----------------------------------------------------
        # CONTINUATION CHUNKS
        # ----------------------------------------------------
        chunk_number = 2

        while (
            len(current_script) < STOP_NEAR_TARGET_CHARACTERS
            and chunk_number <= MAX_CHUNKS
        ):
            is_final = (
                len(current_script) >=
                TARGET_SCRIPT_CHARACTERS - CHUNK_TARGET_CHARACTERS
            )

            prompt = build_continuation_prompt(
                title=title,
                research=research_context,
                current_script=current_script,
                is_final=is_final,
            )

            chunk = request_script_chunk(
                prompt,
                chunk_number=chunk_number,
            )

            chunks.append(chunk)

            current_script = "\n\n".join(chunks)

            log_line(
                f"TOTAL SCRIPT CHARACTERS AFTER CHUNK "
                f"{chunk_number}: {len(current_script)}"
            )

            if len(current_script) >= TARGET_SCRIPT_CHARACTERS:
                break

            chunk_number += 1

        # ----------------------------------------------------
        # FINAL CLEANUP
        # ----------------------------------------------------
        final_script = clean_script(
            "\n\n".join(chunks)
        )

        # If provider produced an unexpectedly huge but valid
        # script, keep it bounded before TTS.
        if len(final_script) > MAX_SCRIPT_CHARACTERS:
            final_script = trim_to_sentence_boundary(
                final_script,
                MAX_SCRIPT_CHARACTERS,
                preferred_min_chars=MIN_SCRIPT_CHARACTERS,
            )

        log_line(
            f"FINAL GENERATED SCRIPT CHARACTERS: "
            f"{len(final_script)}"
        )

        if len(final_script) < MIN_SCRIPT_CHARACTERS:
            raise RuntimeError(
                "Generated Telugu script is too short: "
                f"{len(final_script)} characters. "
                f"Minimum required: {MIN_SCRIPT_CHARACTERS}."
            )

        # Final safety validation prevents accidental prompt
        # content from reaching edge-tts.
        if looks_like_prompt_echo(final_script):
            raise RuntimeError(
                "Final script appears to contain prompt/instruction "
                "echo. TTS generation was blocked."
            )

        if not has_reasonable_telugu(final_script):
            raise RuntimeError(
                "Final script does not contain enough Telugu narration."
            )

        update_topic_status(
            topic_id,
            "script_ready",
        )

        separator()
        log_line("LONG SCRIPT GENERATED SUCCESSFULLY")
        log_line(
            f"GENERATED SCRIPT CHARACTERS: "
            f"{len(final_script)}"
        )
        separator()

        return final_script

    except Exception:
        # Do not permanently lock the topic if generation failed.
        try:
            update_topic_status(
                topic_id,
                "researched",
            )
        except Exception:
            pass

        raise


# ============================================================
# SAVE SCRIPT
# ============================================================

def save_script(
    topic_id: str,
    script: str,
) -> Path:
    ensure_directories()

    output_file = SCRIPTS_DIR / f"{topic_id}.txt"

    output_file.write_text(
        script.strip() + "\n",
        encoding="utf-8",
    )

    log_line(
        f"SAVED SCRIPT: {output_file}"
    )

    return output_file


# ============================================================
# STANDALONE ENTRY POINT
# ============================================================

def main() -> None:
    separator()
    log_line("TELUGU MYSTERY AI — SCRIPT GENERATOR")
    separator()

    ensure_directories()

    topic = find_next_topic()

    topic_id = str(
        topic.get("id", "")
    ).strip()

    title = str(
        topic.get("title", "")
    ).strip()

    if not topic_id:
        raise RuntimeError(
            "Next topic has no ID."
        )

    if not title:
        raise RuntimeError(
            f"Topic {topic_id} has no title."
        )

    research = load_research(
        topic_id
    )

    separator()
    log_line(f"TOPIC: {topic_id}")
    log_line(f"TITLE: {title}")
    separator()
    log_line(
        f"RESEARCH ALREADY EXISTS: "
        f"research/{topic_id}.txt"
    )
    log_line(
        f"RESEARCH CHARACTERS: {len(research)}"
    )
    separator()

    script = generate_script(
        topic_id,
        title,
        research,
    )

    save_script(
        topic_id,
        script,
    )

    separator()
    log_line("SCRIPT GENERATION COMPLETE")
    separator()


if __name__ == "__main__":
    main()
````
