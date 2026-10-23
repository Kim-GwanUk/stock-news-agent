from datetime import datetime,timedelta
import pytest
from app.morning_report import indicators,news_sections,article_time
from app.providers import KST

def test_five_returns_need_six_prices_and_exclude_today():
    rows=[{'date':f'2026-10-{i:02d}','close':100+i,'volume':100,'change_pct':1} for i in range(1,23)]
    result=indicators({'items':rows},'2026-10-22')
    assert len(result['days'])==5 and result['last']['date']=='2026-10-21'
    assert result['return5']==pytest.approx((121/116-1)*100)
    assert result['volume_ratio']==1
    assert result['volatility20'] is not None
    assert indicators({'items':rows[-5:]},'2026-10-23')['return5'] is None

def test_failed_day_disables_metrics():
    rows=[{'date':f'2026-10-{i:02d}','close':100+i,'volume':100} for i in range(1,22)]
    result=indicators({'items':rows,'failed_dates':['20261020']},'2026-10-22')
    assert result['return5'] is None and result['last']['ma5_pct'] is None
    assert result['volatility20'] is None

def test_news_cutoff_failed_status_duplicate_and_maximum():
    start=datetime(2026,10,21,8,tzinfo=KST); end=start+timedelta(days=1)
    articles=[{'id':str(i),'title':str(i),'published':(start+timedelta(hours=i)).isoformat(),'analysis_candidate':True} for i in range(6)]
    articles += [{'id':'future','title':'future','published':end.isoformat(),'analysis_candidate':True}]
    findings=[{'article_id':a['id'],'direction':'상승 요인','processing_status':'분석 완료'} for a in articles]
    findings[0]['processing_status']='검증 실패'
    articles[1]['duplicate_of']='2'
    groups,counts=news_sections({'articles':articles,'findings':findings},start,end)
    assert len(groups['상승 요인'])==3
    assert counts['incomplete']==1 and counts['outside_window']==1
    assert not groups['하락 요인']

def test_unknown_timezone_is_not_assumed():
    assert article_time('2026-10-21T08:00:00') is None
    assert article_time('bad') is None

def test_provider_excluded_window_counts_are_preserved():
    start=datetime(2026,10,21,8,tzinfo=KST)
    _,counts=news_sections({'collection':{'outside_window':12}},start,start+timedelta(days=1))
    assert counts['outside_window']==12

@pytest.mark.asyncio
async def test_price_failure_does_not_discard_news(monkeypatch):
    from app import morning_report as m
    async def fail(*args): raise RuntimeError('unavailable')
    async def market(*args): return []
    async def policy(*args): return {'status':'ok','items':[]}
    async def news(*args,**kwargs): return {'articles':[],'findings':[],'run_id':'test'}
    monkeypatch.setattr(m.providers,'price_history',fail)
    monkeypatch.setattr(m,'macro',market)
    monkeypatch.setattr(m,'fed_releases',policy)
    monkeypatch.setattr(m.graph,'run',news)
    monkeypatch.setattr(m.db,'cache_put',lambda *args:None)
    result=await m.create({'code':'005930','name':'삼성전자'})
    assert result['prices']['last']=={}
    assert result['analysis_run_id']=='test'
    assert any('KRX' in warning for warning in result['warnings'])
