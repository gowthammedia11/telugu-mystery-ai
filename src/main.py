import csv

TOPICS_FILE = "topics/topics.csv"


def get_next_topic():
    with open(TOPICS_FILE, "r", encoding="utf-8") as file:
        topics = list(csv.DictReader(file))

    for topic in topics:
        if topic["status"].strip().lower() == "pending":
            return topic

    return None


def update_topic_status(topic_id, new_status):
    with open(TOPICS_FILE, "r", encoding="utf-8") as file:
        topics = list(csv.DictReader(file))

    for topic in topics:
        if topic["id"] == topic_id:
            topic["status"] = new_status

    with open(TOPICS_FILE, "w", newline="", encoding="utf-8") as file:
        fieldnames = ["id", "title", "status"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(topics)


topic = get_next_topic()

if topic:
    print("NEXT TOPIC")
    print("ID:", topic["id"])
    print("TITLE:", topic["title"])
    print("STATUS:", topic["status"])

    update_topic_status(topic["id"], "processing")

    print("STATUS UPDATED TO: processing")

else:
    print("NO PENDING TOPICS FOUND")
