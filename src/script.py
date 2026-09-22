import os
import re
import time
from pathlib import Path

import requests


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openrouter/free"

SCRIPTS_DIR = Path("scripts")

MIN_CHARS = 4500
TARGET_CHARS = 5500
MAX_CHARS = 6000

MAX_ATTEMPTS = 3
REQUEST_TIMEOUT = 240


FORBIDDEN_PATTERNS = [
    r"\b(latitude|longitude|coordinates?|coordinate)\b",
    r"\b\d+(?:\.\d+)?\s*(?:°|degrees?)\b",
    r"\b\d+(?:\.\d+)?\s*(?:miles?|mi)\b",
    r"\bAI\b",
    r"\bArtificial Intelligence\b",
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
    r"మనము ఇప్పుడు",
    r"ఇక్కడ మనం",
    r"ఇలా రాయాలి",
    r"ప్రశ్నలకు సమాధానం",
    r"---",
]


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

    # Remove markdown headings and bullet formatting.
    text = re.sub(r"(?m)^\s*#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*[-*•]\s+", "", text)
    text = re.sub(r"(?m)^\s*\d+\.\s+", "", text)

    # Remove excessive punctuation.
    text = text.replace("—", " ")
    text = text.replace("–", " ")
    text = re.sub(r"\.{3,}", ".", text)
    text = re.sub(r"\!{2,}", "!", text)
    text = re.sub(r"\?{2,}", "?", text)

    # Normalize spaces.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove blank fragments.
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            lines.append(line)

    text = " ".join(lines)

    # Normalize sentence spacing.
    text = re.sub(r"\s+([,.!?])", r"\1", text)
    text = re.sub(r"([.!?])\s+", r"\1 ", text)

    return text.strip()


def split_sentences(text):
    if not text:
        return []

    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def normalize_for_duplicate_check(text):
    text = text.lower()
    text = re.sub(r"[^ఀ-౿a-z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def has_repeated_sentences(text):
    sentences = split_sentences(text)

    if len(sentences) < 10:
        return False

    normalized = []

    for sentence in sentences:
        cleaned = normalize_for_duplicate_check(sentence)

        if len(cleaned) < 35:
            continue

        normalized.append(cleaned)

    seen = set()

    for sentence in normalized:
        if sentence in seen:
            return True
        seen.add(sentence)

    # Detect repeated 2-sentence blocks.
    blocks = []

    for i in range(len(normalized) - 1):
        block = normalized[i] + " " + normalized[i + 1]
        blocks.append(block)

    block_counts = {}

    for block in blocks:
        block_counts[block] = block_counts.get(block, 0) + 1

    for count in block_counts.values():
        if count >= 2:
            return True

    return False


def has_repeated_paragraphs(text):
    paragraphs = [
        p.strip()
        for p in re.split(r"\n+", text)
        if p.strip()
    ]

    if len(paragraphs) < 3:
        return False

    normalized = [
        normalize_for_duplicate_check(p)
        for p in paragraphs
    ]

    normalized = [
        p for p in normalized
        if len(p) >= 80
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
        "---",
        "script",
        "narration script",
    ]

    for item in checks:
        if item.lower() in lowered:
            return True

    return False


def english_word_check(text):
    words = re.findall(r"\b[A-Za-z]{2,}\b", text)

    allowed = {
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

    remaining = []

    for word in words:
        if word not in allowed:
            remaining.append(word)

    return sorted(set(remaining))


def validate_script(text):
    if not text:
        return False, "EMPTY SCRIPT"

    char_count = len(text)

    if char_count < MIN_CHARS:
        return False, f"SCRIPT TOO SHORT: {char_count} chars"

    if char_count > MAX_CHARS:
        return False, f"SCRIPT TOO LONG: {char_count} chars"

    if has_repeated_sentences(text):
        return False, "REPEATED SENTENCES DETECTED"

    if has_repeated_paragraphs(text):
        return False, "REPEATED PARAGRAPHS DETECTED"

    if contains_meta_text(text):
        return False, "META TEXT DETECTED"

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return False, f"FORBIDDEN CONTENT DETECTED: {pattern}"

    english_words = english_word_check(text)

    if english_words:
        return False, (
            "UNNECESSARY ENGLISH WORDS DETECTED: "
            + ", ".join(english_words[:20])
        )

    return True, "VALID"


def build_prompt(topic_id, topic_title, research):
    return f"""
నువ్వు ఒక ప్రొఫెషనల్ తెలుగు డాక్యుమెంటరీ నారేటర్.

టాపిక్:
{topic_title}

టాపిక్ ID:
{topic_id}

కింద ఇచ్చిన research ఆధారంగా మాత్రమే ఒక సహజమైన, ఆసక్తికరమైన తెలుగు డాక్యుమెంటరీ narration script రాయాలి.

RESEARCH:
{research}

చాలా ముఖ్యమైన నియమాలు:

1. ఇది 7 నుంచి 8 నిమిషాల YouTube long-form documentary narration కోసం.
2. మొత్తం స్క్రిప్ట్ సుమారు 5000 నుంచి 5700 characters మధ్య ఉండాలి.
3. 6000 characters దాటకూడదు.
4. ఒకే విషయం, ఒకే sentence, ఒకే paragraph లేదా ఒకే explanation మళ్లీ మళ్లీ రాయకూడదు.
5. Research లో ఉన్న facts మాత్రమే ఉపయోగించాలి. ఊహాజనిత facts తయారు చేయకూడదు.
6. ప్రారంభం సహజమైన mystery hook తో ఉండాలి.
7. తర్వాత location, discovery/background, unusual features, scientific explanations, opposing interpretations మరియు ప్రస్తుతం తెలిసిన విషయాలను సహజంగా వివరించాలి.
8. చివర్లో complete and satisfying conclusion ఉండాలి. మధ్యలో script ఆగిపోయినట్టు లేదా abrupt ending ఉండకూడదు.
9. తెలుగు మాట్లాడే వ్యక్తి సహజంగా చెప్పినట్టు ఉండాలి. చాలా పుస్తక భాష ఉపయోగించకూడదు.
10. headings వద్దు.
11. bullet points వద్దు.
12. numbered points వద్దు.
13. markdown వద్దు.
14. "---" ఉపయోగించకూడదు.
15. "మీ కోసం స్క్రిప్ట్", "ఈ narration", "ఇప్పుడు మనం", "ఈ వీడియోలో" వంటి meta phrases ఉపయోగించకూడదు.
16. YouTube, AI, artificial intelligence వంటి platform/technology references అవసరం లేకపోతే ఉపయోగించకూడదు.
17. coordinates, latitude, longitude లేదా degree formats ఎట్టి పరిస్థితుల్లోనూ ఉపయోగించకూడదు.
18. miles ఉపయోగించకూడదు. దూరం అవసరమైతే kilometers లేదా సహజమైన తెలుగు వివరణ ఉపయోగించాలి.
19. years ను సహజంగా తెలుగు మాటల్లో చెప్పాలి. digit-by-digit pronunciation కోసం రాయకూడదు.
20. unnecessary decimal numbers వద్దు.
21. English words వీలైనంత వరకు పూర్తిగా నివారించాలి. అవసరమైన proper names మాత్రమే ఉంచాలి.
22. Research లోని ఒక paragraph ను copy చేసి repeat చేయకూడదు.
23. ఒక explanation ను paraphrase చేసి మళ్లీ repeat చేయకూడదు.
24. ప్రతి paragraph కథను ముందుకు తీసుకెళ్లాలి.
25. చివరి 2–3 sentences సహజమైన ముగింపుగా ఉండాలి.

రచనా flow ఇలా ఉండాలి:

మొదట curiosity కలిగించే opening.
తర్వాత ఈ ప్రదేశం లేదా సంఘటన ఏంటి అనే basic context.
తర్వాత అది ఎందుకు mystery అయింది.
తర్వాత అక్కడ కనిపించే ప్రధాన features లేదా observations.
తర్వాత వాటికి సంబంధించిన scientific/geological explanation.
తర్వాత దీనిని human-made structure అని భావించే వాదన ఏ ఆధారాలపై ఉందో.
తర్వాత natural formation అని చెప్పే explanation ఏంటి.
తర్వాత evidence ఏమి చెబుతోంది, ఇంకా ఏ విషయాలు స్పష్టంగా లేవో.
చివర్లో mystery యొక్క ప్రస్తుత స్థితిని balanced గా చెప్పి natural ending ఇవ్వాలి.

IMPORTANT:
నీ output లో narration మాత్రమే ఉండాలి.
ఏ introduction note, explanation, heading, title, disclaimer లేదా closing note ఇవ్వకూడదు.
ఒకసారి రాసిన sentence లేదా paragraph ను మళ్లీ రాయకూడదు.
"""


def generate_script(topic_id, topic_title, research):
    api_key = os.environ.get("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY secret is missing")

    prompt = build_prompt(
        topic_id,
        topic_title,
        research,
    )

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
                    "నువ్వు తెలుగు documentary narration writer. "
                    "కేవలం final narration మాత్రమే ఇవ్వాలి. "
                    "Repeated content ఎట్టి పరిస్థితుల్లోనూ ఇవ్వకూడదు."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.35,
        "max_tokens": 4000,
    }

    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"OPENROUTER SCRIPT ATTEMPT {attempt}/{MAX_ATTEMPTS}")

        try:
            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )

            print(f"OPENROUTER HTTP STATUS: {response.status_code}")

            if response.status_code != 200:
                last_error = (
                    f"HTTP {response.status_code}: "
                    f"{response.text[:1000]}"
                )
                print(last_error)
                time.sleep(3)
                continue

            data = response.json()

            choices = data.get("choices", [])

            if not choices:
                last_error = "OpenRouter returned no choices"
                print(last_error)
                time.sleep(3)
                continue

            message = choices[0].get("message", {})
            content = message.get("content", "")

            if isinstance(content, list):
                content = " ".join(
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict)
                )

            content = str(content).strip()

            if not content:
                last_error = "OpenRouter returned empty content"
                print(last_error)
                time.sleep(3)
                continue

            print("OPENROUTER SCRIPT CONTENT RECEIVED")

            cleaned = clean_text(content)

            valid, reason = validate_script(cleaned)

            print(f"SCRIPT VALIDATION: {reason}")
            print(f"SCRIPT CHARACTERS: {len(cleaned)}")

            if valid:
                return cleaned

            last_error = reason

            if attempt < MAX_ATTEMPTS:
                print(
                    "SCRIPT FAILED VALIDATION. "
                    "REQUESTING A CLEAN REGENERATION."
                )

                payload["messages"].append(
                    {
                        "role": "assistant",
                        "content": content,
                    }
                )

                payload["messages"].append(
                    {
                        "role": "user",
                        "content": (
                            "ఈ output validation లో fail అయింది.\n\n"
                            f"కారణం: {reason}\n\n"
                            "మొత్తం narration ను మొదటి నుంచి కొత్తగా రాయి. "
                            "పాత output ను repeat చేయవద్దు. "
                            "5000 నుంచి 5700 characters మధ్య ఉంచు. "
                            "Repeated sentences లేదా paragraphs ఉండకూడదు. "
                            "Meta text, headings, bullets, markdown వద్దు. "
                            "Narration మాత్రమే ఇవ్వు."
                        ),
                    }
                )

                time.sleep(2)

        except requests.RequestException as exc:
            last_error = f"Request error: {exc}"
            print(last_error)

        except Exception as exc:
            last_error = f"Unexpected script generation error: {exc}"
            print(last_error)

        if attempt < MAX_ATTEMPTS:
            time.sleep(3)

    raise RuntimeError(
        f"Script generation failed after {MAX_ATTEMPTS} attempts: "
        f"{last_error}"
    )


def save_script(topic_id, script):
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    output = SCRIPTS_DIR / f"{str(topic_id).zfill(3)}.txt"

    content = clean_text(script)

    valid, reason = validate_script(content)

    if not valid:
        raise RuntimeError(
            f"Refusing to save invalid script: {reason}"
        )

    output.write_text(content, encoding="utf-8")

    print("=" * 70)
    print("SCRIPT SAVED")
    print("=" * 70)
    print(f"FILE: {output}")
    print(f"CHARACTERS: {len(content)}")
    print("=" * 70)

    return output


def load_research(topic_id):
    research_file = Path("research") / f"{str(topic_id).zfill(3)}.txt"

    if not research_file.exists():
        raise FileNotFoundError(
            f"Research file not found: {research_file}"
        )

    return research_file.read_text(
        encoding="utf-8"
    ).strip()


def main():
    topic_id = os.environ.get("TOPIC_ID")

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

    research = load_research(topic_id)

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
