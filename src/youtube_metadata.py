import csv
import os
import re
from pathlib import Path


TOPICS_FILE = Path("topics/topics.csv")
SCRIPTS_DIR = Path("scripts")
METADATA_DIR = Path("metadata")


def get_topic_by_id(topic_id):

    with TOPICS_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        topics = list(csv.DictReader(file))

    for topic in topics:

        if topic["id"].strip() == topic_id:
            return topic

    raise RuntimeError(
        f"Topic not found: {topic_id}"
    )


def read_script(topic_id):

    file = (
        SCRIPTS_DIR /
        f"{topic_id}.txt"
    )

    if not file.exists():
        raise RuntimeError(
            f"Script not found: {file}"
        )

    return file.read_text(
        encoding="utf-8"
    ).strip()


def clean_text(text):

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def generate_title(topic_title):

    title = topic_title.strip()

    lower = title.lower()

    if (
        "mystery" in lower
        or "mysteries" in lower
    ):
        final_title = (
            f"{title} | అసలు రహస్యం ఏమిటి?"
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

    return final_title.strip()


def generate_description(
    topic_id,
    topic_title,
    script_text
):

    clean_script = clean_text(
        script_text
    )

    preview = (
        clean_script[:1200] + "..."
        if len(clean_script) > 1200
        else clean_script
    )

    return f"""
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
ఈ వీడియోలోని సమాచారం పరిశోధనలు మరియు విశ్వసనీయమైన సమాచారాన్ని ఆధారంగా చేసుకుని రూపొందించబడింది.

⚠️ గమనిక:
కొన్ని అంశాలు ప్రస్తుతం పరిశోధనలో ఉండవచ్చు.

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


def generate_tags(
    topic_title,
    script_text
):

    text = (
        f"{topic_title} "
        f"{script_text}"
    ).lower()

    tags = [
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

    special_groups = {
        "mariana": [
            "mariana trench",
            "mariana trench mystery",
            "deepest ocean",
            "deep sea",
            "ocean mystery",
        ],
        "bermuda": [
            "bermuda triangle",
            "bermuda triangle mystery",
            "atlantic ocean mystery",
            "ship mystery",
            "aircraft mystery",
        ],
        "baltic": [
            "baltic sea",
            "baltic sea anomaly",
            "underwater anomaly",
            "underwater mystery",
        ],
        "antarctica": [
            "antarctica",
            "antarctica mystery",
            "antarctica facts",
            "antarctic science",
        ],
    }

    for keyword, group in special_groups.items():

        if keyword in text:
            tags.extend(group)

    final_tags = []
    seen = set()

    for tag in tags:

        tag = re.sub(
            r"\s+",
            " ",
            tag
        ).strip()

        key = tag.lower()

        if not tag or key in seen:
            continue

        seen.add(key)
        final_tags.append(tag)

    return final_tags[:45]


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

    if "mariana" in text:
        hashtags.extend([
            "#MarianaTrench",
            "#OceanMystery",
        ])

    if "bermuda" in text:
        hashtags.extend([
            "#BermudaTriangle",
            "#BermudaMystery",
        ])

    if "baltic" in text:
        hashtags.extend([
            "#BalticSea",
            "#UnderwaterMystery",
        ])

    if "antarctica" in text:
        hashtags.extend([
            "#Antarctica",
            "#AntarcticaMystery",
        ])

    return list(
        dict.fromkeys(
            hashtags
        )
    )


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
        METADATA_DIR /
        f"{topic_id}.txt"
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

    return metadata_file


def run(topic_id):

    topic = get_topic_by_id(topic_id)

    topic_title = (
        topic["title"].strip()
    )

    script_text = read_script(
        topic_id
    )

    metadata_file = (
        METADATA_DIR /
        f"{topic_id}.txt"
    )

    # Regenerate metadata every successful pipeline run.
    title = generate_title(
        topic_title
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

    print(
        f"METADATA CREATED: {metadata_file}"
    )

    return metadata_file


if __name__ == "__main__":

    topic_id = os.environ.get(
        "PIPELINE_TOPIC_ID"
    )

    if not topic_id:
        raise SystemExit(
            "PIPELINE_TOPIC_ID is required"
        )

    run(topic_id)
