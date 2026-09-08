import os
import csv
import re
import requests
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

TOPICS_FILE = Path("topics/topics.csv")
RESEARCH_DIR = Path("research")
SCRIPTS_DIR = Path("scripts")

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
# FIND NEXT RESEARCHED TOPIC
# ============================================================

def get_next_researched_topic(topics):

    candidates = []

    for topic in topics:

        topic_id = topic[
            "id"
        ].strip()

        status = topic.get(
            "status",
            ""
        ).strip().lower()

        research_file = (
            RESEARCH_DIR
            / f"{topic_id}.txt"
        )

        # Research completed but script not created yet.
        if (
            status == "researched"
            and research_file.exists()
        ):
            candidates.append(
                topic
            )

    if not candidates:
        return None

    # Always process the lowest topic ID first.
    candidates.sort(
        key=lambda topic: int(
            topic["id"].strip()
        )
    )

    return candidates[0]


# ============================================================
# UPDATE STATUS
# ============================================================

def update_topic_status(
    topics,
    topic_id,
    new_status
):

    for topic in topics:

        if topic[
            "id"
        ].strip() == topic_id:

            topic[
                "status"
            ] = new_status

            break

    save_topics(topics)


# ============================================================
# GENERATE TELUGU SCRIPT
# ============================================================

def generate_script(
    topic_id,
    topic_title,
    research
):

    api_key = os.environ.get(
        "OPENROUTER_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY secret is missing"
        )

    prompt = f"""
You are an expert Telugu YouTube documentary
scriptwriter.

Create a completely ORIGINAL Telugu narration
for a mystery/science YouTube channel.

TOPIC ID:
{topic_id}

TOPIC:
{topic_title}

============================================================
RESEARCH MATERIAL
============================================================

{research}

============================================================
SCRIPT REQUIREMENTS
============================================================

Write the script in natural, conversational Telugu.

The narration should sound like a professional
Telugu YouTube documentary.

IMPORTANT:

1. Use ONLY information supported by the research.
2. NEVER invent facts.
3. NEVER invent dates, measurements or discoveries.
4. Clearly distinguish confirmed facts from theories.
5. Never present speculation as confirmed fact.
6. Do not copy sentences from the research.
7. Rewrite everything in original language.
8. Do not mention AI.
9. Do not mention the research material.
10. Do not mention sources inside the narration.
11. Do not use scene directions.
12. Do not use timestamps.
13. Do not use headings.
14. Do not use bullet points.
15. Write ONLY the final narration.
16. Keep the language easy for a general Telugu audience.
17. Avoid unnecessary English words.
18. Scientific terms may use natural Telugu pronunciation
    where necessary.

============================================================
YEAR / NUMBER PRONUNCIATION
============================================================

IMPORTANT:

Years must be written in natural Telugu words.

Examples:

1930 → పంతొమ్మిది వందల ముప్పై

1990 → పంతొమ్మిది వందల తొంభై

1969 → పంతొమ్మిది వందల అరవై తొమ్మిది

2005 → రెండు వేల ఐదు

2002 → రెండు వేల రెండు

2014 → రెండు వేల పద్నాలుగు

2016 → రెండు వేల పదహారు

2020 → రెండు వేల ఇరవై

DO NOT write years digit-by-digit.

WRONG:
ఒకటి తొమ్మిది తొమ్మిది సున్నా

WRONG:
వన్ నైన్ నైన్ జీరో

CORRECT 1990:
పంతొమ్మిది వందల తొంభై

For other important numbers, write them
naturally in Telugu words whenever practical.

Examples:

65 → అరవై ఐదు

14 → పద్నాలుగు

420 → నాలుగు వందల ఇరవై

300 → మూడు వందలు

800,000 → ఎనిమిది లక్షలు

============================================================
ADDITIONAL NUMBER / MEASUREMENT RULES
============================================================

1. Years must use the conventional Telugu year form.
   1930 = పంతొమ్మిది వందల ముప్పై
   1990 = పంతొమ్మిది వందల తొంభై
   1969 = పంతొమ్మిది వందల అరవై తొమ్మిది
   2005 = రెండు వేల ఐదు
2. Never use the "వెయ్యి తొమ్మిది..." form for 1900s years.
3. Never use miles. Convert every distance to kilometers only.
4. Remove unnecessary trailing zeros from decimal measurements.
   Example: 69.900 = 69.9
5. End naturally with a complete conclusion. Never stop mid-sentence.

============================================================
STRUCTURE
============================================================

The narration should naturally contain:

- Powerful opening hook
- Central mystery/question
- Background
- Confirmed scientific facts
- Scientific explanation
- Important discoveries
- Major evidence
- What scientists still don't know
- Theories, clearly identified as theories
- Strong conclusion

Do not explicitly label these sections.

Instead, connect them naturally as one continuous
YouTube narration.

============================================================
STYLE
============================================================

Start with a strong curiosity-driven opening.

The first few sentences should make the viewer
want to continue watching.

Use short and medium-length sentences.

Create natural pauses using punctuation.

Do not exaggerate beyond the evidence.

End with a memorable conclusion that leaves the
viewer thinking about the mystery.

Write ONLY the Telugu narration.
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
                        "You are a highly accurate Telugu "
                        "documentary scriptwriter. "
                        "Never invent factual information."
                },

                {
                    "role": "user",
                    "content": prompt
                }
            ],

            "temperature": 0.55
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

    script = message.get(
        "content",
        ""
    )

    if not script.strip():
        raise RuntimeError(
            "OpenRouter returned empty script"
        )

    return script.strip()


# ============================================================
# CLEAN GENERATED SCRIPT
# ============================================================

def clean_script(script):

    # Remove accidental markdown fences.
    script = script.replace(
        "```text",
        ""
    )

    script = script.replace(
        "```",
        ""
    )

    # Remove common accidental heading markers.
    lines = []

    for line in script.splitlines():

        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            line = line.lstrip("#").strip()

        lines.append(line)

    script = "\n".join(
        lines
    )

    return script.strip()


# ============================================================
# FINAL SCRIPT RULE NORMALIZATION
# ============================================================

ONES_TELUGU = {
    0: "సున్నా", 1: "ఒకటి", 2: "రెండు", 3: "మూడు", 4: "నాలుగు",
    5: "ఐదు", 6: "ఆరు", 7: "ఏడు", 8: "ఎనిమిది", 9: "తొమ్మిది",
}
TENS_TELUGU = {
    20: "ఇరవై", 30: "ముప్పై", 40: "నలభై", 50: "యాభై",
    60: "అరవై", 70: "డెబ్బై", 80: "ఎనభై", 90: "తొంభై",
}
NUM_10_19 = {
    10: "పది", 11: "పదకొండు", 12: "పన్నెండు", 13: "పదమూడు",
    14: "పద్నాలుగు", 15: "పదిహేను", 16: "పదహారు", 17: "పదిహేడు",
    18: "పద్దెనిమిది", 19: "పంతొమ్మిది",
}


def number_to_telugu_script(number):
    number = int(number)
    if number < 10:
        return ONES_TELUGU[number]
    if number < 20:
        return NUM_10_19[number]
    if number < 100:
        tens = (number // 10) * 10
        ones = number % 10
        return TENS_TELUGU[tens] if ones == 0 else f"{TENS_TELUGU[tens]} {ONES_TELUGU[ones]}"
    if number < 1000:
        hundreds = number // 100
        remainder = number % 100
        result = "వంద" if hundreds == 1 else f"{ONES_TELUGU[hundreds]} వందల"
        return result if remainder == 0 else f"{result} {number_to_telugu_script(remainder)}"
    if number < 10000:
        thousands = number // 1000
        remainder = number % 1000
        result = "వెయ్యి" if thousands == 1 else f"{number_to_telugu_script(thousands)} వేల"
        return result if remainder == 0 else f"{result} {number_to_telugu_script(remainder)}"
    return str(number)


def year_to_telugu_script(year):
    year = int(year)
    if 1900 <= year <= 1999:
        remainder = year - 1900
        return "పంతొమ్మిది వందలు" if remainder == 0 else f"పంతొమ్మిది వందల {number_to_telugu_script(remainder)}"
    if 1800 <= year <= 1899:
        remainder = year - 1800
        return "పద్దెనిమిది వందలు" if remainder == 0 else f"పద్దెనిమిది వందల {number_to_telugu_script(remainder)}"
    if 2000 <= year <= 2099:
        remainder = year - 2000
        return "రెండు వేల" if remainder == 0 else f"రెండు వేల {number_to_telugu_script(remainder)}"
    return number_to_telugu_script(year)


def apply_final_script_rules(script):
    # Full years first.
    script = re.sub(
        r"\b(19\d{2}|18\d{2}|20\d{2})\b",
        lambda m: year_to_telugu_script(m.group(1)),
        script,
    )

    # Miles -> kilometers only.
    def miles_to_km(match):
        km = round(float(match.group(1)) * 1.60934)
        return f"{number_to_telugu_script(km)} కిలోమీటర్లు"

    script = re.sub(
        r"\b(\d+(?:\.\d+)?)\s*(?:miles?|mi\.?)\b",
        miles_to_km,
        script,
        flags=re.IGNORECASE,
    )

    # Remove unnecessary trailing decimal zeros.
    script = re.sub(
        r"\b(\d+)\.(\d*?[1-9])0+\b",
        r"\1.\2",
        script,
    )
    script = re.sub(
        r"\b(\d+)\.0+\b",
        r"\1",
        script,
    )

    return script


# ============================================================
# SAVE SCRIPT
# ============================================================

def save_script(
    topic_id,
    script
):

    SCRIPTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        SCRIPTS_DIR
        / f"{topic_id}.txt"
    )

    output_file.write_text(
        script,
        encoding="utf-8"
    )

    return output_file


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("TELUGU MYSTERY AI - SCRIPT GENERATOR")
    print("=" * 70)

    topics = load_topics()

    print(
        f"TOTAL TOPICS: {len(topics)}"
    )

    topic = get_next_researched_topic(
        topics
    )

    if not topic:

        print(
            "NO RESEARCHED TOPICS READY FOR SCRIPT"
        )

        return

    topic_id = topic[
        "id"
    ].strip()

    topic_title = topic[
        "title"
    ].strip()

    research_file = (
        RESEARCH_DIR
        / f"{topic_id}.txt"
    )

    print(
        f"SELECTED TOPIC: {topic_id}"
    )

    print(
        f"TITLE: {topic_title}"
    )

    print(
        f"RESEARCH: {research_file}"
    )

    # --------------------------------------------------------
    # MARK AS SCRIPT PROCESSING
    # --------------------------------------------------------

    update_topic_status(
        topics,
        topic_id,
        "script_processing"
    )

    try:

        # ----------------------------------------------------
        # READ RESEARCH
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # GENERATE SCRIPT
        # ----------------------------------------------------

        print("=" * 70)
        print("GENERATING ORIGINAL TELUGU SCRIPT")
        print("=" * 70)

        script = generate_script(
            topic_id,
            topic_title,
            research
        )

        # ----------------------------------------------------
        # CLEAN
        # ----------------------------------------------------

        script = clean_script(
            script
        )

        script = apply_final_script_rules(
            script
        )

        if len(script) < 500:

            raise RuntimeError(
                "Generated script is suspiciously short"
            )

        print(
            f"SCRIPT CHARACTERS: "
            f"{len(script)}"
        )

        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        output_file = save_script(
            topic_id,
            script
        )

        print(
            f"SCRIPT SAVED: {output_file}"
        )

        # ----------------------------------------------------
        # VERIFY
        # ----------------------------------------------------

        if not output_file.exists():

            raise RuntimeError(
                "Script file was not created"
            )

        file_size = (
            output_file.stat().st_size
        )

        if file_size < 500:

            raise RuntimeError(
                "Script file is suspiciously small"
            )

        # ----------------------------------------------------
        # MARK READY FOR VOICE
        # ----------------------------------------------------

        update_topic_status(
            topics,
            topic_id,
            "script_ready"
        )

        print(
            "STATUS: script_processing -> script_ready"
        )

        print("=" * 70)
        print("TELUGU SCRIPT CREATED SUCCESSFULLY")
        print("=" * 70)

    except Exception as error:

        print("=" * 70)
        print("SCRIPT GENERATION FAILED")
        print("=" * 70)

        print(
            f"ERROR: {error}"
        )

        # Return to researched so the next run
        # can retry script generation.
        try:

            update_topic_status(
                topics,
                topic_id,
                "researched"
            )

            print(
                "STATUS: script_processing -> researched"
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
