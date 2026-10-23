"""Collect unseen source URLs; do not pass evaluation labels to the app."""
import asyncio
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.mcp_client import session, call

CASES = [
    ("v17-lg-q2","066570","LG전자","","https://www.lgcorp.com/media/release/29193"),
    ("v17-sk-q2","000660","SK하이닉스","2025-07-23","https://news.skhynix.com/en/sk-hynix-announces-2q25-financial-results/"),
    ("v17-sdi-gm","006400","삼성SDI","2024-08-28","https://samsungsdi.com/sdi-now/sdi-news/3942.html"),
    ("v17-lges-ford","373220","LG에너지솔루션","2025-12-17","https://www.investing.com/news/stock-market-news/south-koreas-lg-energy-solution-ends-65-billion-ev-batterysupply-deal-with-ford-4411948"),
]


async def main():
    previous = "\n".join(p.read_text(encoding="utf-8",errors="ignore")
                        for folder in ("tmp","output") for p in Path(folder).glob("*.json"))
    assert all(url not in previous for *_,url in CASES)
    rows, manifest = [], []
    async with session("news") as client:
        for ident,code,name,date,url in CASES:
            data = await call(client,"read_article",{"url":url},timeout=35)
            a = {**data,"id":ident,"title":data.get("original_title") or ident,
                 "url":url,"published":date,"relevant":True,"analysis_candidate":True}
            rows.append({"name":"v17-unseen-holdout","stock":{"code":code,"name":name,"market":"KOSPI"},"articles":[a]})
            manifest.append({"id":ident,"url":url,"body_status":data.get("body_status"),
                             "body_sha256":hashlib.sha256(data.get("body","").encode()).hexdigest()})
            print(ident,data.get("body_status"),len(data.get("body","")),flush=True)
    Path("tmp/v17-holdout.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
    Path("output/v17-holdout-manifest.json").write_text(json.dumps(
        {"prior_url_overlap":False,"sources":manifest},ensure_ascii=False,indent=2),encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
