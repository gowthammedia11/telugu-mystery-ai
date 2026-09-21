import asyncio
import csv
import re
import subprocess
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

MIN_LONG_SECONDS = 420.0
MAX_LONG_SECONDS = 480.0
TARGET_LONG_SECONDS = 450.0

MAX_DURATION_ATTEMPTS = 4


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


def get_audio_duration(audio_file):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_file),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    value = result.stdout.strip()

    if not value:
        raise RuntimeError(
            f"Unable to read audio duration: {audio_file}"
        )

    return float(value)


def split_script_sentences(text):
    text = text.replace("\r", " ")
    text = text.replace("\n", " ")

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    if not text:
        return []

    sentences = re.split(
        r"(?<=[.!?।])\s+",
        text
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


def shorten_script_for_duration(
    script,
    current_duration
):
    if current_duration <= MAX_LONG_SECONDS:
        return script

    ratio = (
        MAX_LONG_SECONDS
        / current_duration
    )

    target_characters = int(
        len(script) * ratio * 0.98
    )

    target_characters = max(
        MIN_SCRIPT_CHARACTERS,
        target_characters
    )

    sentences = split_script_sentences(
        script
    )

    if not sentences:
        return script

    selected = []
    current_length = 0

    for sentence in sentences:

        sentence_length = len(sentence)

        if (
            current_length + sentence_length + 1
            > target_characters
        ):
            break

        selected.append(sentence)

        current_length += (
            sentence_length + 1
        )

    if len(selected) < 3:
        return script

    shortened = " ".join(
        selected
    ).strip()

    if (
        len(shortened)
        < MIN_SCRIPT_CHARACTERS
    ):
        return script

    print(
        f"SHORTENING SCRIPT: "
        f"{len(script)} -> "
        f"{len(shortened)} characters"
    )

    return shortened


def validate_and_prepare_script(
    topic_id,
    topic_title,
    research
):
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

    if (
        script_length
        < MIN_SCRIPT_CHARACTERS
    ):
        raise RuntimeError(
            f"Generated script is too short. "
            f"Got {script_length} characters. "
            f"Minimum required: "
            f"{MIN_SCRIPT_CHARACTERS}"
        )

    if (
        script_length
        < TARGET_SCRIPT_CHARACTERS
    ):
        print(
            f"WARNING: Script is below preferred "
            f"{TARGET_SCRIPT_CHARACTERS} characters."
        )

    return script


def generate_and_validate_long_voice(
    topic_id,
    topic_title,
    script
):
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

    duration = get_audio_duration(
        long_audio
    )

    print(
        f"LONG AUDIO DURATION: "
        f"{duration:.2f}s "
        f"({duration / 60:.2f} minutes)"
    )

    return (
        script_file,
        long_audio,
        duration
    )


def build_long_script_and_voice(
    topic_id,
    topic_title,
    research
):
    print("=" * 70)
    print("CREATING LONG SCRIPT + VOICE")
    print("=" * 70)

    script = validate_and_prepare_script(
        topic_id,
        topic_title,
        research
    )

    for attempt in range(
        1,
        MAX_DURATION_ATTEMPTS + 1
    ):

        print("=" * 70)
        print(
            f"LONG DURATION CHECK "
            f"ATTEMPT {attempt}/{MAX_DURATION_ATTEMPTS}"
        )
        print("=" * 70)

        script_file, long_audio, duration = (
            generate_and_validate_long_voice(
                topic_id,
                topic_title,
                script
            )
        )

        if (
            MIN_LONG_SECONDS
            <= duration
            <= MAX_LONG_SECONDS
        ):

            print("=" * 70)
            print("LONG AUDIO DURATION VALID")
            print(
                f"DURATION: "
                f"{duration:.2f}s"
            )
            print(
                f"MINIMUM: "
                f"{MIN_LONG_SECONDS:.2f}s"
            )
            print(
                f"MAXIMUM: "
                f"{MAX_LONG_SECONDS:.2f}s"
            )
            print("=" * 70)

            return (
                script,
                script_file,
                long_audio,
                duration
            )

        if duration > MAX_LONG_SECONDS:

            print(
                f"LONG AUDIO TOO LONG: "
                f"{duration:.2f}s"
            )

            if attempt >= MAX_DURATION_ATTEMPTS:
                raise RuntimeError(
                    f"Unable to reduce long audio "
                    f"to 8 minutes after "
                    f"{MAX_DURATION_ATTEMPTS} attempts. "
                    f"Final duration: "
                    f"{duration:.2f}s"
                )

            new_script = (
                shorten_script_for_duration(
                    script,
                    duration
                )
            )

            if new_script == script:
                print(
                    "LOCAL SHORTENING WAS NOT ENOUGH."
                )
                print(
                    "GENERATING A NEW SCRIPT."
                )

                script = validate_and_prepare_script(
                    topic_id,
                    topic_title,
                    research
                )
            else:
                script = new_script

            continue

        if duration < MIN_LONG_SECONDS:

            print(
                f"LONG AUDIO TOO SHORT: "
                f"{duration:.2f}s"
            )

            if attempt >= MAX_DURATION_ATTEMPTS:
                raise RuntimeError(
                    f"Unable to reach 7 minutes "
                    f"after {MAX_DURATION_ATTEMPTS} "
                    f"attempts. "
                    f"Final duration: "
                    f"{duration:.2f}s"
                )

            print(
                "GENERATING A NEW LONG SCRIPT "
                "TO REACH THE REQUIRED DURATION."
            )

            script = validate_and_prepare_script(
                topic_id,
                topic_title,
                research
            )

    raise RuntimeError(
        "Long script/audio duration validation failed"
    )


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
    # LONG SCRIPT + VOICE
    # ========================================================

    (
        script,
        script_file,
        long_audio,
        long_audio_duration
    ) = build_long_script_and_voice(
        topic_id,
        topic_title,
        research
    )

    save_topic_status(
        load_topics(),
        topic_id,
        "script_ready"
    )

    print(
        f"SCRIPT SAVED: {script_file}"
    )

    print(
        f"LONG AUDIO READY: {long_audio}"
    )

    print(
        f"LONG AUDIO FINAL DURATION: "
        f"{long_audio_duration:.2f}s"
    )

    # ========================================================
    # LONG VIDEO
    # ========================================================

    print("=" * 70)
    print("STARTING LONG VIDEO")
    print("=" * 70)

    run_video(
        topic_id
    )

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

    print("=" * 70)
    print("STARTING LONG YOUTUBE METADATA")
    print("=" * 70)

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

    long_metadata = Path(
        f"metadata/{topic_id}.txt"
    )

    if not long_metadata.exists():
        raise RuntimeError(
            f"Long metadata was not created: "
            f"{long_metadata}"
        )

    if long_metadata.stat().st_size <= 0:
        raise RuntimeError(
            f"Long metadata is empty: "
            f"{long_metadata}"
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
                f"Required Short file missing: "
                f"{file}"
            )

        if file.stat().st_size <= 0:
            raise RuntimeError(
                f"Required Short file is empty: "
                f"{file}"
            )

    print("=" * 70)
    print("DAILY BUILD COMPLETE")
    print("=" * 70)
    print(f"TOPIC: {topic_id}")
    print(f"LONG VIDEO: {long_video}")
    print(f"SHORT VIDEO: {short_video}")
    print(f"LONG AUDIO: {long_audio}")
    print(f"LONG AUDIO DURATION: {long_audio_duration:.2f}s")
    print(f"LONG METADATA: {long_metadata}")
    print(f"SHORT METADATA: {short_metadata}")
    print("READY FOR AUTOMATIC YOUTUBE UPLOAD")
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
