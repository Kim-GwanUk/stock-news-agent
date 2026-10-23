"""New historical source set; labels fixed before any model evaluation."""
import asyncio
import json
from pathlib import Path
from app.mcp_client import session, call

S = "https://news.samsung.com/kr/"
CASES = [
("new-ss24q1","005930","삼성전자",S+"삼성전자-2024년-1분기-실적-발표","2024-04-30","상승 요인","dev",
 "전분기 전사 매출·영업이익 증가와 메모리 흑자 전환. 미래 전망과 실현 실적 구분."),
("new-ss22q4","005930","삼성전자",S+"삼성전자-2022년-4분기-실적-발표","2023-01-31","하락 요인","dev",
 "전분기 전사 매출·영업이익 감소. 연간 최대 매출로 분기 악화를 뒤집지 않음."),
("new-recall","005930","삼성전자","https://www.mk.co.kr/news/business/11088857","2024-08-09","하락 요인","dev",
 "삼성 제품 화재 위험과 리콜·무상 조치 확인. 품질·대응 부담 방향은 부정, 전사 손실액·소송 확정·고영향 단정은 금지."),
("new-grant","000660","SK하이닉스","https://www.donga.com/news/Economy/article/all/20241219/130685954/1","2024-12-19","상승 요인","dev",
 "정부 지원 최종 약정으로 투자 자금 조달에 긍정. 최대 지원액과 조건부 지급을 구분하며 대출을 보조금·매출로 합산하지 않음."),
("new-sk24q1","000660","SK하이닉스","https://news.skhynix.co.kr/1q-2024-business-results/","2024-04-25","상승 요인","holdout",
 "확인된 매출·이익 반등 및 고부가 메모리 판매. 신규 공장 계획만으로 판단하지 않음."),
("new-sk22q4","000660","SK하이닉스","https://news.skhynix.co.kr/2022-business-performance/","2023-02-01","하락 요인","holdout",
 "수요·가격 하락으로 최근 4분기 영업손실, 연간 최대 매출과 기간 구분."),
("new-csr","005930","삼성전자",S+"삼성-2024-나눔의-날-행사-개최","2024-11-14","판단 보류","holdout",
 "사회공헌 행사·기부를 전사 실적 호재로 연결하지 않음."),
("new-anniversary","005930","삼성전자",S+"삼성전자-제55주년-창립기념식-개최","2024-11-01","판단 보류","holdout",
 "기념식과 경영 의지는 확정 수주·실적 변화가 아님."),
]

async def main():
    rows = []
    async with session("news") as client:
        for ident,code,name,url,date,expected,split,rationale in CASES:
            body = await call(client,"read_article",{"url":url},timeout=35)
            a = {**body,"id":ident,"url":url,"title":body.get("original_title") or ident,
                 "published":date,"relevant":True,"analysis_candidate":True}
            rows.append({"stock":{"code":code,"name":name,"market":"KOSPI"},"article":a,
                         "expected":expected,"split":split,"rationale":rationale})
            print(json.dumps({"id":ident,"title":a["title"],"status":a["body_status"],
                              "chars":len(a.get("body",""))},ensure_ascii=False),flush=True)
    Path("tmp/first-judgment-input.json").write_text(json.dumps(rows,ensure_ascii=False),encoding="utf-8")
    Path("output/first-judgment-labels.json").write_text(
        json.dumps([{k:v for k,v in r.items() if k!="article"}|
                   {k:r["article"][k] for k in ("id","title","url","published")} for r in rows],
                   ensure_ascii=False,indent=2),encoding="utf-8")

if __name__=="__main__":
    asyncio.run(main())
