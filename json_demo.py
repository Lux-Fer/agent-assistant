from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
import os

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_API_URL"),
)

article = "DeepSeek API 已接入多种主流 AI Agent 与编程助手工具。如果你使用 Claude Code、GitHub Copilot、OpenCode 等工具，可以直接将 DeepSeek 作为后端模型，无需编写代码即可开始使用。"

resp = client.chat.completions.create(
    model="deepseek-flash",
    messages=[
        {"role": "system", "content": '你是摘要助手。必须只输出 JSON，格式: {"summary": "...", "keywords": ["..."], "one_liner": "..."}'},
        {"role": "user", "content": article},
    ],
    response_format={"type": "json_object"},
)

class Summary(BaseModel):
    summary: str
    keywords: list[str]
    one_liner: str

try:
    data = Summary.model_validate_json(resp.choices[0].message.content)
    print("校验成功：", data)
except ValidationError as e:
    print("校验失败：",e)

