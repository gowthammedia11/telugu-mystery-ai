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

REQUEST_TIMEOUT = 240

MIN_SCRIPT_CHARACTERS = 4500
TARGET_SCRIPT_CHARACTERS = 5500
MAX_SCRIPT_CHARACTERS = 7500

CHUNK_TARGET_CHARACTERS = 1800
CHUNK_MIN_CHARACTERS = 900
MAX_CHUNKS = 5

MAX_RETRIES_PER_CHUNK = 3
CHUNK_MAX_TOKENS = 3500


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

def common_script_rules():

    return """
Write natural, conversational Telugu.

The narration must sound like a professional
Telugu YouTube documentary.

Use ONLY information supported by the research.

NEVER invent:
- facts
- dates
- measurements
- discoveries
- locations
- people
- scientific claims

Clearly distinguish confirmed facts from theories.

Never present speculation as confirmed fact.

Do not copy sentences from the research.

Rewrite everything in original language.

Do not mention AI.

Do not mention the research material.

Do not mention sources inside the narration.

Do not use scene directions.

Do not use timestamps.

Do not use headings.

Do not use bullet points.

Write ONLY the narration.

Keep the language easy for a general Telugu audience.

Avoid unnecessary English words.

Scientific terms may use natural Telugu pronunciation
where necessary.

Do not use filler sentences.

Do not repeat the same fact unnecessarily.

Maintain a natural storytelling flow.

Use short and medium-length sentences.

Create natural pauses using punctuation.

Do not exaggerate beyond the evidence.

Do not make unsupported claims.

The narration must feel like a human Telugu
documentary storyteller.

Every generated continuation must connect naturally
with the previous narration.

Never restart the story.

Never repeat the opening.

Never suddenly change the subject.

The final ending must be complete and memorable.
"""


# ============================================================
# BUILD INITIAL CHUNK PROMPT
# ============================================================

def build_initial_prompt(
    topic_id,
    topic_title,
    research
):

    return f"""
You are an expert Telugu YouTube documentary scriptwriter.

Create the BEGINNING of a long Telugu documentary narration.

TOPIC ID:
{topic_id}

TOPIC:
{topic_title}

============================================================
RESEARCH
============================================================

{research}

============================================================
TASK
============================================================

Write the first approximately
{CHUNK_TARGET_CHARACTERS} Telugu characters.

Start with a strong curiosity-driven opening.

Then naturally introduce:

- the central mystery
- where it is located
- when it became known
- important background
- confirmed observations
- important evidence

Do NOT try to finish the whole documentary yet.

Do NOT write a conclusion.

End at a natural point where another narration segment
can continue the story.

{common_script_rules()}

============================================================
YEAR AND NUMBER RULES
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

Write important numbers naturally in Telugu words
whenever practical.

Write ONLY the narration.
Do not add a heading.
"""


# ============================================================
# BUILD CONTINUATION PROMPT
# ============================================================

def build_continuation_prompt(
    topic_id,
    topic_title,
    research,
    current_script,
    chunk_number,
    is_final
):

    if is_final:

        task = f"""
This is the FINAL continuation.

Continue the documentary naturally and bring the story
to a strong, complete conclusion.

Cover remaining important research-supported information
such as:

- scientific explanations
- investigations
- observations
- discoveries
- evidence
- major theories
- why those theories were proposed
- limitations of those theories
- alternative explanations
- what remains unexplained
- what scientists still do not know

Then conclude naturally.

The ending must feel complete.

Do not restart the story.
Do not repeat the opening.
Do not summarize the entire story again.
"""

    else:

        task = f"""
Continue the documentary naturally.

This is continuation chunk {chunk_number}.

Move the story forward using NEW information from the research.

Depending on what remains, cover:

- background details
- confirmed evidence
- investigations
- scientific observations
- discoveries
- scientific explanations
- major theories
- evidence supporting theories
- limitations of theories
- unresolved questions

Do not finish the entire documentary yet.

Do not restart the story.
Do not repeat information already covered.
End at a natural continuation point.
"""

    return f"""
You are an expert Telugu YouTube documentary scriptwriter.

Continue an existing Telugu documentary.

TOPIC ID:
{topic_id}

TOPIC:
{topic_title}

============================================================
RESEARCH
============================================================

{research}

============================================================
CURRENT NARRATION
============================================================

{current_script}

============================================================
TASK
============================================================

{task}

Write approximately
{CHUNK_TARGET_CHARACTERS} Telugu characters.

{common_script_rules()}

============================================================
YEAR AND NUMBER RULES
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

Write important numbers naturally in Telugu words
whenever practical.

============================================================
IMPORTANT
============================================================

Write ONLY the new continuation.

Do NOT repeat the CURRENT NARRATION.

Do NOT include the current narration in your answer.

Do NOT add headings.

Do NOT add labels.

Do NOT say "continuation".

Do NOT say "part".

Write only the new Telugu narration.
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

        raise RuntimeError(
            "OpenRouter returned null script content "
            f"(provider={provider}, "
            f"finish_reason={finish_reason})"
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

    return (
        script,
        first_choice.get(
            "finish_reason"
        )
    )


# ============================================================
# REQUEST ONE CHUNK
# ============================================================

def request_script_chunk(
    prompt,
    chunk_number
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
        MAX_RETRIES_PER_CHUNK + 1
    ):

        print("=" * 70)

        print(
            f"OPENROUTER CHUNK {chunk_number} "
            f"ATTEMPT: "
            f"{attempt}/{MAX_RETRIES_PER_CHUNK}"
        )

        print(
            f"MODEL: {MODEL}"
        )

        print(
            f"TARGET CHUNK CHARACTERS: "
            f"{CHUNK_TARGET_CHARACTERS}"
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

                    "max_tokens": CHUNK_MAX_TOKENS,

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

            script, finish_reason = (
                extract_script_from_response(
                    result
                )
            )

            script_length = len(
                script
            )

            print(
                f"OPENROUTER CHUNK {chunk_number} "
                f"CHARACTERS: "
                f"{script_length}"
            )

            print(
                f"OPENROUTER CHUNK {chunk_number} "
                f"FINISH REASON: "
                f"{finish_reason}"
            )

            if script_length < CHUNK_MIN_CHARACTERS:

                raise RuntimeError(
                    f"Chunk {chunk_number} is too short: "
                    f"{script_length} characters. "
                    f"Minimum required: "
                    f"{CHUNK_MIN_CHARACTERS}."
                )

            print(
                f"OPENROUTER CHUNK {chunk_number} "
                f"GENERATED SUCCESSFULLY"
            )

            return script

        except Exception as error:

            last_error = error

            print("=" * 70)

            print(
                f"OPENROUTER CHUNK {chunk_number} "
                f"ATTEMPT {attempt} FAILED"
            )

            print(
                f"ERROR: {error}"
            )

            print("=" * 70)

            if attempt < MAX_RETRIES_PER_CHUNK:

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
        f"OpenRouter chunk {chunk_number} generation "
        f"failed after "
        f"{MAX_RETRIES_PER_CHUNK} attempts. "
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
        "GENERATING LONG TELUGU SCRIPT IN CHUNKS"
    )

    print("=" * 70)

    current_script = ""

    # --------------------------------------------------------
    # CHUNK 1
    # --------------------------------------------------------

    initial_prompt = build_initial_prompt(
        topic_id,
        topic_title,
        research
    )

    chunk = request_script_chunk(
        initial_prompt,
        1
    )

    chunk = clean_script(
        chunk
    )

    current_script = chunk

    print(
        f"TOTAL SCRIPT CHARACTERS AFTER CHUNK 1: "
        f"{len(current_script)}"
    )

    # --------------------------------------------------------
    # CONTINUATIONS
    # --------------------------------------------------------

    chunk_number = 2

    while (
        len(current_script)
        < TARGET_SCRIPT_CHARACTERS
        and chunk_number <= MAX_CHUNKS
    ):

        remaining = (
            TARGET_SCRIPT_CHARACTERS
            - len(current_script)
        )

        print("=" * 70)

        print(
            f"CURRENT SCRIPT LENGTH: "
            f"{len(current_script)}"
        )

        print(
            f"REMAINING TARGET: "
            f"{remaining}"
        )

        print(
            f"CREATING CONTINUATION CHUNK: "
            f"{chunk_number}"
        )

        print("=" * 70)

        is_final = (
            len(current_script)
            >= TARGET_SCRIPT_CHARACTERS - 700
        )

        continuation_prompt = build_continuation_prompt(
            topic_id,
            topic_title,
            research,
            current_script,
            chunk_number,
            is_final
        )

        continuation = request_script_chunk(
            continuation_prompt,
            chunk_number
        )

        continuation = clean_script(
            continuation
        )

        current_script = (
            current_script.rstrip()
            + "\n\n"
            + continuation.lstrip()
        )

        current_script = clean_script(
            current_script
        )

        print(
            f"TOTAL SCRIPT CHARACTERS AFTER CHUNK "
            f"{chunk_number}: "
            f"{len(current_script)}"
        )

        chunk_number += 1

    # --------------------------------------------------------
    # FINAL LENGTH CHECK
    # --------------------------------------------------------

    current_script = clean_script(
        current_script
    )

    final_length = len(
        current_script
    )

    print("=" * 70)

    print(
        f"FINAL GENERATED SCRIPT CHARACTERS: "
        f"{final_length}"
    )

    print("=" * 70)

    if final_length < MIN_SCRIPT_CHARACTERS:

        raise RuntimeError(
            f"Generated script is too short: "
            f"{final_length} characters. "
            f"Minimum required: "
            f"{MIN_SCRIPT_CHARACTERS}."
        )

    if final_length > MAX_SCRIPT_CHARACTERS:

        print(
            f"WARNING: Generated script is longer than "
            f"preferred maximum "
            f"{MAX_SCRIPT_CHARACTERS} characters."
        )

    print(
        "LONG TELUGU SCRIPT GENERATED SUCCESSFULLY"
    )

    return current_script


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
# TELUGU NUMBER WORDS
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


# ============================================================
# NUMBER TO TELUGU
# ============================================================

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

        if ones == 0:

            return TENS_TELUGU[
                tens
            ]

        return (
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

        if hundreds == 1:

            result = "వంద"

        else:

            result = (
                f"{ONES_TELUGU[hundreds]} వందల"
            )

        if remainder == 0:

            return result

        return (
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

        if thousands == 1:

            result = "వెయ్యి"

        else:

            result = (
                f"{number_to_telugu_script(thousands)} వేల"
            )

        if remainder == 0:

            return result

        return (
            f"{result} "
            f"{number_to_telugu_script(remainder)}"
        )

    return str(
        number
    )


# ============================================================
# YEAR TO TELUGU
# ============================================================

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

        if remainder == 0:

            return "పంతొమ్మిది వందలు"

        return (
            f"పంతొమ్మిది వందల "
            f"{number_to_telugu_script(remainder)}"
        )

    if 1800 <= year <= 1899:

        remainder = (
            year - 1800
        )

        if remainder == 0:

            return "పద్దెనిమిది వందలు"

        return (
            f"పద్దెనిమిది వందల "
            f"{number_to_telugu_script(remainder)}"
        )

    if 2000 <= year <= 2099:

        remainder = (
            year - 2000
        )

        if remainder == 0:

            return "రెండు వేల"

        return (
            f"రెండు వేల "
            f"{number_to_telugu_script(remainder)}"
        )

    return number_to_telugu_script(
        year
    )


# ============================================================
# FINAL SCRIPT RULE NORMALIZATION
# ============================================================

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

    # --------------------------------------------------------
    # YEARS
    # --------------------------------------------------------

    script = re.sub(
        r"\b(19\d{2}|18\d{2}|20\d{2})\b",

        lambda match:
            year_to_telugu_script(
                match.group(1)
            ),

        script
    )

    # --------------------------------------------------------
    # MILES TO KILOMETERS
    # --------------------------------------------------------

    def miles_to_km(
        match
    ):

        value = float(
            match.group(1)
        )

        km = round(
            value * 1.60934
        )

        return (
            f"{number_to_telugu_script(km)} "
            "కిలోమీటర్లు"
        )

    script = re.sub(
        r"\b(\d+(?:\.\d+)?)\s*(?:miles?|mi\.?)\b",

        miles_to_km,

        script,

        flags=re.IGNORECASE
    )

    # --------------------------------------------------------
    # REMOVE TRAILING DECIMAL ZEROES
    # --------------------------------------------------------

    script = re.sub(
        r"\b(\d+)\.(\d*?[1-9])0+\b",
        r"\1.\2",
        script
    )

    script = re.sub(
        r"\b(\d+)\.0+\b",
        r"\1",
        script
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

        script = apply_final_script_rules(
            script
        )

        script_length = len(
            script
        )

        print(
            f"SCRIPT CHARACTERS AFTER NORMALIZATION: "
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
