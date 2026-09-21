import os
import csv
import re
import time
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

MAX_RETRIES_PER_PART = 3
REQUEST_TIMEOUT = 240

MIN_SCRIPT_CHARACTERS = 4500
TARGET_SCRIPT_CHARACTERS = 5500
MAX_SCRIPT_CHARACTERS = 7500

PART1_MIN_CHARACTERS = 2400
PART1_TARGET_CHARACTERS = 2900
PART1_MAX_CHARACTERS = 3600

PART2_MIN_CHARACTERS = 2400
PART2_TARGET_CHARACTERS = 2900
PART2_MAX_CHARACTERS = 4000

PART_MAX_TOKENS = 5000


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

        if (
            status == "researched"
            and research_file.exists()
        ):
            candidates.append(
                topic
            )

    if not candidates:
        return None

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
# COMMON SCRIPT RULES
# ============================================================

def get_common_script_rules():

    return """
SCRIPT REQUIREMENTS:

1. Write natural, conversational Telugu.
2. Sound like a professional Telugu YouTube documentary.
3. Use ONLY information supported by the research.
4. NEVER invent facts.
5. NEVER invent dates, measurements or discoveries.
6. Clearly distinguish confirmed facts from theories.
7. Never present speculation as confirmed fact.
8. Do not copy sentences from the research.
9. Rewrite everything in original language.
10. Do not mention AI.
11. Do not mention the research material.
12. Do not mention sources inside the narration.
13. Do not use scene directions.
14. Do not use timestamps.
15. Do not use headings.
16. Do not use bullet points.
17. Write ONLY the final narration.
18. Keep the language easy for a general Telugu audience.
19. Avoid unnecessary English words.
20. Scientific terms may use natural Telugu pronunciation where necessary.
21. Do not use filler sentences.
22. Do not repeat the same fact multiple times.
23. Maintain a natural storytelling flow.
24. Use short and medium-length sentences.
25. Create natural pauses using punctuation.
26. Do not exaggerate beyond the evidence.
27. Do not make unsupported claims.
28. The narration must feel like one continuous documentary.
29. End naturally and completely.
"""


# ============================================================
# BUILD PART 1 PROMPT
# ============================================================

def build_part1_prompt(
    topic_id,
    topic_title,
    research
):

    return f"""
You are an expert Telugu YouTube documentary scriptwriter.

Create PART 1 of a completely ORIGINAL Telugu narration
for a mystery, science and unexplained YouTube channel.

TOPIC ID:
{topic_id}

TOPIC:
{topic_title}

============================================================
RESEARCH MATERIAL
============================================================

{research}

============================================================
PART 1 PURPOSE
============================================================

Write approximately {PART1_TARGET_CHARACTERS} Telugu characters.

PART 1 must naturally cover:

- a powerful curiosity-driven opening
- the central mystery or question
- where the subject is located
- when and how it became known
- important historical background
- the first important observations
- confirmed facts
- important evidence

Do NOT finish the entire documentary in Part 1.

Part 1 must end at a natural transition point so that
Part 2 can continue the same documentary.

Do not repeat information unnecessarily.

{get_common_script_rules()}

============================================================
YEAR / NUMBER RULES
============================================================

Years must be written naturally in Telugu words.

Examples:

1930 → పంతొమ్మిది వందల ముప్పై
1990 → పంతొమ్మిది వందల తొంభై
1969 → పంతొమ్మిది వందల అరవై తొమ్మిది
1985 → పంతొమ్మిది వందల ఎనభై ఐదు
2005 → రెండు వేల ఐదు
2002 → రెండు వేల రెండు
2014 → రెండు వేల పద్నాలుగు
2016 → రెండు వేల పదహారు
2020 → రెండు వేల ఇరవై

Never write years digit-by-digit.

Never use miles.

Use kilometers only.

Remove unnecessary trailing zeros from decimal measurements.

Write important numbers naturally in Telugu words whenever practical.

============================================================
IMPORTANT
============================================================

Write ONLY Part 1 narration.

Do not add:
Part 1:
Part 2:
Introduction:
Conclusion:
or any other heading.

Target approximately {PART1_TARGET_CHARACTERS} characters.
Minimum acceptable length: {PART1_MIN_CHARACTERS} characters.
Maximum preferred length: {PART1_MAX_CHARACTERS} characters.
"""


# ============================================================
# BUILD PART 2 PROMPT
# ============================================================

def build_part2_prompt(
    topic_id,
    topic_title,
    research,
    part1
):

    return f"""
You are an expert Telugu YouTube documentary scriptwriter.

Create PART 2 of a completely ORIGINAL Telugu narration.

This is a continuation of an existing documentary about:

TOPIC ID:
{topic_id}

TOPIC:
{topic_title}

============================================================
RESEARCH MATERIAL
============================================================

{research}

============================================================
PART 1 ALREADY WRITTEN
============================================================

{part1}

============================================================
PART 2 PURPOSE
============================================================

Continue naturally from Part 1.

Do NOT restart the story.

Do NOT repeat the opening or background unnecessarily.

Part 2 should naturally cover the remaining important information
supported by the research, including where applicable:

- scientific explanations
- important investigations
- observations
- discoveries
- major evidence
- researchers' findings
- major theories
- why those theories were proposed
- limitations of those theories
- alternative explanations
- what remains unexplained
- what scientists still do not know
- a strong final conclusion

Clearly distinguish confirmed facts from theories.

The final paragraphs must provide a complete,
memorable conclusion.

The ending must NOT feel abrupt.

{get_common_script_rules()}

============================================================
YEAR / NUMBER RULES
============================================================

Years must be written naturally in Telugu words.

Examples:

1930 → పంతొమ్మిది వందల ముప్పై
1990 → పంతొమ్మిది వందల తొంభై
1969 → పంతొమ్మిది వందల అరవై తొమ్మిది
1985 → పంతొమ్మిది వందల ఎనభై ఐదు
2005 → రెండు వేల ఐదు
2002 → రెండు వేల రెండు
2014 → రెండు వేల పద్నాలుగు
2016 → రెండు వేల పదహారు
2020 → రెండు వేల ఇరవై

Never write years digit-by-digit.

Never use miles.

Use kilometers only.

Remove unnecessary trailing zeros from decimal measurements.

Write important numbers naturally in Telugu words whenever practical.

============================================================
IMPORTANT
============================================================

Write ONLY Part 2 narration.

Do not add:
Part 1:
Part 2:
Continuation:
Conclusion:
or any other heading.

Part 2 should be approximately {PART2_TARGET_CHARACTERS} characters.

Minimum acceptable Part 2 length: {PART2_MIN_CHARACTERS} characters.
Maximum preferred Part 2 length: {PART2_MAX_CHARACTERS} characters.

The final sentence must be complete.
"""


# ============================================================
# EXTRACT OPENROUTER SCRIPT
# ============================================================

def extract_script_from_response(
    result
):

    if not isinstance(
        result,
        dict
    ):
        raise RuntimeError(
            "OpenRouter returned an invalid JSON response"
        )

    choices = result.get(
        "choices",
        []
    )

    if not isinstance(
        choices,
        list
    ) or not choices:

        error_info = result.get(
            "error"
        )

        if error_info:
            raise RuntimeError(
                f"OpenRouter returned no choices: "
                f"{error_info}"
            )

        raise RuntimeError(
            "OpenRouter returned no choices"
        )

    first_choice = choices[0]

    if not isinstance(
        first_choice,
        dict
    ):
        raise RuntimeError(
            "OpenRouter returned an invalid choice"
        )

    message = first_choice.get(
        "message"
    )

    if not isinstance(
        message,
        dict
    ):
        raise RuntimeError(
            "OpenRouter returned an invalid message"
        )

    script = message.get(
        "content"
    )

    if isinstance(
        script,
        list
    ):
        text_parts = []

        for item in script:

            if isinstance(
                item,
                dict
            ):

                text = item.get(
                    "text"
                )

                if text:
                    text_parts.append(
                        str(text)
                    )

            elif isinstance(
                item,
                str
            ):

                text_parts.append(
                    item
                )

        script = "".join(
            text_parts
        )

    if script is None:

        refusal = message.get(
            "refusal"
        )

        if refusal:
            raise RuntimeError(
                f"OpenRouter refused the request: "
                f"{refusal}"
            )

        provider = first_choice.get(
            "provider"
        )

        finish_reason = first_choice.get(
            "finish_reason"
        )

        usage = result.get(
            "usage",
            {}
        )

        completion_tokens = None

        if isinstance(
            usage,
            dict
        ):
            completion_tokens = usage.get(
                "completion_tokens"
            )

        raise RuntimeError(
            "OpenRouter returned null script content "
            f"(provider={provider}, "
            f"finish_reason={finish_reason}, "
            f"completion_tokens={completion_tokens})"
        )

    if not isinstance(
        script,
        str
    ):

        script = str(
            script
        )

    script = script.strip()

    if not script:

        raise RuntimeError(
            "OpenRouter returned empty script"
        )

    return script


# ============================================================
# SINGLE OPENROUTER REQUEST
# ============================================================

def request_script_part(
    prompt,
    part_name
):

    api_key = os.environ.get(
        "OPENROUTER_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "OPENROUTER_API_KEY secret is missing"
        )

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES_PER_PART + 1
    ):

        print("=" * 70)

        print(
            f"OPENROUTER {part_name} ATTEMPT: "
            f"{attempt}/{MAX_RETRIES_PER_PART}"
        )

        print(
            f"MODEL: {MODEL}"
        )

        print(
            f"MAX OUTPUT TOKENS: "
            f"{PART_MAX_TOKENS}"
        )

        print("=" * 70)

        try:

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
                                "You are a highly accurate "
                                "Telugu documentary scriptwriter. "
                                "Write only the requested Telugu "
                                "narration. "
                                "Never invent factual information."
                        },

                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],

                    "temperature": 0.45,

                    "max_tokens": PART_MAX_TOKENS,

                    "stream": False
                },

                timeout=REQUEST_TIMEOUT
            )

            print(
                f"OPENROUTER HTTP STATUS: "
                f"{response.status_code}"
            )

            response.raise_for_status()

            try:

                result = response.json()

            except ValueError as error:

                raise RuntimeError(
                    "OpenRouter returned invalid JSON"
                ) from error

            script = extract_script_from_response(
                result
            )

            script_length = len(
                script
            )

            finish_reason = None

            choices = result.get(
                "choices"
            )

            if (
                isinstance(choices, list)
                and choices
                and isinstance(choices[0], dict)
            ):

                finish_reason = choices[0].get(
                    "finish_reason"
                )

            print(
                f"OPENROUTER {part_name} CHARACTERS: "
                f"{script_length}"
            )

            print(
                f"OPENROUTER {part_name} FINISH REASON: "
                f"{finish_reason}"
            )

            if (
                finish_reason == "length"
                and script_length < PART1_MIN_CHARACTERS
            ):

                raise RuntimeError(
                    f"{part_name} was cut short by the "
                    f"provider. Received only "
                    f"{script_length} characters."
                )

            print(
                f"OPENROUTER {part_name} GENERATED SUCCESSFULLY"
            )

            return script

        except Exception as error:

            last_error = error

            print("=" * 70)

            print(
                f"OPENROUTER {part_name} ATTEMPT "
                f"{attempt} FAILED"
            )

            print(
                f"ERROR: {error}"
            )

            print("=" * 70)

            if attempt < MAX_RETRIES_PER_PART:

                wait_seconds = (
                    5 * attempt
                )

                print(
                    f"RETRYING IN "
                    f"{wait_seconds} SECONDS..."
                )

                time.sleep(
                    wait_seconds
                )

    raise RuntimeError(
        f"OpenRouter {part_name} generation failed "
        f"after {MAX_RETRIES_PER_PART} attempts. "
        f"Last error: {last_error}"
    )


# ============================================================
# GENERATE TELUGU SCRIPT
# ============================================================

def generate_script(
    topic_id,
    topic_title,
    research
):

    print("=" * 70)

    print(
        "GENERATING SCRIPT IN TWO PARTS"
    )

    print("=" * 70)

    part1_prompt = build_part1_prompt(
        topic_id,
        topic_title,
        research
    )

    part1 = request_script_part(
        part1_prompt,
        "PART 1"
    )

    part1 = clean_script(
        part1
    )

    part1_length = len(
        part1
    )

    print(
        f"PART 1 FINAL CHARACTERS: "
        f"{part1_length}"
    )

    if part1_length < PART1_MIN_CHARACTERS:

        raise RuntimeError(
            f"Part 1 is too short: "
            f"{part1_length} characters. "
            f"Minimum required: "
            f"{PART1_MIN_CHARACTERS}."
        )

    part2_prompt = build_part2_prompt(
        topic_id,
        topic_title,
        research,
        part1
    )

    part2 = request_script_part(
        part2_prompt,
        "PART 2"
    )

    part2 = clean_script(
        part2
    )

    part2_length = len(
        part2
    )

    print(
        f"PART 2 FINAL CHARACTERS: "
        f"{part2_length}"
    )

    if part2_length < PART2_MIN_CHARACTERS:

        raise RuntimeError(
            f"Part 2 is too short: "
            f"{part2_length} characters. "
            f"Minimum required: "
            f"{PART2_MIN_CHARACTERS}."
        )

    final_script = (
        part1.strip()
        + "\n\n"
        + part2.strip()
    )

    final_script = clean_script(
        final_script
    )

    final_length = len(
        final_script
    )

    print("=" * 70)

    print(
        f"COMBINED SCRIPT CHARACTERS: "
        f"{final_length}"
    )

    print("=" * 70)

    if final_length < MIN_SCRIPT_CHARACTERS:

        raise RuntimeError(
            f"Combined script is too short: "
            f"{final_length} characters. "
            f"Minimum required: "
            f"{MIN_SCRIPT_CHARACTERS}."
        )

    if final_length > MAX_SCRIPT_CHARACTERS:

        print(
            f"WARNING: Combined script is longer than "
            f"preferred maximum "
            f"{MAX_SCRIPT_CHARACTERS} characters."
        )

    return final_script


# ============================================================
# CLEAN GENERATED SCRIPT
# ============================================================

def clean_script(
    script
):

    if script is None:

        raise RuntimeError(
            "Cannot clean a None script"
        )

    if not isinstance(
        script,
        str
    ):

        script = str(
            script
        )

    script = script.replace(
        "```text",
        ""
    )

    script = script.replace(
        "```",
        ""
    )

    lines = []

    for line in script.splitlines():

        line = line.strip()

        if not line:
            continue

        if line.startswith(
            "#"
        ):

            line = line.lstrip(
                "#"
            ).strip()

        lines.append(
            line
        )

    script = "\n".join(
        lines
    )

    script = script.strip()

    if not script:

        raise RuntimeError(
            "Script became empty after cleaning"
        )

    return script


# ============================================================
# FINAL SCRIPT RULE NORMALIZATION
# ============================================================

ONES_TELUGU = {

    0: "సున్నా",
    1: "ఒకటి",
    2: "రెండు",
    3: "మూడు",
    4: "నాలుగు",
    5: "ఐదు",
    6: "ఆరు",
    7: "ఏడు",
    8: "ఎనిమిది",
    9: "తొమ్మిది",
}


TENS_TELUGU = {

    20: "ఇరవై",
    30: "ముప్పై",
    40: "నలభై",
    50: "యాభై",
    60: "అరవై",
    70: "డెబ్బై",
    80: "ఎనభై",
    90: "తొంభై",
}


NUM_10_19 = {

    10: "పది",
    11: "పదకొండు",
    12: "పన్నెండు",
    13: "పదమూడు",
    14: "పద్నాలుగు",
    15: "పదిహేను",
    16: "పదహారు",
    17: "పదిహేడు",
    18: "పద్దెనిమిది",
    19: "పంతొమ్మిది",
}


def number_to_telugu_script(
    number
):

    number = int(
        number
    )

    if number < 10:

        return ONES_TELUGU[
            number
        ]

    if number < 20:

        return NUM_10_19[
            number
        ]

    if number < 100:

        tens = (
            number // 10
        ) * 10

        ones = (
            number % 10
        )

        return (

            TENS_TELUGU[
                tens
            ]

            if ones == 0

            else

            f"{TENS_TELUGU[tens]} "
            f"{ONES_TELUGU[ones]}"
        )

    if number < 1000:

        hundreds = (
            number // 100
        )

        remainder = (
            number % 100
        )

        result = (

            "వంద"

            if hundreds == 1

            else

            f"{ONES_TELUGU[hundreds]} వందల"
        )

        return (

            result

            if remainder == 0

            else

            f"{result} "
            f"{number_to_telugu_script(remainder)}"
        )

    if number < 10000:

        thousands = (
            number // 1000
        )

        remainder = (
            number % 1000
        )

        result = (

            "వెయ్యి"

            if thousands == 1

            else

            f"{number_to_telugu_script(thousands)} వేల"
        )

        return (

            result

            if remainder == 0

            else

            f"{result} "
            f"{number_to_telugu_script(remainder)}"
        )

    return str(
        number
    )


def year_to_telugu_script(
    year
):

    year = int(
        year
    )

    if 1900 <= year <= 1999:

        remainder = (
            year - 1900
        )

        return (

            "పంతొమ్మిది వందలు"

            if remainder == 0

            else

            f"పంతొమ్మిది వందల "
            f"{number_to_telugu_script(remainder)}"
        )

    if 1800 <= year <= 1899:

        remainder = (
            year - 1800
        )

        return (

            "పద్దెనిమిది వందలు"

            if remainder == 0

            else

            f"పద్దెనిమిది వందల "
            f"{number_to_telugu_script(remainder)}"
        )

    if 2000 <= year <= 2099:

        remainder = (
            year - 2000
        )

        return (

            "రెండు వేల"

            if remainder == 0

            else

            f"రెండు వేల "
            f"{number_to_telugu_script(remainder)}"
        )

    return number_to_telugu_script(
        year
    )


def apply_final_script_rules(
    script
):

    if script is None:

        raise RuntimeError(
            "Cannot apply script rules to None"
        )

    if not isinstance(
        script,
        str
    ):

        script = str(
            script
        )

    script = re.sub(
        r"\b(19\d{2}|18\d{2}|20\d{2})\b",

        lambda match:
            year_to_telugu_script(
                match.group(1)
            ),

        script,
    )

    def miles_to_km(
        match
    ):

        km = round(
            float(
                match.group(1)
            ) * 1.60934
        )

        return (
            f"{number_to_telugu_script(km)} "
            "కిలోమీటర్లు"
        )

    script = re.sub(
        r"\b(\d+(?:\.\d+)?)\s*(?:miles?|mi\.?)\b",

        miles_to_km,

        script,

        flags=re.IGNORECASE,
    )

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

    script = script.strip()

    if not script:

        raise RuntimeError(
            "Final script is empty"
        )

    return script


# ============================================================
# SAVE SCRIPT
# ============================================================

def save_script(
    topic_id,
    script
):

    if script is None:

        raise RuntimeError(
            "Cannot save None script"
        )

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

    print(
        "TELUGU MYSTERY AI - SCRIPT GENERATOR"
    )

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

    update_topic_status(
        topics,
        topic_id,
        "script_processing"
    )

    try:

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

        print("=" * 70)

        print(
            "GENERATING ORIGINAL TELUGU SCRIPT"
        )

        print("=" * 70)

        script = generate_script(
            topic_id,
            topic_title,
            research
        )

        if script is None:

            raise RuntimeError(
                "generate_script returned None"
            )

        script = clean_script(
            script
        )

        if script is None:

            raise RuntimeError(
                "clean_script returned None"
            )

        script = apply_final_script_rules(
            script
        )

        if script is None:

            raise RuntimeError(
                "apply_final_script_rules returned None"
            )

        script_length = len(
            script
        )

        print(
            f"SCRIPT CHARACTERS: "
            f"{script_length}"
        )

        if script_length < MIN_SCRIPT_CHARACTERS:

            raise RuntimeError(
                f"Generated script is too short. "
                f"Got {script_length} characters. "
                f"Minimum required: "
                f"{MIN_SCRIPT_CHARACTERS} characters."
            )

        if script_length < TARGET_SCRIPT_CHARACTERS:

            print(
                f"WARNING: Script is below preferred "
                f"{TARGET_SCRIPT_CHARACTERS} characters."
            )

        output_file = save_script(
            topic_id,
            script
        )

        print(
            f"SCRIPT SAVED: {output_file}"
        )

        if not output_file.exists():

            raise RuntimeError(
                "Script file was not created"
            )

        file_size = (
            output_file.stat().st_size
        )

        if file_size < MIN_SCRIPT_CHARACTERS:

            raise RuntimeError(
                "Script file is suspiciously small"
            )

        update_topic_status(
            topics,
            topic_id,
            "script_ready"
        )

        print(
            "STATUS: "
            "script_processing -> script_ready"
        )

        print("=" * 70)

        print(
            "TELUGU SCRIPT CREATED SUCCESSFULLY"
        )

        print("=" * 70)

    except Exception as error:

        print("=" * 70)

        print(
            "SCRIPT GENERATION FAILED"
        )

        print("=" * 70)

        print(
            f"ERROR: {error}"
        )

        try:

            update_topic_status(
                topics,
                topic_id,
                "researched"
            )

            print(
                "STATUS: "
                "script_processing -> researched"
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
