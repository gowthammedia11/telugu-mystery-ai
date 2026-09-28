import os
import re
import time
import requests

from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY",
    ""
).strip()

# Current free OpenRouter endpoints.
MODELS = [
    "nvidia/nemotron-3.5-lightning:free",
    "google/gemma-4-26b-a4b-it:free",
    "qwen/qwen3.8-27b:free",
]

# Final long-script target.
MIN_CHARS = 4500
TARGET_MIN_CHARS = 5000
TARGET_MAX_CHARS = 5500
MAX_CHARS = 5700

# Four-section generation.
SECTION_COUNT = 4
SECTION_MIN_CHARS = 1100
SECTION_TARGET_MIN = 1250
SECTION_TARGET_MAX = 1600
SECTION_MAX_CHARS = 1750

MAX_ATTEMPTS_PER_SECTION = 3

SCRIPTS_DIR = BASE_DIR / "scripts"


# ============================================================
# URL CLEANUP
# ============================================================

def remove_urls(text):
    text = re.sub(
        r"https?://\S+",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"www\.\S+",
        "",
        text,
        flags=re.IGNORECASE
    )

    return text


# ============================================================
# COORDINATE CLEANUP
# ============================================================

def remove_coordinates(text):
    patterns = [
        r"\b\d{1,3}\s*°\s*\d{1,2}\s*[′']?\s*\d{0,2}(?:\.\d+)?\s*[″\"]?\s*[NS]\b",
        r"\b\d{1,3}\s*°\s*\d{1,2}\s*[′']?\s*\d{0,2}(?:\.\d+)?\s*[″\"]?\s*[EW]\b",
        r"\b\d{1,3}(?:\.\d+)?\s*[NS]\b",
        r"\b\d{1,3}(?:\.\d+)?\s*[EW]\b",
        r"\b(?:latitude|lat)\s*[:\-]?\s*\d+(?:\.\d+)?\b",
        r"\b(?:longitude|lon|lng)\s*[:\-]?\s*\d+(?:\.\d+)?\b",
        r"\b\d+(?:\.\d+)?\s*,\s*\d+(?:\.\d+)?\b",
    ]

    for pattern in patterns:
        text = re.sub(
            pattern,
            " ",
            text,
            flags=re.IGNORECASE
        )

    return text


# ============================================================
# FORBIDDEN MEASUREMENT CLEANUP
# ============================================================

def remove_forbidden_measurements(text):

    def miles_to_km(match):
        value = float(match.group(1))
        kilometres = value * 1.60934

        if kilometres >= 100:
            return f"{round(kilometres)} kilometres"

        return f"{round(kilometres, 1)} kilometres"

    def feet_to_metres(match):
        value = float(match.group(1))
        metres = value * 0.3048

        if metres >= 100:
            return f"{round(metres)} metres"

        return f"{round(metres, 1)} metres"

    text = re.sub(
        r"(\d+(?:\.\d+)?)\s*(?:miles|mile|mi)\b",
        miles_to_km,
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"(\d+(?:\.\d+)?)\s*(?:feet|foot|ft)\b",
        feet_to_metres,
        text,
        flags=re.IGNORECASE
    )

    return text


# ============================================================
# BASIC CLEANUP
# ============================================================

def clean_text(text):
    if not text:
        return ""

    text = remove_urls(text)

    text = remove_coordinates(text)

    text = remove_forbidden_measurements(text)

    text = re.sub(
        r"\b(?:latitude|longitude|coordinates?|gps coordinates?)\b",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = text.replace(
        "```text",
        ""
    )

    text = text.replace(
        "```plaintext",
        ""
    )

    text = text.replace(
        "```txt",
        ""
    )

    text = text.replace(
        "```",
        ""
    )

    text = text.replace(
        "**",
        ""
    )

    text = text.replace(
        "__",
        ""
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# META TEXT DETECTION
# ============================================================

def is_meta_line(line):
    stripped = line.strip()

    if not stripped:
        return False

    lowered = stripped.lower()

    patterns = [
        "here is the script",
        "here's the script",
        "here is a script",
        "here's a script",
        "below is the script",
        "below is a script",
        "sure, here",
        "sure here",
        "script:",
        "script :",
        "narration:",
        "narration :",
        "final script:",
        "final narration:",
        "documentary script:",
        "documentary narration:",
        "character count",
        "word count",
        "characters:",
        "words:",
        "sources:",
        "references:",
        "source:",
        "analysis:",
        "reasoning:",
        "instructions:",
        "prompt:",
        "according to the prompt",
        "according to your instructions",
        "as an ai",
        "as a language model",
        "i will write",
        "i'll write",
        "i have written",
        "the following script",
        "the following narration",
    ]

    if any(
        pattern in lowered
        for pattern in patterns
    ):
        return True

    if stripped.startswith("#"):
        return True

    if re.match(
        r"^\s*(?:\d+[\.\)]|[-*•])\s+",
        stripped
    ):
        return True

    return False


# ============================================================
# EXTRACT NARRATION
# ============================================================

def extract_narration(text):
    if not text:
        return ""

    text = clean_text(
        text
    )

    lines = text.splitlines()

    result = []

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if is_meta_line(line):
            continue

        result.append(line)

    text = " ".join(
        result
    )

    return text.strip()


# ============================================================
# SENTENCES
# ============================================================

def split_sentences(text):
    if not text:
        return []

    parts = re.split(
        r"(?<=[.!?।])\s+",
        text.strip()
    )

    return [
        part.strip()
        for part in parts
        if part.strip()
    ]


def normalize_sentence(sentence):
    return re.sub(
        r"\s+",
        " ",
        sentence.strip()
    )


def sentence_key(sentence):
    sentence = sentence.lower()

    sentence = re.sub(
        r"[^a-z0-9\u0C00-\u0C7F]+",
        " ",
        sentence
    )

    sentence = re.sub(
        r"\s+",
        " ",
        sentence
    )

    return sentence.strip()


# ============================================================
# REPETITION CHECK
# ============================================================

def repetition_ratio(text):
    sentences = split_sentences(
        text
    )

    if len(sentences) < 5:
        return 0.0

    keys = [
        sentence_key(sentence)
        for sentence in sentences
    ]

    keys = [
        key
        for key in keys
        if len(key) > 15
    ]

    if not keys:
        return 0.0

    return 1 - (
        len(set(keys))
        / len(keys)
    )


# ============================================================
# META CHECK
# ============================================================

def contains_meta_text(text):
    lowered = text.lower()

    forbidden = [
        "as an ai",
        "as a language model",
        "ai generated",
        "generated by ai",
        "here is the script",
        "here's the script",
        "below is the script",
        "script:",
        "narration:",
        "final script:",
        "final narration:",
        "character count",
        "word count",
        "sources:",
        "references:",
        "according to the prompt",
        "according to your instructions",
        "prompt:",
        "instructions:",
        "analysis:",
        "reasoning:",
    ]

    return any(
        item in lowered
        for item in forbidden
    )


# ============================================================
# FORBIDDEN CONTENT CHECK
# ============================================================

def contains_forbidden_content(text):
    lowered = text.lower()

    patterns = [
        r"https?://",
        r"www\.",
        r"\b\d+(?:\.\d+)?\s*(?:miles?|mi)\b",
        r"\b\d+(?:\.\d+)?\s*(?:feet|foot|ft)\b",
        r"\blatitude\b",
        r"\blongitude\b",
        r"\bcoordinates?\b",
        r"\bgps coordinates?\b",
        r"\b\d{1,3}\s*°\s*\d{1,3}",
    ]

    for pattern in patterns:
        if re.search(
            pattern,
            lowered,
            flags=re.IGNORECASE
        ):
            return True

    return False


# ============================================================
# FINAL SCRIPT SANITIZATION
# ============================================================

def sanitize_final_script(text):
    text = extract_narration(
        text
    )

    sentences = split_sentences(
        text
    )

    cleaned = []

    seen = set()

    for sentence in sentences:

        sentence = normalize_sentence(
            sentence
        )

        if not sentence:
            continue

        key = sentence_key(
            sentence
        )

        if not key:
            continue

        if key in seen:
            continue

        seen.add(
            key
        )

        cleaned.append(
            sentence
        )

    text = " ".join(
        cleaned
    )

    text = clean_text(
        text
    )

    return text.strip()


# ============================================================
# TRIM FINAL SCRIPT
# ============================================================

def trim_to_target(
    text,
    max_chars=TARGET_MAX_CHARS
):
    if len(text) <= max_chars:
        return text

    sentences = split_sentences(
        text
    )

    result = []

    current_length = 0

    for sentence in sentences:

        sentence = sentence.strip()

        if not sentence:
            continue

        extra = len(
            sentence
        )

        if result:
            extra += 1

        if (
            current_length
            + extra
            > max_chars
        ):
            break

        result.append(
            sentence
        )

        current_length += extra

    trimmed = " ".join(
        result
    ).strip()

    if len(trimmed) >= MIN_CHARS:
        return trimmed

    fallback = text[
        :max_chars
    ]

    fallback = fallback.rsplit(
        " ",
        1
    )[0].strip()

    return fallback


# ============================================================
# VALIDATE FINAL SCRIPT
# ============================================================

def validate_script(text):

    if not text:
        return False, "EMPTY SCRIPT"

    length = len(text)

    if length < MIN_CHARS:
        return False, (
            f"TOO SHORT: {length} characters"
        )

    if length > MAX_CHARS:
        return False, (
            f"TOO LONG: {length} characters"
        )

    if contains_meta_text(text):
        return False, (
            "META TEXT DETECTED"
        )

    if contains_forbidden_content(
        text
    ):
        return False, (
            "FORBIDDEN CONTENT DETECTED"
        )

    ratio = repetition_ratio(
        text
    )

    if ratio > 0.30:
        return False, (
            f"TOO REPETITIVE: {ratio:.2f}"
        )

    sentences = split_sentences(
        text
    )

    if len(sentences) < 25:
        return False, (
            f"TOO FEW SENTENCES: {len(sentences)}"
        )

    return True, "VALID"


# ============================================================
# SECTION PROMPTS
# ============================================================

SECTION_INSTRUCTIONS = {
    1: """
ఈ భాగంలో కథకు బలమైన ప్రారంభం ఇవ్వాలి.
Yonaguni Monument ఎక్కడ ఉంది, అది ఎలా కనిపిస్తుంది,
1985లో ఎలా గుర్తించబడింది వంటి విషయాలను natural documentary
style లో explain చేయాలి.

కేవలం research లో ఉన్న facts మాత్రమే ఉపయోగించాలి.
ప్రేక్షకుడికి విషయం ఎందుకు ఆసక్తికరంగా ఉందో explain చేయాలి.
ఈ భాగం మధ్యలో లేదా చివర్లో పూర్తిగా conclusion ఇవ్వకూడదు.
""",

    2: """
ఈ భాగంలో Yonaguni Monument సహజ భౌగోళిక నిర్మాణం అయ్యి ఉండవచ్చనే
వివరణను explain చేయాలి.

రాతి పొరలు, sandstone/shale, fractures, tectonic uplift,
sea-level change, erosion మరియు geological setting వంటి
research లో ఉన్న అంశాలను natural flow లో explain చేయాలి.

మొదటి భాగం facts repeat చేయకూడదు.
""",

    3: """
ఈ భాగంలో ఇది మనుషుల నిర్మాణం అయ్యి ఉండవచ్చనే theory మరియు
దానికి అనుకూలంగా లేదా వ్యతిరేకంగా ఉన్న evidence గురించి
neutral factual documentary narration రాయాలి.

Masaaki Kimura పరిశోధనలు, rock composition, tool marks లేకపోవడం,
artifacts లభించకపోవడం, underwater observations వంటి research
లో ఉన్న విషయాలను explain చేయాలి.

ఏ theory నిజమో నువ్వే నిర్ణయించకూడదు.
""",

    4: """
ఈ భాగంలో Yonaguni Monument చుట్టూ ఉన్న myths మరియు ఇప్పటికీ
తెలియని విషయాలను explain చేసి కథను సహజంగా ముగించాలి.

Atlantis, aliens, torii gate, UNESCO status, dating claims వంటి
research లోని myths/facts distinction ను జాగ్రత్తగా explain చేయాలి.

చివర్లో precise age, possible human modification మరియు ఇంకా
పరిశోధన అవసరమైన ప్రశ్నలను mention చేసి strong but factual
documentary ending ఇవ్వాలి.
"""
}


def build_section_prompt(
    topic_id,
    title,
    research,
    section_number
):

    instruction = SECTION_INSTRUCTIONS[
        section_number
    ]

    return f"""
నువ్వు తెలుగు mystery documentary narration writer.

టాపిక్:
{title}

టాపిక్ ID:
{topic_id}

ఇది 4-part long documentary లో భాగం {section_number}.

RESEARCH:
{research}

ఈ భాగానికి ప్రత్యేక సూచనలు:
{instruction}

కఠినమైన నియమాలు:

1. ఈ భాగం 1250 నుంచి 1600 characters మధ్య ఉండాలి.
2. కనీసం 1100 characters ఉండాలి.
3. సహజమైన conversational Telugu వాడాలి.
4. ఇది narration మాత్రమే కావాలి.
5. Headings వద్దు.
6. Bullet points వద్దు.
7. Numbered lists వద్దు.
8. Markdown వద్దు.
9. URLs వద్దు.
10. Sources list వద్దు.
11. References list వద్దు.
12. AI గురించి చెప్పకూడదు.
13. Prompt లేదా instructions గురించి చెప్పకూడదు.
14. Character count లేదా word count చెప్పకూడదు.
15. Coordinates వద్దు.
16. Latitude లేదా longitude వద్దు.
17. GPS coordinates వద్దు.
18. Miles లేదా mile లేదా mi వద్దు.
19. Feet లేదా foot లేదా ft వద్దు.
20. దూరాలకు kilometres లేదా km మాత్రమే వాడాలి.
21. ఎత్తు, లోతు, వెడల్పు వంటి వాటికి metres లేదా m మాత్రమే వాడాలి.
22. Research లో లేని facts కల్పించకూడదు.
23. Myths ను facts లాగా చెప్పకూడదు.
24. నిర్ధారించని విషయాలను certainty తో చెప్పకూడదు.
25. ఒకే idea ను repeated wording తో చెప్పకూడదు.
26. అవసరం లేని decimals వద్దు.
27. English words అవసరమైన technical terms మాత్రమే.
28. ఈ భాగం ఇతర భాగాల content ను unnecessarily repeat చేయకూడదు.
29. ఈ భాగాన్ని ఒక continuous documentary narration గా రాయాలి.
30. "Here is the script" లేదా "Below is..." వంటి introduction వద్దు.
31. చివరి line incomplete sentence గా ఉండకూడదు.
32. ONLY narration return చేయాలి.

మొత్తం paragraph flow సహజంగా ఉండాలి.
"""
    

# ============================================================
# OPENROUTER RESPONSE EXTRACTION
# ============================================================

def extract_content(data):

    choices = data.get(
        "choices"
    )

    if not isinstance(
        choices,
        list
    ):
        return ""

    if not choices:
        return ""

    choice = choices[0]

    if not isinstance(
        choice,
        dict
    ):
        return ""

    message = choice.get(
        "message"
    )

    if not isinstance(
        message,
        dict
    ):
        return ""

    content = message.get(
        "content"
    )

    if isinstance(
        content,
        str
    ):
        return content.strip()

    if isinstance(
        content,
        list
    ):

        parts = []

        for item in content:

            if not isinstance(
                item,
                dict
            ):
                continue

            item_text = item.get(
                "text"
            )

            if isinstance(
                item_text,
                str
            ):
                parts.append(
                    item_text
                )

        return "\n".join(
            parts
        ).strip()

    return ""


# ============================================================
# OPENROUTER REQUEST
# ============================================================

def request_openrouter(
    prompt,
    model
):

    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not configured"
        )

    url = (
        "https://openrouter.ai/api/v1/"
        "chat/completions"
    )

    headers = {
        "Authorization": (
            f"Bearer {OPENROUTER_API_KEY}"
        ),
        "Content-Type": "application/json",
        "HTTP-Referer": (
            "https://github.com/"
            "gowthammedia11/telugu-mystery-ai"
        ),
        "X-Title": (
            "Telugu Mystery AI"
        ),
    }

    payload = {
        "model": model,

        "messages": [
            {
                "role": "system",
                "content": (
                    "Return only factual Telugu "
                    "documentary narration. "
                    "Do not return reasoning, "
                    "analysis, headings, or meta text."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],

        "temperature": 0.45,

        "max_tokens": 1800,

        "reasoning": {
            "enabled": False
        },
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=180
    )

    raw_response = (
        response.text.strip()
    )

    if response.status_code >= 400:

        raise RuntimeError(
            f"HTTP {response.status_code}: "
            f"{raw_response[:700]}"
        )

    try:

        data = response.json()

    except ValueError:

        raise RuntimeError(
            "OpenRouter returned invalid JSON: "
            f"{raw_response[:500]}"
        )

    content = extract_content(
        data
    )

    if content:
        return content

    error_data = data.get(
        "error"
    )

    if error_data:

        if isinstance(
            error_data,
            dict
        ):

            message = error_data.get(
                "message",
                "Unknown OpenRouter error"
            )

            raise RuntimeError(
                f"OpenRouter error: {message}"
            )

        raise RuntimeError(
            f"OpenRouter error: {error_data}"
        )

    choices = data.get(
        "choices"
    )

    if choices:

        choice = choices[0]

        finish_reason = ""

        if isinstance(
            choice,
            dict
        ):

            finish_reason = (
                choice.get(
                    "finish_reason",
                    ""
                )
            )

            message = choice.get(
                "message",
                {}
            )

            if isinstance(
                message,
                dict
            ):

                reasoning = message.get(
                    "reasoning"
                )

                if reasoning:
                    raise RuntimeError(
                        "Model returned reasoning "
                        "but no final content"
                    )

        raise RuntimeError(
            "OpenRouter returned empty content "
            f"(finish_reason={finish_reason})"
        )

    raise RuntimeError(
        "OpenRouter returned empty content"
    )


# ============================================================
# GENERATE ONE SECTION
# ============================================================

def generate_section(
    topic_id,
    title,
    research,
    section_number
):

    prompt = build_section_prompt(
        topic_id,
        title,
        research,
        section_number
    )

    last_error = (
        "Unknown section error"
    )

    # Change model order on every section so
    # rate-limiting on one provider does not stop
    # the complete pipeline.
    start_index = (
        section_number - 1
    ) % len(MODELS)

    ordered_models = (
        MODELS[start_index:]
        + MODELS[:start_index]
    )

    for attempt in range(
        1,
        MAX_ATTEMPTS_PER_SECTION + 1
    ):

        model_index = (
            attempt - 1
        ) % len(ordered_models)

        model = ordered_models[
            model_index
        ]

        print(
            "-" * 70
        )

        print(
            f"SECTION {section_number}/{SECTION_COUNT}"
        )

        print(
            f"SECTION ATTEMPT: "
            f"{attempt}/{MAX_ATTEMPTS_PER_SECTION}"
        )

        print(
            f"MODEL: {model}"
        )

        try:

            raw = request_openrouter(
                prompt,
                model
            )

            print(
                f"RAW SECTION LENGTH: "
                f"{len(raw)}"
            )

            cleaned = sanitize_final_script(
                raw
            )

            print(
                f"CLEANED SECTION LENGTH: "
                f"{len(cleaned)}"
            )

            if len(cleaned) > SECTION_MAX_CHARS:

                cleaned = trim_section(
                    cleaned,
                    SECTION_MAX_CHARS
                )

                print(
                    f"TRIMMED SECTION LENGTH: "
                    f"{len(cleaned)}"
                )

            if len(cleaned) < SECTION_MIN_CHARS:

                last_error = (
                    f"SECTION TOO SHORT: "
                    f"{len(cleaned)} characters"
                )

                print(
                    f"SECTION VALIDATION FAILED: "
                    f"{last_error}"
                )

                continue

            if contains_meta_text(
                cleaned
            ):

                last_error = (
                    "META TEXT DETECTED"
                )

                print(
                    f"SECTION VALIDATION FAILED: "
                    f"{last_error}"
                )

                continue

            if contains_forbidden_content(
                cleaned
            ):

                last_error = (
                    "FORBIDDEN CONTENT DETECTED"
                )

                print(
                    f"SECTION VALIDATION FAILED: "
                    f"{last_error}"
                )

                continue

            print(
                f"SECTION {section_number} VALID"
            )

            return cleaned

        except Exception as exc:

            last_error = str(
                exc
            )

            print(
                "SECTION GENERATION ERROR: "
                f"{last_error}"
            )

        time.sleep(2)

    raise RuntimeError(
        f"Section {section_number} generation failed "
        f"after {MAX_ATTEMPTS_PER_SECTION} attempts: "
        f"{last_error}"
    )


# ============================================================
# TRIM ONE SECTION
# ============================================================

def trim_section(
    text,
    max_chars
):

    if len(text) <= max_chars:
        return text

    sentences = split_sentences(
        text
    )

    result = []

    current_length = 0

    for sentence in sentences:

        sentence = sentence.strip()

        if not sentence:
            continue

        extra = len(
            sentence
        )

        if result:
            extra += 1

        if (
            current_length
            + extra
            > max_chars
        ):
            break

        result.append(
            sentence
        )

        current_length += extra

    return " ".join(
        result
    ).strip()


# ============================================================
# COMBINE SECTIONS
# ============================================================

def combine_sections(
    sections
):

    text = " ".join(
        section.strip()
        for section in sections
        if section.strip()
    )

    return sanitize_final_script(
        text
    )


# ============================================================
# GENERATE FINAL LONG SCRIPT
# ============================================================

def generate_script(
    topic_id,
    title,
    research
):

    print("=" * 70)
    print(
        "GENERATING LONG SCRIPT"
    )
    print("=" * 70)

    sections = []

    for section_number in range(
        1,
        SECTION_COUNT + 1
    ):

        section = generate_section(
            topic_id,
            title,
            research,
            section_number
        )

        sections.append(
            section
        )

        current_total = len(
            combine_sections(
                sections
            )
        )

        print(
            f"CURRENT COMBINED LENGTH: "
            f"{current_total}"
        )

    # --------------------------------------------------------
    # Combine all four sections.
    # --------------------------------------------------------

    final_script = combine_sections(
        sections
    )

    print("=" * 70)

    print(
        f"COMBINED SCRIPT LENGTH: "
        f"{len(final_script)}"
    )

    # --------------------------------------------------------
    # If slightly above target, trim at sentence boundary.
    # --------------------------------------------------------

    if len(final_script) > TARGET_MAX_CHARS:

        final_script = trim_to_target(
            final_script,
            TARGET_MAX_CHARS
        )

        final_script = sanitize_final_script(
            final_script
        )

        print(
            f"FINAL TRIMMED LENGTH: "
            f"{len(final_script)}"
        )

    # --------------------------------------------------------
    # Final cleanup.
    # --------------------------------------------------------

    final_script = sanitize_final_script(
        final_script
    )

    # --------------------------------------------------------
    # Final validation.
    # --------------------------------------------------------

    valid, reason = validate_script(
        final_script
    )

    if valid:

        print(
            "SCRIPT VALIDATION: PASSED"
        )

        print(
            f"FINAL SCRIPT LENGTH: "
            f"{len(final_script)}"
        )

        return final_script

    # --------------------------------------------------------
    # If four sections together are unexpectedly short,
    # try one controlled expansion call.
    # --------------------------------------------------------

    if (
        len(final_script)
        < TARGET_MIN_CHARS
    ):

        print(
            "=" * 70
        )

        print(
            "FINAL SCRIPT BELOW TARGET"
        )

        print(
            f"CURRENT: {len(final_script)}"
        )

        print(
            f"TARGET: {TARGET_MIN_CHARS}+"
        )

        print(
            "GENERATING FINAL EXPANSION"
        )

        expansion_prompt = f"""
కింద ఉన్న తెలుగు documentary narration ను
అదే factual information ఆధారంగా సహజంగా expand చేయాలి.

EXISTING NARRATION:

{final_script}

టాపిక్:
{title}

Research:
{research}

కఠినమైన నియమాలు:

1. Existing narration ను పూర్తిగా rewrite చేయకూడదు.
2. అవసరమైన చోట మాత్రమే useful factual details add చేయాలి.
3. Repetition వద్దు.
4. మొత్తం final output 5000 నుంచి 5500 characters మధ్య ఉండాలి.
5. Coordinates వద్దు.
6. Latitude లేదా longitude వద్దు.
7. Miles వద్దు.
8. Feet వద్దు.
9. URLs వద్దు.
10. AI mention వద్దు.
11. Headings వద్దు.
12. Bullet points వద్దు.
13. Markdown వద్దు.
14. Research లో లేని facts కల్పించకూడదు.
15. చివర natural documentary ending ఉండాలి.
16. ONLY final narration return చేయాలి.
"""

        for model in MODELS:

            print(
                f"EXPANSION MODEL: {model}"
            )

            try:

                expanded_raw = request_openrouter(
                    expansion_prompt,
                    model
                )

                expanded = sanitize_final_script(
                    expanded_raw
                )

                print(
                    f"EXPANDED LENGTH: "
                    f"{len(expanded)}"
                )

                if len(expanded) > TARGET_MAX_CHARS:

                    expanded = trim_to_target(
                        expanded,
                        TARGET_MAX_CHARS
                    )

                    expanded = sanitize_final_script(
                        expanded
                    )

                valid, reason = validate_script(
                    expanded
                )

                if valid:

                    print(
                        "EXPANDED SCRIPT VALIDATION: PASSED"
                    )

                    print(
                        f"FINAL SCRIPT LENGTH: "
                        f"{len(expanded)}"
                    )

                    return expanded

                print(
                    "EXPANDED SCRIPT VALIDATION FAILED: "
                    f"{reason}"
                )

            except Exception as exc:

                print(
                    "EXPANSION ERROR: "
                    f"{exc}"
                )

            time.sleep(2)

    # --------------------------------------------------------
    # Final failure.
    # --------------------------------------------------------

    raise RuntimeError(
        "Script generation failed: "
        f"{reason}. "
        f"Final length={len(final_script)}"
    )


# ============================================================
# SAVE SCRIPT
# ============================================================

def save_script(
    topic_id,
    script_text
):

    SCRIPTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    topic_id = str(
        topic_id
    ).zfill(3)

    path = (
        SCRIPTS_DIR
        / f"{topic_id}.txt"
    )

    path.write_text(
        script_text.strip(),
        encoding="utf-8"
    )

    print(
        f"SCRIPT SAVED: {path}"
    )

    return path


# ============================================================
# MODULE ENTRY
# ============================================================

if __name__ == "__main__":

    print(
        "script.py is a module and should be "
        "called through build_pipeline.py"
    )
