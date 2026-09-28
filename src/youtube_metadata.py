import re
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

METADATA_DIR = Path("metadata")


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):
    if not text:
        return ""

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

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# TITLE GENERATION
# ============================================================

def generate_title(
    topic_title,
    script_text
):
    title = topic_title.strip()

    lower_title = title.lower()

    if (
        "mystery" in lower_title
        or "mysteries" in lower_title
    ):
        final_title = (
            f"{title} | అసలు రహస్యం ఏమిటి?"
        )

    elif (
        "borehole" in lower_title
        or "trench" in lower_title
        or "antarctica" in lower_title
        or "glacier" in lower_title
    ):
        final_title = (
            f"{title} | శాస్త్రవేత్తలను ఆశ్చర్యపరిచిన రహస్యం"
        )

    elif (
        "yonaguni" in lower_title
        or "monument" in lower_title
    ):
        final_title = (
            f"{title} | ఇది సహజమైనదా లేక మనుషుల నిర్మాణమా?"
        )

    else:
        final_title = (
            f"{title} | నిజంగా అక్కడ ఏం జరిగింది?"
        )

    final_title = re.sub(
        r"\s+",
        " ",
        final_title
    )

    final_title = re.sub(
        r"\?+",
        "?",
        final_title
    )

    return final_title.strip()


# ============================================================
# DESCRIPTION
# ============================================================

def generate_description(
    topic_id,
    topic_title,
    script_text
):
    clean_script = clean_text(
        script_text
    )

    if len(clean_script) > 1200:
        preview = (
            clean_script[:1200]
            + "..."
        )
    else:
        preview = clean_script

    description = f"""
🔎 {topic_title}

ఈ వీడియోలో {topic_title}కి సంబంధించిన ఆసక్తికరమైన విషయాలు, శాస్త్రీయ ఆధారాలు మరియు ఇప్పటికీ సమాధానం లేని ప్రశ్నలను తెలుసుకుందాం.

ఈ విషయం ఎందుకు ఇంత ఆసక్తికరంగా మారింది?
శాస్త్రవేత్తలకు ఇప్పటివరకు ఏమి తెలుసు?
ఇంకా ఏ విషయాలు మిస్టరీగానే ఉన్నాయి?

ఈ వీడియోలో పూర్తి వివరాలను సులభంగా తెలుగులో తెలుసుకోండి.

━━━━━━━━━━━━━━━━━━━━

📌 వీడియోలో:

• {topic_title}
• ముఖ్యమైన శాస్త్రీయ విషయాలు
• పరిశోధనల్లో బయటపడిన ఆధారాలు
• ఇప్పటికీ సమాధానం లేని ప్రశ్నలు
• ఈ మిస్టరీ వెనుక ఉన్న ఆసక్తికరమైన నిజాలు

━━━━━━━━━━━━━━━━━━━━

🎬 Topic ID: {topic_id}

📚 Source / Research:

ఈ వీడియోలోని సమాచారం అందుబాటులో ఉన్న పరిశోధనలు మరియు విశ్వసనీయమైన సమాచారాన్ని ఆధారంగా చేసుకుని రూపొందించబడింది.

⚠️ గమనిక:

ఈ వీడియో విద్యా మరియు సమాచార ప్రయోజనాల కోసం రూపొందించబడింది. కొన్ని అంశాలు ప్రస్తుతం పరిశోధనలో ఉండవచ్చు.

━━━━━━━━━━━━━━━━━━━━

🔔 ఇలాంటి Mystery, Science, History మరియు Unknown Facts వీడియోల కోసం Subscribe చేయండి.

👍 వీడియో నచ్చితే Like చేయండి.
💬 మీ అభిప్రాయాన్ని Comment చేయండి.

#Mystery
#TeluguMystery
#TeluguFacts
#Science
#MysteryFacts

━━━━━━━━━━━━━━━━━━━━

SCRIPT PREVIEW:

{preview}
""".strip()

    return description


# ============================================================
# TAG GENERATION
# ============================================================

def generate_tags(
    topic_title,
    script_text
):
    text = (
        f"{topic_title} "
        f"{script_text}"
    ).lower()

    tags = []

    universal_tags = [
        "telugu mystery",
        "mystery telugu",
        "telugu mysteries",
        "mystery facts",
        "telugu facts",
        "unknown facts",
        "interesting facts",
        "science facts telugu",
        "telugu science",
        "mystery facts telugu",
        "unknown mysteries",
        "unexplained mysteries",
        "telugu youtube",
    ]

    tags.extend(
        universal_tags
    )

    title_words = re.findall(
        r"[A-Za-z0-9]+",
        topic_title
    )

    for word in title_words:

        if len(word) < 3:
            continue

        tags.append(
            word.lower()
        )

        tags.append(
            f"{word.lower()} mystery"
        )

        tags.append(
            f"{word.lower()} facts"
        )

    # --------------------------------------------------------
    # YONAGUNI
    # --------------------------------------------------------

    if (
        "yonaguni" in text
        or "underwater monument" in text
        or "monument" in text
    ):
        tags.extend([
            "yonaguni monument",
            "yonaguni monument mystery",
            "yonaguni mystery",
            "yonaguni underwater monument",
            "yonaguni underwater mystery",
            "yonaguni japan",
            "underwater monument",
            "underwater ruins",
            "underwater mystery",
            "japan mystery",
            "ancient underwater mystery",
            "yonaguni facts",
            "yonaguni telugu",
        ])

    # --------------------------------------------------------
    # ANTARCTICA
    # --------------------------------------------------------

    if (
        "antarctica" in text
        or "antarctic" in text
    ):
        tags.extend([
            "antarctica",
            "antarctica mystery",
            "antarctica facts",
            "antarctica telugu",
            "antarctic mystery",
            "antarctic facts",
            "antarctica science",
            "antarctica secrets",
            "antarctica ice",
            "antarctica glacier",
        ])

    # --------------------------------------------------------
    # KOLA
    # --------------------------------------------------------

    if (
        "borehole" in text
        or "kola" in text
    ):
        tags.extend([
            "kola superdeep borehole",
            "kola borehole",
            "deepest hole on earth",
            "deepest hole mystery",
            "kola superdeep",
            "kola borehole mystery",
        ])

    # --------------------------------------------------------
    # MARIANA
    # --------------------------------------------------------

    if (
        "mariana" in text
        or "trench" in text
    ):
        tags.extend([
            "mariana trench",
            "mariana trench mystery",
            "mariana trench facts",
            "deepest ocean",
            "deepest place on earth",
            "ocean mystery",
        ])

    # --------------------------------------------------------
    # DEATH VALLEY
    # --------------------------------------------------------

    if (
        "death valley" in text
        or "moving rocks" in text
    ):
        tags.extend([
            "death valley",
            "death valley mystery",
            "moving rocks",
            "sailing stones",
            "death valley moving rocks",
            "moving rocks mystery",
        ])

    # --------------------------------------------------------
    # SCIENCE
    # --------------------------------------------------------

    if any(
        word in text
        for word in [
            "science",
            "scientist",
            "research",
            "experiment",
            "laboratory",
            "geology",
            "geological",
        ]
    ):
        tags.extend([
            "science",
            "science facts",
            "scientists",
            "scientific mystery",
            "science mystery",
            "scientific facts",
            "research",
            "geology",
            "geology facts",
        ])

    # --------------------------------------------------------
    # UNIQUE + CLEAN
    # --------------------------------------------------------

    final_tags = []
    seen = set()

    for tag in tags:

        tag = re.sub(
            r"\s+",
            " ",
            tag
        ).strip()

        if not tag:
            continue

        key = tag.lower()

        if key in seen:
            continue

        seen.add(key)

        final_tags.append(
            tag
        )

    return final_tags[:45]


# ============================================================
# HASHTAGS
# ============================================================

def generate_hashtags(
    topic_title,
    script_text
):
    text = (
        f"{topic_title} "
        f"{script_text}"
    ).lower()

    hashtags = [
        "#TeluguMystery",
        "#MysteryFacts",
        "#TeluguFacts",
        "#TeluguScience",
        "#Mystery",
    ]

    if (
        "yonaguni" in text
        or "monument" in text
    ):
        hashtags.extend([
            "#YonaguniMonument",
            "#YonaguniMystery",
            "#UnderwaterMystery",
        ])

    if "antarctica" in text:
        hashtags.extend([
            "#Antarctica",
            "#AntarcticaMystery",
            "#AntarcticaFacts",
        ])

    if (
        "mariana" in text
        or "trench" in text
    ):
        hashtags.extend([
            "#MarianaTrench",
            "#OceanMystery",
        ])

    if (
        "borehole" in text
        or "kola" in text
    ):
        hashtags.extend([
            "#KolaSuperdeep",
            "#DeepestHole",
        ])

    if (
        "death valley" in text
        or "moving rocks" in text
    ):
        hashtags.extend([
            "#DeathValley",
            "#MovingRocks",
        ])

    return list(
        dict.fromkeys(
            hashtags
        )
    )


# ============================================================
# SAVE METADATA
#
# IMPORTANT:
# build_pipeline.py calls:
#
# save_metadata(
#     topic_id,
#     title,
#     script_text,
#     metadata_path
# )
#
# So this function MUST accept exactly those arguments.
# ============================================================

def save_metadata(
    topic_id,
    topic_title,
    script_text,
    metadata_path
):
    script_text = clean_text(
        script_text
    )

    final_title = generate_title(
        topic_title,
        script_text
    )

    description = generate_description(
        topic_id,
        topic_title,
        script_text
    )

    tags = generate_tags(
        topic_title,
        script_text
    )

    hashtags = generate_hashtags(
        topic_title,
        script_text
    )

    metadata_file = Path(
        metadata_path
    )

    metadata_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    content = (
        "TITLE:\n"
        f"{final_title}\n\n"
        "DESCRIPTION:\n"
        f"{description}\n\n"
        "TAGS:\n"
        f"{', '.join(tags)}\n\n"
        "HASHTAGS:\n"
        f"{' '.join(hashtags)}"
    )

    metadata_file.write_text(
        content,
        encoding="utf-8"
    )

    print("=" * 70)
    print("YOUTUBE METADATA CREATED")
    print("=" * 70)

    print(
        f"FILE: {metadata_file}"
    )

    print()

    print(
        f"TITLE: {final_title}"
    )

    print()

    print(
        f"TAGS: {len(tags)}"
    )

    print(
        ", ".join(tags)
    )

    print()

    print(
        "HASHTAGS:"
    )

    print(
        " ".join(hashtags)
    )

    print("=" * 70)

    return metadata_file


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":

    print(
        "youtube_metadata.py is designed "
        "to be called from build_pipeline.py"
    )
