import csv
from pathlib import Path


TOPICS_FILE = Path("topics/topics.csv")


# ============================================================
# GET NEXT TOPIC
# ============================================================

def get_next_topic():
    """
    Priority:
    1. Lowest-ID processing topic
    2. If no processing topic exists,
       lowest-ID pending topic

    Completed topics are always skipped.
    """

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
        return None

    # --------------------------------------------------------
    # NORMALIZE
    # --------------------------------------------------------

    for topic in topics:
        topic["id"] = topic["id"].strip()
        topic["title"] = topic["title"].strip()
        topic["status"] = (
            topic.get("status", "pending")
            .strip()
            .lower()
        )

    # --------------------------------------------------------
    # PROCESSING FIRST
    # --------------------------------------------------------

    processing_topics = [
        topic
        for topic in topics
        if topic["status"] == "processing"
    ]

    if processing_topics:

        processing_topics.sort(
            key=lambda topic: int(topic["id"])
        )

        selected = processing_topics[0]

        print("=" * 70)
        print("TOPIC MANAGER")
        print("FOUND PROCESSING TOPIC")
        print(f"ID: {selected['id']}")
        print(f"TITLE: {selected['title']}")
        print(f"STATUS: {selected['status']}")
        print("=" * 70)

        return selected

    # --------------------------------------------------------
    # OTHERWISE PENDING
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # EVERYTHING COMPLETED
    # --------------------------------------------------------

    print("=" * 70)
    print("ALL 730 TOPICS COMPLETED")
    print("=" * 70)

    return None


# ============================================================
# SET TOPIC STATUS
# ============================================================

def set_topic_status(topic_id, new_status):
    """
    Updates one topic status in topics/topics.csv.
    """

    topic_id = str(topic_id).strip()
    new_status = str(new_status).strip().lower()

    allowed_statuses = {
        "pending",
        "processing",
        "completed",
        "failed",
    }

    if new_status not in allowed_statuses:
        raise ValueError(
            f"Invalid status: {new_status}"
        )

    if not TOPICS_FILE.exists():
        raise FileNotFoundError(
            f"Topics file not found: {TOPICS_FILE}"
        )

    with TOPICS_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        topics = list(reader)

    if not fieldnames:
        raise ValueError(
            "topics.csv has no header"
        )

    found = False

    for topic in topics:

        current_id = topic["id"].strip()

        if current_id == topic_id:

            topic["status"] = new_status
            found = True

            print("=" * 70)
            print("TOPIC STATUS UPDATED")
            print(f"ID: {topic_id}")
            print(f"STATUS: {new_status}")
            print("=" * 70)

            break

    if not found:
        raise ValueError(
            f"Topic ID not found: {topic_id}"
        )

    # --------------------------------------------------------
    # WRITE CSV
    # --------------------------------------------------------

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


# ============================================================
# MARK PROCESSING
# ============================================================

def mark_processing(topic_id):
    set_topic_status(
        topic_id,
        "processing"
    )


# ============================================================
# MARK COMPLETED
# ============================================================

def mark_completed(topic_id):
    set_topic_status(
        topic_id,
        "completed"
    )


# ============================================================
# MARK FAILED
# ============================================================

def mark_failed(topic_id):
    set_topic_status(
        topic_id,
        "failed"
    )


# ============================================================
# MAIN TEST
# ============================================================

if __name__ == "__main__":

    topic = get_next_topic()

    if topic:

        print(
            f"NEXT TOPIC: "
            f"{topic['id']} - {topic['title']}"
        )

    else:

        print(
            "NO TOPICS AVAILABLE"
        )
