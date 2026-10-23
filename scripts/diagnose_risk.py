import asyncio,json
from app import db,analysis,fact_ledger

async def main():
    result=db.history('005930',1)[0]
    with db.connection() as con:
        rows=con.execute("SELECT payload FROM cache WHERE key LIKE 'news:v19:005930:%' ORDER BY expires DESC").fetchall()
    cached=json.loads(rows[0][0])
    articles=[]; findings=[]
    for f in result['findings']:
        if not f.get('fact_ledger'): continue
        a=next((a for a in cached['articles'] if a['id']==f['article_id']),None)
        if not a: continue
        a['fact_ledger']=f['fact_ledger']
        try:
            rebuilt=fact_ledger.render(a,f['interpretation'])
            articles.append(a); findings.append(rebuilt)
        except Exception as exc: print('render',type(exc).__name__,str(exc))
    verdict,_=await analysis.review(result['stock'],articles,[],findings)
    print(json.dumps(verdict,ensure_ascii=False))
asyncio.run(main())
