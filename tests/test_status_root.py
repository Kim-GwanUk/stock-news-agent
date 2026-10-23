import pytest
from app import fact_ledger as fl, graph


def article(subject):
    body=f'{subject}가 총 5100만원 규모 공모전을 열고 서비스 출시를 검토한다.'
    return {'id':'a','body':body}, [dict(paragraph_index=0, role='main',subject=subject,
        subject_paragraph_index=0,event_quote=body,event_kind='development',target_connection_index=None)]


def test_joint_subject_keeps_conditions_without_affiliate_prefix_matching():
    a,refs=article('현대차·기아')
    ledger=fl.materialize(a,refs,{'name':'현대차','code':'005380'})
    assert ledger['facts'][0]['target_eligible']
    assert ledger['facts'][0]['quote']==a['body']
    assert not fl.subject_matches('CJ제일제당',['CJ'])
    assert not fl.subject_matches('CJ ENM',['CJ'])


def test_other_company_event_is_connection_issue_not_api_failure():
    a,refs=article('CJ제일제당')
    with pytest.raises(fl.TargetConnectionUnconfirmed):
        fl.materialize(a,refs,{'name':'CJ','code':'001040'})


@pytest.mark.asyncio
async def test_connection_issue_reconciles_selection(monkeypatch):
    async def extract(*args):
        return {}, {'extraction_diagnostics':[{'article_id':'a','error_type':'TargetConnectionUnconfirmed'}]}
    monkeypatch.setattr(fl,'extract',extract)
    monkeypatch.setattr(graph.db,'cached',lambda key:None)
    a,_=article('CJ ENM'); a['analysis_candidate']=True
    state=await graph.freeze_facts({'stock':{'name':'CJ','code':'001040'},'articles':[a]})
    assert state['articles'][0]['analysis_candidate'] is False
    assert state['articles'][0]['relation']=='연결 미확인'
    assert not state['fact_warnings']


def test_diagnostics_do_not_leak_external_error_payload():
    assert 'secret' not in str(fl.diagnostic(RuntimeError('secret')))
