from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    api_key = os.getenv("DEEPSEEK_API_KEY"),
    base_url = os.getenv("DEEPSEEK_API_URL")
)

resp = client.chat.completions.create(
    model="deepseek-flash",
    messages=[{"role":"user", "content":"讲一个关于猫的笑话"}],
    temperature=0.7,
    top_p=0.9,
    max_tokens=1000,
    stream=True
)

for chunk in resp:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta,end='',flush=True)

print()