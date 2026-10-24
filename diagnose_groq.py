import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path, override=True)

api_key = os.getenv("GROQ_API_KEY")
model = os.getenv("GROQ_MODEL")

print("API key present:", bool(api_key))
print("Configured model:", model)

if not api_key:
    print("ERROR: GROQ_API_KEY was not loaded.")
    raise SystemExit(1)

try:
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": "Reply with: Groq connection successful"}
        ],
        max_tokens=50,
    )
    print("SUCCESS:", response.choices[0].message.content)

except Exception as exc:
    print("ERROR TYPE:", type(exc).__name__)
    print("HTTP STATUS:", getattr(exc, "status_code", "N/A"))
    response = getattr(exc, "response", None)
    if response is not None:
        print("GROQ DETAILS:", response.text)
    else:
        print("DETAILS:", str(exc))
