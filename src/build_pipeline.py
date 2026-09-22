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
from shorts import build_short
from topic_manager import save_topics


TOPICS_FILE = Path("topics/topics.csv")
RESEARCH_DIR = Path("research")
SCRIPTS_DIR = Path("scripts")
AUDIO_DIR = Path("audio")
VIDEOS_DIR = Path("videos")
METADATA_DIR = Path("metadata")

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


def valid_file(path):
    return (
        path.exists()
        and path.is_file()
        and path.stat().st_size > 0
    )


def build_topic(topic):

    topic_id = topic["id"].strip()
    topic_title = topic["title"].strip()

    print("=" * 70)
    print("TELUGU MYSTERY AI - DAILY BUILD")
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

    research_file = (
        RESEARCH_DIR
        / f"{topic_id}.txt"
    )

    if not valid_file(research_file) or research_file.stat().st_size < 500:

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
            f"RESEARCH ALREADY EXISTS: {research_file}"
        )

    research = research_file.read_text(
        encoding="utf-8"
    ).strip()

    if not research:
        raise RuntimeError(
            "Research file is empty"
        )

    print(
        f"RESEARCH CHARACTERS: {len(research)}"
    )

    script_file = (
        SCRIPTS_DIR
        / f"{topic_id}.txt"
    )

    if valid_file(script_file):

        script = script_file.read_text(
            encoding="utf-8"
        ).strip()

        print(
            f"SCRIPT ALREADY EXISTS: {script_file}"
        )

    else:

        print("STARTING SCRIPT")

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

        saved = save_script(
            topic_id,
            script
        )

        script_file = Path(saved)

        if not valid_file(script_file):
            raise RuntimeError(
                "Script file was not created"
            )

    save_topic_status(
        load_topics(),
        topic_id,
        "script_ready"
    )

    print(
        f"SCRIPT READY: {script_file}"
    )

    audio_file = (
        AUDIO_DIR
        / f"{topic_id}.mp3"
    )

    if valid_file(audio_file):

        print(
            f"VOICE ALREADY EXISTS: {audio_file}"
        )

    else:

        print("STARTING VOICE")

        asyncio.run(
            generate_voice(
                {
                    "id": topic_id,
                    "title": topic_title,
                }
            )
        )

    if not valid_file(audio_file):
        raise RuntimeError(
            f"Voice file was not created: {audio_file}"
        )

    video_file = (
        VIDEOS_DIR
        / f"{topic_id}.mp4"
    )

    if valid_file(video_file):

        print(
            f"LONG VIDEO ALREADY EXISTS: {video_file}"
        )

    else:

        print("STARTING LONG VIDEO")

        run_video(
            topic_id
        )

    if not valid_file(video_file):
        raise RuntimeError(
            f"Long video was not created: {video_file}"
        )

    metadata_file = (
        METADATA_DIR
        / f"{topic_id}.txt"
    )

    if valid_file(metadata_file):

        print(
            f"LONG METADATA ALREADY EXISTS: "
            f"{metadata_file}"
        )

    else:

        print("STARTING YOUTUBE METADATA")

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

    if not valid_file(metadata_file):
        raise RuntimeError(
            f"Long metadata was not created: "
            f"{metadata_file}"
        )

    save_topic_status(
        load_topics(),
        topic_id,
        "long_ready"
    )

    print("=" * 70)
    print("STARTING SHORT VIDEO")
    print("=" * 70)

    build_short(
        topic_id,
        topic_title
    )

    short_script = (
        SCRIPTS_DIR
        / f"{topic_id}_short.txt"
    )

    short_audio = (
        AUDIO_DIR
        / f"{topic_id}_short.mp3"
    )

    short_video = (
        VIDEOS_DIR
        / f"{topic_id}_short.mp4"
    )

    short_metadata = (
        METADATA_DIR
        / f"{topic_id}_short.txt"
    )

    required_short_files = [
        short_script,
        short_audio,
        short_video,
        short_metadata,
    ]

    for file_path in required_short_files:

        if not valid_file(file_path):
            raise RuntimeError(
                f"Short output missing: {file_path}"
            )

    save_topic_status(
        load_topics(),
        topic_id,
        "videos_ready"
    )

    print("=" * 70)
    print("DAILY BUILD COMPLETE")
    print("=" * 70)
    print(f"TOPIC: {topic_id}")
    print(f"LONG VIDEO: {video_file}")
    print(f"SHORT VIDEO: {short_video}")
    print(f"LONG METADATA: {metadata_file}")
    print(f"SHORT METADATA: {short_metadata}")
    print("BOTH VIDEOS READY FOR YOUTUBE UPLOAD")
    print("=" * 70)


def main():

    topics = load_topics()

    topic = get_current_topic(
        topics
    )

    if not topic:

        print(
            "NO TOPICS AVAILABLE - ALL TOPICS ARE COMPLETED"
        )

        return

    build_topic(
        topic
    )


if __name__ == "__main__":
    main()
