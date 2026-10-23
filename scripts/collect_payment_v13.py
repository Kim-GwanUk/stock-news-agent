"""Freeze new historical source inputs before evaluation; never touch app history."""
import asyncio
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.mcp_client import session, call

CASES = [
    ("v13-sk-final", "000660", "SK하이닉스", "2024-12-19",
     "https://www.nist.gov/news-events/news/2024/12/biden-harris-administration-announces-chips-incentives-award-sk-hynix",
     "최종 지원 약정과 사업 단계 달성 후 지급을 구분. 보조금 최대 458백만 달러와 대출 최대 500백만 달러를 혼합하지 않음."),
    ("v13-siltron", "034730", "SK", "2024-02-22",
     "https://eng.sk.com/news/sk-siltron-css-secures-conditional-commitment-from-u-s-department-of-energy-for-a-loan-of-up-to-544-million",
     "계열사 SK실트론 CSS 조건부 대출. 최대 544백만 달러, 최종 승인 전 종결 조건 충족 필요. SK 본사 직접 수령으로 확대 금지."),
    ("v13-qcells", "009830", "한화솔루션", "2024-08-08",
     "https://us.qcells.com/blog/qcells-historic-investment-supported-by-conditional-commitment-for-a-loan-from-the-u-s-department-of-energy/",
     "큐셀 프로젝트 최대 14.5억 달러 조건부 대출 보증. 기술·법률·환경·재무 조건 충족 후 최종 금융 문서 체결·집행. 수령 완료로 표현 금지."),
]

async def main():
    rows = []
    async with session("news") as client:
        for ident, code, name, date, url, rationale in CASES:
            data = await call(client, "read_article", {"url": url}, timeout=35)
            article = {**data, "id": ident, "title": data.get("original_title") or ident,
                       "url": url, "published": date, "relevant": True, "analysis_candidate": True}
            rows.append({"stock": {"code": code, "name": name, "market": "KOSPI"},
                         "article": article, "expected": "상승 요인", "split": "holdout", "rationale": rationale})
            print(ident, article["body_status"], len(article.get("body", "")), flush=True)
    Path("tmp/payment-v13-input.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    Path("output/payment-v13-labels.json").write_text(json.dumps([
        {k:v for k,v in r.items() if k != "article"} |
        {k:r["article"][k] for k in ("id","title","url","published","body_status")} |
        {"body_sha256":hashlib.sha256(r["article"].get("body","").encode()).hexdigest()}
        for r in rows], ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    asyncio.run(main())
