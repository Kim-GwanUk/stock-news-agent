import asyncio,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import providers,db
async def main():
    samples=[]
    for stock in db.stocks():
        result=await providers.news(stock)
        samples.append({'stock':stock,**result})
        print(stock['name'], flush=True)
        for a in result['articles']:
            print(json.dumps({k:a.get(k) for k in ['id','title','url','analysis_candidate','body_status']},ensure_ascii=False),flush=True)
    Path('tmp/news-evaluation-input.json').write_text(json.dumps(samples,ensure_ascii=False),encoding='utf-8')
asyncio.run(main())
