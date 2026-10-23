import asyncio, hashlib, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.mcp_client import session,call
CASES=[('105560','KB금융','KB금융 자사주'),('138040','메리츠금융지주','메리츠금융지주 자사주'),('011170','롯데케미칼','롯데케미칼 실적'),('011070','LG이노텍','LG이노텍 실적')]
if '--fresh' in sys.argv:
    CASES=[('071050','한국금융지주','한국금융지주 주주환원'),('017670','SK텔레콤','SK텔레콤 자사주'),('055550','신한지주','신한지주 자사주 소각')]
async def main():
    prior='\n'.join(p.read_text(encoding='utf-8',errors='ignore') for folder in ('tmp','output','scripts','tests') for p in Path(folder).glob('*') if p.suffix in ('.json','.html','.py') and (('--fresh' in sys.argv and 'fresh' not in p.name) or 'ownership' not in p.name))
    rows=[]
    async with session('news') as c:
        for code,name,query in CASES:
            data=await call(c,'search_stock_news',{'query':query,'count':4,'days':7})
            aa=[]
            for a in data['articles']:
                a['prior_url_overlap']=a['url'] in prior
                if not a['prior_url_overlap']:
                    try:a.update(await call(c,'read_article',{'url':a['url']},timeout=35))
                    except Exception:a.update(body='',body_status='접근 실패')
                if a.get('original_title'):a['title']=a['original_title']
                a['body_sha256']=hashlib.sha256(a.get('body','').encode()).hexdigest()
                aa.append(a)
            rows.append({'stock':{'code':code,'name':name,'market':'KOSPI'},'articles':aa})
            Path('tmp/ownership-v19-fresh-pool.json' if '--fresh' in sys.argv else 'tmp/ownership-v19-new-pool.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps({'stock':name,'articles':[{k:a.get(k) for k in ('id','title','url','prior_url_overlap','body_status')} for a in aa]},ensure_ascii=False),flush=True)
asyncio.run(main())
