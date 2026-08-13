import os
import csv
import requests
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

TOPICS_FILE = Path("topics/topics.csv")
RESEARCH_DIR = Path("research")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL = "openrouter/free"


# ============================================================
# LOAD TOPICS
# ============================================================

def load_topics():

    if not TOPICS_FILE.exists():
        raise FileNotFoundError(
            f"Topics file not found: {TOPICS_FILE}"
        )

    with TOPICS_FILE.open(
        "r",
        encoding="utf-8",
        newline=""
    ) as file:

        return list(
            csv.DictReader(file)
        )


# ============================================================
# SAVE TOPICS
# ============================================================

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


# ============================================================
# FIND NEXT PENDING TOPIC
# ============================================================

def get_next_topic(topics):

    pending_topics = [
        topic
        for topic in topics
        if topic.get("status", "")
        .strip()
        .lower()
        == "pending"
    ]

    if not pending_topics:
        return None

    # Always select lowest numeric ID.
    pending_topics.sort(
        key=lambda topic: int(
            topic["id"].strip()
        )
    )

    return pending_topics[0]


# ============================================================
# UPDATE STATUS
# ============================================================

def update_topic_status(
    topics,
    topic_id,
    new_status
):

    for topic in topics:

        if topic["id"].strip() == topic_id:

            topic["status"] = new_status

            break

    save_topics(topics)


# ============================================================
# OPENROUTER RESEARCH
# ============================================================

def research_topic(
    topic_id,
    topic_title
):

    api_key = os.environ.get(
        "OPENROUTER_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "OPENROUTER_API_KEY secret is missing"
        )

    prompt = f"""
You are a professional factual research assistant
for a Telugu mystery and science YouTube channel.

TOPIC ID:
{topic_id}

TOPIC:
{topic_title}

Research this topic deeply and accurately.

The research will later be converted into an
original Telugu YouTube documentary script.

IMPORTANT RULES:

1. NEVER invent facts.
2. NEVER fabricate dates, measurements,
   scientific findings or quotations.
3. Clearly distinguish:
   - CONFIRMED FACTS
   - SCIENTIFIC EXPLANATIONS
   - THEORIES / HYPOTHESES
   - WHAT REMAINS UNKNOWN
4. If a claim is disputed or uncertain,
   explicitly say that it is uncertain.
5. Prefer:
   - NASA
   - NOAA
   - ESA
   - USGS
   - scientific institutions
   - universities
   - government sources
   - peer-reviewed research
   - reputable scientific publications
6. Include exact dates when relevant.
7. Include important measurements and numbers.
8. Explain scientific concepts in simple language.
9. Do not write a fictional story.
10. Do not exaggerate the mystery.
11. Do not present theories as facts.
12. Do not create fake sources.

STRUCTURE THE RESEARCH AS:

TITLE

1. OVERVIEW

2. CONFIRMED FACTS

3. IMPORTANT DATES

4. IMPORTANT NUMBERS AND MEASUREMENTS

5. SCIENTIFIC EXPLANATION

6. MAJOR DISCOVERIES

7. POPULAR THEORIES

8. WHAT SCIENTISTS ACTUALLY KNOW

9. WHAT REMAINS UNKNOWN

10. POSSIBLE EXPLANATIONS

11. SOURCE / VERIFICATION NOTES

For every important factual claim,
include enough information to allow later verification.

This is research material only.
Do not write the final YouTube script.
"""


    response = requests.post(
        OPENROUTER_URL,

        headers={
            "Authorization":
                f"Bearer {api_key}",

            "Content-Type":
                "application/json",

            "HTTP-Referer":
                "https://github.com/",

            "X-Title":
                "Telugu Mystery AI"
        },

        json={
            "model": MODEL,

            "messages": [
                {
                    "role": "system",
                    "content":
                        "You are a careful factual research assistant. "
                        "Accuracy is more important than creativity."
                },

                {
                    "role": "user",
                    "content": prompt
                }
            ],

            "temperature": 0.2
        },

        timeout=180
    )

    response.raise_for_status()

    result = response.json()

    choices = result.get(
        "choices",
        []
    )

    if not choices:

        raise RuntimeError(
            "OpenRouter returned no choices"
        )

    message = choices[0].get(
        "message",
        {}
    )

    answer = message.get(
        "content",
        ""
    )

    if not answer.strip():

        raise RuntimeError(
            "OpenRouter returned empty research"
        )

    return answer.strip()


# ============================================================
# SAVE RESEARCH
# ============================================================

def save_research(
    topic_id,
    topic_title,
    research
):

    RESEARCH_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        RESEARCH_DIR
        / f"{topic_id}.txt"
    )

    content = (
        f"TOPIC ID: {topic_id}\n"
        f"TOPIC: {topic_title}\n"
        f"RESEARCH STATUS: COMPLETED\n"
        f"{'=' * 70}\n\n"
        f"{research}\n"
    )

    output_file.write_text(
        content,
        encoding="utf-8"
    )

    return output_file


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("TELUGU MYSTERY AI - RESEARCH")
    print("=" * 70)

    topics = load_topics()

    print(
        f"TOTAL TOPICS: {len(topics)}"
    )

    topic = get_next_topic(
        topics
    )

    if not topic:

        print(
            "NO PENDING TOPICS"
        )

        return

    topic_id = topic[
        "id"
    ].strip()

    topic_title = topic[
        "title"
    ].strip()

    print(
        f"SELECTED TOPIC: {topic_id}"
    )

    print(
        f"TITLE: {topic_title}"
    )

    print(
        "STATUS: pending -> processing"
    )

    # --------------------------------------------------------
    # MARK PROCESSING
    # --------------------------------------------------------

    update_topic_status(
        topics,
        topic_id,
        "processing"
    )

    try:

        # ----------------------------------------------------
        # RESEARCH
        # ----------------------------------------------------

        print("=" * 70)
        print("STARTING FACTUAL RESEARCH")
        print("=" * 70)

        research = research_topic(
            topic_id,
            topic_title
        )

        print(
            f"RESEARCH CHARACTERS: "
            f"{len(research)}"
        )

        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        output_file = save_research(
            topic_id,
            topic_title,
            research
        )

        print(
            f"RESEARCH SAVED: {output_file}"
        )

        # ----------------------------------------------------
        # VERIFY FILE
        # ----------------------------------------------------

        if not output_file.exists():

            raise RuntimeError(
                "Research file was not created"
            )

        file_size = (
            output_file.stat().st_size
        )

        if file_size < 500:

            raise RuntimeError(
                "Research file is suspiciously small"
            )

        print(
            f"RESEARCH FILE SIZE: "
            f"{file_size} bytes"
        )

        # ----------------------------------------------------
        # MARK COMPLETED
        # ----------------------------------------------------

        update_topic_status(
            topics,
            topic_id,
            "researched"
        )

        print(
            "STATUS: processing -> researched"
        )

        print("=" * 70)
        print("RESEARCH COMPLETED SUCCESSFULLY")
        print("=" * 70)

    except Exception as error:

        print("=" * 70)
        print("RESEARCH FAILED")
        print("=" * 70)

        print(
            f"ERROR: {error}"
        )

        # ----------------------------------------------------
        # RETURN TO PENDING
        # ----------------------------------------------------

        try:

            update_topic_status(
                topics,
                topic_id,
                "pending"
            )

            print(
                "STATUS: processing -> pending"
            )

            print(
                "Topic will be retried on the next run."
            )

        except Exception as status_error:

            print(
                f"FAILED TO RESTORE STATUS: "
                f"{status_error}"
            )

        raise


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
