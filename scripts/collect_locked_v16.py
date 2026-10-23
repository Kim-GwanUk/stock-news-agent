"""New historical articles; exclude previously used URLs before evaluation."""
import asyncio
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.mcp_client import session, call

CASES = [
    ("samsung-q2", "005930", "삼성전자", "2025-07-31",
     "https://news.samsung.com/global/samsung-electronics-announces-second-quarter-2025-results"),
    ("hyundai-q3", "005380", "현대차", "2025-10-30",
     "https://www.hyundai.com/worldwide/en/newsroom/detail/0000001042"),
    ("hyundai-press", "005380", "현대차", "2025-10-30",
     "https://m.etnews.com/20251030000413"),
    ("sdi-conditional", "006400", "삼성SDI", "2024-12-03",
     "https://v.daum.net/v/20241203012027984"),
    ("sdi-conditions", "006400", "삼성SDI", "2024-12-02",
     "https://stage.energy.gov/edf/articles/lpo-announces-conditional-commitment-starplus-energy-construct-lithium-ion-battery"),
    ("sk-final-loan", "096770", "SK이노베이션", "2024-12-17",
     "https://www.donga.com/news/Economy/article/all/20241217/130659200/1"),
]


async def main():
    old = "\n".join(p.read_text(encoding="utf-8",errors="ignore")
                    for folder in ("tmp","output") for p in Path(folder).glob("*.json")
                    if "locked-v16" not in p.name)
    assert all(url not in old for *_,url in CASES), "기존 사용 URL 발견"
    rows = {}
    manifest = []
    async with session("news") as client:
        for ident, code, name, date, url in CASES:
            data = await call(client,"read_article",{"url":url},timeout=35)
            article = {**data,"id":"v16-"+ident, "title":data.get("original_title") or ident,
                       "url":url,"published":date,"relevant":True,"analysis_candidate":True}
            row = rows.setdefault(code, {"name":"unseen-historical-holdout",
                                        "stock":{"code":code,"name":name,"market":"KOSPI"},
                                        "articles":[]})
            row["articles"].append(article)
            manifest.append({"id":article["id"],"url":url,"published":date,"status":data.get("body_status"),
                             "body_sha256":hashlib.sha256(data.get("body","").encode()).hexdigest()})
            print(ident,data.get("body_status"),len(data.get("body","")),flush=True)
    # Real company-confusion control: the SDI loan is not Samsung Electronics news.
    control = next(a for a in rows["006400"]["articles"] if a["id"]=="v16-sdi-conditional")
    rows["005930"]["articles"].append({**control,"id":"v16-unrelated-sdi"})
    Path("tmp/locked-v16-holdout-input.json").write_text(json.dumps(list(rows.values()),ensure_ascii=False,indent=2),encoding="utf-8")
    Path("output/locked-v16-holdout-manifest.json").write_text(json.dumps(
        {"kind":"new-to-project historical sources; not current recommendations",
         "prior_url_overlap":False,"sources":manifest},ensure_ascii=False,indent=2),encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
