import asyncio
import csv
from pathlib import Path

from research import research_topic, save_research
from script import (
    generate_script,
    clean_script,
    apply_final_script_rules,
    save_script,
)
from topic_manager import save_topics
from voice import generate_voice
from video import run as run_video
from youtube_metadata import (
    read_script,
    generate_title,
    generate_description,
    generate_tags,
    generate_hashtags,
    save_metadata,
)


TOPICS_FILE = Path("topics/topics.csv")
RESEARCH_DIR = Path("research")
SCRIPTS_DIR = Path("scripts")

# ============================================================
# VIDEO / SCRIPT LENGTH TARGET
# ============================================================

MIN_SCRIPT_CHARACTERS = 4500
TARGET_SCRIPT_CHARACTERS = 5500


def load_topics():
    with TOPICS_FILE.open(
        "r",
        encoding="utf-8",
        newline=""
    ) as file:
        return list(csv.DictReader(file))


def save_topic_status(
    topics,
    topic_id,
    status
):
    for topic in topics:
        if topic.get("id", "").strip() == topic_id:
            topic["status"] = status
            break

    save_topics(topics)


def get_current_topic(topics):
    """
    Always process the lowest-numbered topic
    that is not completed.

    Guarantees strict:
    001 -> 002 -> 003 -> 004 ...
    """

    candidates = [
        topic
        for topic in topics
        if topic.get(
            "status",
            ""
        ).strip().lower() != "completed"
    ]

    if not candidates:
        return None

    candidates.sort(
        key=lambda topic: int(
            topic["id"].strip()
        )
    )

    return candidates[0]


def build_topic(topic):

    topic_id = topic[
        "id"
    ].strip()

    topic_title = topic[
        "title"
    ].strip()

    print("=" * 70)
    print("TELUGU MYSTERY AI — DAILY BUILD")
    print("=" * 70)
    print(
        f"TOPIC: {topic_id}"
    )
    print(
        f"TITLE: {topic_title}"
    )
    print("=" * 70)

    topics = load_topics()

    save_topic_status(
        topics,
        topic_id,
        "processing"
    )

    # ========================================================
    # RESEARCH
    # ========================================================

    research_file = (
        RESEARCH_DIR
        / f"{topic_id}.txt"
    )

    if (
        not research_file.exists()
        or research_file.stat().st_size < 500
    ):

        print(
            "STARTING RESEARCH"
        )

        research = research_topic(
            topic_id,
            topic_title
        )

        research_file = save_research(
            topic_id,
            topic_title,
            research
        )

        save_topic_status(
            load_topics(),
            topic_id,
            "researched"
        )

    else:

        print(
            f"RESEARCH ALREADY EXISTS: "
            f"{research_file}"
        )

    research = research_file.read_text(
        encoding="utf-8"
    ).strip()

    if not research:
        raise RuntimeError(
            "Research file is empty"
        )

    print(
        f"RESEARCH CHARACTERS: "
        f"{len(research)}"
    )

    # ========================================================
    # SCRIPT
    # ========================================================

    print(
        "STARTING SCRIPT"
    )

    script = generate_script(
        topic_id,
        topic_title,
        research
    )

    if script is None:
        raise RuntimeError(
            "Script generation returned None"
        )

    script = clean_script(
        script
    )

    if script is None:
        raise RuntimeError(
            "Script cleaning returned None"
        )

    script = apply_final_script_rules(
        script
    )

    if script is None:
        raise RuntimeError(
            "Final script processing returned None"
        )

    script_length = len(
        script
    )

    print(
        f"GENERATED SCRIPT CHARACTERS: "
        f"{script_length}"
    )

    # ========================================================
    # MINIMUM SCRIPT LENGTH
    # ========================================================

    if script_length < MIN_SCRIPT_CHARACTERS:

        raise RuntimeError(
            f"Generated script is too short. "
            f"Got {script_length} characters. "
            f"Minimum required: "
            f"{MIN_SCRIPT_CHARACTERS} characters "
            f"for a 7-8 minute target video."
        )

    if script_length < TARGET_SCRIPT_CHARACTERS:

        print(
            f"WARNING: Script is below the preferred "
            f"{TARGET_SCRIPT_CHARACTERS} characters."
        )

    # ========================================================
    # SAVE SCRIPT
    # ========================================================

    script_file = save_script(
        topic_id,
        script
    )

    if not script_file.exists():
        raise RuntimeError(
            "Script file was not created"
        )

    if script_file.stat().st_size <= 0:
        raise RuntimeError(
            "Script file is empty"
        )

    save_topic_status(
        load_topics(),
        topic_id,
        "script_ready"
    )

    print(
        f"SCRIPT SAVED: {script_file}"
    )

    # ========================================================
    # VOICE
    # ========================================================

    print(
        "STARTING VOICE"
    )

    asyncio.run(
        generate_voice(
            {
                "id": topic_id,
                "title": topic_title,
            }
        )
    )

    # ========================================================
    # VIDEO
    # ========================================================

    print(
        "STARTING VIDEO"
    )

    run_video(
        topic_id
    )

    # ========================================================
    # YOUTUBE METADATA
    # ========================================================

    print(
        "STARTING YOUTUBE METADATA"
    )

    script_text = read_script(
        topic_id
    )

    if not script_text:
        raise RuntimeError(
            "Unable to read generated script"
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

    print("=" * 70)
    print(
        "DAILY BUILD COMPLETE"
    )
    print(
        f"TOPIC: {topic_id}"
    )
    print(
        f"TITLE: {title}"
    )
    print(
        "VIDEO READY FOR AUTOMATIC YOUTUBE POSTING"
    )
    print("=" * 70)


def main():

    topics = load_topics()

    topic = get_current_topic(
        topics
    )

    if not topic:

        print(
            "NO TOPICS AVAILABLE"
        )

        return

    build_topic(
        topic
    )


if __name__ == "__main__":
    main()
