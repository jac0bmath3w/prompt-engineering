import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use OpenRouter’s API
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

resp = client.chat.completions.create(
    model="deepseek/deepseek-r1:free",   # free variant
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Summarize 'Finding Nemo' in one sentence."}
    ],
)

print(resp.choices[0].message.content)
