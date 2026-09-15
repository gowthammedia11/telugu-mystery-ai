import asyncio
import re
import subprocess
from pathlib import Path

import edge_tts


VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

MIN_SHORT_SECONDS = 45.0
MAX_SHORT_SECONDS = 60.0
TARGET_SHORT_SECONDS = 55.0

SHORT_VOICE = "te-IN-MohanNeural"


def split_sentences(text):
    text = text.replace("\n", " ")

    parts = re.split(
        r"(?<=[.!?।])\s+",
        text
    )

    cleaned = []

    for part in parts:
        part = part.strip()

        if len(part) < 20:
            continue

        cleaned.append(part)

    return cleaned


def clean_sentence(sentence):
    sentence = re.sub(
        r"\s+",
        " ",
        sentence
    )

    return sentence.strip()


def build_highlight_script(
    topic_title,
    long_script
):

    sentences = split_sentences(
        long_script
    )

    if not sentences:
        raise RuntimeError(
            "Unable to split long script into sentences"
        )

    selected = []

    # ========================================================
    # Strong opening
    # ========================================================

    selected.append(
        sentences[0]
    )

    # ========================================================
    # Highlight scoring
    # ========================================================

    keywords = [
        "రహస్యం",
        "మిస్టరీ",
        "ఆశ్చర్య",
        "వింత",
        "శాస్త్రవేత్త",
        "సాక్ష్యం",
        "ఆధారం",
        "పరిశోధన",
        "కనుగొన్నారు",
        "కనుగొన",
        "తెలియదు",
        "మొదటిసారి",
        "అసాధారణ",
        "ప్రశ్న",
        "రహస్యంగా",
        "నిజంగా",
        "సముద్రం",
        "లోతు",
        "నీటిలో",
        "అక్కడ",
        "ఎందుకు",
        "ఎలా",
        "కానీ",
        "అయితే",
    ]

    scored = []

    for index, sentence in enumerate(sentences):

        if index == 0:
            continue

        score = 0

        lower = sentence.lower()

        for keyword in keywords:
            if keyword.lower() in lower:
                score += 2

        if "?" in sentence:
            score += 3

        if len(sentence) >= 50:
            score += 1

        if len(sentence) >= 80:
            score += 1

        scored.append(
            (
                score,
                index,
                sentence
            )
        )

    scored.sort(
        key=lambda item: (
            item[0],
            -item[1]
        ),
        reverse=True
    )

    used_indexes = {0}

    for _, index, sentence in scored:

        if index in used_indexes:
            continue

        selected.append(sentence)
        used_indexes.add(index)

        candidate = " ".join(
            selected
        )

        if len(candidate) >= 850:
            break

    # ========================================================
    # Add a middle fact if still short
    # ========================================================

    if len(" ".join(selected)) < 600:

        middle_index = len(sentences) // 2

        for offset in range(
            0,
            min(10, len(sentences))
        ):

            for index in [
                middle_index - offset,
                middle_index + offset
            ]:

                if (
                    index < 0
                    or index >= len(sentences)
                    or index in used_indexes
                ):
                    continue

                selected.append(
                    sentences[index]
                )

                used_indexes.add(index)

                if len(" ".join(selected)) >= 650:
                    break

            if len(" ".join(selected)) >= 650:
                break

    # ========================================================
    # Natural ending
    # ========================================================

    last_candidates = [
        sentence
        for sentence in sentences[-8:]
        if len(sentence) >= 30
    ]

    if last_candidates:

        last_sentence = last_candidates[-1]

        if last_sentence not in selected:
            selected.append(
                last_sentence
            )

    short_script = " ".join(
        clean_sentence(sentence)
        for sentence in selected
    )

    short_script = re.sub(
        r"\s+",
        " ",
        short_script
    ).strip()

    # ========================================================
    # Keep Short reasonably sized
    # ========================================================

    if len(short_script) > 1100:

        shortened = []

        total = 0

        for sentence in selected:

            sentence = clean_sentence(
                sentence
            )

            if not sentence:
                continue

            if total + len(sentence) + 1 > 1050:
                break

            shortened.append(
                sentence
            )

            total += len(sentence) + 1

        short_script = " ".join(
            shortened
        )

    if len(short_script) < 300:

        raise RuntimeError(
            "Generated Short highlight script is too short"
        )

    print(
        f"SHORT SCRIPT CHARACTERS: "
        f"{len(short_script)}"
    )

    return short_script


async def generate_short_voice(
    script,
    output_file
):

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    communicate = edge_tts.Communicate(
        script,
        SHORT_VOICE
    )

    await communicate.save(
        str(output_file)
    )


def get_duration(media_file):

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(media_file),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    return float(
        result.stdout.strip()
    )


def create_vertical_video(
    long_video,
    short_audio,
    output_video,
    duration
):

    command = [
        "ffmpeg",
        "-y",

        "-stream_loop",
        "-1",

        "-i",
        str(long_video),

        "-i",
        str(short_audio),

        "-t",
        f"{duration:.3f}",

        "-filter_complex",
        (
            "[0:v]"
            "scale=1080:1920:"
            "force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "eq=saturation=1.08:contrast=1.03:brightness=0.02,"
            "setsar=1"
            "[v]"
        ),

        "-map",
        "[v]",

        "-map",
        "1:a:0",

        "-r",
        "30",

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-crf",
        "20",

        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-ar",
        "48000",

        "-ac",
        "2",

        "-movflags",
        "+faststart",

        str(output_video),
    ]

    subprocess.run(
        command,
        check=True
    )


def create_short(
    topic_id,
    topic_title,
    long_script,
    long_video
):

    print("=" * 70)
    print("CREATING YOUTUBE SHORT")
    print("=" * 70)
    print(f"TOPIC: {topic_id}")
    print(f"TITLE: {topic_title}")

    scripts_dir = Path("scripts")
    audio_dir = Path("audio")
    videos_dir = Path("videos")
    metadata_dir = Path("metadata")

    scripts_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    audio_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    videos_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    metadata_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    short_script_file = (
        scripts_dir
        / f"{topic_id}_short.txt"
    )

    short_audio_file = (
        audio_dir
        / f"{topic_id}_short.mp3"
    )

    short_video_file = (
        videos_dir
        / f"{topic_id}_short.mp4"
    )

    short_metadata_file = (
        metadata_dir
        / f"{topic_id}_short.txt"
    )

    # ========================================================
    # SHORT SCRIPT
    # ========================================================

    short_script = build_highlight_script(
        topic_title,
        long_script
    )

    short_script_file.write_text(
        short_script,
        encoding="utf-8"
    )

    print(
        f"SHORT SCRIPT SAVED: "
        f"{short_script_file}"
    )

    # ========================================================
    # SHORT VOICE
    # ========================================================

    print("GENERATING SHORT VOICE")

    asyncio.run(
        generate_short_voice(
            short_script,
            short_audio_file
        )
    )

    if not short_audio_file.exists():
        raise RuntimeError(
            "Short audio was not created"
        )

    short_audio_duration = get_duration(
        short_audio_file
    )

    print(
        f"SHORT AUDIO DURATION: "
        f"{short_audio_duration:.2f}s"
    )

    if short_audio_duration < MIN_SHORT_SECONDS:

        raise RuntimeError(
            f"Short audio is too short: "
            f"{short_audio_duration:.2f}s"
        )

    if short_audio_duration > MAX_SHORT_SECONDS:

        raise RuntimeError(
            f"Short audio is too long: "
            f"{short_audio_duration:.2f}s"
        )

    # ========================================================
    # VERTICAL VIDEO
    # ========================================================

    print("CREATING 9:16 VERTICAL VIDEO")

    create_vertical_video(
        long_video,
        short_audio_file,
        short_video_file,
        short_audio_duration
    )

    if not short_video_file.exists():
        raise RuntimeError(
            "Short video was not created"
        )

    final_duration = get_duration(
        short_video_file
    )

    if final_duration < MIN_SHORT_SECONDS:
        raise RuntimeError(
            f"Short video too short: "
            f"{final_duration:.2f}s"
        )

    if final_duration > MAX_SHORT_SECONDS + 0.5:
        raise RuntimeError(
            f"Short video too long: "
            f"{final_duration:.2f}s"
        )

    # ========================================================
    # SHORT METADATA
    # ========================================================

    short_title = (
        f"{topic_title} | Mystery Explained #Shorts"
    )

    short_description = (
        f"{topic_title} గురించి ముఖ్యమైన విషయాలు "
        f"మరియు ఆసక్తికరమైన ఆధారాలను ఈ Short లో "
        f"సంక్షిప్తంగా తెలుసుకోండి.\n\n"
        f"{short_script}\n\n"
        f"#Shorts #Telugu #Mystery #Science"
    )

    tags = [
        topic_title,
        "Telugu Mystery",
        "Mystery",
        "Science Mystery",
        "Unexplained",
        "Telugu Shorts",
        "Mystery Shorts",
        "Science Shorts",
    ]

    hashtags = [
        "#Shorts",
        "#Telugu",
        "#Mystery",
        "#Science",
    ]

    metadata_text = (
        f"TITLE: {short_title}\n"
        f"DESCRIPTION: {short_description}\n"
        f"TAGS: {', '.join(tags)}\n"
        f"HASHTAGS: {' '.join(hashtags)}\n"
    )

    short_metadata_file.write_text(
        metadata_text,
        encoding="utf-8"
    )

    print(
        f"SHORT METADATA SAVED: "
        f"{short_metadata_file}"
    )

    print("=" * 70)
    print("SHORT CREATED SUCCESSFULLY")
    print("=" * 70)
    print(f"VIDEO: {short_video_file}")
    print(f"DURATION: {final_duration:.2f}s")
    print("RESOLUTION: 1080x1920")
    print("FORMAT: 9:16")
    print("=" * 70)

    return True


if __name__ == "__main__":
    print(
        "Use create_short() from build_pipeline.py"
    )
