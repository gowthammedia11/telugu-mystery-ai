import os

from topic_manager import (
    get_next_topic,
    mark_processing,
    mark_completed,
    mark_failed,
)

from research import run as run_research
from script import run as run_script
from voice import run as run_voice
from video import generate_video
from youtube_metadata import run as run_metadata
from youtube_upload import run as run_upload


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():

    print("=" * 70)
    print("TELUGU MYSTERY AI PIPELINE")
    print("=" * 70)

    topic = get_next_topic()

    if not topic:

        print(
            "NO TOPICS AVAILABLE"
        )

        return

    topic_id = topic["id"]
    topic_title = topic["title"]

    os.environ[
        "PIPELINE_TOPIC_ID"
    ] = topic_id

    print("=" * 70)
    print("SELECTED TOPIC")
    print(f"ID: {topic_id}")
    print(f"TITLE: {topic_title}")
    print("=" * 70)

    mark_processing(
        topic_id
    )

    try:

        # ----------------------------------------------------
        # RESEARCH
        # ----------------------------------------------------

        print("=" * 70)
        print("RESEARCH STEP")
        print("=" * 70)

        run_research(
            topic_id
        )

        # ----------------------------------------------------
        # SCRIPT
        # ----------------------------------------------------

        print("=" * 70)
        print("SCRIPT STEP")
        print("=" * 70)

        run_script(
            topic_id
        )

        # ----------------------------------------------------
        # VOICE
        # ----------------------------------------------------

        print("=" * 70)
        print("VOICE STEP")
        print("=" * 70)

        run_voice(
            topic_id
        )

        # ----------------------------------------------------
        # VIDEO
        # ----------------------------------------------------

        print("=" * 70)
        print("VIDEO STEP")
        print("=" * 70)

        generate_video(
            topic_id
        )

        # ----------------------------------------------------
        # METADATA
        # ----------------------------------------------------

        print("=" * 70)
        print("YOUTUBE METADATA STEP")
        print("=" * 70)

        run_metadata(
            topic_id
        )

        # ----------------------------------------------------
        # YOUTUBE UPLOAD + SCHEDULE
        # ----------------------------------------------------

        print("=" * 70)
        print("YOUTUBE UPLOAD STEP")
        print("=" * 70)

        run_upload(
            topic_id
        )

        # ----------------------------------------------------
        # COMPLETE
        # ----------------------------------------------------

        mark_completed(
            topic_id
        )

        print("=" * 70)
        print("PIPELINE COMPLETED SUCCESSFULLY")
        print(f"TOPIC: {topic_id}")
        print(f"TITLE: {topic_title}")
        print("=" * 70)

    except Exception as error:

        print("=" * 70)
        print("PIPELINE FAILED")
        print(f"TOPIC: {topic_id}")
        print(f"ERROR: {error}")
        print("=" * 70)

        # Keep it as processing so next day's run
        # can resume this exact topic.
        try:

            mark_processing(
                topic_id
            )

        except Exception as status_error:

            print(
                f"Could not restore processing status: "
                f"{status_error}"
            )

        raise


if __name__ == "__main__":
    main()
