import os

from topic_manager import load_topics, save_topics, get_next_topic
from research import research_topic
from script import generate_script, save_script
from voice import generate_voice
from video import run as create_video
from youtube_metadata import save_metadata
from shorts import build_short


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TOPICS_FILE = os.path.join(BASE_DIR, "topics", "topics.csv")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
VIDEOS_DIR = os.path.join(BASE_DIR, "videos")
METADATA_DIR = os.path.join(BASE_DIR, "metadata")
RESEARCH_DIR = os.path.join(BASE_DIR, "research")

FORCE_REBUILD_IDS = {"005"}


def ensure_directories():
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    os.makedirs(AUDIO_DIR, exist_ok=True)
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    os.makedirs(METADATA_DIR, exist_ok=True)
    os.makedirs(RESEARCH_DIR, exist_ok=True)
    os.makedirs(os.path.join(METADATA_DIR, "uploads"), exist_ok=True)


def remove_old_topic_files(topic_id):
    files = [
        os.path.join(SCRIPTS_DIR, f"{topic_id}.txt"),
        os.path.join(SCRIPTS_DIR, f"{topic_id}_short.txt"),
        os.path.join(AUDIO_DIR, f"{topic_id}.mp3"),
        os.path.join(AUDIO_DIR, f"{topic_id}_short.mp3"),
        os.path.join(VIDEOS_DIR, f"{topic_id}.mp4"),
        os.path.join(VIDEOS_DIR, f"{topic_id}_short.mp4"),
        os.path.join(METADATA_DIR, f"{topic_id}.txt"),
        os.path.join(METADATA_DIR, f"{topic_id}_short.txt"),
        os.path.join(METADATA_DIR, "uploads", f"{topic_id}.json"),
        os.path.join(METADATA_DIR, "uploads", f"{topic_id}_short.json"),
    ]

    for path in files:
        if os.path.exists(path):
            print(f"Removing old file: {path}")
            os.remove(path)


def find_topic(topics, topic_id):
    for topic in topics:
        if str(topic.get("id", "")).strip() == str(topic_id).strip():
            return topic
    return None


def validate_file(path):
    if not os.path.exists(path):
        raise RuntimeError(f"Required file not found: {path}")

    if os.path.getsize(path) <= 0:
        raise RuntimeError(f"Required file is empty: {path}")


def build_long_video(topic_id, title, research_text):
    script_path = os.path.join(SCRIPTS_DIR, f"{topic_id}.txt")
    audio_path = os.path.join(AUDIO_DIR, f"{topic_id}.mp3")
    video_path = os.path.join(VIDEOS_DIR, f"{topic_id}.mp4")
    metadata_path = os.path.join(METADATA_DIR, f"{topic_id}.txt")

    if os.path.exists(script_path) and topic_id not in FORCE_REBUILD_IDS:
        print("LONG SCRIPT ALREADY EXISTS")

        with open(script_path, "r", encoding="utf-8") as file:
            script_text = file.read()
    else:
        print("GENERATING LONG SCRIPT")

        script_text = generate_script(
            title,
            research_text
        )

        save_script(
            script_text,
            script_path
        )

    validate_file(script_path)

    if os.path.exists(audio_path) and topic_id not in FORCE_REBUILD_IDS:
        print("LONG AUDIO ALREADY EXISTS")
    else:
        print("GENERATING LONG AUDIO")

        generate_voice(
            script_text,
            audio_path
        )

    validate_file(audio_path)

    if os.path.exists(video_path) and topic_id not in FORCE_REBUILD_IDS:
        print("LONG VIDEO ALREADY EXISTS")
    else:
        print("CREATING LONG VIDEO")

        create_video(topic_id)

    validate_file(video_path)

    print("GENERATING LONG METADATA")

    save_metadata(
        topic_id,
        title,
        script_text,
        metadata_path
    )

    validate_file(metadata_path)

    return script_text


def build_short_video(topic_id, title, long_script):
    short_script_path = os.path.join(
        SCRIPTS_DIR,
        f"{topic_id}_short.txt"
    )

    short_audio_path = os.path.join(
        AUDIO_DIR,
        f"{topic_id}_short.mp3"
    )

    short_video_path = os.path.join(
        VIDEOS_DIR,
        f"{topic_id}_short.mp4"
    )

    short_metadata_path = os.path.join(
        METADATA_DIR,
        f"{topic_id}_short.txt"
    )

    print("CREATING SHORT VIDEO")

    build_short(
        topic_id,
        title,
        long_script
    )

    validate_file(short_script_path)
    validate_file(short_audio_path)
    validate_file(short_video_path)
    validate_file(short_metadata_path)


def main():
    print("=" * 70)
    print("TELUGU MYSTERY AI PIPELINE")
    print("=" * 70)

    ensure_directories()

    topics = load_topics()

    forced_topic = find_topic(
        topics,
        "005"
    )

    if forced_topic:
        topic_status = forced_topic.get(
            "status",
            ""
        ).strip().lower()

        if (
            topic_status != "completed"
            and "005" in FORCE_REBUILD_IDS
        ):
            topic = forced_topic
        else:
            topic = get_next_topic(topics)
    else:
        topic = get_next_topic(topics)

    if not topic:
        print("NO PENDING TOPICS FOUND")
        return

    topic_id = str(
        topic["id"]
    ).zfill(3)

    title = topic["title"].strip()

    print(f"TOPIC: {topic_id}")
    print(f"TITLE: {title}")

    if topic_id in FORCE_REBUILD_IDS:
        print("=" * 70)
        print(f"FORCE REBUILD: {topic_id}")
        print("=" * 70)

        topic["status"] = "pending"

        remove_old_topic_files(
            topic_id
        )

    research_path = os.path.join(
        RESEARCH_DIR,
        f"{topic_id}.txt"
    )

    if (
        os.path.exists(research_path)
        and topic_id not in FORCE_REBUILD_IDS
    ):
        print("RESEARCH ALREADY EXISTS")

        with open(
            research_path,
            "r",
            encoding="utf-8"
        ) as file:
            research_text = file.read()

    else:
        print("RESEARCHING TOPIC")

        research_text = research_topic(
            title
        )

        if not research_text:
            raise RuntimeError(
                f"Research failed for topic {topic_id}"
            )

        with open(
            research_path,
            "w",
            encoding="utf-8"
        ) as file:
            file.write(research_text)

    validate_file(
        research_path
    )

    long_script = build_long_video(
        topic_id,
        title,
        research_text
    )

    build_short_video(
        topic_id,
        title,
        long_script
    )

    long_video = os.path.join(
        VIDEOS_DIR,
        f"{topic_id}.mp4"
    )

    short_video = os.path.join(
        VIDEOS_DIR,
        f"{topic_id}_short.mp4"
    )

    long_metadata = os.path.join(
        METADATA_DIR,
        f"{topic_id}.txt"
    )

    short_metadata = os.path.join(
        METADATA_DIR,
        f"{topic_id}_short.txt"
    )

    validate_file(
        long_video
    )

    validate_file(
        short_video
    )

    validate_file(
        long_metadata
    )

    validate_file(
        short_metadata
    )

    topic["status"] = "videos_ready"

    save_topics(
        topics
    )

    print("=" * 70)
    print(f"TOPIC {topic_id} BUILD COMPLETED")
    print("LONG + SHORT READY FOR YOUTUBE")
    print("=" * 70)


if __name__ == "__main__":
    main()
