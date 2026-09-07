
import os
import subprocess
import sys

from topic_manager import (
    get_next_topic,
    mark_processing,
)


def run_step(
    name,
    script,
    topic_id,
    extra_env=None
):

    print("=" * 80)
    print(f"STARTING STEP: {name}")
    print(f"TOPIC ID: {topic_id}")
    print("=" * 80)

    env = os.environ.copy()

    env["PIPELINE_TOPIC_ID"] = topic_id

    if extra_env:
        env.update(extra_env)

    result = subprocess.run(
        [
            sys.executable,
            script,
        ],
        env=env,
        check=False,
    )

    if result.returncode != 0:

        raise RuntimeError(
            f"{name} failed with exit code "
            f"{result.returncode}"
        )

    print("=" * 80)
    print(f"STEP COMPLETED: {name}")
    print("=" * 80)


def main():

    print("=" * 80)
    print("TELUGU MYSTERY AI — MASTER PIPELINE")
    print("=" * 80)

    topic = get_next_topic()

    if not topic:

        print(
            "NO TOPIC AVAILABLE"
        )

        return 0

    topic_id = topic["id"].strip()
    topic_title = topic["title"].strip()

    print(
        f"SELECTED TOPIC: {topic_id}"
    )

    print(
        f"TITLE: {topic_title}"
    )

    # Lock exact topic.
    mark_processing(
        topic_id
    )

    try:

        run_step(
            "RESEARCH",
            "src/research.py",
            topic_id
        )

        run_step(
            "SCRIPT",
            "src/script.py",
            topic_id
        )

        run_step(
            "VOICE",
            "src/voice.py",
            topic_id
        )

        run_step(
            "VIDEO",
            "src/video.py",
            topic_id
        )

        run_step(
            "YOUTUBE METADATA",
            "src/youtube_metadata.py",
            topic_id
        )

        run_step(
            "YOUTUBE UPLOAD",
            "src/youtube_upload.py",
            topic_id
        )

    except Exception as error:

        print("=" * 80)
        print("PIPELINE FAILED")
        print("=" * 80)

        print(
            f"TOPIC: {topic_id}"
        )

        print(
            f"ERROR: {error}"
        )

        print()
        print(
            "IMPORTANT:"
        )

        print(
            "Topic remains in processing state."
        )

        print(
            "Next scheduled run will retry the SAME topic."
        )

        print("=" * 80)

        return 1

    print("=" * 80)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print(f"TOPIC {topic_id} FINISHED")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
