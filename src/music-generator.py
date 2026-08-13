import json
import os
import subprocess
from pathlib import Path

MUSIC_CONFIG_FILE = Path("music/music-config.json")


def load_config():
    if not MUSIC_CONFIG_FILE.exists():
        raise FileNotFoundError(
            "music/music-config.json not found"
        )

    with MUSIC_CONFIG_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def generate_silent_music(output_file, duration=30):
    """
    Temporary fallback music generator.

    Creates a very low-volume ambient track using FFmpeg.
    This keeps the pipeline functional even when no external
    music-generation API is configured.
    """

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    command = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        (
            "sine=frequency=220:"
            f"duration={duration}"
        ),
        "-af",
        "volume=0.08",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "128k",
        str(output_file),
    ]

    subprocess.run(
        command,
        check=True
    )


def main():
    config = load_config()

    categories = config.get(
        "categories",
        {}
    )

    output_config = config.get(
        "output",
        {}
    )

    output_folder = Path(
        output_config.get(
            "folder",
            "music/generated"
        )
    )

    output_format = output_config.get(
        "format",
        "mp3"
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    print("=" * 60)
    print("MYSTERY AI MUSIC GENERATOR")
    print("=" * 60)

    for category in categories:

        output_file = (
            output_folder
            / f"{category}_background.{output_format}"
        )

        if output_file.exists():
            print(
                f"ALREADY EXISTS: {output_file}"
            )
            continue

        print(
            f"GENERATING: {category}"
        )

        generate_silent_music(
            output_file,
            duration=30
        )

        print(
            f"CREATED: {output_file}"
        )

    print("=" * 60)
    print("MUSIC GENERATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
