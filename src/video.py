# ============================================================
# BACKGROUND MUSIC CONFIG
# ============================================================

MUSIC_CONFIG_FILE = Path("music/music-config.json")

DEFAULT_MUSIC_CATEGORY = "mystery"
DEFAULT_MUSIC_VOLUME = 0.055


def load_music_config():
    """
    Loads music/music-config.json.
    Falls back safely to default settings if config is unavailable.
    """
    if not MUSIC_CONFIG_FILE.exists():
        print("MUSIC CONFIG NOT FOUND")
        return {
            "defaultCategory": DEFAULT_MUSIC_CATEGORY,
            "categories": {},
            "output": {}
        }

    try:
        import json

        with MUSIC_CONFIG_FILE.open("r", encoding="utf-8") as file:
            config = json.load(file)

        print("MUSIC CONFIG LOADED")
        return config

    except Exception as error:
        print(f"MUSIC CONFIG ERROR: {error}")

        return {
            "defaultCategory": DEFAULT_MUSIC_CATEGORY,
            "categories": {},
            "output": {}
        }


def detect_music_category(topic_title, script_text):
    """
    Selects background music category based on topic/script keywords.
    """

    text = f"{topic_title} {script_text}".lower()

    category_keywords = {
        "dark": [
            "dark", "death", "dead", "killer", "horror",
            "danger", "evil", "disappearance", "murder"
        ],

        "suspense": [
            "mystery", "unknown", "secret", "missing",
            "strange", "unexplained", "hidden", "mysterious"
        ],

        "science": [
            "science", "scientist", "research", "experiment",
            "laboratory", "space", "earth", "physics",
            "technology", "antarctica", "ocean", "ice"
        ],

        "emotional": [
            "emotional", "loss", "lost", "tragedy",
            "survivor", "victim", "family", "hope"
        ]
    }

    scores = {
        "mystery": 0,
        "dark": 0,
        "suspense": 0,
        "science": 0,
        "emotional": 0
    }

    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in text:
                scores[category] += 1

    selected_category = max(
        scores,
        key=scores.get
    )

    # If no meaningful keyword was detected,
    # use the configured default category.
    if scores[selected_category] == 0:
        selected_category = DEFAULT_MUSIC_CATEGORY

    print("=" * 60)
    print("MUSIC CATEGORY ANALYSIS")
    print(f"SCORES: {scores}")
    print(f"SELECTED CATEGORY: {selected_category}")
    print("=" * 60)

    return selected_category


def find_music_file(topic_title="", script_text=""):
    """
    Finds legally usable local background music
    from the configured category folder.
    """

    config = load_music_config()

    categories = config.get("categories", {})

    category = detect_music_category(
        topic_title,
        script_text
    )

    category_config = categories.get(category)

    if not category_config:
        category = config.get(
            "defaultCategory",
            DEFAULT_MUSIC_CATEGORY
        )

        category_config = categories.get(category)

    if not category_config:
        print("NO VALID MUSIC CATEGORY CONFIGURED")
        return None, DEFAULT_MUSIC_VOLUME

    folder = Path(
        category_config.get(
            "folder",
            f"music/tracks/{category}"
        )
    )

    configured_volume = float(
        category_config.get(
            "volume",
            DEFAULT_MUSIC_VOLUME
        )
    )

    # Safety limit.
    # Never allow background music to become too loud.
    music_volume = min(
        max(configured_volume, 0.01),
        0.15
    )

    folder.mkdir(
        parents=True,
        exist_ok=True
    )

    candidates = sorted(
        [
            p for p in folder.iterdir()
            if p.is_file()
            and p.suffix.lower() in {
                ".mp3",
                ".wav",
                ".m4a"
            }
        ]
    )

    if not candidates:
        print(
            f"NO MUSIC FOUND IN CATEGORY: {category}"
        )
        print(
            f"EXPECTED FOLDER: {folder}"
        )
        return None, music_volume

    # Rotate music files instead of always using
    # the first file.
    state_file = folder / ".last_used.txt"

    last_used = ""

    if state_file.exists():
        last_used = state_file.read_text(
            encoding="utf-8"
        ).strip()

    selected = candidates[0]

    for candidate in candidates:
        if candidate.name != last_used:
            selected = candidate
            break

    state_file.write_text(
        selected.name,
        encoding="utf-8"
    )

    print("=" * 60)
    print("BACKGROUND MUSIC SELECTED")
    print(f"CATEGORY: {category}")
    print(f"FILE: {selected}")
    print(f"VOLUME: {music_volume}")
    print("=" * 60)

    return selected, music_volume
