"""New frozen sources and predeclared qualitative expectations, before evaluation."""
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.mcp_client import session, call

CASES = [
    ("v10-sk-preliminary", "000660", "SK하이닉스", "2024-08-06",
     "https://eng.sk.com/news/sk-hynix-signs-preliminary-memorandum-of-terms-with-u-s-department-of-commerce-for-advanced-packaging-facility-in-indiana",
     "상승 요인", "비구속 예비 합의에 따른 재원 확보 가능성. 보조금·대출 구분, 최종 확정·입금 완료 금지."),
    ("v10-samsung-preliminary", "005930", "삼성전자", "2024-04-15",
     "https://www.nist.gov/news-events/news/2024/04/biden-harris-administration-announces-preliminary-terms-samsung-electronics",
     "상승 요인", "예비 지원 합의의 투자 재원 가능성. 최종 약정·수령·실현 이익으로 바꾸지 않음."),
    ("v10-washer22", "005930", "삼성전자", "2022-12-23",
     "https://cbiz.chosun.com/svc/bulletin/bulletin_art.html?contid=2022122301869",
     "하락 요인", "화재 위험 리콜과 대응 부담. 무료 업데이트·국내 제외에서 전사 영향 경미·무비용 추론 금지."),
    ("v10-washer16", "005930", "삼성전자", "2016-11-04",
     "https://news.samsung.com/us/samsung-announces-voluntary-recall-of-certain-top-load-washers/",
     "하락 요인", "안전 위험과 리콜 수리·환급 대응 부담. 무료 수리를 기업 무비용으로 전환 금지. 전사 손실 규모 추정 금지."),
]

async def main():
    korean = "--korean" in sys.argv
    cases = [("v10-sk-preliminary-ko", "000660", "SK하이닉스", "2024-08-06",
              "https://m.newsis.com/view/NISX20240806_0002840449", "상승 요인",
              "앞서 평가한 SK 예비 합의의 한국어 보도. 별도 사건으로 세지 않음. 대출 한도·보조금 구분, 최종 수령 단정 금지.")] if korean else CASES
    prefix = "explanation-v10-korean" if korean else "explanation-v10"
    rows = []
    async with session("news") as client:
        for ident, code, name, date, url, expected, rationale in cases:
            result = await call(client, "read_article", {"url": url}, timeout=35)
            article = {**result, "id": ident, "title": result.get("original_title") or ident,
                       "url": url, "published": date, "relevant": True, "analysis_candidate": True}
            if ident == "v10-washer22" and article["title"] == ident:
                # Legacy page body extractor omits the title; verified against the source page.
                article["title"] = "삼성전자, 美서 세탁기 66만대 리콜…“소프트웨어 업데이트로 해결”"
            rows.append({"stock": {"code": code, "name": name, "market": "KOSPI"},
                         "article": article, "expected": expected, "rationale": rationale, "split": "holdout"})
            print(json.dumps({"id": ident, "status": article["body_status"],
                              "chars": len(article.get("body", "")), "title": article["title"]},
                             ensure_ascii=False), flush=True)
    Path(f"tmp/{prefix}-input.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    Path(f"output/{prefix}-labels.json").write_text(json.dumps([
        {k: v for k, v in r.items() if k != "article"} |
        {k: r["article"][k] for k in ("id", "title", "url", "published", "body_status")} for r in rows
    ], ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    asyncio.run(main())
