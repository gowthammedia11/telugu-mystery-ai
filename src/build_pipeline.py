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
        return list(
            csv.DictReader(file)
        )


def save_topic_status(
    topics,
    topic_id,
    status
):

    for topic in topics:

        if topic.get(
            "id",
            ""
        ).strip() == topic_id:

            topic["status"] = status
            break

    save_topics(
        topics
    )


def get_current_topic(
    topics
):

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


def build_topic(
    topic
):

    topic_id = topic[
        "id"
    ].strip()

    topic_title = topic[
        "title"
    ].strip()

    print("=" * 70)
    print("TELUGU MYSTERY AI - DAILY BUILD")
    print("=" * 70)
    print(
        f"TOPIC: {topic_id}"
    )
    print(
        f"TITLE: {topic_title}"
    )
    print("=" * 70)

    save_topic_status(
        load_topics(),
        topic_id,
        "processing"
    )

    research_file = (
        RESEARCH_DIR
        / f"{topic_id}.txt"
    )

    if not valid_file(
        research_file
    ) or research_file.stat().st_size < 500:

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

    research = research_file.read_text(
        encoding="utf-8"
    ).strip()

    if not research:
        raise RuntimeError(
            "Research file is empty"
        )

    script_file = (
        SCRIPTS_DIR
        / f"{topic_id}.txt"
    )

    if valid_file(
        script_file
    ):

        print(
            f"SCRIPT EXISTS: {script_file}"
        )

        script = script_file.read_text(
            encoding="utf-8"
        ).strip()

    else:

        print(
            "STARTING SCRIPT"
        )

        script = generate_script(
            topic_id,
            topic_title,
            research
        )

        script = clean_script(
            script
        )

        script = apply_final_script_rules(
            script
        )

        if not script:
            raise RuntimeError(
                "Final script is empty"
            )

        if len(script) < MIN_SCRIPT_CHARACTERS:
            raise RuntimeError(
                f"Script too short: {len(script)}"
            )

        if len(script) < TARGET_SCRIPT_CHARACTERS:
            print(
                "WARNING: Script below preferred length"
            )

        script_file = Path(
            save_script(
                topic_id,
                script
            )
        )

    save_topic_status(
        load_topics(),
        topic_id,
        "script_ready"
    )

    audio_file = (
        AUDIO_DIR
        / f"{topic_id}.mp3"
    )

    if valid_file(
        audio_file
    ):

        print(
            f"VOICE EXISTS: {audio_file}"
        )

    else:

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

    if not valid_file(
        audio_file
    ):
        raise RuntimeError(
            "Long audio was not created"
        )

    video_file = (
        VIDEOS_DIR
        / f"{topic_id}.mp4"
    )

    if valid_file(
        video_file
    ):

        print(
            f"LONG VIDEO EXISTS: {video_file}"
        )

    else:

        print(
            "STARTING LONG VIDEO"
        )

        run_video(
            topic_id
        )

    if not valid_file(
        video_file
    ):
        raise RuntimeError(
            "Long video was not created"
        )

    metadata_file = (
        METADATA_DIR
        / f"{topic_id}.txt"
    )

    print(
        "CREATING LONG METADATA"
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

    metadata_file = save_metadata(
        topic_id,
        title,
        description,
        tags,
        hashtags
    )

    if not valid_file(
        metadata_file
    ):
        raise RuntimeError(
            "Long metadata was not created"
        )

    print(
        "STARTING SHORT"
    )

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

    for path in [
        short_script,
        short_audio,
        short_video,
        short_metadata,
    ]:

        if not valid_file(
            path
        ):
            raise RuntimeError(
                f"Short output missing: {path}"
            )

    save_topic_status(
        load_topics(),
        topic_id,
        "videos_ready"
    )

    print("=" * 70)
    print("BOTH LONG AND SHORT READY")
    print(
        f"TOPIC: {topic_id}"
    )
    print(
        f"LONG: {video_file}"
    )
    print(
        f"SHORT: {short_video}"
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
