from openai import OpenAI
from dotenv import load_dotenv
import os
import re
import json
import asyncio
import httpx

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_API_URL"),
)

MAX_STEPS = 10

SYSTEM_PROMPT = "你是 Agent 助手，可以根据需要使用工具来回答问题。"

# ==================== 工具函数 ====================

def calculator(expr: str) -> str:
    if not re.fullmatch(r"^[0-9+\-*/().\s]+$", expr):
        return "错误：表达式含非法字符"
    try:
        return str(eval(expr, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"错误：{e}"


async def get_weather(city: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            geo = (await c.get("https://geocoding-api.open-meteo.com/v1/search",
                               params={"name": city, "count": 1})).json()
            if not geo.get("results"):
                return f"找不到城市: {city}"
            loc = geo["results"][0]
            w = (await c.get("https://api.open-meteo.com/v1/forecast",
                             params={"latitude": loc["latitude"], "longitude": loc["longitude"],
                                     "current_weather": "true"})).json()
            cur = w["current_weather"]
            return f"{city} 当前 {cur['temperature']}°C，风速 {cur['windspeed']}km/h"
    except Exception as e:
        return f"天气查询失败: {e}"


def search(query: str) -> str:
    # 先尝试真实搜索；网络不可用时退回模拟结果，保证工具永不失败
    try:
        from ddgs import DDGS
        results = DDGS().text(query, max_results=3)
        if results:
            return "\n".join(f"{i+1}. {r['title']} - {r['href']}" for i, r in enumerate(results))
    except Exception:
        pass  # 真搜索失败（网络受限），走下面的模拟结果
    mock = [
        {"title": f"「{query}」百科介绍", "href": "https://example.com/intro"},
        {"title": f"「{query}」最新动态", "href": "https://example.com/news"},
        {"title": f"「{query}」入门教程", "href": "https://example.com/tutorial"},
    ]
    return "\n".join(f"{i+1}. {r['title']} - {r['href']}" for i, r in enumerate(mock))


# ==================== 工具注册表（分发表） ====================

TOOL_FUNCS = {
    "calculator": calculator,
    "get_weather": get_weather,
    "search": search,
}


def run_tool(name: str, args: dict) -> str:
    fn = TOOL_FUNCS.get(name)
    if fn is None:
        return f"未知工具: {name}"
    try:
        if asyncio.iscoroutinefunction(fn):      # 异步工具单独驱动
            return asyncio.run(fn(**args))
        return fn(**args)
    except Exception as e:
        return f"工具执行出错: {e}"


# ==================== 工具说明书（给模型看的 schema） ====================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算数学表达式，当用户需要算术计算时使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "expr": {"type": "string", "description": "只含数字和运算符的表达式，如 1+2*3"},
                },
                "required": ["expr"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气，当用户问天气时使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如 北京"},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "联网搜索信息，当用户问实时资讯或你不了解的知识时使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                },
                "required": ["query"],
            },
        },
    },
]


# ==================== Agent 主循环 ====================

def chat(user_input: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]

    for step in range(MAX_STEPS):
        resp = client.chat.completions.create(
            model="deepseek-flash",
            messages=messages,
            tools=TOOLS,
        )
        msg = resp.choices[0].message
        messages.append(msg)                     # assistant 消息必须先入历史

        if msg.tool_calls:                       # 模型请求调用工具
            for tc in msg.tool_calls:
                print(f"  [工具] {tc.function.name}({tc.function.arguments})")
                args = json.loads(tc.function.arguments)
                result = run_tool(tc.function.name, args)
                print(f"  [结果] {result[:60]}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
            continue                             # 回循环，让模型看结果继续想

        if msg.content:                          # 模型给出最终文字回答
            return msg.content

    return "任务超时，请简化问题"


# ==================== 交互入口 ====================

if __name__ == "__main__":
    print("Agent 已就绪（输入 exit 退出）")
    while True:
        q = input("你: ")
        if q.lower() in ("exit", "quit"):
            break
        print("Agent:", chat(q))
