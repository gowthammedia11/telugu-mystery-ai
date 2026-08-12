import os
import requests

api_key = os.environ["OPENROUTER_API_KEY"]

topic = "Mariana Trench Mystery"

prompt = f"""
You are a factual research assistant for a Telugu YouTube channel.

Research this topic:
{topic}

Give:
1. Confirmed scientific facts
2. Important dates/numbers
3. Scientific explanations
4. Popular theories
5. What is actually unknown
6. Reliable sources to verify the claims

Do not invent facts.
Clearly separate confirmed facts from theories.
"""

response = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    },
    json={
        "model": "openrouter/free",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    },
    timeout=120
)

response.raise_for_status()

result = response.json()
answer = result["choices"][0]["message"]["content"]

os.makedirs("research", exist_ok=True)

with open("research/002.txt", "w", encoding="utf-8") as file:
    file.write(answer)

print("Research completed successfully.")
