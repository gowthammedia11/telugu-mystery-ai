```python
import os
import sys

from topic_manager import load_topics, save_topics, get_next_topic
from research import research_topic
from script import generate_script, save_script
from voice import generate_voice
from video import create_video
from youtube_metadata import save_metadata
from shorts import build_short


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TOPICS_FILE = os.path.join(BASE_DIR, "topics", "topics.csv")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
VIDEOS_DIR = os.path.join(BASE_DIR, "videos")
METADATA_DIR = os.path.join(BASE_DIR, "metadata")


# ============================================================
# FORCE REBUILD
# ============================================================
# 005 must be rebuilt from scratch.
# After 005 is successfully completed, future topics will use
# the normal reuse/build logic.
FORCE_REBUILD_IDS = {"005"}


def file_path(directory, filename):
    return os.path.join(directory, filename)


def remove_old_topic_files(topic_id):
    """
    Remove all old generated files for a topic so that a fresh
    Long + Short video is generated.
    """

    files_to_remove = [
        file_path(SCRIPTS_DIR, f"{topic_id}.txt"),
        file_path(SCRIPTS_DIR, f"{topic_id}_short.txt"),

        file_path(AUDIO_DIR, f"{topic_id}.mp3"),
        file_path(AUDIO_DIR, f"{topic_id}_short.mp3"),

        file_path(VIDEOS_DIR, f"{topic_id}.mp4"),
        file_path(VIDEOS_DIR, f"{topic_id}_short.mp4"),

        file_path(METADATA_DIR, f"{topic_id}.txt"),
        file_path(METADATA_DIR, f"{topic_id}_short.txt"),

        file_path(METADATA_DIR, "uploads", f"{topic_id}.json"),
        file_path(METADATA_DIR, "uploads", f"{topic_id}_short.json"),
    ]

    for path in files_to_remove:
        if os.path.exists(path):
            print(f"REMOVING OLD FILE: {path}")
            os.remove(path)


def ensure_directories():
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    os.makedirs(AUDIO_DIR, exist_ok=True)
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    os.makedirs(METADATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(METADATA_DIR, "uploads"), exist_ok=True)


def validate_file(path, label):
    if not os.path.exists(path):
        raise RuntimeError(f"{label} NOT FOUND: {path}")

    size = os.path.getsize(path)

    if size <= 0:
        raise RuntimeError(f"{label} IS EMPTY: {path}")

    print(f"{label} OK: {path} ({size} bytes)")


def build_long_video(topic_id, title, research_text):
    print("=" * 70)
    print("BUILDING LONG VIDEO")
    print("=" * 70)

    script_path = file_path(SCRIPTS_DIR, f"{topic_id}.txt")
    audio_path = file_path(AUDIO_DIR, f"{topic_id}.mp3")
    video_path = file_path(VIDEOS_DIR, f"{topic_id}.mp4")
    metadata_path = file_path(METADATA_DIR, f"{topic_id}.txt")

    # --------------------------------------------------------
    # SCRIPT
    # --------------------------------------------------------
    if os.path.exists(script_path) and topic_id not in FORCE_REBUILD_IDS:
        print("LONG SCRIPT ALREADY EXISTS")
        with open(script_path, "r", encoding="utf-8") as f:
            script_text = f.read()
    else:
        print("GENERATING LONG SCRIPT...")
        script_text = generate_script(title, research_text)
        save_script(script_text, script_path)

    validate_file(script_path, "LONG SCRIPT")

    # --------------------------------------------------------
    # VOICE
    # --------------------------------------------------------
    if os.path.exists(audio_path) and topic_id not in FORCE_REBUILD_IDS:
        print("LONG AUDIO ALREADY EXISTS")
    else:
        print("GENERATING LONG VOICE...")
        generate_voice(script_text, audio_path)

    validate_file(audio_path, "LONG AUDIO")

    # --------------------------------------------------------
    # VIDEO
    # --------------------------------------------------------
    if os.path.exists(video_path) and topic_id not in FORCE_REBUILD_IDS:
        print("LONG VIDEO ALREADY EXISTS")
    else:
        print("CREATING LONG VIDEO...")
        create_video(
            topic_id=topic_id,
            title=title,
            audio_path=audio_path,
            output_path=video_path
        )

    validate_file(video_path, "LONG VIDEO")

    # --------------------------------------------------------
    # METADATA
    # --------------------------------------------------------
    print("GENERATING LONG METADATA...")
    save_metadata(
        topic_id=topic_id,
        title=title,
        script_text=script_text,
        output_path=metadata_path
    )

    validate_file(metadata_path, "LONG METADATA")

    return script_text


def build_short_video(topic_id, title, long_script):
    print("=" * 70)
    print("BUILDING SHORT VIDEO")
    print("=" * 70)

    short_script_path = file_path(
        SCRIPTS_DIR,
        f"{topic_id}_short.txt"
    )

    short_audio_path = file_path(
        AUDIO_DIR,
        f"{topic_id}_short.mp3"
    )

    short_video_path = file_path(
        VIDEOS_DIR,
        f"{topic_id}_short.mp4"
    )

    short_metadata_path = file_path(
        METADATA_DIR,
        f"{topic_id}_short.txt"
    )

    print("GENERATING SHORT...")
    
    # build_short() handles:
    # - highlight selection
    # - Telugu script
    # - TTS
    # - 9:16 video
    # - 45-60 seconds
    # - Shorts metadata
    build_short(
        topic_id=topic_id,
        title=title,
        long_script=long_script
    )

    validate_file(short_script_path, "SHORT SCRIPT")
    validate_file(short_audio_path, "SHORT AUDIO")
    validate_file(short_video_path, "SHORT VIDEO")
    validate_file(short_metadata_path, "SHORT METADATA")


def main():
    print("=" * 70)
    print("TELUGU MYSTERY AI PIPELINE")
    print("=" * 70)

    ensure_directories()

    topics = load_topics(TOPICS_FILE)

    topic = get_next_topic(topics)

    if not topic:
        print("NO PENDING TOPICS FOUND")
        return

    topic_id = str(topic["id"]).zfill(3)
    title = topic["title"]

    print(f"NEXT TOPIC: {topic_id}")
    print(f"TITLE: {title}")

    # ========================================================
    # FORCE REBUILD 005
    # ========================================================
    if topic_id in FORCE_REBUILD_IDS:
        print("=" * 70)
        print(f"FORCE REBUILD ENABLED FOR TOPIC {topic_id}")
        print("=" * 70)

        remove_old_topic_files(topic_id)

        # Make sure the topic is pending before rebuilding.
        topic["status"] = "pending"

    # ========================================================
    # RESEARCH
    # ========================================================
    research_file = file_path(
        BASE_DIR,
        f"research/{topic_id}.txt"
    )

    os.makedirs(
        os.path.join(BASE_DIR, "research"),
        exist_ok=True
    )

    if os.path.exists(research_file) and topic_id not in FORCE_REBUILD_IDS:
        print("RESEARCH ALREADY EXISTS")

        with open(research_file, "r", encoding="utf-8") as f:
            research_text = f.read()

    else:
        print("RESEARCHING TOPIC...")

        research_text = research_topic(title)

        if not research_text:
            raise RuntimeError(
                f"Research failed for topic {topic_id}"
            )

        with open(
            research_file,
            "w",
            encoding="utf-8"
        ) as f:
            f.write(research_text)

    validate_file(research_file, "RESEARCH")

    # ========================================================
    # LONG VIDEO
    # ========================================================
    long_script = build_long_video(
        topic_id,
        title,
        research_text
    )

    # ========================================================
    # SHORT VIDEO
    # ========================================================
    build_short_video(
        topic_id,
        title,
        long_script
    )

    # ========================================================
    # FINAL VALIDATION
    # ========================================================
    long_video = file_path(
        VIDEOS_DIR,
        f"{topic_id}.mp4"
    )

    short_video = file_path(
        VIDEOS_DIR,
        f"{topic_id}_short.mp4"
    )

    long_metadata = file_path(
        METADATA_DIR,
        f"{topic_id}.txt"
    )

    short_metadata = file_path(
        METADATA_DIR,
        f"{topic_id}_short.txt"
    )

    validate_file(long_video, "FINAL LONG VIDEO")
    validate_file(short_video, "FINAL SHORT VIDEO")
    validate_file(long_metadata, "FINAL LONG METADATA")
    validate_file(short_metadata, "FINAL SHORT METADATA")

    # ========================================================
    # DO NOT MARK COMPLETED HERE
    # ========================================================
    # youtube_upload.py will mark the topic completed only
    # after BOTH Long + Short are successfully uploaded.
    topic["status"] = "videos_ready"

    save_topics(TOPICS_FILE, topics)

    print("=" * 70)
    print(f"TOPIC {topic_id} BUILD COMPLETED")
    print("LONG + SHORT READY FOR YOUTUBE UPLOAD")
    print("=" * 70)


if __name__ == "__main__":
    main()
