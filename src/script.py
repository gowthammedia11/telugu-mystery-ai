import os
import re
import time
import requests


MODEL = "openrouter/free"
MAX_RETRIES = 3
REQUEST_TIMEOUT = 240

MIN_SCRIPT_CHARACTERS = 4500
TARGET_SCRIPT_CHARACTERS = 5500
MAX_SCRIPT_CHARACTERS = 7500

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


FORBIDDEN_PATTERNS = [
    r"\blatitude\b",
    r"\blongitude\b",
    r"\bcoordinates?\b",
    r"\bgeo[- ]?coordinates?\b",
    r"\bGPS\b",
    r"\b\d+(?:\.\d+)?\s*°\s*[NSWE]\b",
    r"\b\d+(?:\.\d+)?\s*degrees?\s*[NSWE]\b",
    r"\b\d+(?:\.\d+)?\s*[NSWE]\b",
]


def get_api_key():
    key = os.getenv(
        "OPENROUTER_API_KEY",
        ""
    ).strip()

    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY environment variable is missing"
        )

    return key


def build_prompt(
    topic_id,
    topic_title,
    research
):
    return f"""
నువ్వు ఒక తెలుగు Mystery, Science మరియు Unexplained YouTube documentary writer.

Topic ID: {topic_id}
Topic: {topic_title}

క్రింద ఇచ్చిన research ఆధారంగా సహజంగా వినిపించే తెలుగు narration script రాయాలి.

Research:
{research}

కఠినమైన నియమాలు:

1. మొత్తం script 7 నుంచి 8 నిమిషాల narration కి సరిపోయేంత పొడవుగా ఉండాలి.
2. సుమారు 5500 నుంచి 7000 తెలుగు characters ఉండాలి.
3. కనీసం {MIN_SCRIPT_CHARACTERS} characters ఉండాలి.
4. గరిష్ఠంగా {MAX_SCRIPT_CHARACTERS} characters లోపు ఉండాలి.
5. పూర్తిగా సహజమైన conversational documentary Telugu లో రాయాలి.
6. AI గురించి ఎక్కడా చెప్పకూడదు.
7. Headings, sections, bullet points, numbered lists వాడకూడదు.
8. ప్రారంభం curiosity కలిగించేలా ఉండాలి.
9. మధ్యలో mystery, known facts, scientific explanations, unanswered questions సహజంగా explain చేయాలి.
10. చివర్లో abrupt ending ఉండకూడదు.
11. చివరి భాగం natural documentary ending లాగా ఉండాలి.
12. Fake facts, invented statistics, invented quotes లేదా unsupported claims చేర్చకూడదు.
13. Research లో uncertainty ఉంటే uncertainty గానే చెప్పాలి.
14. Miles ఉపయోగించకూడదు.
15. Unnecessary decimal numbers వాడకూడదు.
16. Years ని narration కి సహజంగా చదివే విధంగా రాయాలి.
17. English technical terms అవసరమైతే మాత్రమే natural గా ఉపయోగించాలి.
18. Script మొత్తం narration మాత్రమే ఉండాలి.
19. Intro, outro, heading labels వంటివి ప్రత్యేకంగా రాయకూడదు.
20. ఒకే విషయం పదే పదే repeat చేయకూడదు.
21. Latitude, longitude, coordinates, GPS coordinates ఎట్టి పరిస్థితుల్లోనూ రాయకూడదు.
22. Degree symbol లేదా degree-based geographic location format ఉపయోగించకూడదు.
23. ఉదాహరణకు "12.345° N, 78.901° E" లాంటి locations అసలు రాయకూడదు.
24. Locations ని place name, region, direction లేదా normal distance ద్వారా మాత్రమే explain చేయాలి.

కేవలం final Telugu narration script మాత్రమే ఇవ్వాలి.
"""


def contains_forbidden_coordinates(text):
    if not text:
        return False

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        ):
            return True

    if "°" in text:
        return True

    return False


def remove_coordinate_lines(text):
    if not text:
        return text

    lines = []

    for line in text.splitlines():

        if contains_forbidden_coordinates(line):
            continue

        lines.append(line)

    text = "\n".join(lines)

    text = re.sub(
        r"\b\d+(?:\.\d+)?\s*°\s*[NSWE]\b",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\b\d+(?:\.\d+)?\s*degrees?\s*[NSWE]\b",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\b(?:latitude|longitude|coordinates?|GPS)\b",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = text.replace(
        "°",
        ""
    )

    return text


def extract_content(response_json):

    if not isinstance(
        response_json,
        dict
    ):
        return None

    choices = response_json.get(
        "choices"
    )

    if not choices:
        return None

    first_choice = choices[0]

    if not isinstance(
        first_choice,
        dict
    ):
        return None

    message = first_choice.get(
        "message"
    )

    if isinstance(
        message,
        dict
    ):

        content = message.get(
            "content"
        )

        if isinstance(
            content,
            str
        ) and content.strip():

            return content.strip()

        if isinstance(
            content,
            list
        ):

            parts = []

            for item in content:

                if isinstance(
                    item,
                    dict
                ):

                    value = item.get(
                        "text"
                    )

                    if isinstance(
                        value,
                        str
                    ):

                        parts.append(
                            value
                        )

            joined = "\n".join(
                parts
            ).strip()

            if joined:
                return joined

    text = first_choice.get(
        "text"
    )

    if isinstance(
        text,
        str
    ) and text.strip():

        return text.strip()

    return None


def clean_script(text):

    if not text:
        return None

    text = str(text).strip()

    text = re.sub(
        r"^```(?:text|txt|telugu|python)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    text = re.sub(
        r"^(SCRIPT|TELUGU SCRIPT|FINAL SCRIPT)\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    lines = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        if re.match(
            r"^(INTRO|INTRODUCTION|OUTRO|CONCLUSION|SCRIPT|FINAL SCRIPT)\s*:?$",
            line,
            flags=re.IGNORECASE
        ):
            continue

        if re.match(
            r"^#{1,6}\s+",
            line
        ):
            line = re.sub(
                r"^#{1,6}\s+",
                "",
                line
            ).strip()

        if re.match(
            r"^\d+[\.\)]\s+",
            line
        ):
            line = re.sub(
                r"^\d+[\.\)]\s+",
                "",
                line
            ).strip()

        if line:
            lines.append(line)

    text = " ".join(
        lines
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    text = re.sub(
        r"\.{3,}",
        "...",
        text
    )

    text = text.replace(
        "—",
        "-"
    )

    text = text.replace(
        "–",
        "-"
    )

    text = remove_coordinate_lines(
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


def apply_final_script_rules(text):

    if not text:
        return None

    text = clean_script(
        text
    )

    if not text:
        return None

    text = re.sub(
        r"\b(\d+(?:\.\d+)?)\s*miles?\b",
        r"\1 kilometres",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\b(\d+)\.900\b",
        r"\1",
        text
    )

    text = re.sub(
        r"\b(\d+)\.0+\b",
        r"\1",
        text
    )

    text = remove_coordinate_lines(
        text
    )

    text = re.sub(
        r"\s+([,.!?])",
        r"\1",
        text
    )

    text = re.sub(
        r"([,.!?])([^\s])",
        r"\1 \2",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    if contains_forbidden_coordinates(
        text
    ):
        raise RuntimeError(
            "Forbidden latitude/longitude/coordinate content detected in final script"
        )

    return text


def generate_script(
    topic_id,
    topic_title,
    research
):

    api_key = get_api_key()

    prompt = build_prompt(
        topic_id,
        topic_title,
        research
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/gowthammedia11/telugu-mystery-ai",
        "X-Title": "Telugu Mystery AI"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert Telugu documentary script writer. "
                    "Write factual, natural, engaging Telugu narration. "
                    "Never use geographic coordinates, latitude, longitude, "
                    "GPS coordinates or degree-based locations."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.45,
        "max_tokens": 9000
    }

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        print(
            f"OPENROUTER SCRIPT ATTEMPT "
            f"{attempt}/{MAX_RETRIES}"
        )

        try:

            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT
            )

            print(
                f"OPENROUTER HTTP STATUS: "
                f"{response.status_code}"
            )

            if response.status_code != 200:

                last_error = (
                    f"OpenRouter HTTP "
                    f"{response.status_code}: "
                    f"{response.text[:2000]}"
                )

                print(last_error)

            else:

                try:

                    data = response.json()

                except Exception as exc:

                    last_error = (
                        f"OpenRouter returned invalid JSON: {exc}"
                    )

                    print(last_error)
                    data = None

                if data:

                    content = extract_content(
                        data
                    )

                    if content:

                        content = clean_script(
                            content
                        )

                        if content:

                            content = apply_final_script_rules(
                                content
                            )

                            if (
                                content
                                and not contains_forbidden_coordinates(
                                    content
                                )
                            ):

                                print(
                                    "OPENROUTER SCRIPT CONTENT RECEIVED"
                                )

                                return content

                    choices = data.get(
                        "choices",
                        []
                    )

                    if choices:

                        finish_reason = (
                            choices[0].get(
                                "finish_reason"
                            )
                            if isinstance(
                                choices[0],
                                dict
                            )
                            else None
                        )

                        print(
                            "OPENROUTER FINISH REASON:",
                            finish_reason
                        )

                    error_data = data.get(
                        "error"
                    )

                    if error_data:

                        print(
                            "OPENROUTER ERROR:",
                            error_data
                        )

                    last_error = (
                        "OpenRouter returned null or "
                        "invalid script content"
                    )

        except requests.RequestException as exc:

            last_error = (
                f"OpenRouter request failed: {exc}"
            )

            print(last_error)

        except Exception as exc:

            last_error = (
                f"Unexpected OpenRouter error: {exc}"
            )

            print(last_error)

        if attempt < MAX_RETRIES:

            wait_seconds = attempt * 10

            print(
                f"Retrying in {wait_seconds} seconds..."
            )

            time.sleep(
                wait_seconds
            )

    raise RuntimeError(
        last_error
        or "Script generation failed"
    )


def save_script(
    topic_id,
    script
):

    output_dir = Path(
        "scripts"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        output_dir
        / f"{topic_id}.txt"
    )

    final_script = apply_final_script_rules(
        script
    )

    if not final_script:
        raise RuntimeError(
            "Final script is empty"
        )

    if contains_forbidden_coordinates(
        final_script
    ):
        raise RuntimeError(
            "Forbidden geographic coordinates detected before saving script"
        )

    output_file.write_text(
        final_script.strip() + "\n",
        encoding="utf-8"
    )

    return output_file


if __name__ == "__main__":
    print(
        "script.py is a library module."
    )
