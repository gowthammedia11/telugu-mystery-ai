import os
import re
import time
from pathlib import Path

import requests


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openrouter/free"

SCRIPTS_DIR = Path("scripts")

MIN_CHARS = 4700
TARGET_MIN_CHARS = 5000
TARGET_MAX_CHARS = 5700
MAX_CHARS = 6000

MAX_ATTEMPTS = 5
REQUEST_TIMEOUT = 240


FORBIDDEN_PATTERNS = [
    r"\blatitude\b",
    r"\blongitude\b",
    r"\bcoordinates?\b",
    r"\b\d+(?:\.\d+)?\s*(?:°|degrees?)\b",
    r"\b\d+(?:\.\d+)?\s*(?:miles?|mi)\b",
    r"\bArtificial Intelligence\b",
    r"\bAI\b",
    r"కృత్రిమ మేధస్సు",
]


META_PATTERNS = [
    r"మీ కోసం",
    r"ఇక్కడ మీకు",
    r"ఈ స్క్రిప్ట్",
    r"ఈ నార్షన్",
    r"డాక్యుమెంటరీగా రాయ",
    r"తెలుగు డాక్యుమెంటరీ",
    r"మీరు ఒక",
    r"ఇలా రాయాలి",
    r"ప్రశ్నలకు సమాధానం",
    r"---",
]


ALLOWED_ENGLISH_WORDS = {
    "YouTube",
    "Yonaguni",
    "Monument",
    "Japan",
    "Pacific",
    "Asia",
    "Google",
    "BBC",
    "NASA",
    "NOAA",
    "UNESCO",
}


def clean_text(text):
    if not text:
        return ""

    text = text.replace("\r", "\n")
    text = text.replace("```text", "")
    text = text.replace("```", "")

    for pattern in FORBIDDEN_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    for pattern in META_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    text = re.sub(r"(?m)^\s*#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*[-*•]\s+", "", text)
    text = re.sub(r"(?m)^\s*\d+\.\s+", "", text)

    text = text.replace("—", " ")
    text = text.replace("–", " ")

    text = re.sub(r"\.{3,}", ".", text)
    text = re.sub(r"!{2,}", "!", text)
    text = re.sub(r"\?{2,}", "?", text)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    lines = []

    for line in text.splitlines():
        line = line.strip()

        if line:
            lines.append(line)

    text = " ".join(lines)

    text = re.sub(r"\s+([,.!?])", r"\1", text)
    text = re.sub(r"([.!?])\s+", r"\1 ", text)

    return text.strip()


def split_sentences(text):
    if not text:
        return []

    parts = re.split(r"(?<=[.!?])\s+", text)

    return [
        part.strip()
        for part in parts
        if part.strip()
    ]


def normalize_for_duplicate_check(text):
    text = text.lower()

    text = re.sub(
        r"[^ఀ-౿a-z0-9 ]",
        " ",
        text,
    )

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def has_repeated_sentences(text):
    sentences = split_sentences(text)

    if len(sentences) < 10:
        return False

    normalized = []

    for sentence in sentences:
        cleaned = normalize_for_duplicate_check(sentence)

        if len(cleaned) >= 35:
            normalized.append(cleaned)

    seen = set()

    for sentence in normalized:
        if sentence in seen:
            return True

        seen.add(sentence)

    if len(normalized) >= 8:
        for index in range(len(normalized) - 3):
            block = " ".join(
                normalized[index:index + 3]
            )

            later_blocks = [
                " ".join(
                    normalized[j:j + 3]
                )
                for j in range(
                    index + 1,
                    len(normalized) - 2,
                )
            ]

            if block in later_blocks:
                return True

    return False


def has_repeated_paragraphs(text):
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n+", text)
        if paragraph.strip()
    ]

    if len(paragraphs) < 3:
        return False

    normalized = [
        normalize_for_duplicate_check(paragraph)
        for paragraph in paragraphs
    ]

    normalized = [
        paragraph
        for paragraph in normalized
        if len(paragraph) >= 80
    ]

    return len(normalized) != len(set(normalized))


def contains_meta_text(text):
    lowered = text.lower()

    checks = [
        "మీ కోసం",
        "ఇక్కడ మీకు",
        "ఈ స్క్రిప్ట్",
        "ఈ నార్షన్",
        "మీరు ఒక తెలుగు",
        "డాక్యుమెంటరీగా రాయ",
        "script",
        "narration script",
        "---",
    ]

    for item in checks:
        if item.lower() in lowered:
            return True

    return False


def english_word_check(text):
    words = re.findall(
        r"\b[A-Za-z]{2,}\b",
        text,
    )

    remaining = []

    for word in words:
        if word not in ALLOWED_ENGLISH_WORDS:
            remaining.append(word)

    return sorted(set(remaining))


def validate_script(text):
    if not text:
        return False, "EMPTY SCRIPT"

    char_count = len(text)

    if char_count < MIN_CHARS:
        return False, (
            f"SCRIPT TOO SHORT: {char_count} chars"
        )

    if char_count > MAX_CHARS:
        return False, (
            f"SCRIPT TOO LONG: {char_count} chars"
        )

    if has_repeated_sentences(text):
        return False, "REPEATED SENTENCES DETECTED"

    if has_repeated_paragraphs(text):
        return False, "REPEATED PARAGRAPHS DETECTED"

    if contains_meta_text(text):
        return False, "META TEXT DETECTED"

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            return False, (
                f"FORBIDDEN CONTENT DETECTED: {pattern}"
            )

    english_words = english_word_check(text)

    if english_words:
        return False, (
            "UNNECESSARY ENGLISH WORDS DETECTED: "
            + ", ".join(english_words[:20])
        )

    return True, "VALID"


def build_prompt(
    topic_id,
    topic_title,
    research,
    retry_reason=None,
):
    retry_instruction = ""

    if retry_reason:
        retry_instruction = f"""

PREVIOUS GENERATION FAILED VALIDATION.

FAILURE:
{retry_reason}

Generate the COMPLETE narration again from the beginning.

Do NOT answer with an explanation.
Do NOT say that you cannot do it.
Do NOT provide a short response.
Do NOT discuss the validation.
Return ONLY the complete Telugu narration.
"""

    return f"""
నువ్వు ఒక ప్రొఫెషనల్ తెలుగు డాక్యుమెంటరీ నారేటర్.

టాపిక్:
{topic_title}

టాపిక్ ID:
{topic_id}

RESEARCH:
{research}

ఈ research ఆధారంగా 7 నుంచి 8 నిమిషాల తెలుగు documentary narration తయారు చేయాలి.

చాలా ముఖ్యమైన నియమాలు:

1. మొత్తం narration 5000 నుంచి 5700 characters మధ్య ఉండాలి.
2. 4700 characters కంటే తక్కువ ఉండకూడదు.
3. 6000 characters దాటకూడదు.
4. ఒకే sentence మళ్లీ రాయకూడదు.
5. ఒకే paragraph మళ్లీ రాయకూడదు.
6. ఒకే explanation ను వేరే పదాలతో మళ్లీ repeat చేయకూడదు.
7. ప్రతి paragraph కొత్త information లేదా story progression ఇవ్వాలి.
8. Research లో ఉన్న facts మాత్రమే ఉపయోగించాలి.
9. ఊహాజనిత facts తయారు చేయకూడదు.
10. మొదట curiosity కలిగించే natural opening ఉండాలి.
11. తర్వాత topic యొక్క background చెప్పాలి.
12. discovery/background వివరించాలి.
13. mystery ఎందుకు ఏర్పడిందో వివరించాలి.
14. కనిపించే ప్రధాన features గురించి చెప్పాలి.
15. వాటికి సంబంధించిన scientific/geological explanation చెప్పాలి.
16. human-made structure అనే వాదనకు ఉన్న evidence చెప్పాలి.
17. natural formation అనే explanation కూడా చెప్పాలి.
18. ప్రస్తుతం experts/scientific evidence ఏం చెబుతున్నాయో balanced గా చెప్పాలి.
19. ఇంకా పూర్తిగా పరిష్కారం కాని అంశాలు ఉంటే అవి చెప్పాలి.
20. చివర్లో complete natural conclusion ఉండాలి.
21. ending abrupt గా ఉండకూడదు.
22. headings వద్దు.
23. bullet points వద్దు.
24. numbered lists వద్దు.
25. markdown వద్దు.
26. "---" వద్దు.
27. "మీ కోసం", "ఈ స్క్రిప్ట్", "ఈ narration", "ఇప్పుడు మనం", "ఈ వీడియోలో" వంటి meta language వద్దు.
28. "AI", "Artificial Intelligence", "కృత్రిమ మేధస్సు" వంటి terms వద్దు.
29. latitude, longitude, coordinates లేదా geographic degree formats ఎట్టి పరిస్థితుల్లోనూ వద్దు.
30. miles వద్దు.
31. distance అవసరమైతే kilometers లేదా సహజమైన తెలుగు వివరణ మాత్రమే ఉపయోగించాలి.
32. unnecessary decimal numbers వద్దు.
33. English words వీలైనంత వరకు పూర్తిగా వద్దు.
34. అవసరమైన proper names మాత్రమే English లో ఉండవచ్చు.
35. ఒకే fact ను repeatedly explain చేయకూడదు.
36. research text ను copy-paste చేసి repeat చేయకూడదు.
37. narration ఒక మనిషి సహజంగా తెలుగులో చెప్పినట్టు ఉండాలి.
38. చాలా formal లేదా textbook style వద్దు.
39. ప్రతి sentence meaningful గా ఉండాలి.
40. చివరి భాగం mystery యొక్క ప్రస్తుత స్థితిని clear గా చెప్పాలి.

NARRATION FLOW:

మొదట ఒక strong mystery hook.

తర్వాత ఈ ప్రదేశం లేదా సంఘటన ఏంటి అనే basic context.

తర్వాత discovery మరియు background.

తర్వాత unusual features.

తర్వాత mystery ఎందుకు ఏర్పడిందో.

తర్వాత scientific explanation.

తర్వాత opposing interpretation.

తర్వాత evidence యొక్క limitations.

తర్వాత ప్రస్తుతం తెలిసిన విషయం.

చివర్లో natural, complete conclusion.

IMPORTANT OUTPUT RULE:

నీ response లో narration మాత్రమే ఉండాలి.

Title వద్దు.
Heading వద్దు.
Explanation వద్దు.
Disclaimer వద్దు.
"ఇదిగో script" వంటి మాటలు వద్దు.
Validation గురించి ఏమీ చెప్పకూడదు.

మొత్తం 5000 నుంచి 5700 characters మధ్య ఒక పూర్తి narration ఇవ్వాలి.

ప్రతి paragraph కొత్త విషయం ముందుకు తీసుకెళ్లాలి.

ఒకే sentence లేదా paragraph repeat అయితే output invalid అవుతుంది.

{retry_instruction}
"""


def call_openrouter(
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
                    "నువ్వు తెలుగు documentary narration writer. "
                    "కేవలం పూర్తి narration మాత్రమే ఇవ్వాలి. "
                    "ఎట్టి పరిస్థితుల్లోనూ meta response, "
                    "short refusal లేదా explanation ఇవ్వకూడదు. "
                    "Repeated content ఇవ్వకూడదు."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.30,
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
            f"OpenRouter HTTP {response.status_code}: "
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
            raw_content = call_openrouter(
                api_key,
                topic_id,
                topic_title,
                research,
                retry_reason=last_error,
            )

            cleaned = clean_text(
                raw_content
            )

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

            print(
                "SCRIPT FAILED VALIDATION"
            )

            if attempt < MAX_ATTEMPTS:
                print(
                    "REQUESTING A COMPLETELY "
                    "FRESH SCRIPT"
                )

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


def load_research(topic_id):
    topic_id = str(topic_id).zfill(3)

    research_file = (
        Path("research")
        / f"{topic_id}.txt"
    )

    if not research_file.exists():
        raise FileNotFoundError(
            f"Research file not found: "
            f"{research_file}"
        )

    return research_file.read_text(
        encoding="utf-8"
    ).strip()


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
