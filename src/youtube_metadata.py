import csv
import re
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

TOPICS_FILE = "topics/topics.csv"
SCRIPTS_DIR = Path("scripts")
METADATA_DIR = Path("metadata")


# ============================================================
# GET READY TOPIC
# ============================================================

def get_ready_topic():

    if not Path(TOPICS_FILE).exists():
        raise Exception(
            f"Topics file not found: {TOPICS_FILE}"
        )

    with open(
        TOPICS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        topics = list(
            csv.DictReader(file)
        )

    for topic in topics:

        topic_id = topic["id"].strip()

        script_file = (
            SCRIPTS_DIR
            / f"{topic_id}.txt"
        )

        audio_file = Path(
            "audio"
        ) / f"{topic_id}.mp3"

        video_file = Path(
            "videos"
        ) / f"{topic_id}.mp4"

        if (
            script_file.exists()
            and audio_file.exists()
            and video_file.exists()
        ):

            return topic

    return None


# ============================================================
# READ SCRIPT
# ============================================================

def read_script(topic_id):

    script_file = (
        SCRIPTS_DIR
        / f"{topic_id}.txt"
    )

    if not script_file.exists():

        raise Exception(
            f"Script not found: {script_file}"
        )

    return script_file.read_text(
        encoding="utf-8"
    ).strip()


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

    # --------------------------------------------------------
    # SPECIAL TITLE STYLES
    # --------------------------------------------------------

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

    else:

        final_title = (
            f"{title} | నిజంగా అక్కడ ఏం జరిగింది?"
        )

    # --------------------------------------------------------
    # REMOVE DUPLICATE PUNCTUATION
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # SCRIPT PREVIEW
    # --------------------------------------------------------

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

SCRIPT SUMMARY:

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

    # --------------------------------------------------------
    # UNIVERSAL TAGS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # TOPIC TITLE WORDS
    # --------------------------------------------------------

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
    # TOPIC SPECIFIC
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

    if (
        "glacier" in text
        or "ice" in text
    ):

        tags.extend([
            "glacier",
            "ice mystery",
            "ice facts",
            "glacier mystery",
            "climate science",
            "ice sheet",
            "iceberg",
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
        ])

    # --------------------------------------------------------
    # CLEAN + UNIQUE
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

    # YouTube API tag field should remain reasonably sized.
    final_tags = final_tags[:45]

    return final_tags


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
# ============================================================

def save_metadata(
    topic_id,
    title,
    description,
    tags,
    hashtags
):

    METADATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    metadata_file = (
        METADATA_DIR
        / f"{topic_id}.txt"
    )

    content = f"""
TITLE:
{title}

DESCRIPTION:
{description}

TAGS:
{", ".join(tags)}

HASHTAGS:
{" ".join(hashtags)}
""".strip()

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
        f"TITLE: {title}"
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
# MAIN
# ============================================================

def main():

    topic = get_ready_topic()

    if not topic:

        print(
            "NO TOPIC READY FOR YOUTUBE METADATA"
        )

        return

    topic_id = topic[
        "id"
    ].strip()

    topic_title = topic[
        "title"
    ].strip()

    print("=" * 70)
    print("GENERATING YOUTUBE METADATA")
    print("=" * 70)

    print(
        f"TOPIC ID: {topic_id}"
    )

    print(
        f"TOPIC: {topic_title}"
    )

    script_text = read_script(
        topic_id
    )

    title = generate_title(
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

    save_metadata(
        topic_id,
        title,
        description,
        tags,
        hashtags
    )

    print()
    print(
        "YOUTUBE METADATA GENERATION COMPLETE"
    )


if __name__ == "__main__":
    main()
