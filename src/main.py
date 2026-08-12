import csv

TOPICS_FILE = "topics/topics.csv"

def get_next_topic():
    with open(TOPICS_FILE, "r", encoding="utf-8") as file:
        topics = list(csv.DictReader(file))

    for topic in topics:
        if topic["status"].strip().lower() == "pending":
            return topic

    return None


topic = get_next_topic()

if topic:
    print("NEXT TOPIC")
    print("ID:", topic["id"])
    print("TITLE:", topic["title"])
    print("STATUS:", topic["status"])
else:
    print("NO PENDING TOPICS FOUND")
