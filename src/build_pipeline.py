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
from shorts import create_short
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

    topic_id = topic["id"].strip()
    topic_title = topic["title"].strip()

    print("=" * 70)
    print("TELUGU MYSTERY AI — DAILY BUILD")
    print("=" * 70)
    print(f"TOPIC: {topic_id}")
    print(f"TITLE: {topic_title}")
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

        print("STARTING RESEARCH")

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
    # LONG SCRIPT
    # ========================================================

    print("STARTING LONG SCRIPT")

    script = generate_script(
        topic_id,
        topic_title,
        research
    )

    if script is None:
        raise RuntimeError(
            "Script generation returned None"
        )

    script = clean_script(script)

    if script is None:
        raise RuntimeError(
            "Script cleaning returned None"
        )

    script = apply_final_script_rules(script)

    if script is None:
        raise RuntimeError(
            "Final script processing returned None"
        )

    script_length = len(script)

    print(
        f"GENERATED SCRIPT CHARACTERS: "
        f"{script_length}"
    )

    if script_length < MIN_SCRIPT_CHARACTERS:
        raise RuntimeError(
            f"Generated script is too short. "
            f"Got {script_length} characters. "
            f"Minimum required: "
            f"{MIN_SCRIPT_CHARACTERS}"
        )

    if script_length < TARGET_SCRIPT_CHARACTERS:
        print(
            f"WARNING: Script is below preferred "
            f"{TARGET_SCRIPT_CHARACTERS} characters."
        )

    # ========================================================
    # SAVE LONG SCRIPT
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
    # LONG VOICE
    # ========================================================

    print("STARTING LONG VOICE")

    asyncio.run(
        generate_voice(
            {
                "id": topic_id,
                "title": topic_title,
            }
        )
    )

    long_audio = Path(
        f"audio/{topic_id}.mp3"
    )

    if not long_audio.exists():
        raise RuntimeError(
            f"Long audio was not created: {long_audio}"
        )

    if long_audio.stat().st_size <= 0:
        raise RuntimeError(
            f"Long audio is empty: {long_audio}"
        )

    # ========================================================
    # LONG VIDEO
    # ========================================================

    print("STARTING LONG VIDEO")

    run_video(topic_id)

    long_video = Path(
        f"videos/{topic_id}.mp4"
    )

    if not long_video.exists():
        raise RuntimeError(
            f"Long video was not created: {long_video}"
        )

    if long_video.stat().st_size <= 0:
        raise RuntimeError(
            f"Long video is empty: {long_video}"
        )

    # ========================================================
    # LONG YOUTUBE METADATA
    # ========================================================

    print("STARTING LONG YOUTUBE METADATA")

    script_text = read_script(topic_id)

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

    long_metadata = Path(
        f"metadata/{topic_id}.txt"
    )

    if not long_metadata.exists():
        raise RuntimeError(
            f"Long metadata was not created: {long_metadata}"
        )

    # ========================================================
    # SHORT
    # ========================================================

    print("=" * 70)
    print("STARTING YOUTUBE SHORT")
    print("=" * 70)

    short_result = create_short(
        topic_id=topic_id,
        topic_title=topic_title,
        long_script=script,
        long_video=long_video,
    )

    if not short_result:
        raise RuntimeError(
            "Short creation failed"
        )

    short_video = Path(
        f"videos/{topic_id}_short.mp4"
    )

    short_audio = Path(
        f"audio/{topic_id}_short.mp3"
    )

    short_script = Path(
        f"scripts/{topic_id}_short.txt"
    )

    short_metadata = Path(
        f"metadata/{topic_id}_short.txt"
    )

    required_short_files = [
        short_video,
        short_audio,
        short_script,
        short_metadata,
    ]

    for file in required_short_files:
        if not file.exists():
            raise RuntimeError(
                f"Required Short file missing: {file}"
            )

        if file.stat().st_size <= 0:
            raise RuntimeError(
                f"Required Short file is empty: {file}"
            )

    print("=" * 70)
    print("DAILY BUILD COMPLETE")
    print("=" * 70)
    print(f"TOPIC: {topic_id}")
    print(f"LONG VIDEO: {long_video}")
    print(f"SHORT VIDEO: {short_video}")
    print(f"LONG METADATA: {long_metadata}")
    print(f"SHORT METADATA: {short_metadata}")
    print("READY FOR AUTOMATIC YOUTUBE UPLOAD")
    print("=" * 70)


def main():

    topics = load_topics()

    topic = get_current_topic(topics)

    if not topic:

        print(
            "NO TOPICS AVAILABLE"
        )

        return

    build_topic(topic)


if __name__ == "__main__":
    main()
