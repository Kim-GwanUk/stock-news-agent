import asyncio,json,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.mcp_client import session,call
S='https://news.samsung.com/kr/'
CASES=[
('ss23','005930','삼성전자',S+'삼성전자-2023년-1분기-실적-발표','2023-04-27','하락 요인','dev','수요 부진과 전분기 매출·영업이익 감소'),
('ss24','005930','삼성전자',S+'삼성전자-2024년-2분기-실적-발표','2024-07-31','상승 요인','dev','메모리 수요 회복, 전분기 매출·영업이익 증가'),
('sk23','000660','SK하이닉스','https://news.skhynix.co.kr/1q-2023-business-results/','2023-04-26','하락 요인','dev','수요·가격 하락과 영업손실 확대, 회복 전망은 반대 근거'),
('contract','005930','삼성전자','https://kr.tradingview.com/news/reuters.com%2C2025%3Anewsml_L4N3TP025%3A0/','2025-07-28','상승 요인','dev','확정된 반도체 위탁생산 공급계약, 이익률·주가 상승은 확정 아님'),
('sk25','000660','SK하이닉스','https://news.skhynix.co.kr/2025-business-results/','2026-01-28','상승 요인','holdout','공식 연간 매출·영업이익 증가'),
('ss25','005930','삼성전자',S+'삼성전자-2025년-2분기-실적-발표','2025-07-31','하락 요인','holdout','전분기 매출·영업이익 감소와 반도체 비용 부담')]
async def main():
    rows=[]
    async with session('news') as client:
        for ident,code,name,url,day,direction,split,why in CASES:
            r=await call(client,'read_article',{'url':url},timeout=30)
            a={'id':ident,'title':r.get('original_title') or ident,'url':url,'published':day,'relevant':True,'analysis_candidate':True,**r}
            rows.append({'stock':{'code':code,'name':name,'market':'KOSPI'},'article':a,'expected':direction,'split':split,'rationale':why})
            print(json.dumps({'id':ident,'status':r['body_status'],'length':len(r.get('body','')),'title':a['title']},ensure_ascii=False),flush=True)
    Path('tmp/direction-audit-input.json').write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')
    Path('output/direction-audit-labels.json').write_text(json.dumps([{k:v for k,v in r.items() if k!='article'}|{'id':r['article']['id'],'url':r['article']['url'],'published':r['article']['published']} for r in rows],ensure_ascii=False,indent=2),encoding='utf-8')
asyncio.run(main())
