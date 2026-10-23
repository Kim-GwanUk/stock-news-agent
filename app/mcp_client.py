import asyncio
import json
import os
from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from app.config import ROOT, PYTHON, NODE

@asynccontextmanager
async def session(provider):
    env = {k: v for k, v in os.environ.items()
           if k.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME",
                            "USERPROFILE", "APPDATA", "LOCALAPPDATA", "PYTHONPATH"}}
    keys = ["NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET"] if provider == "news" else ["DART_API_KEY", "KRX_API_KEY"]
    env.update({k: os.getenv(k, "") for k in keys})
    env["PYTHONIOENCODING"] = "utf-8"
    if provider == "news":
        command, args = PYTHON, [str(ROOT / "vendor/korean-news-mcp/server.py")]
    else:
        if not NODE:
            raise RuntimeError("Node.js 실행 경로가 없습니다.")
        command, args = NODE, [str(ROOT / "vendor/korea-stock-mcp/dist/index.js")]
    params = StdioServerParameters(command=command, args=args, env=env, cwd=str(ROOT))
    # Upstream errors can contain provider URLs; do not expose them in user logs.
    with open(os.devnull, "w") as errlog:
        async with stdio_client(params, errlog=errlog) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                yield client

async def call(client, name, args, timeout=30):
    result = await asyncio.wait_for(client.call_tool(name, args), timeout)
    if result.isError:
        raise RuntimeError(f"{name} 도구 조회 실패")
    for part in result.content:
        if getattr(part, "type", None) == "text":
            return json.loads(part.text)
    raise RuntimeError("도구 응답 데이터가 없습니다.")
