import json
import random
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "music" / "music-config.json"


def load_music_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Music config not found: {CONFIG_PATH}"
        )

    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def get_music_track(category=None):
    config = load_music_config()

    if category is None:
        category = config.get("defaultCategory", "mystery")

    categories = config.get("categories", {})

    if category not in categories:
        category = config.get("defaultCategory", "mystery")

    category_config = categories[category]

    music_folder = ROOT_DIR / category_config["folder"]

    if not music_folder.exists():
        return None, category_config["volume"]

    tracks = [
        file
        for file in music_folder.iterdir()
        if file.is_file()
        and file.suffix.lower() == ".mp3"
    ]

    if not tracks:
        return None, category_config["volume"]

    selected_track = random.choice(tracks)

    return selected_track, category_config["volume"]


def get_category_for_topic(topic):
    topic_lower = topic.lower()

    dark_words = [
        "death",
        "dark",
        "mystery",
        "killer",
        "disappear",
        "haunted"
    ]

    science_words = [
        "space",
        "antarctica",
        "borehole",
        "ocean",
        "mariana",
        "science"
    ]

    suspense_words = [
        "missing",
        "unknown",
        "secret",
        "strange",
        "mystery"
    ]

    for word in dark_words:
        if word in topic_lower:
            return "dark"

    for word in science_words:
        if word in topic_lower:
            return "science"

    for word in suspense_words:
        if word in topic_lower:
            return "suspense"

    return "mystery"


if __name__ == "__main__":
    track, volume = get_music_track()

    if track:
        print(f"🎵 Music: {track}")
        print(f"🔊 Volume: {volume}")
    else:
        print("⚠️ No background music track available yet.")
