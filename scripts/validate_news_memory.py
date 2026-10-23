"""Live pipeline + real Qdrant checks; no synthetic items in production storage."""
import asyncio
import json
from pathlib import Path
from app import graph, news_memory as memory, db


async def main():
    stocks=[{'code':'005930','name':'삼성전자','market':'KOSPI','kind':'관심'},
            {'code':'000660','name':'SK하이닉스','market':'KOSPI','kind':'보유'},
            {'code':'005380','name':'현대차','market':'KOSPI','kind':'관심'}]
    report={'scope':'실제 기사 수집·분석 후 사건 보관과 기업별 검색 분리 검증. 투자 판단 정확도 평가가 아님.',
            'runs':[], 'searches':[], 'checks':[]}
    path=Path('/app/data/news-memory-validation.json')
    def save(): path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    for stock in stocks:
        print('START',stock['code'],flush=True)
        try:
            r=await graph.run(stock)
            items=memory.records(stock['code'])
            report['runs'].append({'code':stock['code'],'run_id':r['run_id'],
                                   'storage':r.get('news_memory'),'records':items})
            print('STORED',stock['code'],r.get('news_memory'),flush=True)
        except Exception as exc:
            report['runs'].append({'code':stock['code'],'error':type(exc).__name__})
            print('FAILED',stock['code'],type(exc).__name__,flush=True)
        save()
    for stock in stocks:
        for query in [stock['name']+' 주요 사건 실적 투자', '현대차 삼성전자 SK하이닉스 자사주 매입 실적 예비 합의']:
            try:
                hits=await memory.search(stock['code'],query)
                report['searches'].append({'code':stock['code'],'query':query,
                    'company_clean':all(h['code']==stock['code'] for h in hits),'hits':hits})
            except Exception as exc:
                report['searches'].append({'code':stock['code'],'error':type(exc).__name__})
            save()
    for code,query,cutoff in [('999999','삼성전자 자사주',None),('005930','실적','2000-01-01T00:00:00+09:00')]:
        hits=await memory.search(code,query,cutoff)
        report['checks'].append({'code':code,'as_of':cutoff,'expected_empty':len(hits)==0})
    report['checks'].append({'nonempty_company_searches':len({r['code'] for r in report['searches'] if r.get('hits')})})
    save()
    print('DONE',str(path),flush=True)


asyncio.run(main())
