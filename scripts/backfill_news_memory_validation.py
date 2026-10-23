"""Verify historical real-news snapshots against their original cached bodies."""
import asyncio
import json
from pathlib import Path
from app import db, news_memory as memory


async def main():
    path=Path('/app/data/news-memory-validation.json')
    report=json.loads(path.read_text(encoding='utf-8'))
    report['historical_backfill']=[]
    for code in ('005930','000660','005380'):
        with db.connection() as con:
            raw=[json.loads(r[0]) for r in con.execute('SELECT payload FROM cache WHERE key LIKE ?',('news:v19:'+code+'%',))]
        bodies={}
        for batch in raw:
            for a in batch.get('articles',[]):
                if a.get('body'): bodies.setdefault(a['id'],[]).append(a)
        for run in db.history(code,30):
            articles=[]
            import hashlib
            for f in run.get('findings',[]):
                ledger=f.get('fact_ledger',{})
                candidates=bodies.get(f['article_id'],[])
                body=next((a for a in candidates if hashlib.sha256(a['body'].encode()).hexdigest()==ledger.get('body_sha256')),None)
                if body:
                    meta=next(a for a in run['articles'] if a['id']==f['article_id'])
                    articles.append({**body,**meta,'fact_ledger':ledger})
            if articles:
                saved=await memory.persist(run,articles)
                report['historical_backfill'].append({'code':code,'as_of':run['as_of'],'run_id':run['run_id'],**saved})
                print('BACKFILL',code,saved['status'],saved['indexed'],flush=True)
        report.setdefault('final_records',{})[code]=memory.records(code,100)
    report['searches']=[]
    for code in ('005930','000660','005380'):
        for query in ('주요 사건 실적 투자','현대차 삼성전자 SK하이닉스 자사주 매입 예비 합의'):
            hits=await memory.search(code,query)
            report['searches'].append({'code':code,'query':query,'company_clean':all(h['code']==code for h in hits),'hits':hits})
    report['checks'].append({'nonempty_companies_after_backfill':len({r['code'] for r in report['searches'] if r['hits']})})
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('DONE',flush=True)


asyncio.run(main())
