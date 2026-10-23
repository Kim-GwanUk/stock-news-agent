import pytest
from app import db, fact_ledger, news_memory as memory


def sample(code='005930',name='삼성전자'):
    stock={'code':code,'name':name}
    body=f'{name}는 최대 500억원의 대출을 위한 예비 합의를 체결했다.\n{name}의 자금 지급은 승인 조건을 충족해야 가능하다.\n다른회사는 매출이 30% 증가했다고 밝혔다.'
    a={'id':'article-'+code,'title':name+' 예비 합의','body':body,'published':'2026-01-01T08:00:00+09:00',
       'url':'https://example.com/'+code,'relevant':True,'analysis_candidate':True}
    refs=[{'paragraph_index':i,'subject_paragraph_index':i,'subject':name if i<2 else '다른회사',
           'event_quote':p,'role':['main','condition','context'][i],
           'event_kind':'funding' if i<2 else 'earnings','target_connection_index':None}
          for i,p in enumerate(body.splitlines())]
    a['fact_ledger']=fact_ledger.materialize(a,refs,stock)
    f=fact_ledger.render(a,{'fact_ids':['p0'],'effect':'funding','impact':'중간'})
    f['processing_status']='분석 완료'
    r={'stock':stock,'findings':[f],'run_id':'r1','as_of':'2026-01-02T08:00:00+09:00','model':'test','prompt_version':'test'}
    return r,a


@pytest.fixture(autouse=True)
def isolated(monkeypatch,tmp_path):
    monkeypatch.setattr(db,'DATA',tmp_path)


def test_roundtrip_conditions_attribution_idempotency_and_relations():
    r,a=sample()
    first=memory.store(r,[a]); r['run_id']='r2'
    assert memory.store(r,[a])['saved_ids']==first['saved_ids']
    items=memory.records('005930')
    assert len(items)==1 and items[0]['reusable']
    assert len(items[0]['facts'])==2 and len(items[0]['excluded_context'])==1
    assert '최대 500억원' in items[0]['facts'][0]['quote']
    assert '승인 조건' in items[0]['facts'][1]['quote']
    assert items[0]['statistical_label'] is None
    with db.connection() as con:
        assert con.execute('SELECT count(*) FROM news_event_runs').fetchone()[0]==2
        assert con.execute('SELECT count(*) FROM news_event_relations').fetchone()[0]==4


@pytest.mark.parametrize('mutation',['code','quote','body'])
def test_tampering_rejected(mutation):
    r,a=sample()
    if mutation=='code': r['stock']['code']='000660'
    if mutation=='quote': r['findings'][0]['fact_ledger']['facts'][0]['quote']='가짜 사실'
    if mutation=='body': a['body']+='변경'
    assert memory.store(r,[a])['saved_ids']==[]


@pytest.mark.parametrize('mutation',['failed','duplicate','prose'])
def test_unusable_decisions_stored_but_not_reusable(mutation):
    r,a=sample()
    if mutation=='failed': r['findings'][0]['processing_status']='검증 실패'
    if mutation=='duplicate': a['duplicate_of']='original'
    if mutation=='prose': r['findings'][0]['reason']='허위 해석'
    memory.store(r,[a])
    event=memory.records('005930')[0]
    assert not event['decision_reusable']
    assert event['reusable'] is (mutation != 'duplicate')


@pytest.mark.asyncio
async def test_search_requires_company_filter_and_rechecks_sql(monkeypatch):
    r,a=sample(); memory.store(r,[a])
    r2,a2=sample('000660','SK하이닉스'); memory.store(r2,[a2])
    own=memory.records('005930')[0]; other=memory.records('000660')[0]
    with db.connection() as con: con.execute("UPDATE news_events SET vector_status='indexed'")
    async def embed(texts): return [[0.0]*1536 for _ in texts]
    async def query(method,path,**kwargs):
        conditions=kwargs['json']['filter']['must']
        assert {'key':'code','match':{'value':'005930'}} in conditions
        return {'result':{'points':[{'id':e['id'],'score':.9} for e in [other,own]]}}
    monkeypatch.setattr(memory.dart_rag,'embed',embed)
    monkeypatch.setattr(memory.dart_rag,'qrequest',query)
    hits=await memory.search('005930','SK하이닉스 실적')
    assert len(hits)==1 and hits[0]['code']=='005930'
    assert '다른회사' not in str(hits[0]['facts'])
    assert await memory.search('005930','예비 합의','2025-12-31T00:00:00+09:00')==[]
    assert await memory.search('999999','예비 합의')==[]


@pytest.mark.asyncio
async def test_vector_failure_preserves_record_and_retry(monkeypatch):
    r,a=sample()
    async def fail(code): raise RuntimeError('offline')
    monkeypatch.setattr(memory,'sync',fail)
    result=await memory.persist(r,[a])
    assert result['status']=='pending_retry'
    assert len(memory.records('005930'))==1


def test_joint_company_is_not_solo_subject():
    stock={'code':'005380','name':'현대차'}
    assert memory.subject_scope(stock,'현대자동차·기아')=='joint'
    assert memory.subject_scope(stock,'현대자동차')=='direct'
    assert memory.subject_scope(stock,'기아')=='related_or_other'


@pytest.mark.asyncio
async def test_failed_judgment_never_returned_as_verified_direction(monkeypatch):
    r,a=sample()
    r['findings'][0]['processing_status']='검증 실패'
    memory.store(r,[a])
    e=memory.records('005930')[0]
    with db.connection() as con: con.execute("UPDATE news_events SET vector_status='indexed'")
    async def embed(texts): return [[0.0]*1536]
    async def query(*args,**kwargs): return {'result':{'points':[{'id':e['id'],'score':.9}]}}
    monkeypatch.setattr(memory.dart_rag,'embed',embed)
    monkeypatch.setattr(memory.dart_rag,'qrequest',query)
    hit=(await memory.search('005930','대출'))[0]
    assert not hit['decision_reusable'] and 'direction' not in hit['decision']
    assert hit['condition_context'][0]['quote']==a['body'].splitlines()[1]


@pytest.mark.asyncio
async def test_revised_failed_judgment_supersedes_old_version(monkeypatch):
    r,a=sample(); memory.store(r,[a]); old=memory.records('005930')[0]
    r['findings'][0]['processing_status']='검증 실패'
    r['as_of']='2026-01-03T08:00:00+09:00'; r['run_id']='r2'
    memory.store(r,[a]); new=memory.records('005930')[0]
    with db.connection() as con: con.execute("UPDATE news_events SET vector_status='indexed'")
    async def embed(texts): return [[0.0]*1536]
    async def query(*args,**kwargs): return {'result':{'points':[{'id':e['id'],'score':.9} for e in [old,new]]}}
    monkeypatch.setattr(memory.dart_rag,'embed',embed)
    monkeypatch.setattr(memory.dart_rag,'qrequest',query)
    hits=await memory.search('005930','대출')
    assert len(hits)==1 and hits[0]['id']==new['id'] and not hits[0]['decision_reusable']
    historical=await memory.search('005930','대출','2026-01-02T09:00:00+09:00')
    assert len(historical)==1 and historical[0]['id']==old['id']
