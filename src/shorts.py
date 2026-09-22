import asyncio
import re
import subprocess
from pathlib import Path

import edge_tts


VOICE = "te-IN-MohanNeural"

SHORT_MIN_SECONDS = 45
SHORT_MAX_SECONDS = 60

SCRIPTS_DIR = Path("scripts")
AUDIO_DIR = Path("audio")
VIDEOS_DIR = Path("videos")
METADATA_DIR = Path("metadata")
MUSIC_DIR = Path("assets/music")


HIGHLIGHT_WORDS = [
    "మిస్టరీ",
    "రహస్యం",
    "అయితే",
    "కానీ",
    "శాస్త్ర",
    "పరిశోధ",
    "కనుగొ",
    "ఆధారం",
    "సాక్ష్యం",
    "తెలియదు",
    "ఎందుకు",
    "నిజం",
    "వివాద",
    "సిద్ధాంతం",
    "అసాధారణ",
    "ఆశ్చర్య",
    "ప్రశ్న",
    "కారణం",
    "సముద్రం",
    "లోతు",
    "శాస్త్రవేత్త",
]


def valid_file(path):

    return (
        path.exists()
        and path.is_file()
        and path.stat().st_size > 0
    )


def split_sentences(text):

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    parts = re.split(
        r"(?<=[.!?।])\s+",
        text
    )

    return [
        part.strip()
        for part in parts
        if len(part.strip()) >= 20
    ]


def score_sentence(
    sentence,
    index
):

    score = 0

    if index == 0:
        score += 12

    elif index == 1:
        score += 8

    if 50 <= len(sentence) <= 280:
        score += 3

    if "?" in sentence:
        score += 5

    for word in HIGHLIGHT_WORDS:

        if word in sentence:
            score += 4

    return score


def create_highlight_selection(
    sentences
):

    scores = [
        (
            score_sentence(
                sentence,
                index
            ),
            index
        )
        for index, sentence
        in enumerate(sentences)
    ]

    selected = [0]

    if len(sentences) > 1:
        selected.append(1)

    for _, index in sorted(
        scores[2:],
        key=lambda item: (
            -item[0],
            item[1]
        )
    ):

        if index not in selected:
            selected.append(index)

        if len(selected) >= 9:
            break

    return sorted(
        set(selected)
    )


def make_text(
    sentences,
    indices
):

    return " ".join(
        sentences[index]
        for index in indices
    ).strip()


async def generate_tts(
    text,
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
        text,
        VOICE,
        rate=rate
    )

    await communicate.save(
        str(output_file)
    )


def get_audio_duration(
    path
):

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True
    )

    return float(
        result.stdout.strip()
    )


def find_music():

    if not MUSIC_DIR.exists():
        return None

    files = []

    for pattern in (
        "*.mp3",
        "*.wav",
        "*.m4a",
    ):
        files.extend(
            MUSIC_DIR.glob(pattern)
        )

    if not files:
        return None

    return sorted(files)[0]


def create_short_metadata(
    topic_id
):

    source = (
        METADATA_DIR
        / f"{topic_id}.txt"
    )

    output = (
        METADATA_DIR
        / f"{topic_id}_short.txt"
    )

    if not valid_file(source):
        raise RuntimeError(
            f"Long metadata missing: {source}"
        )

    text = source.read_text(
        encoding="utf-8"
    )

    title = ""
    description_lines = []
    tags = ""
    hashtags = ""

    current = None

    for line in text.splitlines():

        stripped = line.strip()
        upper = stripped.upper()

        if upper.startswith("TITLE:"):
            title = stripped[6:].strip()
            current = "title"
            continue

        if upper.startswith("DESCRIPTION:"):
            description_lines = [
                stripped[12:].strip()
            ]
            current = "description"
            continue

        if upper.startswith("TAGS:"):
            tags = stripped[5:].strip()
            current = "tags"
            continue

        if upper.startswith("HASHTAGS:"):
            hashtags = stripped[9:].strip()
            current = "hashtags"
            continue

        if current == "description":
            description_lines.append(
                stripped
            )

    description = "\n".join(
        item
        for item in description_lines
        if item
    ).strip()

    if not title:
        title = f"Telugu Mystery {topic_id}"

    if "#Shorts" not in title.lower():
        title = title[:91].rstrip()
        title += " #Shorts"

    required_hashtags = [
        "#TeluguMystery",
        "#Mystery",
        "#Science",
        "#Unexplained",
        "#Shorts",
    ]

    hashtag_text = (
        hashtags
        + " "
        + " ".join(required_hashtags)
    )

    final_hashtags = []

    for tag in hashtag_text.split():

        if tag.startswith("#"):

            if tag.lower() not in [
                item.lower()
                for item in final_hashtags
            ]:

                final_hashtags.append(
                    tag
                )

    hashtags = " ".join(
        final_hashtags
    )

    if hashtags not in description:

        description = (
            description
            + "\n\n"
            + hashtags
        ).strip()

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with output.open(
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            f"TITLE: {title[:100]}\n"
        )

        file.write(
            "DESCRIPTION:\n"
        )

        file.write(
            description
        )

        file.write(
            "\n"
        )

        file.write(
            f"TAGS: {tags}\n"
        )

        file.write(
            f"HASHTAGS: {hashtags}\n"
        )

    return output


def create_vertical_video(
    topic_id,
    long_video,
    short_audio
):

    output = (
        VIDEOS_DIR
        / f"{topic_id}_short.mp4"
    )

    duration = get_audio_duration(
        short_audio
    )

    if not (
        SHORT_MIN_SECONDS
        <= duration
        <= SHORT_MAX_SECONDS
    ):
        raise RuntimeError(
            f"Short duration {duration:.2f}s is outside 45-60 seconds"
        )

    music = find_music()

    filter_video = (
        "[0:v]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "gblur=sigma=18"
        "[bg];"
        "[0:v]"
        "scale=1080:-2:"
        "force_original_aspect_ratio=decrease"
        "[fg];"
        "[fg]"
        "eq=saturation=1.08:contrast=1.03"
        "[fg2];"
        "[bg][fg2]"
        "overlay=(W-w)/2:(H-h)/2,"
        "setsar=1"
        "[v]"
    )

    if music and valid_file(music):

        filter_audio = (
            "[1:a]"
            "aresample=48000,"
            "volume=1.0"
            "[voice];"
            "[2:a]"
            "aresample=48000,"
            "volume=0.055,"
            "aloop=loop=-1:size=2e+09"
            "[music];"
            "[voice][music]"
            "amix=inputs=2:"
            "duration=first:"
            "dropout_transition=2"
            "[a]"
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
            "-stream_loop",
            "-1",
            "-i",
            str(music),
            "-filter_complex",
            filter_video
            + ";"
            + filter_audio,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-t",
            f"{duration:.3f}",
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            str(output),
        ]

    else:

        command = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(long_video),
            "-i",
            str(short_audio),
            "-filter_complex",
            filter_video,
            "-map",
            "[v]",
            "-map",
            "1:a",
            "-t",
            f"{duration:.3f}",
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            str(output),
        ]

    subprocess.run(
        command,
        check=True
    )

    if not valid_file(output):
        raise RuntimeError(
            f"Short video not created: {output}"
        )

    return output


def build_short(
    topic_id,
    topic_title
):

    long_script_file = (
        SCRIPTS_DIR
        / f"{topic_id}.txt"
    )

    long_video = (
        VIDEOS_DIR
        / f"{topic_id}.mp4"
    )

    short_script_file = (
        SCRIPTS_DIR
        / f"{topic_id}_short.txt"
    )

    short_audio_file = (
        AUDIO_DIR
        / f"{topic_id}_short.mp3"
    )

    short_video_file = (
        VIDEOS_DIR
        / f"{topic_id}_short.mp4"
    )

    short_metadata_file = (
        METADATA_DIR
        / f"{topic_id}_short.txt"
    )

    if not valid_file(long_script_file):
        raise RuntimeError(
            f"Long script missing: {long_script_file}"
        )

    if not valid_file(long_video):
        raise RuntimeError(
            f"Long video missing: {long_video}"
        )

    long_script = long_script_file.read_text(
        encoding="utf-8"
    ).strip()

    sentences = split_sentences(
        long_script
    )

    if len(sentences) < 3:
        raise RuntimeError(
            "Not enough sentences for Short"
        )

    selected = create_highlight_selection(
        sentences
    )

    rates = [
        "+0%",
        "-10%",
        "-20%",
        "+10%",
        "+20%",
        "+30%",
    ]

    best_text = None
    best_duration = None

    for _ in range(12):

        candidate = make_text(
            sentences,
            selected
        )

        for rate in rates:

            asyncio.run(
                generate_tts(
                    candidate,
                    short_audio_file,
                    rate
                )
            )

            duration = get_audio_duration(
                short_audio_file
            )

            print(
                f"SHORT DURATION: "
                f"{duration:.2f}s "
                f"RATE: {rate}"
            )

            if (
                SHORT_MIN_SECONDS
                <= duration
                <= SHORT_MAX_SECONDS
            ):

                best_text = candidate
                best_duration = duration
                break

        if best_text:
            break

        current_duration = get_audio_duration(
            short_audio_file
        )

        if current_duration < SHORT_MIN_SECONDS:

            remaining = [
                i
                for i in range(
                    len(sentences)
                )
                if i not in selected
            ]

            if not remaining:
                break

            selected.append(
                remaining[0]
            )

            selected = sorted(
                set(selected)
            )

        else:

            removable = [
                i
                for i in selected
                if i not in (0, 1)
            ]

            if not removable:
                break

            selected.remove(
                removable[-1]
            )

    if not best_text:
        raise RuntimeError(
            "Could not create 45-60 second Short"
        )

    short_script_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    short_script_file.write_text(
        best_text.strip() + "\n",
        encoding="utf-8"
    )

    create_vertical_video(
        topic_id,
        long_video,
        short_audio_file
    )

    create_short_metadata(
        topic_id
    )

    if not valid_file(
        short_metadata_file
    ):
        raise RuntimeError(
            "Short metadata was not created"
        )

    print(
        f"SHORT READY: {topic_id}"
    )

    print(
        f"SHORT DURATION: {best_duration:.2f}s"
    )
