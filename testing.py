from openai import OpenAI
from config import GROK_API_KEY
client = OpenAI(
    api_key="GROK_API_KEY",
    base_url="https://api.groq.com/openai/v1"
)

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {
            "role": "user",
            "content": "Say Hello"
        }
    ]
)

print(response.choices[0].message.content)