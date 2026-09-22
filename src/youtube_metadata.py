import re
from pathlib import Path


SCRIPTS_DIR = Path("scripts")
METADATA_DIR = Path("metadata")


FORBIDDEN_PATTERNS = [
    r"\blatitude\b",
    r"\blongitude\b",
    r"\bcoordinates?\b",
    r"\bGPS\b",
    r"\b\d+(?:\.\d+)?\s*°\s*[NSWE]\b",
    r"\b\d+(?:\.\d+)?\s*degrees?\s*[NSWE]\b",
]


def contains_forbidden_coordinates(text):

    if not text:
        return False

    if "°" in text:
        return True

    for pattern in FORBIDDEN_PATTERNS:

        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        ):
            return True

    return False


def sanitize_text(text):

    if not text:
        return ""

    text = re.sub(
        r"\b\d+(?:\.\d+)?\s*°\s*[NSWE]\b",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\b\d+(?:\.\d+)?\s*degrees?\s*[NSWE]\b",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\b(?:latitude|longitude|coordinates?|GPS)\b",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = text.replace(
        "°",
        ""
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


def read_script(topic_id):

    path = (
        SCRIPTS_DIR
        / f"{topic_id}.txt"
    )

    if not path.exists():
        return ""

    return path.read_text(
        encoding="utf-8"
    ).strip()


def clean_title(topic_title):

    title = sanitize_text(
        topic_title
    )

    title = re.sub(
        r"\s+",
        " ",
        title
    ).strip()

    return title


def generate_title(
    topic_title,
    script_text
):

    title = clean_title(
        topic_title
    )

    if not title:
        title = "తెలియని రహస్యం"

    return title[:100]


def generate_description(
    topic_id,
    topic_title,
    script_text
):

    title = clean_title(
        topic_title
    )

    description = (
        f"{title} గురించి ఈ వీడియోలో "
        "తెలిసిన విషయాలు, శాస్త్రీయ వివరణలు, "
        "మరియు ఇంకా సమాధానం లేని ప్రశ్నలను "
        "సహజంగా తెలుసుకుందాం."
        "\n\n"
        "ఈ వీడియోలో చెప్పే సమాచారం అందుబాటులో ఉన్న "
        "పరిశోధనలు మరియు విశ్వసనీయమైన సమాచారంపై "
        "ఆధారపడి ఉంటుంది."
    )

    description = sanitize_text(
        description
    )

    return description


def extract_hashtag_words(
    topic_title
):

    words = re.findall(
        r"[A-Za-z0-9]+",
        topic_title
    )

    result = []

    for word in words:

        if len(word) < 3:
            continue

        if word.lower() in {
            "the",
            "and",
            "for",
            "with",
            "under",
            "mystery",
        }:
            continue

        clean = re.sub(
            r"[^A-Za-z0-9]",
            "",
            word
        )

        if clean:
            result.append(
                clean
            )

    return result[:4]


def generate_hashtags(
    topic_title,
    script_text
):

    hashtags = [
        "#TeluguMystery",
        "#Mystery",
        "#Science",
        "#Unexplained",
    ]

    topic_words = extract_hashtag_words(
        topic_title
    )

    for word in topic_words:

        tag = "#" + word

        if tag.lower() not in [
            item.lower()
            for item in hashtags
        ]:

            hashtags.append(
                tag
            )

    return " ".join(
        hashtags
    )


def generate_tags(
    topic_title,
    script_text
):

    tags = [
        "Telugu mystery",
        "mystery Telugu",
        "Telugu science",
        "unexplained mysteries",
        "mystery facts",
        "science facts",
        "unknown facts",
    ]

    topic_words = extract_hashtag_words(
        topic_title
    )

    for word in topic_words:

        tags.append(
            word
        )

        tags.append(
            f"{word} mystery"
        )

    unique = []

    for tag in tags:

        if tag.lower() not in [
            item.lower()
            for item in unique
        ]:

            unique.append(
                tag
            )

    return unique


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

    title = sanitize_text(
        title
    )

    description = sanitize_text(
        description
    )

    hashtags = sanitize_text(
        hashtags
    )

    if "#TeluguMystery" not in hashtags:
        hashtags = (
            "#TeluguMystery "
            + hashtags
        ).strip()

    if "#Mystery" not in hashtags:
        hashtags += " #Mystery"

    if "#Science" not in hashtags:
        hashtags += " #Science"

    if "#Unexplained" not in hashtags:
        hashtags += " #Unexplained"

    if "#TeluguMystery" not in description:
        description += (
            "\n\n"
            + hashtags
        )

    if contains_forbidden_coordinates(
        title
    ):
        raise RuntimeError(
            "Forbidden coordinates found in title"
        )

    if contains_forbidden_coordinates(
        description
    ):
        raise RuntimeError(
            "Forbidden coordinates found in description"
        )

    if contains_forbidden_coordinates(
        hashtags
    ):
        raise RuntimeError(
            "Forbidden coordinates found in hashtags"
        )

    path = (
        METADATA_DIR
        / f"{topic_id}.txt"
    )

    with path.open(
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            f"TITLE: {title}\n"
        )

        file.write(
            "DESCRIPTION:\n"
        )

        file.write(
            description
        )

        file.write(
            "\n"
        )

        file.write(
            "TAGS: "
            + ", ".join(tags)
            + "\n"
        )

        file.write(
            f"HASHTAGS: {hashtags}\n"
        )

    return path


if __name__ == "__main__":
    print(
        "youtube_metadata.py is a library module."
    )
