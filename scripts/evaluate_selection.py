import asyncio,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.news_selection import select
async def main():
    data=json.loads(Path('tmp/news-evaluation-input.json').read_text(encoding='utf-8'))
    for group in data:
        articles,usage,warnings=await select(group['stock'],group['articles'], 'tmp/selection-audit-'+group['stock']['code']+'.json')
        group['articles']=articles
        print(json.dumps({'stock':group['stock']['name'],'warnings':warnings,'tokens':usage.get('total_tokens'),'items':[{'id':a['id'],'relation':a['relation'],'selected':a['analysis_candidate']} for a in articles if a.get('body')]},ensure_ascii=False),flush=True)
    Path('tmp/news-evaluation-selected.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
asyncio.run(main())
