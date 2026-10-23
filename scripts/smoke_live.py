"""Explicit live smoke test: provider summaries only, no secrets or article bodies."""
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import providers, analysis
from app.mcp_client import session, call

async def main():
    stock = {"code": "005930", "name": "삼성전자", "market": "KOSPI", "kind": "관심"}
    async with session("stock") as client:
        tools = await client.list_tools()
        print(json.dumps({"stock_mcp_tools": len(tools.tools)}), flush=True)
        result = await call(client, "get_disclosure_list", {
            "corp_code": "00126380", "bgn_de": "20261001", "page_no": "1",
            "page_count": "10", "sort": "crp", "sort_mth": "asc"})
        print(json.dumps({"dart_status": result.get("status"), "records": len(result.get("list", []))}), flush=True)
    price, news = await asyncio.gather(providers.price(stock), providers.news(stock))
    print(json.dumps({"price_as_of": price["as_of"], "news_count": len(news["articles"]),
                      "body_count": sum(bool(a.get("body")) for a in news["articles"])}), flush=True)
    usable = [a for a in news["articles"] if a.get("body") and a.get("relevant")]
    if usable:
        draft, usage = await analysis.generate(stock, usable[:1], [])
        errors = analysis.validate(draft, usable[:1], [])
        print(json.dumps({"generation": "ok", "findings": len(draft["findings"]), "validation_errors": errors,
                          "tokens": usage.get("total_tokens")}, ensure_ascii=False), flush=True)
    else:
        print('{"generation": "skipped: no body evidence"}', flush=True)

if __name__ == "__main__":
    asyncio.run(main())
