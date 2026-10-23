"""Fresh sources, labels and source hashes frozen before model evaluation."""
import asyncio
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.mcp_client import session, call

CASES = [
    ("v12-sk-pmt", "000660", "SK하이닉스", "2024-08-07",
     "https://www.asiae.co.kr/en/article/2024080708372261709",
     "최대 4억5000만 달러 직접 보조금, 5억 달러 대출의 예비 합의. 이전 평가와 같은 사건의 새 언론 기사로 사건 독립성은 없음."),
    ("v12-samsung-award", "005930", "삼성전자", "2024-12-20",
     "https://www.nist.gov/news-events/news/2024/12/biden-harris-administration-announces-chips-incentives-award-samsung",
     "최대 47억4500만 달러 최종 지원 결정. 과거 예비 합의와 구분, 마일스톤별 지급을 입금 완료로 바꾸지 않음."),
    ("v12-lg-closed", "373220", "LG에너지솔루션", "2022-12-13",
     "https://www.lg.co.kr/media/release/25667",
     "합작법인에 대한 25억 달러 대출 종결. 조건부 단계로 되돌리거나 LG 단독 수령·매출로 바꾸지 않음."),
]

async def main():
    rows = []
    async with session("news") as client:
        for ident, code, name, date, url, rationale in CASES:
            data = await call(client, "read_article", {"url": url}, timeout=35)
            article = {**data, "id": ident, "title": data.get("original_title") or ident,
                       "url": url, "published": date, "relevant": True, "analysis_candidate": True}
            rows.append({"stock": {"code": code, "name": name, "market": "KOSPI"}, "article": article,
                         "expected": "상승 요인", "split": "holdout", "rationale": rationale})
            print(json.dumps({"id": ident, "status": article["body_status"],
                              "chars": len(article.get("body", ""))}, ensure_ascii=False), flush=True)
    Path("tmp/financial-v12-input.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    Path("output/financial-v12-labels.json").write_text(json.dumps([
        {k:v for k,v in row.items() if k != "article"} |
        {k:row["article"][k] for k in ("id","title","url","published","body_status")} |
        {"body_sha256": hashlib.sha256(row["article"].get("body","").encode()).hexdigest()}
        for row in rows], ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    asyncio.run(main())
