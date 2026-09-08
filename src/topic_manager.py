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

        raise FileNotFoundError(
            f"Topics file not found: {TOPICS_FILE}"
        )

    with TOPICS_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        topics = list(
            csv.DictReader(file)
        )

    if not topics:
        return []

    for topic in topics:

        topic["id"] = (
            topic.get("id", "").strip()
        )

        topic["title"] = (
            topic.get("title", "").strip()
        )

        topic["status"] = (
            topic.get(
                "status",
                "pending"
            )
            .strip()
            .lower()
        )

    return topics


def save_topics(topics):

    if not topics:
        return

    fieldnames = list(
        topics[0].keys()
    )

    with TOPICS_FILE.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(topics)


def get_next_topic():

    topics = load_topics()

    if not topics:
        return None

    active_topics = [
        topic
        for topic in topics
        if topic["status"] in ACTIVE_STATUSES
    ]

    if active_topics:

        active_topics.sort(
            key=lambda topic: int(topic["id"])
        )

        selected = active_topics[0]

        print("=" * 70)
        print("TOPIC MANAGER")
        print("RESUMING ACTIVE TOPIC")
        print(f"ID: {selected['id']}")
        print(f"TITLE: {selected['title']}")
        print(f"STATUS: {selected['status']}")
        print("=" * 70)

        return selected

    pending_topics = [
        topic
        for topic in topics
        if topic["status"] == "pending"
    ]

    if pending_topics:

        pending_topics.sort(
            key=lambda topic: int(topic["id"])
        )

        selected = pending_topics[0]

        print("=" * 70)
        print("TOPIC MANAGER")
        print("FOUND NEXT PENDING TOPIC")
        print(f"ID: {selected['id']}")
        print(f"TITLE: {selected['title']}")
        print(f"STATUS: {selected['status']}")
        print("=" * 70)

        return selected

    print("=" * 70)
    print("ALL TOPICS COMPLETED")
    print("=" * 70)

    return None


def get_topic_by_id(topic_id):

    topic_id = str(topic_id).strip()

    for topic in load_topics():

        if topic["id"] == topic_id:
            return topic

    raise ValueError(
        f"Topic ID not found: {topic_id}"
    )


def set_topic_status(
    topic_id,
    new_status
):

    topic_id = str(topic_id).strip()
    new_status = (
        str(new_status)
        .strip()
        .lower()
    )

    allowed_statuses = {
        "pending",
        "processing",
        "researched",
        "script_processing",
        "script_ready",
        "completed",
        "failed",
    }

    if new_status not in allowed_statuses:

        raise ValueError(
            f"Invalid topic status: {new_status}"
        )

    topics = load_topics()

    found = False

    for topic in topics:

        if topic["id"] == topic_id:

            topic["status"] = new_status
            found = True
            break

    if not found:

        raise ValueError(
            f"Topic ID not found: {topic_id}"
        )

    save_topics(topics)

    print("=" * 70)
    print("TOPIC STATUS UPDATED")
    print(f"ID: {topic_id}")
    print(f"STATUS: {new_status}")
    print("=" * 70)


def mark_processing(topic_id):
    set_topic_status(
        topic_id,
        "processing"
    )


def mark_completed(topic_id):
    set_topic_status(
        topic_id,
        "completed"
    )


def mark_failed(topic_id):
    set_topic_status(
        topic_id,
        "failed"
    )


if __name__ == "__main__":

    topic = get_next_topic()

    if topic:

        print(
            f"NEXT TOPIC: "
            f"{topic['id']} - "
            f"{topic['title']}"
        )

    else:

        print(
            "NO TOPICS AVAILABLE"
        )
