import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[{"role": "user", "content": "Say hello in one sentence."}],
    temperature=0.3,
    max_tokens=300
)

print("Full response object:")
print(response)
print("\nFinish reason:", response.choices[0].finish_reason)
print("Content:", repr(response.choices[0].message.content))
print("Usage:", response.usage)