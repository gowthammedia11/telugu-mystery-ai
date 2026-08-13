import csv
import asyncio
import re
from pathlib import Path

import edge_tts


TOPICS_FILE = "topics/topics.csv"


# ============================================================
# TELUGU PRONUNCIATION NORMALIZATION
# ============================================================

PRONUNCIATION_MAP = {

    # Places / topics
    "Antarctica": "అంటార్కిటికా",
    "antarctica": "అంటార్కిటికా",
    "Antarctic": "అంటార్కిటిక్",
    "antarctic": "అంటార్కిటిక్",

    # Important Antarctic locations
    "Thwaites": "త్వైట్స్",
    "Thwaites Glacier": "త్వైట్స్ గ్లేసియర్",
    "Weddell Sea": "వెడెల్ సీ",

    # Scientific terms
    "Circumpolar Deep Water": "సర్కంపోలార్ డీప్ వాటర్",
    "Marine Ice Sheet Instability": "మెరైన్ ఐస్ షీట్ ఇన్‌స్టెబిలిటీ",
    "MISI": "మైసీ",
    "MICI": "మైసీ",

    "ice shelf": "ఐస్ షెల్ఫ్",
    "Ice Shelf": "ఐస్ షెల్ఫ్",

    "grounding line": "గ్రౌండింగ్ లైన్",
    "Grounding Line": "గ్రౌండింగ్ లైన్",

    "ice sheet": "ఐస్ షీట్",
    "Ice Sheet": "ఐస్ షీట్",

    "ice core": "ఐస్ కోర్",
    "Ice Core": "ఐస్ కోర్",

    # Satellites
    "GRACE-FO": "గ్రేస్ ఎఫ్ ఓ",
    "GRACE": "గ్రేస్",
    "ICESat-2": "ఐస్‌శాట్ టూ",
    "ICESat": "ఐస్‌శాట్",
    "CryoSat-2": "క్రయోశాట్ టూ",
    "CryoSat": "క్రయోశాట్",

    # Science / climate
    "satellite": "శాటిలైట్",
    "satellites": "శాటిలైట్స్",

    "climate": "క్లైమేట్",
    "Climate": "క్లైమేట్",

    "glacier": "గ్లేసియర్",
    "glaciers": "గ్లేసియర్స్",

    "polynya": "పాలిన్యా",
    "Polynya": "పాలిన్యా",

    "buttress": "బట్రెస్",
    "buttresses": "బట్రెసెస్",

    # Organisations / reports
    "NASA": "నాసా",
    "NSIDC": "ఎన్ ఎస్ ఐ డీ సీ",
    "IPCC": "ఐ పీ సీ సీ",
    "IMBIE": "ఇంబీ",

    # Units
    "ppm": "పీపీఎం",
    "PPM": "పీపీఎం",

    "Gt/year": "గిగాటన్నుల చొప్పున సంవత్సరానికి",
    "Gt/yr": "గిగాటన్నుల చొప్పున సంవత్సరానికి",

    "km": "కిలోమీటర్లు",
    "km.": "కిలోమీటర్లు",

    "m": "మీటర్లు",

    # Common technical words
    "mass": "మాస్",
    "sea level": "సీ లెవెల్",
    "sea-level": "సీ లెవెల్",

    "freshwater": "ఫ్రెష్ వాటర్",
    "fresh water": "ఫ్రెష్ వాటర్",

    "carbon dioxide": "కార్బన్ డయాక్సైడ్",
    "Carbon Dioxide": "కార్బన్ డయాక్సైడ్",
    "CO2": "సీ ఓ టూ",
    "CO₂": "సీ ఓ టూ",

    # Time / common English
    "years": "సంవత్సరాలు",
    "year": "సంవత్సరం",

    # Research words
    "research": "రీసెర్చ్",
    "scientists": "సైంటిస్టులు",
    "scientist": "సైంటిస్ట్",
    "satellite monitoring": "శాటిలైట్ మానిటరింగ్",

}


# ============================================================
# NORMALIZE TEXT FOR TELUGU TTS
# ============================================================

def normalize_for_telugu_tts(text):

    if not text:
        return text

    # --------------------------------------------------------
    # Replace known multi-word terms FIRST
    # --------------------------------------------------------

    replacements = sorted(
        PRONUNCIATION_MAP.items(),
        key=lambda item: len(item[0]),
        reverse=True
    )

    for original, replacement in replacements:

        text = re.sub(
            re.escape(original),
            replacement,
            text,
            flags=re.IGNORECASE
        )

    # --------------------------------------------------------
    # Convert common numeric patterns
    # --------------------------------------------------------

    # 800,000
    text = re.sub(
        r"\b800,000\b",
        "ఎనిమిది లక్షలు",
        text
    )

    # 420 ppm
    text = re.sub(
        r"\b420\s*పీపీఎం\b",
        "నాలుగు వందల ఇరవై పీపీఎం",
        text,
        flags=re.IGNORECASE
    )

    # 180-300 ppm
    text = re.sub(
        r"\b180\s*[-–]\s*300\s*పీపీఎం\b",
        "వంద ఎనభై నుంచి మూడు వందల పీపీఎం వరకు",
        text,
        flags=re.IGNORECASE
    )

    # 14 km
    text = re.sub(
        r"\b14\s*కిలోమీటర్లు\b",
        "పద్నాలుగు కిలోమీటర్లు",
        text,
        flags=re.IGNORECASE
    )

    # 65 cm
    text = re.sub(
        r"\b65\s*cm\b",
        "అరవై ఐదు సెంటీమీటర్లు",
        text,
        flags=re.IGNORECASE
    )

    # 10 m
    text = re.sub(
        r"\b10\s*మీటర్లు\b",
        "పది మీటర్లు",
        text,
        flags=re.IGNORECASE
    )

    # --------------------------------------------------------
    # Clean Markdown / formatting characters
    # --------------------------------------------------------

    text = re.sub(
        r"^#+\s*",
        "",
        text,
        flags=re.MULTILINE
    )

    text = text.replace(
        "**",
        ""
    )

    text = text.replace(
        "__",
        ""
    )

    text = text.replace(
        "*",
        ""
    )

    # --------------------------------------------------------
    # Remove unnecessary structural labels
    # --------------------------------------------------------

    lines = []

    ignored_headings = {
        "hook",
        "mystery",
        "background",
        "facts",
        "explanation",
        "discoveries",
        "unknowns",
        "conclusion",
    }

    for line in text.splitlines():

        clean_line = line.strip()

        if not clean_line:
            continue

        heading_check = (
            clean_line
            .rstrip(":")
            .strip()
            .lower()
        )

        if heading_check in ignored_headings:
            continue

        lines.append(
            clean_line
        )

    text = "\n".join(lines)

    # --------------------------------------------------------
    # Improve pauses for narration
    # --------------------------------------------------------

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    text = re.sub(
        r"\s*,\s*",
        ", ",
        text
    )

    text = re.sub(
        r"\s*\.\s*",
        ". ",
        text
    )

    text = re.sub(
        r"\?\s*",
        "? ",
        text
    )

    text = re.sub(
        r"!\s*",
        "! ",
        text
    )

    # Avoid excessive punctuation
    text = re.sub(
        r"\.{2,}",
        ".",
        text
    )

    return text.strip()


# ============================================================
# FIND NEXT SCRIPT
# ============================================================

def get_next_script():

    with open(
        TOPICS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        topics = list(
            csv.DictReader(file)
        )

    for topic in topics:

        topic_id = topic[
            "id"
        ].strip()

        script_file = Path(
            f"scripts/{topic_id}.txt"
        )

        status = topic.get(
            "status",
            ""
        ).strip().lower()

        if (
            script_file.exists()
            and status == "pending"
        ):

            return topic

    return None


# ============================================================
# GENERATE VOICE
# ============================================================

async def generate_voice(
    topic_id
):

    script_file = Path(
        f"scripts/{topic_id}.txt"
    )

    output_file = Path(
        f"audio/{topic_id}.mp3"
    )

    text = script_file.read_text(
        encoding="utf-8"
    ).strip()

    if not text:
        raise Exception(
            "Script is empty"
        )

    # --------------------------------------------------------
    # Convert script to Telugu-friendly speech
    # --------------------------------------------------------

    normalized_text = (
        normalize_for_telugu_tts(
            text
        )
    )

    if not normalized_text:
        raise Exception(
            "Normalized script is empty"
        )

    Path(
        "audio"
    ).mkdir(
        exist_ok=True
    )

    # --------------------------------------------------------
    # Telugu Neural Voice
    # --------------------------------------------------------

    voice = (
        "te-IN-MohanNeural"
    )

    print(
        "=" * 60
    )

    print(
        "GENERATING TELUGU VOICE"
    )

    print(
        f"TOPIC: {topic_id}"
    )

    print(
        f"VOICE: {voice}"
    )

    print(
        f"ORIGINAL CHARACTERS: "
        f"{len(text)}"
    )

    print(
        f"NORMALIZED CHARACTERS: "
        f"{len(normalized_text)}"
    )

    print(
        "=" * 60
    )

    # --------------------------------------------------------
    # Print first part for verification
    # --------------------------------------------------------

    print(
        "NORMALIZED TEXT PREVIEW:"
    )

    print(
        normalized_text[:1000]
    )

    print(
        "=" * 60
    )

    communicate = edge_tts.Communicate(
        text=normalized_text,
        voice=voice,
        rate="+0%",
        volume="+0%"
    )

    await communicate.save(
        str(output_file)
    )

    print(
        "=" * 60
    )

    print(
        f"VOICE CREATED: "
        f"{output_file}"
    )

    print(
        "=" * 60
    )


# ============================================================
# MAIN
# ============================================================

topic = get_next_script()

if not topic:

    print(
        "NO SCRIPT READY FOR VOICE"
    )

    exit(0)


topic_id = topic[
    "id"
].strip()


asyncio.run(
    generate_voice(
        topic_id
    )
)
