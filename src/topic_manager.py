import csv
from pathlib import Path

TOPICS_FILE = Path("topics/topics.csv")
ACTIVE_STATUSES = {
    "processing",
    "researched",
    "script_processing",
    "script_ready",
}


def load_topics():
    if not TOPICS_FILE.exists():
        raise FileNotFoundError(f"Topics file not found: {TOPICS_FILE}")
    with TOPICS_FILE.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def save_topics(topics):
    if not topics:
        return
    fieldnames = list(topics[0].keys())
    with TOPICS_FILE.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(topics)


def numeric_id(topic):
    try:
        return int(topic.get("id", "0").strip())
    except ValueError:
        return 10**9


def get_next_topic(topics=None):
    if topics is None:
        topics = load_topics()

    active = [
        topic for topic in topics
        if topic.get("status", "").strip().lower() in ACTIVE_STATUSES
    ]
    if active:
        return sorted(active, key=numeric_id)[0]

    pending = [
        topic for topic in topics
        if topic.get("status", "").strip().lower() == "pending"
    ]
    if not pending:
        return None

    return sorted(pending, key=numeric_id)[0]


def get_topic_by_id(topic_id):
    for topic in load_topics():
        if topic.get("id", "").strip() == str(topic_id).strip():
            return topic
    return None


def set_topic_status(topic_id, new_status):
    topics = load_topics()
    found = False
    for topic in topics:
        if topic.get("id", "").strip() == str(topic_id).strip():
            topic["status"] = new_status
            found = True
            break
    if not found:
        raise ValueError(f"Topic {topic_id} not found in topics.csv")
    save_topics(topics)


def mark_processing(topic_id):
    set_topic_status(topic_id, "processing")


def mark_completed(topic_id):
    set_topic_status(topic_id, "completed")


def mark_failed(topic_id):
    # Keep the topic retryable on the next build run.
    set_topic_status(topic_id, "processing")


if __name__ == "__main__":
    topic = get_next_topic()
    if topic:
        print(f"NEXT TOPIC: {topic['id']} - {topic['title']}")
    else:
        print("NO TOPICS AVAILABLE")
