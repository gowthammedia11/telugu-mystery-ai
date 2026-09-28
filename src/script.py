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

MIN_TOTAL_CHARS = 4800
TARGET_TOTAL_MIN = 5000
TARGET_TOTAL_MAX = 5700
MAX_TOTAL_CHARS = 6000

PART_MIN_CHARS = 2200
PART_MAX_CHARS = 3200

MAX_ATTEMPTS_PER_PART = 6
REQUEST_TIMEOUT = 240

ALLOWED_ENGLISH_WORDS = {
    "AI",
    "US",
    "UK",
    "Japan",
    "Japanese",
    "Yonaguni",
    "Kimura",
    "Aratake",
    "JAMSTEC",
    "UNESCO",
    "East",
    "China",
    "Sea",
}


def load_research(topic_id):
    path = RESEARCH_DIR / f"{topic_id}.txt"

    if not path.exists():
        raise FileNotFoundError(f"Research file not found: {path}")

    text = path.read_text(encoding="utf-8").strip()

    if not text:
        raise RuntimeError(f"Research file is empty: {path}")

    return text


def remove_urls(text):
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"www\.\S+", " ", text)
    return text


def remove_coordinates(text):
    patterns = [
        r"\b\d{1,3}\s*°\s*\d{1,2}\s*[′']\s*\d{1,2}(?:\.\d+)?\s*[″\"]?\s*[NS]\b",
        r"\b\d{1,3}\s*°\s*\d{1,2}\s*[′']\s*\d{1,2}(?:\.\d+)?\s*[″\"]?\s*[EW]\b",
        r"\b\d{1,3}(?:\.\d+)?\s*[NS]\b",
        r"\b\d{1,3}(?:\.\d+)?\s*[EW]\b",
        r"\blatitude\b",
        r"\blatitude\b",
        r"\blongitude\b",
        r"\blongitude\b",
        r"\bcoordinates?\b",
    ]

    for pattern in patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    return text


def remove_measurement_formats(text):
    text = re.sub(r"\b\d+(?:\.\d+)?\s*(?:miles?|mi)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d+(?:\.\d+)?\s*(?:feet|foot|ft)\b", " ", text, flags=re.IGNORECASE)
    return text


def clean_text(text):
    if not text:
        return ""

    text = text.replace("\r", "\n")

    text = remove_urls(text)
    text = remove_coordinates(text)
    text = remove_measurement_formats(text)

    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*•]\s*", "", text, flags=re.MULTILINE)

    text = re.sub(
        r"^(?:title|heading|section|part|introduction|conclusion)\s*[:\-].*$",
        " ",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def split_sentences(text):
    return [
        item.strip()
        for item in re.split(r"(?<=[.!?।])\s+", text)
        if item.strip()
    ]


def normalize_sentence(sentence):
    sentence = sentence.lower()
    sentence = re.sub(r"\s+", " ", sentence)
    sentence = re.sub(r"[^\w\s]", "", sentence, flags=re.UNICODE)
    return sentence.strip()


def has_repeated_sentences(text):
    sentences = split_sentences(text)

    seen = set()

    for sentence in sentences:
        normalized = normalize_sentence(sentence)

        if len(normalized) < 35:
            continue

        if normalized in seen:
            return True

        seen.add(normalized)

    return False


def has_excessive_repetition(text):
    words = re.findall(r"\S+", text.lower())

    if len(words) < 100:
        return False

    counts = {}

    for word in words:
        word = re.sub(r"[^\w\u0C00-\u0C7F]", "", word)

        if len(word) < 4:
            continue

        counts[word] = counts.get(word, 0) + 1

    total = len(words)

    for count in counts.values():
        if count / total > 0.08:
            return True

    return False


def contains_meta_text(text):
    patterns = [
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

    lower = text.lower()

    return any(pattern in lower for pattern in patterns)


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

    return [item for item in forbidden if item in lower]


def find_unwanted_english(text):
    words = re.findall(r"\b[A-Za-z]{3,}\b", text)

    unwanted = []

    for word in words:
        if word in ALLOWED_ENGLISH_WORDS:
            continue

        if word.lower() in {
            "the",
            "and",
            "or",
            "of",
            "in",
            "on",
            "to",
            "from",
            "for",
            "with",
            "about",
            "under",
            "over",
            "east",
            "west",
            "north",
            "south",
            "sea",
        }:
            continue

        unwanted.append(word)

    unique = []

    for word in unwanted:
        if word not in unique:
            unique.append(word)

    return unique[:10]


def validate_part(text, part_name):
    if not text:
        return "EMPTY SCRIPT"

    length = len(text)

    if length < PART_MIN_CHARS:
        return f"{part_name} TOO SHORT: {length} chars"

    if length > PART_MAX_CHARS:
        return f"{part_name} TOO LONG: {length} chars"

    if contains_meta_text(text):
        return f"{part_name} CONTAINS META TEXT"

    forbidden = contains_forbidden_content(text)

    if forbidden:
        return f"{part_name} CONTAINS FORBIDDEN CONTENT: {', '.join(forbidden)}"

    if has_repeated_sentences(text):
        return f"{part_name} CONTAINS REPEATED SENTENCES"

    if has_excessive_repetition(text):
        return f"{part_name} HAS EXCESSIVE WORD REPETITION"

    return None


def validate_total_script(text):
    length = len(text)

    if length < MIN_TOTAL_CHARS:
        return f"SCRIPT TOO SHORT: {length} chars"

    if length > MAX_TOTAL_CHARS:
        return f"SCRIPT TOO LONG: {length} chars"

    if contains_meta_text(text):
        return "SCRIPT CONTAINS META TEXT"

    forbidden = contains_forbidden_content(text)

    if forbidden:
        return f"SCRIPT CONTAINS FORBIDDEN CONTENT: {', '.join(forbidden)}"

    if has_repeated_sentences(text):
        return "SCRIPT CONTAINS REPEATED SENTENCES"

    if has_excessive_repetition(text):
        return "SCRIPT HAS EXCESSIVE WORD REPETITION"

    return None


def build_research_summary(research):
    text = clean_text(research)

    if len(text) > 18000:
        text = text[:18000]

    return text


def build_part_prompt(topic_id, title, research, part_number, previous_part=""):
    research_text = build_research_summary(research)

    if part_number == 1:
        structure = """
ఈ మొదటి భాగంలో:
- ప్రేక్షకుడిని వెంటనే ఆకట్టుకునే సహజమైన ప్రారంభం
- Yonaguni Monument అంటే ఏమిటి
- అది ఎక్కడ ఉంది అనే సాధారణ వివరణ
- 1985లో జరిగిన గుర్తింపు/ఆవిష్కరణ
- తర్వాత జరిగిన పరిశోధన
- ఆ నిర్మాణం యొక్క పరిమాణం, లోతు, రాళ్ల స్వభావం
- అక్కడి భౌగోళిక పరిస్థితులు
- సహజంగా ఏర్పడి ఉండవచ్చనే శాస్త్రీయ వివరణకు అవసరమైన నేపథ్యం

ఈ భాగం చివర్లో రెండో భాగానికి సహజంగా వెళ్లేలా చేయాలి.
"""
    else:
        structure = """
ఈ రెండో భాగంలో:
- ఈ నిర్మాణం మనుషులు నిర్మించారా అనే ప్రశ్న
- సహజ నిర్మాణం అనే వివరణ
- మానవ మార్పులు జరిగి ఉండవచ్చనే మధ్యస్థ అభిప్రాయం
- రాళ్లలో కనిపించే లక్షణాలు
- టూల్ మార్కులు మరియు పురావస్తు వస్తువులు లభించకపోవడం
- సముద్ర మట్టం మార్పులు, భూకంప/టెక్టానిక్ మార్పులు, కోత వంటి ప్రక్రియలు
- ఇంకా ఖచ్చితంగా తెలియని విషయాలు
- Atlantis, aliens వంటి నిర్ధారణలేని కథనాలపై జాగ్రత్త
- చివర్లో ప్రేక్షకుడికి ఆలోచన కలిగించే కానీ అతిశయోక్తి లేని పూర్తి ముగింపు

ముగింపు ఒక్కసారిగా కట్ అయినట్టు ఉండకూడదు.
"""

    previous_instruction = ""

    if previous_part:
        previous_instruction = f"""
ఇది మొదటి భాగం:

{previous_part}

రెండో భాగం మొదటి భాగాన్ని మళ్లీ చెప్పకూడదు.
అదే వాక్యాలు లేదా అదే సమాచారాన్ని పునరావృతం చేయకూడదు.
"""

    return f"""
మీరు తెలుగు యూట్యూబ్ డాక్యుమెంటరీ కోసం సహజమైన spoken Telugu narration రాయాలి.

TOPIC ID: {topic_id}
TOPIC: {title}

ఇది రెండు భాగాలుగా తయారయ్యే ఒకే 7–8 నిమిషాల documentary narrationలో భాగం.

{structure}

కఠినమైన నియమాలు:

1. మొత్తం output spoken Telugu narration మాత్రమే.
2. Headings వద్దు.
3. Bullets వద్దు.
4. Numbered lists వద్దు.
5. Markdown వద్దు.
6. Source list వద్దు.
7. URLs వద్దు.
8. Researchలో ఉన్న coordinates ఎట్టి పరిస్థితుల్లోనూ narrationలో చెప్పకూడదు.
9. Latitude, longitude అనే పదాలు వాడకూడదు.
10. Miles, feet వాడకూడదు. అవసరమైన చోట kilometers లేదా meters వాడాలి.
11. అవసరం లేని English words వద్దు.
12. AI గురించి చెప్పకూడదు.
13. "ఇప్పుడు మనం చూద్దాం", "ఈ స్క్రిప్ట్‌లో" వంటి meta narration తగ్గించాలి.
14. Facts మాత్రమే చెప్పాలి. నిర్ధారణ లేని విషయాన్ని factలా చెప్పకూడదు.
15. Artificial theory, natural formation theory, hybrid theoryలను సమతుల్యంగా వివరించాలి.
16. Atlantis లేదా aliens వంటి విషయాలను నిజం జరిగినట్టు చెప్పకూడదు.
17. Telugu natural conversational documentary styleలో రాయాలి.
18. చిన్న చిన్న repetitive sentences ఎక్కువగా వాడకూడదు.
19. ఒకే factను వేర్వేరు పదాలతో మళ్లీ మళ్లీ చెప్పకూడదు.
20. ముగింపు పూర్తి భావంతో ఉండాలి.

ప్రతి భాగం సుమారు 2400–2900 characters ఉండేలా రాయండి.
చాలా చిన్నగా రాయకండి.
పూర్తి భాగాన్ని ఒకేసారి ఇవ్వండి.

RESEARCH:

{research_text}

{previous_instruction}

ఇప్పుడు narration భాగాన్ని మాత్రమే ఇవ్వండి.
"""


def request_part(topic_id, title, research, part_number, previous_part=""):
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    prompt = build_part_prompt(
        topic_id,
        title,
        research,
        part_number,
        previous_part,
    )

    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Generate only the requested Telugu documentary narration. "
                        "Never return explanations, notes, headings, or commentary."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.45,
            "max_tokens": 3500,
        },
        timeout=REQUEST_TIMEOUT,
    )

    print(f"OPENROUTER HTTP STATUS: {response.status_code}")

    if response.status_code != 200:
        raise RuntimeError(
            f"OpenRouter HTTP {response.status_code}: {response.text[:1000]}"
        )

    data = response.json()

    choices = data.get("choices", [])

    if not choices:
        raise RuntimeError("OpenRouter returned no choices")

    message = choices[0].get("message", {})

    content = message.get("content", "")

    if isinstance(content, list):
        content = "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict)
        )

    content = str(content or "").strip()

    print("OPENROUTER PART CONTENT RECEIVED")

    return clean_text(content)


def generate_part(
    topic_id,
    title,
    research,
    part_number,
    previous_part="",
):
    last_error = None

    for attempt in range(1, MAX_ATTEMPTS_PER_PART + 1):
        print(
            f"OPENROUTER PART {part_number} ATTEMPT "
            f"{attempt}/{MAX_ATTEMPTS_PER_PART}"
        )

        try:
            part = request_part(
                topic_id,
                title,
                research,
                part_number,
                previous_part,
            )

            print(
                f"PART {part_number} CHARACTERS: {len(part)}"
            )

            error = validate_part(
                part,
                f"PART {part_number}",
            )

            if error:
                print(f"PART VALIDATION: {error}")
                last_error = error
                print("REQUESTING A FRESH PART")
                time.sleep(1)
                continue

            return part

        except Exception as exc:
            last_error = str(exc)
            print(
                f"PART {part_number} ERROR: {last_error}"
            )
            time.sleep(2)

    raise RuntimeError(
        f"Part {part_number} generation failed after "
        f"{MAX_ATTEMPTS_PER_PART} attempts: {last_error}"
    )


def generate_script(topic_id, title, research_text):
    print("=" * 70)
    print("GENERATING LONG SCRIPT IN 2 PARTS")
    print("=" * 70)

    part1 = generate_part(
        topic_id=topic_id,
        title=title,
        research=research_text,
        part_number=1,
    )

    print("=" * 70)
    print("PART 1 READY")
    print("=" * 70)

    part2 = generate_part(
        topic_id=topic_id,
        title=title,
        research=research_text,
        part_number=2,
        previous_part=part1,
    )

    print("=" * 70)
    print("PART 2 READY")
    print("=" * 70)

    final_script = clean_text(
        f"{part1} {part2}"
    )

    print(
        f"COMBINED SCRIPT CHARACTERS: "
        f"{len(final_script)}"
    )

    error = validate_total_script(final_script)

    if error:
        print(f"FINAL SCRIPT VALIDATION: {error}")

        if len(final_script) < MIN_TOTAL_CHARS:
            raise RuntimeError(
                f"Combined script is too short: "
                f"{len(final_script)} chars"
            )

        if len(final_script) > MAX_TOTAL_CHARS:
            raise RuntimeError(
                f"Combined script is too long: "
                f"{len(final_script)} chars"
            )

        raise RuntimeError(
            f"Final script validation failed: {error}"
        )

    print("=" * 70)
    print("LONG SCRIPT GENERATION SUCCESSFUL")
    print(
        f"FINAL SCRIPT LENGTH: {len(final_script)} characters"
    )
    print("=" * 70)

    return final_script


def save_script(topic_id, script_text):
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    error = validate_total_script(script_text)

    if error:
        raise RuntimeError(
            f"Cannot save invalid script: {error}"
        )

    path = SCRIPTS_DIR / f"{topic_id}.txt"

    path.write_text(
        script_text.strip(),
        encoding="utf-8",
    )

    print(f"SCRIPT SAVED: {path}")
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

    research = load_research(topic_id)

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
