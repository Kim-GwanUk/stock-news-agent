"""Live corpus sync and predeclared topic checks; saves source excerpts for review."""
import asyncio
import json
from pathlib import Path
import httpx
import sys

CASES = {
    "001040":[("주요 사업 부문과 지주회사의 역할", ["지주","사업"]),
              ("배당 정책과 주주 환원", ["배당"])],
    "005930":[("반도체 메모리 DRAM NAND 주요 제품", ["DRAM","NAND","메모리"]),
              ("환율 변동과 외화 위험 관리", ["환율","외화"])],
    "247540":[("양극재 주요 제품과 원재료 니켈 리튬", ["양극","리튬","니켈"]),
              ("차입금과 유동성 위험", ["차입","유동성"])],
    "005380":[("자동차 주요 제품과 판매 현황", ["자동차","판매"]),
              ("연구개발과 전기차 투자", ["연구","전기차"])],
}

async def main():
    holdout = "--holdout" in sys.argv
    cases = {"001040":[("특수관계자 거래와 지급보증 내역",["특수관계","보증"])],
             "005930":[("연구개발비 지출과 연구개발 조직",["연구개발"])],
             "247540":[("매출채권 회수와 신용 위험",["신용","매출채권"])],
             "005380":[("제품 보증 충당부채와 품질 비용",["보증","충당부채"])]} if holdout else CASES
    out = Path("output/dart-rag-validation-holdout.json" if holdout else "output/dart-rag-validation.json")
    results = {"method":"사전 지정 8개 질문의 키워드 기반 검색 점검. 의미 정확도는 원문 별도 검토.","sync":[],"cases":[],"isolation":[]}
    def save(): out.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
    async with httpx.AsyncClient(timeout=1200) as client:
        stocks = (await client.get("http://127.0.0.1:8000/stocks")).json()
        for stock in stocks:
            code = stock["code"]
            response = await client.post("http://127.0.0.1:8000/rag/sync/"+code)
            response.raise_for_status()
            summary=response.json()
            results["sync"].append(summary)
            print(code, "documents",len(summary["documents"]),"chunks",sum(d["chunks"] for d in summary["documents"]),"errors",summary["errors"],flush=True)
            save()
        for stock in stocks:
            code=stock["code"]
            for query,terms in cases.get(code,[]):
                response=await client.get("http://127.0.0.1:8000/rag/search/"+code,params={"q":query})
                response.raise_for_status()
                hits=response.json()["items"]
                check={"code":code,"query":query,"topic_hit":any(any(t in h["text"] for t in terms) for h in hits),
                       "issuer_clean":all(h["stock_code"]==code for h in hits),"hits":hits}
                results["cases"].append(check)
                print(code,query,check["topic_hit"],check["issuer_clean"],flush=True)
                save()
            for other in stocks:
                if other["code"]==code: continue
                query=other["name"]+" 실적 매출 주요 제품"
                response=await client.get("http://127.0.0.1:8000/rag/search/"+code,params={"q":query})
                response.raise_for_status()
                hits=response.json()["items"]
                results["isolation"].append({"code":code,"query":query,"count":len(hits),
                    "issuer_clean":all(h["stock_code"]==code for h in hits)})
                save()
    print("saved",out,flush=True)

asyncio.run(main())
