"""Issuer-scoped evidence memory. Model decisions are records, never ground truth."""
import asyncio
import hashlib
import json
import re
import time
import uuid
from datetime import datetime

from app import db, dart_rag, fact_ledger

COLLECTION = 'news_evidence_small_v1'
VERSION = 2


def setup(con):
    con.executescript('''
    CREATE TABLE IF NOT EXISTS news_events(
      id TEXT PRIMARY KEY, code TEXT NOT NULL, article_id TEXT NOT NULL,
      available_at REAL NOT NULL, reusable INTEGER NOT NULL, payload TEXT NOT NULL,
      vector_status TEXT NOT NULL DEFAULT 'pending');
    CREATE INDEX IF NOT EXISTS news_events_company ON news_events(code,available_at);
    CREATE TABLE IF NOT EXISTS news_event_runs(
      event_id TEXT NOT NULL, run_id TEXT NOT NULL, PRIMARY KEY(event_id,run_id));
    CREATE TABLE IF NOT EXISTS news_event_relations(
      event_id TEXT NOT NULL, relation TEXT NOT NULL, target TEXT NOT NULL,
      PRIMARY KEY(event_id,relation,target));
    ''')


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timezone required')
    return parsed.timestamp()


def check_code(code):
    if not re.fullmatch(r'\d{6}', code):
        raise ValueError('A six-digit stock code is required')


def subject_scope(stock, subject):
    normal = lambda text: re.sub(r'[\s·.,()]','',text).casefold()
    if normal(subject) in {normal(n) for n in fact_ledger.target_names(stock)}:
        return 'direct'
    if fact_ledger.subject_matches(subject, fact_ledger.target_names(stock)):
        return 'joint'
    return 'related_or_other'


def prepare(result, article, finding):
    stock = result['stock']
    check_code(stock['code'])
    ledger = finding.get('fact_ledger') or article.get('fact_ledger')
    if not ledger:
        raise ValueError('no_ledger')
    if ledger.get('target_stock', {}).get('code') != stock['code']:
        raise ValueError('wrong_company')
    fact_ledger.verify(article, ledger)
    # Subscriptions, suppliers and subsidiaries must not silently become issuer facts.
    own = [f for f in ledger['facts'] if f.get('target_eligible') is True
           and subject_scope(stock,f.get('subject','')) == 'direct']
    other = [f for f in ledger['facts'] if f not in own]
    chosen = set(finding.get('interpretation', {}).get('fact_ids', []))
    direction_facts = [f for f in ledger['facts'] if f['id'] in chosen or f.get('role') == 'main']
    errors = fact_ledger.validate_finding(finding, article)
    reusable = (any(f.get('role') != 'condition' for f in own) and not article.get('duplicate_of')
                and article.get('analysis_candidate', article.get('relevant', False)))
    decision_reusable = (reusable and finding.get('processing_status') == '분석 완료'
                         and not errors and all(f in own for f in direction_facts))
    # Store immutable decision revisions; repeat runs link to the same revision.
    decision = {k:finding.get(k) for k in ('direction', 'impact', 'resolved_effect',
                'processing_status', 'interpretation', 'review_diagnostic')}
    signature = json.dumps([VERSION, stock['code'], article['id'], ledger['sha256'],
                            decision, article.get('duplicate_of'), bool(reusable), bool(decision_reusable),
                            result.get('prompt_version'), result.get('model')],
                           sort_keys=True, ensure_ascii=False)
    event_id = str(uuid.uuid5(uuid.NAMESPACE_URL, hashlib.sha256(signature.encode()).hexdigest()))
    published = timestamp(article['published'])
    available = max(published, timestamp(result['as_of']))
    return {'id':event_id, 'schema_version':VERSION, 'code':stock['code'], 'company':stock['name'],
            'article_id':article['id'], 'title':article['title'], 'url':article['url'],
            'publisher':article.get('publisher') or article.get('source'),
            'published':article['published'], 'available_at':available,
            'source_body_sha256':ledger['body_sha256'], 'ledger_sha256':ledger['sha256'],
            'facts':own, 'excluded_context':other,
            'joint_context':[f for f in other if subject_scope(stock,f.get('subject','')) == 'joint'],
            'condition_context':[f for f in ledger['facts'] if f.get('role') == 'condition'],
            'article_caveats':ledger.get('coverage_context', []),
            'decision':decision, 'reusable':bool(reusable),
            'decision_reusable':bool(decision_reusable),
            'judgment_record':{k:finding.get(k) for k in ('reason','counterpoint','evidence','processing_detail')},
            'event_types':sorted({f.get('event_kind', 'other') for f in own}),
            'duplicate_of':article.get('duplicate_of'),
            'model':result.get('model'), 'prompt_version':result.get('prompt_version'),
            'pipeline_version':result.get('pipeline_version'),
            'verification':'source_and_subject_checked',
            'statistical_label':None, 'human_reviewed':False}


def store(result, articles):
    by_id = {a['id']:a for a in articles}
    saved, rejected = [], []
    with db.connection() as con:
        setup(con)
        for finding in result.get('findings', []):
            article = by_id.get(finding['article_id'])
            try:
                if article is None:
                    raise ValueError('missing_source')
                event = prepare(result, article, finding)
            except (ValueError, KeyError, IndexError, TypeError):
                rejected.append(finding['article_id'])
                continue
            con.execute('INSERT OR IGNORE INTO news_events(id,code,article_id,available_at,reusable,payload,vector_status) VALUES(?,?,?,?,?,?,?)',
                        (event['id'],event['code'],event['article_id'],event['available_at'],
                         int(event['reusable']),json.dumps(event,ensure_ascii=False),
                         'pending' if event['reusable'] else 'not_eligible'))
            con.execute('INSERT OR IGNORE INTO news_event_runs VALUES(?,?)',(event['id'],result['run_id']))
            relations = [('about_company',event['code']),('reported_by_article',event['article_id'])]
            relations += [('supported_by_fact', f['id']) for f in event['facts']]
            if event['duplicate_of']:
                relations.append(('duplicate_of_article',event['duplicate_of']))
            for kind, target in relations:
                con.execute('INSERT OR IGNORE INTO news_event_relations VALUES(?,?,?)',(event['id'],kind,target))
            saved.append(event['id'])
    return {'saved_ids':saved, 'skipped_ids':rejected}


def records(code, limit=50):
    check_code(code)
    with db.connection() as con:
        setup(con)
        return [{**json.loads(r['payload']), 'vector_status':r['vector_status']} for r in con.execute(
            'SELECT payload,vector_status FROM news_events WHERE code=? ORDER BY available_at DESC LIMIT ?',
            (code,min(max(limit,1),100)))]


async def ensure_collection():
    listing = await dart_rag.qrequest('GET','/collections')
    if COLLECTION not in {c['name'] for c in listing['result']['collections']}:
        await dart_rag.qrequest('PUT',f'/collections/{COLLECTION}',json={
            'vectors':{'size':1536,'distance':'Cosine'}})
    for key, schema in [('code','keyword'),('reusable','bool'),('available_at','float')]:
        await dart_rag.qrequest('PUT',f'/collections/{COLLECTION}/index?wait=true',
                               json={'field_name':key,'field_schema':schema})


async def sync(code):
    check_code(code)
    with db.connection() as con:
        setup(con)
        pending = [json.loads(r[0]) for r in con.execute(
            "SELECT payload FROM news_events WHERE code=? AND reusable=1 AND vector_status!='indexed' LIMIT 50",(code,))]
    if not pending:
        return {'indexed':0,'status':'up_to_date'}
    await ensure_collection()
    # Only source facts enter embeddings, never the model's bullish/bearish wording.
    texts = [e['company']+'\n'+'\n'.join(f['event_quote'] for f in e['facts']) for e in pending]
    vectors = await dart_rag.embed(texts)
    if len(vectors) != len(pending):
        raise ValueError('Embedding count mismatch')
    await dart_rag.qrequest('PUT',f'/collections/{COLLECTION}/points?wait=true',json={'points':[
        {'id':e['id'],'vector':v,'payload':{'code':code,'reusable':True,'available_at':e['available_at']}}
        for e,v in zip(pending,vectors)]})
    with db.connection() as con:
        for e in pending:
            con.execute("UPDATE news_events SET vector_status='indexed' WHERE id=? AND code=?",(e['id'],code))
    return {'indexed':len(pending),'status':'indexed'}


async def persist(result, articles):
    summary = store(result, articles)
    try:
        summary.update(await asyncio.wait_for(sync(result['stock']['code']),35))
    except Exception:
        summary.update(status='pending_retry',indexed=0)
    return summary


async def search(code, query, as_of=None, limit=5):
    check_code(code)
    cutoff = timestamp(as_of) if as_of else time.time()
    limit = min(max(limit,1),20)
    with db.connection() as con:
        setup(con)
        if not con.execute("SELECT 1 FROM news_events WHERE code=? AND reusable=1 AND vector_status='indexed' LIMIT 1",(code,)).fetchone():
            return []
    vector = (await dart_rag.embed([query]))[0]
    found = await dart_rag.qrequest('POST',f'/collections/{COLLECTION}/points/query',json={
        'query':vector,'limit':min(limit*5,100),'with_payload':True,
        'filter':{'must':[{'key':'code','match':{'value':code}},
                          {'key':'reusable','match':{'value':True}},
                          {'key':'available_at','range':{'lte':cutoff}}]}})
    hits = []
    with db.connection() as con:
        for point in found['result']['points']:
            # Defense in depth: do not trust vector payloads for issuer isolation.
            row = con.execute('SELECT payload FROM news_events WHERE id=? AND code=? AND reusable=1 AND available_at<=?',
                              (str(point['id']),code,cutoff)).fetchone()
            if row is None:
                continue
            event = json.loads(row[0])
            # Use the latest revision available at the requested historical cutoff.
            latest = con.execute('''SELECT id FROM news_events WHERE code=? AND article_id=? AND available_at<=?
                ORDER BY available_at DESC,rowid DESC LIMIT 1''',(code,event['article_id'],cutoff)).fetchone()
            if latest is None or latest[0] != event['id']:
                continue
            hits.append({k:event[k] for k in ('id','code','company','title','url','published',
                         'facts','condition_context','article_caveats','event_types','available_at',
                         'human_reviewed','statistical_label')})
            hits[-1]['decision_reusable'] = event.get('decision_reusable',False)
            hits[-1]['joint_context'] = event.get('joint_context',[])
            hits[-1]['decision'] = (event['decision'] if event.get('decision_reusable') else
                                   {'processing_status':event['decision']['processing_status'],
                                    'detail':'판단 재사용 제외 · 확인된 사실만 검색했습니다.'})
            hits[-1]['similarity'] = point['score']
            hits[-1]['usage_note'] = ('과거 분석 기록이며 정답·주가 상승 확률이 아닙니다. '
                'facts의 subject가 귀속 주체이며 quote는 원문 문단 전체라 타사 언급을 포함할 수 있습니다. '
                'joint_context·condition_context·article_caveats는 별도 문맥이며 해당 기업의 단독 실적이 아닙니다.')
    return hits[:limit]
