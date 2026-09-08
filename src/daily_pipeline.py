import asyncio
import csv
from pathlib import Path

from research import research_topic, save_research
from script import generate_script, clean_script, apply_final_script_rules, save_script
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


def load_topics():
    with TOPICS_FILE.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def save_topic_status(topics, topic_id, status):
    for topic in topics:
        if topic.get("id", "").strip() == topic_id:
            topic["status"] = status
            break
    save_topics(topics)


def get_current_topic(topics):
    active = [
        t for t in topics
        if t.get("status", "").strip().lower()
        in {"processing", "researched", "script_processing", "script_ready"}
    ]

    if active:
        active.sort(key=lambda t: int(t["id"].strip()))
        return active[0]

    pending = [
        t for t in topics
        if t.get("status", "").strip().lower() == "pending"
    ]

    if not pending:
        return None

    pending.sort(key=lambda t: int(t["id"].strip()))
    return pending[0]


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
    save_topic_status(topics, topic_id, "processing")

    research_file = RESEARCH_DIR / f"{topic_id}.txt"

    if not research_file.exists() or research_file.stat().st_size < 500:
        print("STARTING RESEARCH")
        research = research_topic(topic_id, topic_title)
        research_file = save_research(topic_id, topic_title, research)
        save_topic_status(load_topics(), topic_id, "researched")
    else:
        print(f"RESEARCH ALREADY EXISTS: {research_file}")

    research = research_file.read_text(encoding="utf-8").strip()
    if not research:
        raise RuntimeError("Research file is empty")

    print("STARTING SCRIPT")
    script = generate_script(topic_id, topic_title, research)
    script = clean_script(script)
    script = apply_final_script_rules(script)

    if len(script) < 500:
        raise RuntimeError("Generated script is suspiciously short")

    script_file = save_script(topic_id, script)
    save_topic_status(load_topics(), topic_id, "script_ready")
    print(f"SCRIPT SAVED: {script_file}")

    print("STARTING VOICE")
    asyncio.run(
        generate_voice({"id": topic_id, "title": topic_title})
    )

    print("STARTING VIDEO")
    run_video(topic_id)

    print("STARTING YOUTUBE METADATA")
    script_text = read_script(topic_id)
    title = generate_title(topic_title, script_text)
    description = generate_description(topic_id, topic_title, script_text)
    tags = generate_tags(topic_title, script_text)
    hashtags = generate_hashtags(topic_title, script_text)
    save_metadata(topic_id, title, description, tags, hashtags)

    print("=" * 70)
    print("DAILY BUILD COMPLETE — READY FOR 5:30 PM PUBLIC UPLOAD")
    print(f"TOPIC: {topic_id}")
    print(f"TITLE: {title}")
    print("=" * 70)


def main():
    topics = load_topics()
    topic = get_current_topic(topics)

    if not topic:
        print("NO TOPICS AVAILABLE")
        return

    build_topic(topic)


if __name__ == "__main__":
    main()
