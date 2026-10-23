"""Live smoke check inside a fresh, isolated backend (uses provider quota)."""
import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from openai import AsyncOpenAI
from app import config, dart_rag
from app.mcp_client import session, call
from app.morning_report import krx_index
from app.providers import KST


async def main():
    if os.getenv('PORTABILITY_TEST') != '1':
        raise SystemExit('Run only in an isolated test container with PORTABILITY_TEST=1; writes a test vector.')
    checks = {}
    async def check(name, action):
        try:
            checks[name] = {'ok': True, 'result': await action()}
        except Exception as exc:
            checks[name] = {'ok': False, 'error_type': type(exc).__name__}
    async def stock_mcp():
        async with session('stock') as client:
            tools = await client.list_tools()
            now = datetime.now(KST)
            result = await call(client, 'get_disclosure_list', {
                'corp_code': '00126380', 'bgn_de': (now-timedelta(days=30)).strftime('%Y%m%d'),
                'page_no': '1', 'page_count': '1', 'sort': 'date', 'sort_mth': 'desc'})
            assert result.get('status') in ('000', '013')
            return {'tool_count': len(tools.tools), 'dart_status': result.get('status')}
    async def news_mcp():
        async with session('news') as client:
            result = await call(client, 'search_stock_news', {'query': '삼성전자', 'count': 2, 'days': 7})
            assert result.get('articles') and not result.get('warnings')
            return {'article_count': len(result['articles']), 'naver_fallback': False}
    async def indices():
        async with httpx.AsyncClient(timeout=25) as client:
            rows = await asyncio.gather(*(krx_index(client, m, datetime.now(KST).date()) for m in ('KOSPI', 'KOSDAQ')))
            assert all(r['status']=='ok' for r in rows)
            return [{'name':r['name'], 'date':r['date']} for r in rows]
    async def model():
        async with AsyncOpenAI(timeout=35, max_retries=0) as client:
            result = await client.chat.completions.create(model=config.MODEL, messages=[{'role':'user','content':'Reply OK.'}], max_completion_tokens=8)
            assert result.choices[0].message.content
            return {'model': result.model}
    async def vectors():
        vector = (await dart_rag.embed(['국내주식 검색 연결 확인']))[0]
        assert len(vector)==1536
        await dart_rag.ensure_collection()
        point='00000000-0000-0000-0000-000000000001'
        await dart_rag.qrequest('PUT', f'/collections/{dart_rag.COLLECTION}/points?wait=true', json={'points':[{'id':point,'vector':vector,'payload':{'code':'005930','test_only':True}}]})
        result=await dart_rag.qrequest('POST',f'/collections/{dart_rag.COLLECTION}/points',json={'ids':[point],'with_payload':True})
        assert len(result['result'])==1
        return {'dimensions':len(vector),'qdrant_write_read':True}
    checks['env_not_baked_into_image']={'ok':not Path('/app/.env.local').exists()}
    await asyncio.gather(check('stock_mcp_dart',stock_mcp),check('news_mcp_naver',news_mcp),
                         check('krx_indices',indices),check('openai_chat',model),check('embedding_qdrant',vectors))
    print(json.dumps(checks,ensure_ascii=False,indent=2))
    return 0 if all(c['ok'] for c in checks.values()) else 1


if __name__=='__main__':
    raise SystemExit(asyncio.run(main()))
