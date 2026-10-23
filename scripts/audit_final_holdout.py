import asyncio, copy, hashlib, json, sys
from pathlib import Path
from unittest.mock import patch
from contextlib import asynccontextmanager
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import graph, db, providers
from app.news_duplicates import display_articles
from app.news_selection import select

def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
async def analyze(row,articles,usage,warnings):
    s={'stock':row['stock'],'articles':articles,'usage':[usage],'news_warnings':warnings}
    s.update(await graph.freeze_facts(s)); frozen=copy.deepcopy(s['articles'])
    s.update(await graph.analyze(s)); first=copy.deepcopy(s['draft'])
    s.update(graph.validate(s)); first_errors=copy.deepcopy(s['validation_errors'])
    if s['validation_errors']:
        s.update(graph.correct(s)); s.update(await graph.analyze(s)); s.update(graph.validate(s))
    s.update(await graph.review(s)); result=graph.finish(s)['result']
    return dict(name=row['name'],result=result,extracted=frozen,first=first,first_errors=first_errors,final_errors=s['validation_errors'],display_articles=display_articles(result))

async def main():
    manifest=read('output/final-holdout-manifest.json')
    assert manifest['code']=={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in manifest['code']}
    rows=read('tmp/final-holdout-frozen.json'); results=[]
    with patch.object(db,'cached',return_value=None),patch.object(db,'cache_put'),patch.object(db,'save_run'):
        for row in rows:
            supplied=copy.deepcopy(row['articles'])
            # Controlled stage audit: bodies have already been supplied; emulate
            # the collection-stage eligibility flag required by validation.
            # Production replay below uses the unmodified real lexical gate.
            for article in supplied: article['relevant']=True
            a,u,w=await select(row['stock'],supplied)
            results.append(await analyze(row,a,u,w))
            Path('output/final-holdout-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
            print(row['name'],'done',flush=True)
        # Replay exact production collection budgets using the captured search list.
        pools=read('tmp/final-holdout-pool.json')+read('tmp/final-holdout-kakao.json')
        for row in pools:
            row['name']='production-replay-'+row['stock']['code']
            originals={a['url']:a for a in row['articles']}
            @asynccontextmanager
            async def session(_): yield None
            async def call(client,name,args,**kwargs):
                if name=='search_stock_news':
                    clean=[]
                    for a in row['articles']:
                        clean.append({k:v for k,v in a.items() if k in ('id','url','published','description','provider','publisher','title')})
                        clean[-1]['title']=a.get('search_title',a['title'])
                    return {'articles':clean,'warnings':[]}
                a=originals[args['url']]
                return {k:a[k] for k in ('body','body_status','original_title','publisher') if k in a}
            with patch.object(providers,'session',session),patch.object(providers,'call',call):
                data=await providers.news(row['stock'])
            # Collection/selection audit only: no need to repeat paid directional analysis.
            results.append(dict(name=row['name'],stock=row['stock'],articles=data['articles'],warnings=data.get('warnings',[])))
            Path('output/final-holdout-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
            print(row['name'],'done',flush=True)
    assert manifest['code']=={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in manifest['code']}
asyncio.run(main())
