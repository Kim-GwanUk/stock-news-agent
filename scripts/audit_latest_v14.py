"""Current-news end-to-end audit, without changing watchlist/history or caches."""
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import db, graph, providers

PREFIX = "latest-v14"

STOCKS = [
    {"code":"005930", "name":"삼성전자", "market":"KOSPI"},
    {"code":"005380", "name":"현대차", "market":"KOSPI"},
    {"code":"247540", "name":"에코프로비엠", "market":"KOSDAQ"},
]

async def main():
    files = ["app/news_selection.py", "app/providers.py", "app/analysis.py",
             "app/graph.py", "app/payment_conditions.py", "app/financial_grounding.py"]
    hashes = {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in files}
    original_news = providers.news
    frozen = {}
    async def capture(stock):
        result = await original_news(stock)
        frozen[stock["code"]] = json.loads(json.dumps(result))
        Path(f"tmp/{PREFIX}-bodies-{stock['code']}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result
    results = []
    with patch.object(db, "cached", return_value=None), patch.object(db, "cache_put"), \
         patch.object(db, "save_run"), patch.object(providers, "news", side_effect=capture):
        for stock in STOCKS:
            result = await graph.run(stock)
            results.append(result)
            Path(f"output/{PREFIX}-results.json").write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            ids = {a["id"] for a in result["articles"] if a.get("analysis_candidate")}
            print(json.dumps({"stock":stock["name"], "articles":len(result["articles"]),
                "bodies":sum(a.get("body_status")=="추출됨" for a in result["articles"]),
                "selected":len(ids), "warnings":result["warnings"],
                "findings":[{"title":next(a["title"] for a in result["articles"] if a["id"]==f["article_id"]),
                             **f} for f in result["findings"] if f["article_id"] in ids]},
                ensure_ascii=False), flush=True)
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in hashes.items())
    Path(f"output/{PREFIX}-code.json").write_text(json.dumps({
        "sha256":hashes, "cache_enabled":False, "history_written":False,
        "evaluation":"post-hoc source review; no pre-labelled accuracy claim",
        "source_hashes":{code:{a["id"]:hashlib.sha256(a.get("body","").encode()).hexdigest()
                               for a in data["articles"]} for code,data in frozen.items()}
        },indent=2), encoding="utf-8")

if __name__ == "__main__":
    asyncio.run(main())
