import os
import re
import asyncio
from pathlib import Path

import edge_tts


def normalize_for_telugu_tts(text):

    if not text:
        return text

    # Keep your existing PRONUNCIATION_MAP above this function.

    replacements = sorted(
        PRONUNCIATION_MAP.items(),
        key=lambda item: len(item[0]),
        reverse=True
    )

    for original, replacement in replacements:

        text = re.sub(
            r"(?<![A-Za-z])"
            + re.escape(original)
            + r"(?![A-Za-z])",
            replacement,
            text,
            flags=re.IGNORECASE
        )

    # Years
    def replace_year(match):
        year = int(match.group(0))
        return year_to_telugu(year)

    text = re.sub(
        r"\b(?:1[6-9][0-9]{2}|20[0-9]{2})\b",
        replace_year,
        text
    )

    # Numeric ranges
    def replace_numeric_range(match):
        first = int(match.group(1))
        second = int(match.group(2))

        return (
            f"{number_to_telugu(first)} "
            f"నుంచి "
            f"{number_to_telugu(second)}"
        )

    text = re.sub(
        r"\b(\d+)\s*[-–]\s*(\d+)\b",
        replace_numeric_range,
        text
    )

    # Remaining numbers
    def replace_number(match):
        number = int(match.group(0))
        return number_to_telugu(number)

    text = re.sub(
        r"\b\d+\b",
        replace_number,
        text
    )

    text = text.replace(
        "```",
        ""
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


async def generate_voice(topic_id):

    script_file = Path(
        f"scripts/{topic_id}.txt"
    )

    output_file = Path(
        f"audio/{topic_id}.mp3"
    )

    if not script_file.exists():
        raise RuntimeError(
            f"Script not found: {script_file}"
        )

    text = script_file.read_text(
        encoding="utf-8"
    ).strip()

    if not text:
        raise RuntimeError(
            "Script is empty"
        )

    normalized_text = normalize_for_telugu_tts(text)

    if not normalized_text:
        raise RuntimeError(
            "Normalized script is empty"
        )

    Path("audio").mkdir(
        parents=True,
        exist_ok=True
    )

    if output_file.exists():
        output_file.unlink()

    voice = "te-IN-MohanNeural"

    print("=" * 70)
    print("VOICE GENERATION")
    print(f"TOPIC: {topic_id}")
    print(f"SCRIPT: {script_file}")
    print(f"OUTPUT: {output_file}")
    print(f"VOICE: {voice}")
    print("=" * 70)

    communicate = edge_tts.Communicate(
        text=normalized_text,
        voice=voice,
        rate="+0%",
        volume="+0%"
    )

    await communicate.save(
        str(output_file)
    )

    if not output_file.exists():
        raise RuntimeError(
            "MP3 was not created"
        )

    file_size = output_file.stat().st_size

    if file_size < 1000:
        raise RuntimeError(
            "Generated audio file is too small"
        )

    print(
        f"VOICE CREATED: {output_file}"
    )

    return output_file


def run(topic_id):

    return asyncio.run(
        generate_voice(topic_id)
    )


if __name__ == "__main__":

    topic_id = os.environ.get(
        "PIPELINE_TOPIC_ID"
    )

    if not topic_id:
        raise SystemExit(
            "PIPELINE_TOPIC_ID is required"
        )

    run(topic_id)
