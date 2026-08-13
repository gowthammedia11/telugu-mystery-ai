import csv
import asyncio
import re
from pathlib import Path

import edge_tts


TOPICS_FILE = "topics/topics.csv"


# ============================================================
# TELUGU PRONUNCIATION MAP
# ============================================================

PRONUNCIATION_MAP = {

    # --------------------------------------------------------
    # ANTARCTICA / PLACES
    # --------------------------------------------------------

    "Antarctica": "అంటార్కిటికా",
    "antarctica": "అంటార్కిటికా",

    "Antarctic": "అంటార్కిటిక్",
    "antarctic": "అంటార్కిటిక్",

    "Thwaites Glacier": "త్వైట్స్ గ్లేసియర్",
    "Thwaites": "త్వైట్స్",

    "Weddell Sea": "వెడెల్ సీ",

    "West Antarctica": "వెస్ట్ అంటార్కిటికా",
    "East Antarctica": "ఈస్ట్ అంటార్కిటికా",

    "Southern Ocean": "సదరన్ ఓషన్",

    # --------------------------------------------------------
    # SCIENTIFIC TERMS
    # --------------------------------------------------------

    "Circumpolar Deep Water":
        "సర్కంపోలార్ డీప్ వాటర్",

    "Marine Ice Sheet Instability":
        "మెరైన్ ఐస్ షీట్ ఇన్‌స్టెబిలిటీ",

    "Marine Ice Sheet":
        "మెరైన్ ఐస్ షీట్",

    "Ice Sheet":
        "ఐస్ షీట్",

    "ice sheet":
        "ఐస్ షీట్",

    "Ice Shelf":
        "ఐస్ షెల్ఫ్",

    "ice shelf":
        "ఐస్ షెల్ఫ్",

    "Grounding Line":
        "గ్రౌండింగ్ లైన్",

    "grounding line":
        "గ్రౌండింగ్ లైన్",

    "Ice Core":
        "ఐస్ కోర్",

    "ice core":
        "ఐస్ కోర్",

    "Marine Ice Cliff Instability":
        "మెరైన్ ఐస్ క్లిఫ్ ఇన్‌స్టెబిలిటీ",

    "MISI":
        "మైసీ",

    "MICI":
        "మైసీ",

    "polynya":
        "పాలిన్యా",

    "Polynya":
        "పాలిన్యా",

    "buttresses":
        "బట్రెసెస్",

    "buttress":
        "బట్రెస్",

    # --------------------------------------------------------
    # SATELLITES
    # --------------------------------------------------------

    "GRACE-FO":
        "గ్రేస్ ఎఫ్ ఓ",

    "GRACE":
        "గ్రేస్",

    "ICESat-2":
        "ఐస్‌శాట్ టూ",

    "ICESat":
        "ఐస్‌శాట్",

    "CryoSat-2":
        "క్రయోశాట్ టూ",

    "CryoSat":
        "క్రయోశాట్",

    # --------------------------------------------------------
    # SCIENCE ORGANISATIONS
    # --------------------------------------------------------

    "NASA":
        "నాసా",

    "NSIDC":
        "ఎన్ ఎస్ ఐ డీ సీ",

    "IPCC":
        "ఐ పీ సీ సీ",

    "IMBIE":
        "ఇంబీ",

    # --------------------------------------------------------
    # SCIENCE WORDS
    # --------------------------------------------------------

    "scientifically":
        "సైంటిఫికల్లీ",

    "scientific":
        "సైంటిఫిక్",

    "scientists":
        "సైంటిస్టులు",

    "scientist":
        "సైంటిస్ట్",

    "research":
        "రీసెర్చ్",

    "researchers":
        "రీసెర్చర్స్",

    "researcher":
        "రీసెర్చర్",

    "discovery":
        "డిస్కవరీ",

    "discoveries":
        "డిస్కవరీలు",

    "theory":
        "థియరీ",

    "theories":
        "థియరీస్",

    "hypothesis":
        "హైపోథిసిస్",

    "hypotheses":
        "హైపోథసీస్",

    "evidence":
        "ఎవిడెన్స్",

    "data":
        "డేటా",

    "monitoring":
        "మానిటరింగ్",

    "satellite monitoring":
        "శాటిలైట్ మానిటరింగ్",

    "satellites":
        "శాటిలైట్స్",

    "satellite":
        "శాటిలైట్",

    # --------------------------------------------------------
    # CLIMATE / ICE / OCEAN
    # --------------------------------------------------------

    "climate change":
        "క్లైమేట్ చేంజ్",

    "climate":
        "క్లైమేట్",

    "Climate":
        "క్లైమేట్",

    "glaciers":
        "గ్లేసియర్స్",

    "glacier":
        "గ్లేసియర్",

    "iceberg":
        "ఐస్‌బర్గ్",

    "icebergs":
        "ఐస్‌బర్గ్స్",

    "ice":
        "ఐస్",

    "snow":
        "స్నో",

    "ocean":
        "ఓషన్",

    "oceans":
        "ఓషన్స్",

    "water":
        "వాటర్",

    "deep water":
        "డీప్ వాటర్",

    "freshwater":
        "ఫ్రెష్ వాటర్",

    "fresh water":
        "ఫ్రెష్ వాటర్",

    "sea level":
        "సీ లెవెల్",

    "sea-level":
        "సీ లెవెల్",

    "sea":
        "సీ",

    "ocean heat":
        "ఓషన్ హీట్",

    "melting":
        "మెల్టింగ్",

    "melt":
        "మెల్ట్",

    "mass":
        "మాస్",

    "collapse":
        "కలాప్స్",

    "retreat":
        "రిట్రీట్",

    "retreated":
        "రిట్రీటెడ్",

    "thinning":
        "థిన్నింగ్",

    # --------------------------------------------------------
    # CARBON / ATMOSPHERE
    # --------------------------------------------------------

    "carbon dioxide":
        "కార్బన్ డయాక్సైడ్",

    "Carbon Dioxide":
        "కార్బన్ డయాక్సైడ్",

    "CO2":
        "సీ ఓ టూ",

    "CO₂":
        "సీ ఓ టూ",

    "ppm":
        "పీపీఎం",

    "PPM":
        "పీపీఎం",

    # --------------------------------------------------------
    # UNITS
    # --------------------------------------------------------

    "Gt/year":
        "గిగాటన్నుల చొప్పున సంవత్సరానికి",

    "Gt/yr":
        "గిగాటన్నుల చొప్పున సంవత్సరానికి",

    "km":
        "కిలోమీటర్లు",

    "km.":
        "కిలోమీటర్లు",

    "cm":
        "సెంటీమీటర్లు",

    "m":
        "మీటర్లు",

    # --------------------------------------------------------
    # COMMON ENGLISH WORDS
    # --------------------------------------------------------

    "mystery":
        "మిస్టరీ",

    "Mystery":
        "మిస్టరీ",

    "unknown":
        "అన్‌నోన్",

    "unknowns":
        "అన్‌నోన్ విషయాలు",

    "fact":
        "ఫ్యాక్ట్",

    "facts":
        "ఫ్యాక్ట్స్",

    "scientific facts":
        "సైంటిఫిక్ ఫ్యాక్ట్స్",

    "video":
        "వీడియో",

    "videos":
        "వీడియోలు",

    "world":
        "వరల్డ్",

    "Earth":
        "ఎర్త్",

    "earth":
        "ఎర్త్",

    "planet":
        "ప్లానెట్",

    "planets":
        "ప్లానెట్స్",

    "surface":
        "సర్ఫేస్",

    "below":
        "బిలో",

    "above":
        "అబవ్",

    "inside":
        "ఇన్‌సైడ్",

    "outside":
        "అవుట్‌సైడ్",

    "large":
        "లార్జ్",

    "largest":
        "లార్జెస్ట్",

    "current":
        "కరెంట్",

    "future":
        "ఫ్యూచర్",

    "past":
        "పాస్ట్",

    "present":
        "ప్రెజెంట్",

    "possible":
        "పాజిబుల్",

    "exact":
        "ఎగ్జాక్ట్",

    "important":
        "ఇంపార్టెంట్",

    "major":
        "మేజర్",

    "global":
        "గ్లోబల్",

    "natural":
        "నేచురల్",

    "process":
        "ప్రాసెస్",

    "processes":
        "ప్రాసెసెస్",

    "system":
        "సిస్టమ్",

    "systems":
        "సిస్టమ్స్",

    "change":
        "చేంజ్",

    "changes":
        "చేంజెస్",

    "increase":
        "ఇన్‌క్రీజ్",

    "decrease":
        "డిక్రీజ్",

    "speed":
        "స్పీడ్",

    "accelerate":
        "యాక్సిలరేట్",

    "accelerating":
        "యాక్సిలరేటింగ్",

    "temperature":
        "టెంపరేచర్",

    "warm":
        "వార్మ్",

    "cold":
        "కోల్డ్",

    "deep":
        "డీప్",

    "shallow":
        "షాలో",

    "pressure":
        "ప్రెషర్",

    "energy":
        "ఎనర్జీ",

    "force":
        "ఫోర్స్",

    "feedback":
        "ఫీడ్‌బ్యాక్",

    "response":
        "రెస్పాన్స్",

    "instability":
        "ఇన్‌స్టెబిలిటీ",

    "stability":
        "స్టెబిలిటీ",

    "impact":
        "ఇంపాక్ట్",

    "effect":
        "ఎఫెక్ట్",

    "effects":
        "ఎఫెక్ట్స్",

    # --------------------------------------------------------
    # CONNECTING WORDS
    # --------------------------------------------------------

    "because":
        "బికాజ్",

    "however":
        "హౌఎవర్",

    "therefore":
        "దేర్‌ఫోర్",

    "especially":
        "ఎస్పెషల్లీ",

    "currently":
        "కరెంట్‌లీ",

    "recently":
        "రీసెంట్‌లీ",

    "actually":
        "యాక్చువల్లీ",

    "mostly":
        "మోస్ట్‌లీ",

    "almost":
        "ఆల్మోస్ట్",

    "around":
        "అరౌండ్",

    "about":
        "అబౌట్",

    "more":
        "మోర్",

    "less":
        "లెస్",

    "than":
        "దాన్",

    "through":
        "త్రూ",

    "during":
        "డ్యూరింగ్",

    "after":
        "ఆఫ్టర్",

    "before":
        "బిఫోర్",

    "between":
        "బిట్వీన్",

    "without":
        "వితౌట్",

    "within":
        "వితిన్",

    "under":
        "అండర్",

    "over":
        "ఓవర్",

    "from":
        "ఫ్రమ్",

    "into":
        "ఇంటూ",

    "near":
        "నియర్",

    # --------------------------------------------------------
    # YEARS / TIME
    # --------------------------------------------------------

    "years":
        "సంవత్సరాలు",

    "year":
        "సంవత్సరం",

    "decades":
        "దశాబ్దాలు",

    "decade":
        "దశాబ్దం",
}


# ============================================================
# NUMBER WORDS
# ============================================================

NUMBER_WORDS = {
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
    19: "పంతొమ్మిది",
    20: "ఇరవై",
    30: "ముప్పై",
    40: "నలభై",
    50: "యాభై",
    60: "అరవై",
    70: "డెబ్బై",
    80: "ఎనభై",
    90: "తొంభై",
}


# ============================================================
# TELUGU NUMBER CONVERSION
# ============================================================

def number_to_telugu(number):
    """
    Natural Telugu number pronunciation.

    Examples:

    0    -> సున్నా
    15   -> పదిహేను
    25   -> ఇరవై ఐదు
    100  -> వంద
    105  -> వంద ఐదు
    190  -> వంద తొంభై

    Years:

    1900 -> పంతొమ్మిది వందల
    1947 -> పంతొమ్మిది వందల నలభై ఏడు
    1990 -> పంతొమ్మిది వందల తొంభై
    2000 -> రెండు వేల
    2002 -> రెండు వేల రెండు
    2014 -> రెండు వేల పద్నాలుగు
    2026 -> రెండు వేల ఇరవై ఆరు
    """

    number = int(number)

    # --------------------------------------------------------
    # 0 - 20 / Tens
    # --------------------------------------------------------

    if number in NUMBER_WORDS:
        return NUMBER_WORDS[number]

    # --------------------------------------------------------
    # 21 - 99
    # --------------------------------------------------------

    if number < 100:

        tens = (number // 10) * 10
        ones = number % 10

        if ones == 0:
            return NUMBER_WORDS[tens]

        return (
            NUMBER_WORDS[tens]
            + " "
            + NUMBER_WORDS[ones]
        )

    # --------------------------------------------------------
    # 100 - 999
    # --------------------------------------------------------

    if number < 1000:

        hundreds = number // 100
        remainder = number % 100

        if hundreds == 1:
            result = "వంద"
        else:
            result = (
                NUMBER_WORDS[hundreds]
                + " వందల"
            )

        if remainder:
            result += " " + number_to_telugu(remainder)

        return result

    # --------------------------------------------------------
    # 1000 - 1999
    #
    # Natural Telugu year style:
    #
    # 1000 -> వెయ్యి
    # 1100 -> పదకొండు వందల
    # 1947 -> పంతొమ్మిది వందల నలభై ఏడు
    # 1990 -> పంతొమ్మిది వందల తొంభై
    # --------------------------------------------------------

    if 1000 <= number < 2000:

        remainder = number - 1000

        if remainder == 0:
            return "వెయ్యి"

        # 1100 - 1199
        if remainder >= 100:

            hundreds_part = number // 100
            last_two = number % 100

            if hundreds_part == 11:
                result = "పదకొండు వందల"

            elif hundreds_part == 12:
                result = "పన్నెండు వందల"

            elif hundreds_part == 13:
                result = "పదమూడు వందల"

            elif hundreds_part == 14:
                result = "పద్నాలుగు వందల"

            elif hundreds_part == 15:
                result = "పదిహేను వందల"

            elif hundreds_part == 16:
                result = "పదహారు వందల"

            elif hundreds_part == 17:
                result = "పదిహేడు వందల"

            elif hundreds_part == 18:
                result = "పద్దెనిమిది వందల"

            elif hundreds_part == 19:
                result = "పంతొమ్మిది వందల"

            else:
                result = "వెయ్యి"

            if last_two:
                result += " " + number_to_telugu(last_two)

            return result

        # 1001 - 1099
        result = "వెయ్యి"

        if remainder:
            result += " " + number_to_telugu(remainder)

        return result

    # --------------------------------------------------------
    # 2000 - 9999
    # --------------------------------------------------------

    if number < 10000:

        thousands = number // 1000
        remainder = number % 1000

        result = (
            NUMBER_WORDS[thousands]
            + " వేల"
        )

        if remainder:
            result += " " + number_to_telugu(remainder)

        return result

    # --------------------------------------------------------
    # Larger numbers
    # --------------------------------------------------------

    return str(number)


# ============================================================
# NORMALIZE TEXT FOR TELUGU TTS
# ============================================================

def normalize_for_telugu_tts(text):

    if not text:
        return text

    # ========================================================
    # MULTI-WORD PRONUNCIATION TERMS FIRST
    # ========================================================

    replacements = sorted(
        PRONUNCIATION_MAP.items(),
        key=lambda item: len(item[0]),
        reverse=True
    )

    for original, replacement in replacements:

        text = re.sub(
            r"(?<![A-Za-z])"
            + re.escape(original)
            + r"(?![A-Za-z])",
            replacement,
            text,
            flags=re.IGNORECASE
        )

    # ========================================================
    # SPECIAL NUMBER EXPRESSIONS
    # ========================================================

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

    # 14 kilometers
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

    # 10 meters
    text = re.sub(
        r"\b10\s*మీటర్లు\b",
        "పది మీటర్లు",
        text,
        flags=re.IGNORECASE
    )

    # ========================================================
    # SPECIAL YEAR RANGES
    # ========================================================

    text = re.sub(
        r"\b2014[-–]15\b",
        "రెండు వేల పద్నాలుగు నుంచి పదిహేను",
        text
    )

    text = re.sub(
        r"\b2016[-–]17\b",
        "రెండు వేల పదహారు నుంచి పదిహేడు",
        text
    )

    # ========================================================
    # 1990s
    # ========================================================

    text = re.sub(
        r"\b1990s\b",
        "పంతొమ్మిది వందల తొంభై దశకం",
        text,
        flags=re.IGNORECASE
    )

    # ========================================================
    # GENERAL 4-DIGIT YEARS
    #
    # IMPORTANT:
    #
    # 1990 -> పంతొమ్మిది వందల తొంభై
    # 1947 -> పంతొమ్మిది వందల నలభై ఏడు
    # 1985 -> పంతొమ్మిది వందల ఎనభై ఐదు
    #
    # 2002 -> రెండు వేల రెండు
    # 2014 -> రెండు వేల పద్నాలుగు
    # 2026 -> రెండు వేల ఇరవై ఆరు
    #
    # ========================================================

    def replace_year(match):

        year = int(match.group(0))

        if 1000 <= year <= 2099:
            return number_to_telugu(year)

        return match.group(0)

    text = re.sub(
        r"\b(?:1[0-9]{3}|20[0-9]{2})\b",
        replace_year,
        text
    )

    # ========================================================
    # NORMAL INTEGER NUMBERS
    #
    # Convert remaining numbers so TTS does not read:
    #
    # 15 -> one five
    # 25 -> two five
    # 100 -> one zero zero
    #
    # ========================================================

    def replace_number(match):

        value = match.group(0)

        try:
            number = int(value)
        except ValueError:
            return value

        # Avoid touching very large numbers that may be IDs.
        if number <= 9999:
            return number_to_telugu(number)

        return value

    text = re.sub(
        r"\b\d+\b",
        replace_number,
        text
    )

    # ========================================================
    # REMOVE MARKDOWN
    # ========================================================

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

    # ========================================================
    # REMOVE HEADINGS
    # ========================================================

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

    # ========================================================
    # CLEAN SPACES / PAUSES
    # ========================================================

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

    # ========================================================
    # NORMALIZE
    # ========================================================

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

    # ========================================================
    # DELETE OLD AUDIO
    # ========================================================

    if output_file.exists():

        print(
            f"Deleting old audio: "
            f"{output_file}"
        )

        output_file.unlink()

    # ========================================================
    # CHECK REMAINING ENGLISH
    # ========================================================

    remaining_english = re.findall(
        r"\b[A-Za-z]{3,}\b",
        normalized_text
    )

    print("=" * 70)
    print("ENGLISH WORD CHECK")
    print("=" * 70)

    if remaining_english:

        unique_words = []

        for word in remaining_english:

            if word.lower() not in [
                item.lower()
                for item in unique_words
            ]:

                unique_words.append(
                    word
                )

        print(
            "REMAINING ENGLISH WORDS:"
        )

        print(
            ", ".join(
                unique_words[:100]
            )
        )

    else:

        print(
            "NO ENGLISH WORDS FOUND"
        )

    print("=" * 70)

    # ========================================================
    # TELUGU VOICE
    # ========================================================

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
        normalized_text[:3000]
    )

    print("=" * 70)

    # ========================================================
    # GENERATE AUDIO
    # ========================================================

    communicate = edge_tts.Communicate(
        text=normalized_text,
        voice=voice,
        rate="+0%",
        volume="+0%"
    )

    await communicate.save(
        str(output_file)
    )

    # ========================================================
    # VERIFY
    # ========================================================

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
        "FRESH TELUGU VOICE CREATED SUCCESSFULLY"
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
