"""Freeze unseen real articles before evaluation; no analysis during collection."""
import asyncio, hashlib, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.mcp_client import session, call
from app.relevance import rank

async def main():
    prior='\n'.join(p.read_text(encoding='utf-8',errors='ignore') for folder in ('tmp','output','tests','scripts')
                   for p in Path(folder).glob('*') if p.suffix in ('.json','.py','.html') and 'status-holdout' not in p.name and 'status_holdout' not in p.name)
    rows=[]
    async with session('news') as client:
        for code,name,query in [('001040','CJ','CJ 지주 배당'),('097950','CJ제일제당','CJ제일제당 실적'),('005380','현대차','현대차 수출')]:
            stock={'code':code,'name':name,'market':'KOSPI'}
            result=await call(client,'search_stock_news',{'query':query,'count':20,'days':30})
            chosen=[]
            for a in result['articles']:
                if a['url'] in prior or a['title'] in prior: continue
                body=await call(client,'read_article',{'url':a['url']},timeout=30)
                if body.get('body_status')!='추출됨': continue
                a.update(body)
                a['title']=body.get('original_title') or a['title']
                if a['title'] in prior: continue
                a.update(rank(stock,a))
                a['body_sha256']=hashlib.sha256(a['body'].encode()).hexdigest()
                chosen.append(a)
                if len(chosen)==2: break
            rows.append({'name':name,'stock':stock,'articles':chosen})
            print(json.dumps({'stock':name,'articles':[{'title':a['title'],'url':a['url'],'body':a['body'][:3000]} for a in chosen]},ensure_ascii=False),flush=True)
    Path('tmp/status-holdout-input.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
asyncio.run(main())
