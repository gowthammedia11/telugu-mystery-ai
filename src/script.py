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

OPENROUTER_BASE_URL = (
    "https://openrouter.ai/api/v1"
)

SCRIPTS_DIR = BASE_DIR / "scripts"

# Final long-script target.
MIN_CHARS = 4500
TARGET_MIN_CHARS = 5000
TARGET_MAX_CHARS = 5500
MAX_CHARS = 5700

# Generate 5 smaller sections instead of asking one free
# model for the complete long script in one response.
SECTION_COUNT = 5

SECTION_MIN_CHARS = 850
SECTION_TARGET_MIN = 1000
SECTION_TARGET_MAX = 1350
SECTION_MAX_CHARS = 1500

# Maximum API attempts per section.
MAX_ATTEMPTS_PER_SECTION = 6

# Maximum number of dynamically discovered free models
# used for generation.
MAX_FREE_MODELS = 12

# Small pause between requests.
REQUEST_DELAY_SECONDS = 1.5


# ============================================================
# PREFERRED MODEL KEYWORDS
#
# We do NOT hard-code old model IDs.
# These keywords are only used to rank currently available
# free models discovered from the OpenRouter models endpoint.
# ============================================================

PREFERRED_KEYWORDS = [
    "nemotron",
    "qwen",
    "gemma",
    "llama",
    "gpt-oss",
    "mistral",
    "deepseek",
    "kimi",
    "glm",
]


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
        # Example: 24°20′ N
        r"\b\d{1,3}\s*°\s*\d{1,2}\s*[′']?\s*\d{0,2}(?:\.\d+)?\s*[″\"]?\s*[NS]\b",

        # Example: 123°14′ E
        r"\b\d{1,3}\s*°\s*\d{1,2}\s*[′']?\s*\d{0,2}(?:\.\d+)?\s*[″\"]?\s*[EW]\b",

        # Example: 24.33 N
        r"\b\d{1,3}(?:\.\d+)?\s*[NS]\b",

        # Example: 123.23 E
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

        return (
            f"{round(kilometres, 1)} kilometres"
        )

    def feet_to_metres(match):
        value = float(match.group(1))
        metres = value * 0.3048

        if metres >= 100:
            return f"{round(metres)} metres"

        return (
            f"{round(metres, 1)} metres"
        )

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

    text = remove_urls(
        text
    )

    text = remove_coordinates(
        text
    )

    text = remove_forbidden_measurements(
        text
    )

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
# META LINE DETECTION
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

        if is_meta_line(
            line
        ):
            continue

        result.append(
            line
        )

    return " ".join(
        result
    ).strip()


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
        sentence_key(
            sentence
        )
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
# META CONTENT CHECK
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
# FINAL SANITIZATION
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

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


# ============================================================
# FINAL TRIM
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

    if contains_meta_text(
        text
    ):
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
# DYNAMIC FREE MODEL DISCOVERY
# ============================================================

def discover_free_models():

    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not configured"
        )

    url = (
        f"{OPENROUTER_BASE_URL}/models"
    )

    headers = {
        "Authorization": (
            f"Bearer {OPENROUTER_API_KEY}"
        )
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    models = data.get(
        "data",
        []
    )

    candidates = []

    for model in models:

        if not isinstance(
            model,
            dict
        ):
            continue

        model_id = str(
            model.get(
                "id",
                ""
            )
        ).strip()

        if not model_id:
            continue

        pricing = model.get(
            "pricing",
            {}
        )

        if not isinstance(
            pricing,
            dict
        ):
            continue

        prompt_price = str(
            pricing.get(
                "prompt",
                ""
            )
        ).strip()

        completion_price = str(
            pricing.get(
                "completion",
                ""
            )
        ).strip()

        # Free means both prompt and completion are zero.
        if (
            prompt_price not in {
                "0",
                "0.0",
                "0.000000",
            }
            or
            completion_price not in {
                "0",
                "0.0",
                "0.000000",
            }
        ):
            continue

        architecture = model.get(
            "architecture",
            {}
        )

        if isinstance(
            architecture,
            dict
        ):

            modalities = (
                architecture.get(
                    "output_modalities",
                    []
                )
            )

            if modalities:

                if (
                    isinstance(
                        modalities,
                        list
                    )
                    and
                    "text" not in modalities
                ):
                    continue

        candidates.append(
            model
        )

    # --------------------------------------------------------
    # Rank models.
    # --------------------------------------------------------

    def score_model(model):

        model_id = str(
            model.get(
                "id",
                ""
            )
        ).lower()

        score = 0

        # Prefer models known to be useful for general text.
        for index, keyword in enumerate(
            PREFERRED_KEYWORDS
        ):

            if keyword in model_id:
                score += (
                    100 - index * 5
                )

        # Prefer larger contexts.
        context = model.get(
            "context_length",
            0
        )

        try:
            context = int(
                context or 0
            )
        except (
            TypeError,
            ValueError
        ):
            context = 0

        if context >= 100000:
            score += 15
        elif context >= 32000:
            score += 8

        # Avoid specialised models for finance/medicine/etc.
        specialized_words = [
            "medical",
            "medicine",
            "health",
            "finance",
            "financial",
            "legal",
            "code",
            "coding",
            "embed",
            "embedding",
            "rerank",
        ]

        for word in specialized_words:

            if word in model_id:
                score -= 50

        return score

    candidates.sort(
        key=score_model,
        reverse=True
    )

    final_models = []

    seen = set()

    for model in candidates:

        model_id = str(
            model.get(
                "id",
                ""
            )
        ).strip()

        if not model_id:
            continue

        if model_id in seen:
            continue

        seen.add(
            model_id
        )

        final_models.append(
            model_id
        )

        if len(
            final_models
        ) >= MAX_FREE_MODELS:
            break

    # Always keep the dynamic free router as a final fallback.
    if (
        "openrouter/free"
        not in final_models
    ):
        final_models.append(
            "openrouter/free"
        )

    if not final_models:
        final_models = [
            "openrouter/free"
        ]

    print("=" * 70)
    print(
        "CURRENT FREE MODELS DISCOVERED"
    )
    print("=" * 70)

    for index, model_id in enumerate(
        final_models,
        start=1
    ):
        print(
            f"{index}. {model_id}"
        )

    print("=" * 70)

    return final_models


# ============================================================
# SECTION PROMPTS
# ============================================================

SECTION_INSTRUCTIONS = {
    1: """
కథను బలమైన opening తో ప్రారంభించాలి.
Yonaguni Monument గురించి పరిచయం, దాని underwater location,
1985లో గుర్తించబడిన విషయం, దాని ఆకృతి ఎందుకు ఆసక్తికరంగా
అనిపిస్తుందో natural documentary flow లో చెప్పాలి.

తర్వాతి భాగాలకు అవసరమైన facts మాత్రమే ఇక్కడ ఉపయోగించాలి.
""",

    2: """
ఈ భాగంలో సహజమైన geological explanation పై focus చేయాలి.
రాతి నిర్మాణం, sandstone మరియు shale, rock layers,
fractures, tectonic uplift, sea-level changes మరియు erosion
వంటి research facts ను natural narration గా explain చేయాలి.

ముందు భాగాన్ని unnecessarily repeat చేయకూడదు.
""",

    3: """
ఈ భాగంలో Yonaguni Monument artificial structure అయ్యి ఉండవచ్చనే
theory గురించి explain చేయాలి.

Masaaki Kimura పరిశోధనలు, monument యొక్క geometry గురించి వచ్చిన
వాదనలు మరియు పరిశీలనల్లో కనిపించిన అంశాలను neutral factual
language లో చెప్పాలి.

ఇది నిజమని లేదా తప్పని narrator స్వయంగా తీర్పు ఇవ్వకూడదు.
""",

    4: """
ఈ భాగంలో natural formation theoryకి అనుకూలంగా ఉన్న evidence
మరియు artificial theoryకి వ్యతిరేకంగా చెప్పబడే evidence ను
explain చేయాలి.

Rock composition, tool marks కనిపించకపోవడం, archaeological
artifacts లభించకపోవడం, geological setting మరియు underwater
research వంటి అంశాలను explain చేయాలి.

అదే విషయం repeated wording తో చెప్పకూడదు.
""",

    5: """
చివరి భాగంలో Yonaguni Monument చుట్టూ ఉన్న myths మరియు
ఇప్పటికీ unanswered questions గురించి చెప్పాలి.

Atlantis, aliens, torii gate, UNESCO status, age, possible
human modification వంటి అంశాలను fact మరియు myth మధ్య
స్పష్టమైన తేడాతో explain చేయాలి.

చివర్లో సహజమైన documentary conclusion ఇవ్వాలి.
""",
}


# ============================================================
# BUILD SECTION PROMPT
# ============================================================

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
నువ్వు తెలుగు YouTube mystery documentary narration writer.

టాపిక్:
{title}

టాపిక్ ID:
{topic_id}

ఇది 5-part long documentary narration లో
Part {section_number}.

RESEARCH:
{research}

PART-SPECIFIC INSTRUCTION:
{instruction}

కఠినమైన నియమాలు:

1. ఈ భాగం 1000 నుంచి 1350 characters మధ్య ఉండేలా ప్రయత్నించాలి.
2. కనీసం 850 characters తప్పనిసరిగా ఉండాలి.
3. సహజమైన conversational Telugu వాడాలి.
4. Documentary voice-over style ఉండాలి.
5. Narration మాత్రమే return చేయాలి.
6. Headings వద్దు.
7. Bullet points వద్దు.
8. Numbered lists వద్దు.
9. Markdown వద్దు.
10. URLs వద్దు.
11. Sources list వద్దు.
12. References list వద్దు.
13. AI గురించి చెప్పకూడదు.
14. Prompt గురించి చెప్పకూడదు.
15. Instructions గురించి చెప్పకూడదు.
16. Character count చెప్పకూడదు.
17. Word count చెప్పకూడదు.
18. Coordinates వద్దు.
19. Latitude వద్దు.
20. Longitude వద్దు.
21. GPS coordinates వద్దు.
22. Miles, mile, mi వద్దు.
23. Feet, foot, ft వద్దు.
24. దూరాలకు kilometres లేదా km మాత్రమే వాడాలి.
25. ఎత్తు, లోతు, వెడల్పుకు metres లేదా m మాత్రమే వాడాలి.
26. అవసరం లేని decimals వద్దు.
27. Research లో లేని facts కల్పించకూడదు.
28. Myths ను facts లాగా చెప్పకూడదు.
29. Uncertain claims ను certainty గా చెప్పకూడదు.
30. One idea ను repeated wording తో చెప్పకూడదు.
31. ఇతర parts లో చెప్పబోయే content ను unnecessarily repeat చేయకూడదు.
32. చివరి line incomplete sentence కాకూడదు.
33. "Here is the script", "Sure", "Below is" వంటి మాటలు వద్దు.
34. ONLY narration return చేయాలి.

Research లో ఉన్న నిజమైన information మాత్రమే ఉపయోగించాలి.
"""


# ============================================================
# EXTRACT OPENROUTER CONTENT
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
        f"{OPENROUTER_BASE_URL}/chat/completions"
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
                    "Return ONLY the requested "
                    "factual Telugu documentary "
                    "narration. Never return reasoning, "
                    "analysis, headings, or meta commentary."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],

        "temperature": 0.40,

        "max_tokens": 1800,

        # OpenRouter supports the reasoning parameter
        # for reasoning-capable models.
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

    body_text = (
        response.text.strip()
    )

    if response.status_code >= 400:

        raise RuntimeError(
            f"HTTP {response.status_code}: "
            f"{body_text[:700]}"
        )

    try:
        data = response.json()

    except ValueError:

        raise RuntimeError(
            "OpenRouter returned invalid JSON: "
            f"{body_text[:500]}"
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
                        "MODEL RETURNED REASONING "
                        "WITHOUT FINAL CONTENT"
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
    section_number,
    models
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

    # --------------------------------------------------------
    # Rotate starting model for each section so the same
    # provider is not hammered repeatedly.
    # --------------------------------------------------------

    if models:

        start = (
            section_number - 1
        ) % len(models)

        ordered_models = (
            models[start:]
            + models[:start]
        )

    else:

        ordered_models = [
            "openrouter/free"
        ]

    # --------------------------------------------------------
    # Attempts
    # --------------------------------------------------------

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

            # ------------------------------------------------
            # Reject tiny model replies.
            # ------------------------------------------------

            if len(cleaned) < SECTION_MIN_CHARS:

                last_error = (
                    f"SECTION TOO SHORT: "
                    f"{len(cleaned)} characters"
                )

                print(
                    "SECTION VALIDATION FAILED: "
                    f"{last_error}"
                )

                continue

            # ------------------------------------------------
            # Trim oversized section.
            # ------------------------------------------------

            if len(cleaned) > SECTION_MAX_CHARS:

                cleaned = trim_section(
                    cleaned,
                    SECTION_MAX_CHARS
                )

                cleaned = sanitize_final_script(
                    cleaned
                )

                print(
                    f"SECTION TRIMMED TO: "
                    f"{len(cleaned)}"
                )

            # ------------------------------------------------
            # Final section validation.
            # ------------------------------------------------

            if contains_meta_text(
                cleaned
            ):

                last_error = (
                    "META TEXT DETECTED"
                )

                print(
                    "SECTION VALIDATION FAILED: "
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
                    "SECTION VALIDATION FAILED: "
                    f"{last_error}"
                )

                continue

            print(
                f"SECTION {section_number}: VALID"
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

        time.sleep(
            REQUEST_DELAY_SECONDS
        )

    raise RuntimeError(
        f"Section {section_number} generation failed "
        f"after {MAX_ATTEMPTS_PER_SECTION} attempts: "
        f"{last_error}"
    )


# ============================================================
# TRIM SECTION
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
# FINAL EXPANSION
# ============================================================

def expand_script(
    topic_id,
    title,
    research,
    current_script,
    models
):

    prompt = f"""
ఈ తెలుగు documentary narration ఇప్పటికే రూపొందించబడింది.

దీనిని natural factual narration గా expand చేయాలి.

టాపిక్:
{title}

RESEARCH:
{research}

CURRENT NARRATION:
{current_script}

RULES:

1. Existing useful facts ను ఉంచాలి.
2. Missing useful research details మాత్రమే add చేయాలి.
3. Repetition వద్దు.
4. Final narration 5000 నుంచి 5500 characters మధ్య ఉండాలి.
5. Coordinates వద్దు.
6. Latitude/longitude వద్దు.
7. Miles వద్దు.
8. Feet వద్దు.
9. URLs వద్దు.
10. AI mention వద్దు.
11. Headings వద్దు.
12. Bullet points వద్దు.
13. Markdown వద్దు.
14. Meta commentary వద్దు.
15. Research లో లేని facts వద్దు.
16. Myth మరియు fact distinction స్పష్టంగా ఉండాలి.
17. Natural documentary ending ఉండాలి.
18. ONLY final Telugu narration return చేయాలి.
"""

    for model in models:

        print(
            "=" * 70
        )

        print(
            f"FINAL EXPANSION MODEL: {model}"
        )

        try:

            raw = request_openrouter(
                prompt,
                model
            )

            print(
                f"RAW EXPANSION LENGTH: "
                f"{len(raw)}"
            )

            cleaned = sanitize_final_script(
                raw
            )

            if len(cleaned) > TARGET_MAX_CHARS:

                cleaned = trim_to_target(
                    cleaned,
                    TARGET_MAX_CHARS
                )

                cleaned = sanitize_final_script(
                    cleaned
                )

            print(
                f"EXPANSION CLEANED LENGTH: "
                f"{len(cleaned)}"
            )

            valid, reason = validate_script(
                cleaned
            )

            if valid:

                print(
                    "FINAL EXPANSION VALIDATION: PASSED"
                )

                return cleaned

            print(
                "FINAL EXPANSION VALIDATION FAILED: "
                f"{reason}"
            )

        except Exception as exc:

            print(
                f"EXPANSION ERROR: {exc}"
            )

        time.sleep(
            REQUEST_DELAY_SECONDS
        )

    return ""


# ============================================================
# GENERATE LONG SCRIPT
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

    # --------------------------------------------------------
    # Discover CURRENT free models from OpenRouter.
    # --------------------------------------------------------

    models = discover_free_models()

    sections = []

    # --------------------------------------------------------
    # Generate five independent sections.
    # --------------------------------------------------------

    for section_number in range(
        1,
        SECTION_COUNT + 1
    ):

        section = generate_section(
            topic_id,
            title,
            research,
            section_number,
            models
        )

        sections.append(
            section
        )

        current_combined = combine_sections(
            sections
        )

        print(
            "=" * 70
        )

        print(
            f"COMBINED LENGTH AFTER SECTION "
            f"{section_number}: "
            f"{len(current_combined)}"
        )

        print("=" * 70)

    # --------------------------------------------------------
    # Combine.
    # --------------------------------------------------------

    final_script = combine_sections(
        sections
    )

    print(
        f"COMBINED SCRIPT LENGTH: "
        f"{len(final_script)}"
    )

    # --------------------------------------------------------
    # Trim if needed.
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
    # Validate.
    # --------------------------------------------------------

    valid, reason = validate_script(
        final_script
    )

    if valid:

        print("=" * 70)
        print(
            "SCRIPT VALIDATION: PASSED"
        )

        print(
            f"FINAL SCRIPT LENGTH: "
            f"{len(final_script)}"
        )

        print("=" * 70)

        return final_script

    # --------------------------------------------------------
    # If still below target, perform one controlled
    # expansion using the current free-model list.
    # --------------------------------------------------------

    if len(final_script) < TARGET_MIN_CHARS:

        print("=" * 70)

        print(
            "FINAL SCRIPT BELOW TARGET"
        )

        print(
            f"CURRENT LENGTH: "
            f"{len(final_script)}"
        )

        print(
            f"TARGET MINIMUM: "
            f"{TARGET_MIN_CHARS}"
        )

        print(
            "RUNNING CONTROLLED FINAL EXPANSION"
        )

        expanded = expand_script(
            topic_id,
            title,
            research,
            final_script,
            models
        )

        if expanded:

            return expanded

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
        "=" * 70
    )

    print(
        f"SCRIPT SAVED: {path}"
    )

    print(
        f"SCRIPT LENGTH: {len(script_text)}"
    )

    print("=" * 70)

    return path


# ============================================================
# MODULE ENTRY
# ============================================================

if __name__ == "__main__":

    print(
        "script.py is a module and should be "
        "called through build_pipeline.py"
    )
