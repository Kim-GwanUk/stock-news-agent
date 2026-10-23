from app.risk_outlook import outlook

def test_old_fx_is_not_a_today_risk_and_missing_news_is_not_safe():
    report={'report_date':'2026-10-22','prices':{'last':{'date':'2026-10-21','change_pct':5},'volatility20':4},
            'macro':[{'name':'원/달러 환율','status':'ok','date':'2026-10-16','value':1300,'change':20}],
            'news':{},'news_counts':{'incomplete':2}}
    result=outlook(report)
    assert len(result['items'])==1
    assert result['items'][0]['title']=='장중 가격 변동 주의'
    assert not any('환율 상승' in x['title'] for x in result['items'])
    assert '환율 자료 지연 또는 미확보' in result['gaps']
    assert '일부 뉴스 분석 미완료' in result['gaps']

def test_missing_inputs_do_not_invent_direction():
    result=outlook({'report_date':'2026-10-22'})
    assert len(result['items'])==1
    assert '구체화하기 어렵습니다' in result['items'][0]['scenario']

def test_fresh_negative_market_has_named_evidence():
    result=outlook({'report_date':'2026-10-22','macro':[
        {'name':'나스닥 종합','status':'ok','date':'2026-10-21','value':20000,'change':-100}]})
    assert result['items'][0]['title']=='해외 증시 약세 전이 가능성'
    assert '-100.00pt' in result['items'][0]['evidence']

def sample_report(subject='테스트기업',kind='shareholder_return',quote='자사주 매입 완료, 소각 예정'):
    fact={'role':'main','subject':subject,'event_kind':kind,'event_quote':quote,'quote':quote,'target_eligible':True}
    finding={'processing_status':'분석 완료','fact_ledger':{'target_stock':{'code':'123456'},'facts':[fact]}}
    item={'article':{'title':'기사 제목','url':'https://example.com'},'finding':finding}
    return {'stock':{'name':'테스트기업','code':'123456'},'report_date':'2026-10-22',
            'prices':{'last':{'date':'2026-10-21','change_pct':4},'volatility20':3},
            'news':{'상승 요인':[item,item]},'macro':[]}

def test_completed_buyback_preserves_planned_cancellation_and_deduplicates():
    result=outlook(sample_report())
    assert len(result['items'])==1
    card=result['items'][0]
    assert '매입 완료 이후' in card['title']
    assert '소각 예정은 실제 소각 완료와 구분' in card['scenario']
    assert '+4.00%' in card['scenario']
    assert card['facts']==['자사주 매입 완료, 소각 예정']

def test_other_company_fact_and_bad_event_class_are_not_used():
    for report in (sample_report(subject='타사'), sample_report(kind='sales',quote='테스트기업은 지분 96%를 보유한다')):
        result=outlook(report)
        assert all('facts' not in x for x in result['items'])

def test_failed_analysis_is_not_reused_as_news_risk():
    report=sample_report()
    report['news']['상승 요인'][0]['finding']['processing_status']='검증 실패'
    assert all('facts' not in x for x in outlook(report)['items'])

def test_news_and_market_are_separate_short_points():
    report=sample_report()
    report['macro']=[{'name':'KOSPI','status':'ok','date':'2026-10-21','value':3000,'change_pct':-1.25}]
    items=outlook(report)['items']
    assert len(items)==2
    assert items[0]['factor']=='자사주 매입 완료 이후 수급 확인'
    assert '소각은 아직 예정' in items[0]['summary']
    assert items[1]['factor']=='KOSPI 하락'
    assert '-1.25%' in items[1]['summary']
    assert all(len(x['summary'])<130 for x in items)

def test_unchanged_or_old_rates_do_not_become_new_risks():
    report={'report_date':'2026-10-22','macro':[
        {'name':'한국 기준금리','status':'ok','date':'2026-08-27','value':3,'change':0.25},
        {'name':'미국 정책금리 상단','status':'ok','date':'2026-10-21','value':4,'change':0}]}
    assert all(x['title']!='금리 상승' for x in outlook(report)['items'])
    report['macro'][1]['change']=0.25
    assert any(x['factor']=='미국 정책금리 상단' for x in outlook(report)['items'])
