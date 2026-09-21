import asyncio
import re
import subprocess
from pathlib import Path

import edge_tts


VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

MIN_SHORT_SECONDS = 45.0
MAX_SHORT_SECONDS = 60.0
TARGET_SHORT_SECONDS = 52.0

SHORT_VOICE = "te-IN-MohanNeural"


def split_sentences(text):
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()

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


def score_sentence(sentence, index):
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
        "నిరూపణ",
        "వివాదం",
        "వివాదాస్పద",
        "సిద్ధాంతం",
        "పరిష్కారం",
    ]

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

    if index <= 2:
        score += 2

    return score


def build_highlight_script(
    topic_title,
    long_script,
    target_characters=700
):
    sentences = split_sentences(
        long_script
    )

    if not sentences:
        raise RuntimeError(
            "Unable to split long script into sentences"
        )

    if len(sentences) < 3:
        raise RuntimeError(
            "Long script does not contain enough sentences"
        )

    scored = []

    for index, sentence in enumerate(sentences):
        scored.append(
            (
                score_sentence(
                    sentence,
                    index
                ),
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

    selected_indexes = []

    selected_indexes.append(0)

    if len(sentences) > 1:
        selected_indexes.append(1)

    for _, index, _ in scored:

        if index in selected_indexes:
            continue

        selected_indexes.append(index)

        candidate_indexes = sorted(
            selected_indexes
        )

        candidate = " ".join(
            clean_sentence(
                sentences[i]
            )
            for i in candidate_indexes
        )

        if len(candidate) >= target_characters:
            break

    selected_indexes = sorted(
        set(selected_indexes)
    )

    short_script = " ".join(
        clean_sentence(
            sentences[i]
        )
        for i in selected_indexes
    )

    short_script = re.sub(
        r"\s+",
        " ",
        short_script
    ).strip()

    if len(short_script) < 300:

        for index in range(
            2,
            len(sentences)
        ):

            if index in selected_indexes:
                continue

            selected_indexes.append(
                index
            )

            selected_indexes.sort()

            short_script = " ".join(
                clean_sentence(
                    sentences[i]
                )
                for i in selected_indexes
            )

            if len(short_script) >= 300:
                break

    print(
        f"SHORT SCRIPT CHARACTERS: "
        f"{len(short_script)}"
    )

    return short_script


async def generate_short_voice(
    script,
    output_file,
    rate="+0%"
):
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if output_file.exists():
        output_file.unlink()

    communicate = edge_tts.Communicate(
        script,
        SHORT_VOICE,
        rate=rate
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
    output_video.parent.mkdir(
        parents=True,
        exist_ok=True
    )

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


def generate_valid_short_audio(
    long_script,
    short_audio_file,
    short_script_file
):
    target_sizes = [
        600,
        650,
        700,
        750,
        800,
    ]

    rates = [
        "+0%",
        "-5%",
        "-10%",
        "+5%",
        "+10%",
        "+15%",
        "+20%",
    ]

    best_result = None

    for target_size in target_sizes:

        short_script = build_highlight_script(
            "",
            long_script,
            target_characters=target_size
        )

        for rate in rates:

            print(
                f"TESTING SHORT: "
                f"{len(short_script)} chars "
                f"at TTS rate {rate}"
            )

            asyncio.run(
                generate_short_voice(
                    short_script,
                    short_audio_file,
                    rate
                )
            )

            duration = get_duration(
                short_audio_file
            )

            print(
                f"SHORT AUDIO TEST: "
                f"{duration:.2f}s"
            )

            distance = abs(
                TARGET_SHORT_SECONDS
                - duration
            )

            if (
                best_result is None
                or distance < best_result["distance"]
            ):
                best_result = {
                    "script": short_script,
                    "duration": duration,
                    "distance": distance,
                    "rate": rate,
                }

            if (
                MIN_SHORT_SECONDS
                <= duration
                <= MAX_SHORT_SECONDS
            ):

                short_script_file.write_text(
                    short_script,
                    encoding="utf-8"
                )

                print(
                    f"VALID SHORT FOUND: "
                    f"{duration:.2f}s"
                )

                return (
                    short_script,
                    duration,
                    rate
                )

    if best_result is not None:

        short_script_file.write_text(
            best_result["script"],
            encoding="utf-8"
        )

        if (
            MIN_SHORT_SECONDS
            <= best_result["duration"]
            <= MAX_SHORT_SECONDS
        ):
            return (
                best_result["script"],
                best_result["duration"],
                best_result["rate"]
            )

    raise RuntimeError(
        "Unable to generate a Short audio between "
        "45 and 60 seconds."
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

    if not Path(long_video).exists():
        raise RuntimeError(
            f"Long video not found: {long_video}"
        )

    if not long_script.strip():
        raise RuntimeError(
            "Long script is empty"
        )

    print("GENERATING SHORT HIGHLIGHTS")

    short_script, short_audio_duration, tts_rate = (
        generate_valid_short_audio(
            long_script,
            short_audio_file,
            short_script_file
        )
    )

    print(
        f"SHORT SCRIPT SAVED: "
        f"{short_script_file}"
    )

    print(
        f"SHORT SCRIPT CHARACTERS: "
        f"{len(short_script)}"
    )

    print(
        f"SHORT TTS RATE: "
        f"{tts_rate}"
    )

    print(
        f"SHORT AUDIO DURATION: "
        f"{short_audio_duration:.2f}s"
    )

    if not (
        MIN_SHORT_SECONDS
        <= short_audio_duration
        <= MAX_SHORT_SECONDS
    ):
        raise RuntimeError(
            f"Short audio duration is outside "
            f"45-60 seconds: "
            f"{short_audio_duration:.2f}s"
        )

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

    print(
        f"SHORT VIDEO DURATION: "
        f"{final_duration:.2f}s"
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
