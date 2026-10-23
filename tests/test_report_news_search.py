import importlib.util
from pathlib import Path
from datetime import datetime,timedelta,timezone
from email.utils import format_datetime
import pytest

@pytest.mark.asyncio
async def test_report_search_reaches_older_page_and_respects_cutoff(monkeypatch):
    directory=Path(__file__).resolve().parents[1]/'vendor/korean-news-mcp'
    monkeypatch.syspath_prepend(str(directory))
    spec=importlib.util.spec_from_file_location('report_news_server',directory/'server.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    end=datetime.now(timezone.utc)-timedelta(hours=2)
    start=end-timedelta(days=1)
    offsets=[]
    class Response:
        def raise_for_status(self): pass
        def __init__(self,offset): self.offset=offset
        def json(self):
            stamp=end+timedelta(hours=1) if self.offset==1 else end-timedelta(hours=1)
            return {'items':[{'title':str(i),'originallink':f'https://example.com/{self.offset}/{i}',
                             'pubDate':format_datetime(stamp)} for i in range(100)]}
    class Client:
        def __init__(self,**kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def get(self,url,params,headers):
            offsets.append(params['start'])
            return Response(params['start'])
    monkeypatch.setattr(module.httpx,'AsyncClient',Client)
    result=await module.search_stock_news('삼성전자',window_start=start.isoformat(),window_end=end.isoformat())
    assert offsets==[1,101]
    assert len(result['articles'])==20
    assert result['window_outside']==100
    assert all(start<=datetime.fromisoformat(a['published'])<end for a in result['articles'])
