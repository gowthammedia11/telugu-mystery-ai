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

    "Antarctica": "అంటార్కిటికా",
    "antarctica": "అంటార్కిటికా",
    "Antarctic": "అంటార్కిటిక్",
    "antarctic": "అంటార్కిటిక్",

    "Thwaites Glacier": "త్వైట్స్ గ్లేసియర్",
    "Thwaites": "త్వైట్స్",

    "Weddell Sea": "వెడెల్ సీ",

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

    "GRACE-FO": "గ్రేస్ ఎఫ్ ఓ",
    "GRACE": "గ్రేస్",

    "ICESat-2": "ఐస్‌శాట్ టూ",
    "ICESat": "ఐస్‌శాట్",

    "CryoSat-2": "క్రయోశాట్ టూ",
    "CryoSat": "క్రయోశాట్",

    "satellites": "శాటిలైట్స్",
    "satellite": "శాటిలైట్",

    "climate": "క్లైమేట్",
    "Climate": "క్లైమేట్",

    "glaciers": "గ్లేసియర్స్",
    "glacier": "గ్లేసియర్",

    "polynya": "పాలిన్యా",
    "Polynya": "పాలిన్యా",

    "buttresses": "బట్రెసెస్",
    "buttress": "బట్రెస్",

    "NASA": "నాసా",
    "NSIDC": "ఎన్ ఎస్ ఐ డీ సీ",
    "IPCC": "ఐ పీ సీ సీ",
    "IMBIE": "ఇంబీ",

    "ppm": "పీపీఎం",
    "PPM": "పీపీఎం",

    "Gt/year": "గిగాటన్నుల చొప్పున సంవత్సరానికి",
    "Gt/yr": "గిగాటన్నుల చొప్పున సంవత్సరానికి",

    "km": "కిలోమీటర్లు",
    "km.": "కిలోమీటర్లు",

    "mass": "మాస్",

    "sea level": "సీ లెవెల్",
    "sea-level": "సీ లెవెల్",

    "freshwater": "ఫ్రెష్ వాటర్",
    "fresh water": "ఫ్రెష్ వాటర్",

    "carbon dioxide": "కార్బన్ డయాక్సైడ్",
    "Carbon Dioxide": "కార్బన్ డయాక్సైడ్",

    "CO2": "సీ ఓ టూ",
    "CO₂": "సీ ఓ టూ",

    "research": "రీసెర్చ్",
    "scientists": "సైంటిస్టులు",
    "scientist": "సైంటిస్ట్",

    "satellite monitoring": "శాటిలైట్ మానిటరింగ్",
}


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_for_telugu_tts(text):

    if not text:
        return text

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

    # Numbers

    text = re.sub(
        r"\b800,000\b",
        "ఎనిమిది లక్షలు",
        text
    )

    text = re.sub(
        r"\b420\s*పీపీఎం\b",
        "నాలుగు వందల ఇరవై పీపీఎం",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\b180\s*[-–]\s*300\s*పీపీఎం\b",
        "వంద ఎనభై నుంచి మూడు వందల పీపీఎం వరకు",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\b14\s*కిలోమీటర్లు\b",
        "పద్నాలుగు కిలోమీటర్లు",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\b65\s*cm\b",
        "అరవై ఐదు సెంటీమీటర్లు",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\b10\s*మీటర్లు\b",
        "పది మీటర్లు",
        text,
        flags=re.IGNORECASE
    )

    # Remove markdown

    text = re.sub(
        r"^#+\s*",
        "",
        text,
        flags=re.MULTILINE
    )

    text = text.replace("**", "")
    text = text.replace("__", "")
    text = text.replace("*", "")

    # Remove headings

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

    lines = []

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

    # Improve narration pauses

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

    text = re.sub(
        r"\.{2,}",
        ".",
        text
    )

    return text.strip()


# ============================================================
# FIND SCRIPT
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

    # --------------------------------------------------------
    # FIRST PRIORITY:
    # Topic with script + audio target.
    #
    # This allows us to regenerate the audio whenever
    # the script changes.
    # --------------------------------------------------------

    for topic in topics:

        topic_id = topic[
            "id"
        ].strip()

        script_file = Path(
            f"scripts/{topic_id}.txt"
        )

        if script_file.exists():

            return topic

    return None


# ============================================================
# GENERATE VOICE
# ============================================================

async def generate_voice(topic_id):

    script_file = Path(
        f"scripts/{topic_id}.txt"
    )

    output_file = Path(
        f"audio/{topic_id}.mp3"
    )

    if not script_file.exists():
        raise Exception(
            f"Script not found: {script_file}"
        )

    text = script_file.read_text(
        encoding="utf-8"
    ).strip()

    if not text:
        raise Exception(
            "Script is empty"
        )

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
    # DELETE OLD AUDIO FIRST
    # --------------------------------------------------------

    if output_file.exists():

        print(
            f"Deleting old audio: "
            f"{output_file}"
        )

        output_file.unlink()

    # --------------------------------------------------------
    # TELUGU VOICE
    # --------------------------------------------------------

    voice = (
        "te-IN-MohanNeural"
    )

    print("=" * 70)

    print(
        "GENERATING FRESH TELUGU VOICE"
    )

    print(
        f"TOPIC: {topic_id}"
    )

    print(
        f"SCRIPT: {script_file}"
    )

    print(
        f"OUTPUT: {output_file}"
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

    print("=" * 70)

    print(
        "NORMALIZED TEXT PREVIEW:"
    )

    print(
        normalized_text[:1200]
    )

    print("=" * 70)

    communicate = edge_tts.Communicate(
        text=normalized_text,
        voice=voice,
        rate="+0%",
        volume="+0%"
    )

    await communicate.save(
        str(output_file)
    )

    # --------------------------------------------------------
    # VERIFY
    # --------------------------------------------------------

    if not output_file.exists():

        raise Exception(
            "Voice generation failed: "
            "MP3 was not created"
        )

    file_size = (
        output_file.stat().st_size
    )

    if file_size < 1000:

        raise Exception(
            "Generated audio file is too small"
        )

    print("=" * 70)

    print(
        "FRESH VOICE CREATED SUCCESSFULLY"
    )

    print(
        f"FILE: {output_file}"
    )

    print(
        f"SIZE: {file_size} bytes"
    )

    print("=" * 70)


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

print(
    f"SELECTED TOPIC FOR VOICE: {topic_id}"
)

asyncio.run(
    generate_voice(
        topic_id
    )
)
