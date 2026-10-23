"""Collect raw unseen news; never invoke selection or analysis during collection."""
import asyncio, hashlib, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.mcp_client import session, call

STOCKS=[('035420','NAVER','인터넷'),('042660','한화오션','조선'),('068270','셀트리온','바이오'),('051910','LG화학','화학')]
async def main():
    prior='\n'.join(p.read_text(encoding='utf-8',errors='ignore') for folder in ('tmp','output','tests','scripts') for p in Path(folder).glob('*') if p.suffix in ('.json','.py','.html') and 'final_holdout' not in p.name and 'final-holdout' not in p.name)
    extra='--extra' in sys.argv
    rows=[]
    async with session('news') as client:
        for code,name,sector in ([('035720','카카오','인터넷')] if '--kakao' in sys.argv else STOCKS[:1] if '--naver' in sys.argv else STOCKS):
            query=({'NAVER':'네이버','한화오션':'한화오션 계약','셀트리온':'셀트리온 계약','LG화학':'LG화학 기소'}[name] if extra else name)
            if '--naver' in sys.argv: query='네이버 실적'
            data=await call(client,'search_stock_news',{'query':query,'count':8 if extra else 20,'days':7})
            articles=data['articles']
            sem=asyncio.Semaphore(3)
            async def enrich(a):
                a['prior_url_overlap']=a['url'] in prior
                if a['prior_url_overlap']: return
                async with sem:
                    try: body=await call(client,'read_article',{'url':a['url']},timeout=35)
                    except Exception: body={'body':'','body_status':'본문 접근 실패'}
                a.update(body)
                if body.get('original_title'):
                    a['search_title']=a['title']; a['title']=body['original_title']
                a['body_sha256']=hashlib.sha256(a.get('body','').encode()).hexdigest()
            await asyncio.gather(*(enrich(a) for a in articles))
            rows.append({'stock':{'code':code,'name':name,'market':'KOSPI'},'sector':sector,'articles':articles})
            Path('tmp/final-holdout-kakao.json' if '--kakao' in sys.argv else 'tmp/final-holdout-naver.json' if '--naver' in sys.argv else 'tmp/final-holdout-extra.json' if extra else 'tmp/final-holdout-pool.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps({'stock':name,'items':[{'id':a['id'],'title':a['title'],'status':a.get('body_status'),'overlap':a['prior_url_overlap']} for a in articles]},ensure_ascii=False),flush=True)
asyncio.run(main())
