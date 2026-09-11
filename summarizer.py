from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel
from pathlib import Path
import os
import sys


load_dotenv()

article = Path(sys.argv[1]).read_text(encoding="utf-8")

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_API_URL")
    )

resp = client.chat.completions.create(
    model="deepseek-flash",
    messages=[
        {"role": "system", "content": '你是摘要助手，必须输出JSON格式，格式要求: {"summary": "...", "keywords": "...", "one-liner": "..."}'},
        {"role": "user", "content": article}
    ]
)

class Summary(BaseModel):
    summary: str
    keywords: list[str]
    one_liner: str

try:
    data = Summary.model_validate_json(resp.choices[0].message.content)
    print("校验通过：", data)
except ValidationError as e:
    print("校验失败：", e)

