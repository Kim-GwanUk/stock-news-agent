import asyncio,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.mcp_client import session,call
async def main():
    rows=[]
    cases=[('sk24q2','000660','SK하이닉스','https://news.skhynix.co.kr/2q-2024-business-results/','2024-07-25','상승 요인'),('ss24q4','005930','삼성전자','https://news.samsung.com/kr/삼성전자-2024년-4분기-실적-발표','2025-01-31','하락 요인')]
    async with session('news') as client:
        for ident,code,name,url,day,expected in cases:
            r=await call(client,'read_article',{'url':url},timeout=30)
            a={'id':ident,'title':r.get('original_title') or ident,'url':url,'published':day,'relevant':True,'analysis_candidate':True,**r}
            rows.append({'stock':{'code':code,'name':name,'market':'KOSPI'},'article':a,'expected':expected,'split':'final-holdout'})
            print(ident,r['body_status'],r.get('body','')[:1500],flush=True)
    Path('tmp/direction-audit-holdout.json').write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')
asyncio.run(main())
