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

# Current free OpenRouter model endpoints.
# The order is intentional:
# 1. Gemma 4 26B A4B
# 2. Nemotron 3.5 Lightning
# 3. Qwen3.8 27B
# 4. OpenRouter free router as final fallback
#
# Do NOT use old qwen3-30b-a3b:free endpoint.
MODELS = [
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3.5-lightning:free",
    "qwen/qwen3.8-27b:free",
    "openrouter/free",
]

MIN_CHARS = 4500
TARGET_MIN_CHARS = 5000
TARGET_MAX_CHARS = 5500
MAX_CHARS = 5700

MAX_ATTEMPTS = 8

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
        # 24°20′ N
        r"\b\d{1,3}\s*°\s*\d{1,2}\s*[′']?\s*\d{0,2}(?:\.\d+)?\s*[″\"]?\s*[NS]\b",

        # 123°14′ E
        r"\b\d{1,3}\s*°\s*\d{1,2}\s*[′']?\s*\d{0,2}(?:\.\d+)?\s*[″\"]?\s*[EW]\b",

        # 24.33 N
        r"\b\d{1,3}(?:\.\d+)?\s*[NS]\b",

        # 123.23 E
        r"\b\d{1,3}(?:\.\d+)?\s*[EW]\b",

        # latitude: 24.33
        r"\b(?:latitude|lat)\s*[:\-]?\s*\d+(?:\.\d+)?\b",

        # longitude: 123.23
        r"\b(?:longitude|lon|lng)\s*[:\-]?\s*\d+(?:\.\d+)?\b",

        # 24.33, 123.23
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

    def fahrenheit_to_celsius(match):
        value = float(match.group(1))
        celsius = (value - 32) * 5 / 9

        return f"{round(celsius, 1)} degrees Celsius"

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

    text = re.sub(
        r"(\d+(?:\.\d+)?)\s*(?:°F|degrees?\s+Fahrenheit)\b",
        fahrenheit_to_celsius,
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
        "```",
        ""
    )

    text = text.replace(
        "\r",
        ""
    )

    return text


# ============================================================
# META LINE DETECTION
# ============================================================

def is_meta_line(line):
    stripped = line.strip()

    if not stripped:
        return False

    lowered = stripped.lower()

    meta_patterns = [
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
        "documentary script:",
        "documentary narration:",
        "final script:",
        "final narration:",
        "character count",
        "word count",
        "characters:",
        "words:",
        "sources:",
        "references:",
        "source:",
        "according to the prompt",
        "according to your instructions",
        "as an ai",
        "as a language model",
        "i will write",
        "i'll write",
        "i have written",
        "i wrote",
        "this script",
        "the following script",
        "the following narration",
        "note:",
        "notes:",
        "analysis:",
        "reasoning:",
        "instructions:",
        "prompt:",
    ]

    if any(
        pattern in lowered
        for pattern in meta_patterns
    ):
        return True

    if stripped.startswith("#"):
        return True

    if stripped.startswith("```"):
        return True

    if re.match(
        r"^\s*(?:\d+[\.\)]|[-*•])\s+",
        stripped
    ):
        return True

    return False


# ============================================================
# REMOVE GENERATED WRAPPERS
# ============================================================

def remove_generated_wrappers(text):
    if not text:
        return ""

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

    lines = text.splitlines()

    cleaned_lines = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        if is_meta_line(
            stripped
        ):
            continue

        cleaned_lines.append(
            stripped
        )

    text = "\n".join(
        cleaned_lines
    )

    return text.strip()


# ============================================================
# EXTRACT ACTUAL NARRATION
# ============================================================

def extract_narration(text):
    if not text:
        return ""

    text = remove_generated_wrappers(
        text
    )

    lines = text.splitlines()

    # Find the first line containing Telugu script.
    # This helps remove English model introductions.
    first_telugu_index = None

    for index, line in enumerate(lines):
        if re.search(
            r"[\u0C00-\u0C7F]",
            line
        ):
            first_telugu_index = index
            break

    if first_telugu_index is not None:
        lines = lines[
            first_telugu_index:
        ]

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
# SENTENCE HELPERS
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
    sentence = sentence.strip()

    sentence = re.sub(
        r"\s+",
        " ",
        sentence
    )

    return sentence


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

    unique_count = len(
        set(keys)
    )

    return 1 - (
        unique_count / len(keys)
    )


# ============================================================
# META TEXT CHECK
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
        phrase in lowered
        for phrase in forbidden
    )


# ============================================================
# FORBIDDEN CONTENT CHECK
# ============================================================

def contains_forbidden_content(text):
    lowered = text.lower()

    forbidden_patterns = [
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

    for pattern in forbidden_patterns:
        if re.search(
            pattern,
            lowered,
            flags=re.IGNORECASE
        ):
            return True

    return False


# ============================================================
# FINAL SANITIZATION
# ============================================================

def sanitize_final_script(text):

    text = extract_narration(
        text
    )

    text = clean_text(
        text
    )

    sentences = split_sentences(
        text
    )

    cleaned_sentences = []

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

        seen.add(key)

        cleaned_sentences.append(
            sentence
        )

    text = " ".join(
        cleaned_sentences
    )

    text = clean_text(
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


# ============================================================
# TRIM TO TARGET
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

        extra_length = len(
            sentence
        )

        if result:
            extra_length += 1

        if (
            current_length
            + extra_length
            > max_chars
        ):
            break

        result.append(
            sentence
        )

        current_length += (
            extra_length
        )

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
# VALIDATE SCRIPT
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
# PROMPT
# ============================================================

def build_prompt(
    topic_id,
    title,
    research
):

    return f"""
నువ్వు తెలుగు యూట్యూబ్ డాక్యుమెంటరీ narration writer.

టాపిక్:
{title}

టాపిక్ ID:
{topic_id}

కింద ఇచ్చిన research సమాచారాన్ని మాత్రమే ఆధారంగా చేసుకుని సహజమైన తెలుగు documentary narration రాయాలి.

RESEARCH:
{research}

కఠినమైన నియమాలు:

1. Script మొత్తం సహజమైన conversational Telugu narration లాగా ఉండాలి.
2. మొత్తం 5000 నుంచి 5500 characters మధ్య ఉండాలి.
3. 7 నుంచి 8 నిమిషాల voice-over కి సరిపోయేలా ఉండాలి.
4. ప్రారంభం ఆసక్తికరంగా ఉండాలి.
5. విషయం natural story flow లో ముందుకు వెళ్లాలి.
6. ప్రతి paragraph ఒక కొత్త useful point లేదా explanation ఇవ్వాలి.
7. ఒకే విషయాన్ని repeated wording తో చెప్పకూడదు.
8. చివర్లో natural ending ఉండాలి.
9. అకస్మాత్తుగా script ఆపకూడదు.
10. Headings వద్దు.
11. Bullet points వద్దు.
12. Numbered lists వద్దు.
13. Markdown వద్దు.
14. URLs వద్దు.
15. Sources list వద్దు.
16. References list వద్దు.
17. AI గురించి చెప్పకూడదు.
18. "as an AI" వంటి మాటలు వద్దు.
19. Character count లేదా word count చెప్పకూడదు.
20. Prompt లేదా instructions గురించి చెప్పకూడదు.
21. Coordinates ఎట్టి పరిస్థితుల్లోనూ చెప్పకూడదు.
22. Latitude లేదా longitude గురించి చెప్పకూడదు.
23. GPS coordinates గురించి చెప్పకూడదు.
24. Miles, mile, mi వాడకూడదు.
25. Feet, foot, ft వాడకూడదు.
26. దూరాలకు kilometres లేదా km మాత్రమే వాడాలి.
27. ఎత్తు, వెడల్పు, లోతు వంటి measurements కి metres లేదా m మాత్రమే వాడాలి.
28. అవసరం లేని decimals వాడకూడదు.
29. Research లో లేని facts కల్పించకూడదు.
30. Rumours లేదా myths ను facts లాగా చెప్పకూడదు.
31. Artificial theory మరియు natural explanation ఉంటే రెండింటినీ neutral factual language లో explain చేయాలి.
32. నిర్ధారించని విషయాలకు certainty ఇవ్వకూడదు.
33. English words అవసరమైన technical terms మాత్రమే ఉండాలి.
34. ప్రతి విషయం easy Telugu లో explain చేయాలి.
35. Script మాత్రమే return చేయాలి.
36. Script ముందు "Here is the script", "Sure", "Below is..." వంటి మాటలు రాయకూడదు.
37. Script తర్వాత explanation లేదా note ఇవ్వకూడదు.
38. "###", "**", "```" వంటి markdown symbols వాడకూడదు.
39. చివరి sentence పూర్తి అర్థవంతమైన sentence అయి ఉండాలి.

ముఖ్యంగా:
Research లో ఉన్న నిజమైన సమాచారాన్ని మాత్రమే ఉపయోగించు.
No invented facts.
No coordinates.
No miles.
No feet.
No meta commentary.
Return ONLY the Telugu narration.
"""


# ============================================================
# EXTRACT API CONTENT
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

    first_choice = choices[0]

    if not isinstance(
        first_choice,
        dict
    ):
        return ""

    message = first_choice.get(
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
                    "Write only the requested "
                    "factual Telugu documentary "
                    "narration. Do not provide "
                    "reasoning, analysis, headings, "
                    "or meta commentary."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],

        "temperature": 0.45,

        "max_tokens": 4000,

        # Prevent reasoning-only output.
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

    response_text = (
        response.text.strip()
    )

    # --------------------------------------------------------
    # HTTP ERRORS
    # --------------------------------------------------------

    if response.status_code >= 400:

        short_error = response_text[
            :800
        ]

        raise RuntimeError(
            f"HTTP {response.status_code}: "
            f"{short_error}"
        )

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    try:
        data = response.json()

    except ValueError:

        raise RuntimeError(
            "OpenRouter returned invalid JSON: "
            f"{response_text[:500]}"
        )

    # --------------------------------------------------------
    # NORMAL CONTENT
    # --------------------------------------------------------

    content = extract_content(
        data
    )

    if content:
        return content

    # --------------------------------------------------------
    # API ERROR
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # CHOICES EXIST BUT CONTENT EMPTY
    # --------------------------------------------------------

    choices = data.get(
        "choices"
    )

    if choices:

        first_choice = choices[0]

        finish_reason = ""

        if isinstance(
            first_choice,
            dict
        ):

            finish_reason = (
                first_choice.get(
                    "finish_reason",
                    ""
                )
            )

            message = (
                first_choice.get(
                    "message",
                    {}
                )
            )

            if isinstance(
                message,
                dict
            ):

                reasoning = (
                    message.get(
                        "reasoning"
                    )
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
# GENERATE SCRIPT
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

    prompt = build_prompt(
        topic_id,
        title,
        research
    )

    last_error = (
        "Unknown error"
    )

    # --------------------------------------------------------
    # Try multiple current free models.
    # --------------------------------------------------------

    for attempt in range(
        1,
        MAX_ATTEMPTS + 1
    ):

        model_index = (
            attempt - 1
        ) % len(MODELS)

        model = MODELS[
            model_index
        ]

        print(
            f"OPENROUTER SCRIPT ATTEMPT "
            f"{attempt}/{MAX_ATTEMPTS}"
        )

        print(
            f"MODEL: {model}"
        )

        try:

            raw_text = request_openrouter(
                prompt,
                model
            )

            print(
                f"RAW SCRIPT LENGTH: "
                f"{len(raw_text)}"
            )

            if not raw_text:

                last_error = (
                    "EMPTY RESPONSE"
                )

                print(
                    "SCRIPT GENERATION ERROR: "
                    f"{last_error}"
                )

                time.sleep(2)

                continue

            # ------------------------------------------------
            # Clean model wrapper/meta output.
            # ------------------------------------------------

            cleaned = sanitize_final_script(
                raw_text
            )

            print(
                f"CLEANED SCRIPT LENGTH: "
                f"{len(cleaned)}"
            )

            # ------------------------------------------------
            # Trim long output at sentence boundary.
            # ------------------------------------------------

            if len(cleaned) > TARGET_MAX_CHARS:

                cleaned = trim_to_target(
                    cleaned,
                    TARGET_MAX_CHARS
                )

                cleaned = sanitize_final_script(
                    cleaned
                )

                print(
                    f"TRIMMED SCRIPT LENGTH: "
                    f"{len(cleaned)}"
                )

            # ------------------------------------------------
            # Final validation.
            # ------------------------------------------------

            valid, reason = validate_script(
                cleaned
            )

            if valid:

                print(
                    "SCRIPT VALIDATION: PASSED"
                )

                print(
                    f"FINAL SCRIPT LENGTH: "
                    f"{len(cleaned)}"
                )

                return cleaned

            last_error = reason

            print(
                "SCRIPT VALIDATION FAILED: "
                f"{reason}"
            )

        except Exception as exc:

            last_error = str(
                exc
            )

            print(
                "SCRIPT GENERATION ERROR: "
                f"{last_error}"
            )

        # Small pause before switching model.
        time.sleep(2)

    raise RuntimeError(
        "Script generation failed after "
        f"{MAX_ATTEMPTS} attempts: "
        f"{last_error}"
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

    with path.open(
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            script_text.strip()
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
