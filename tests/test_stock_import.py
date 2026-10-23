import base64
import pytest
from app.stock_import import inspect_csv
from app import db

CATALOG=[{'code':'005930','name':'삼성전자','market':'KOSPI','as_of':'20261021'},
         {'code':'005380','name':'현대차','market':'KOSPI','as_of':'20261021'}]

def test_preview_duplicates_unknown_and_code_name_conflict():
    rows=inspect_csv('종목코드,종목명,구분\n5930,삼성전자,관심\n005380,현대차,보유\n005380,,관심\n999999,비상장회사,관심\n005930,현대차,관심\n'.encode(),CATALOG,[CATALOG[0]])
    assert [r['valid'] for r in rows]==[False,True,False,False,False]
    assert '이미 등록' in rows[0]['status']
    assert '중복' in rows[2]['status']
    assert '목록에 없음' in rows[3]['status']
    assert '일치하지' in rows[4]['status']

@pytest.mark.parametrize('encoding',['utf-8-sig','cp949'])
def test_exact_name_and_encodings(encoding):
    rows=inspect_csv('종목명,구분\n삼성전자,보유\n삼성,관심'.encode(encoding),CATALOG,[])
    assert rows[0]['code']=='005930' and rows[0]['valid']
    assert not rows[1]['valid']

@pytest.mark.parametrize('content',['a,b\n1,2','code,종목코드\n1,2','code\n','code,kind\n005930,매수','code\n=5930'])
def test_malformed_and_invalid(content):
    try: rows=inspect_csv(content.encode(),CATALOG,[])
    except ValueError: return
    assert not any(r['valid'] for r in rows)

def test_unlimited_import_and_idempotency(monkeypatch,tmp_path):
    monkeypatch.setattr(db,'DATA',tmp_path)
    stocks=[{'code':str(i).zfill(6),'name':str(i),'market':'KOSPI','kind':'관심'} for i in range(6)]
    assert len(db.import_stocks(stocks))==6
    assert len(db.stocks())==6
    assert db.import_stocks([{**stocks[0],'kind':'보유'}])==[]
    assert db.stocks()[0]['kind']=='관심'

def test_endpoints_reject_tampering_and_recheck(monkeypatch,tmp_path):
    import asyncio
    from app import api,providers
    from fastapi import HTTPException
    monkeypatch.setattr(db,'DATA',tmp_path)
    async def catalog(): return CATALOG
    monkeypatch.setattr(providers,'stock_catalog',catalog)
    async def run():
        p=await api.preview_csv(api.CsvPreview(content=base64.b64encode(b'code\n005380\n999999').decode()))
        assert db.stocks()==[]
        with pytest.raises(HTTPException):
            await api.commit_csv(api.CsvCommit(token=p['token'],rows=[3]))
        result=await api.commit_csv(api.CsvCommit(token=p['token'],rows=[2]))
        assert len(result['added'])==1
        assert (await api.commit_csv(api.CsvCommit(token=p['token'],rows=[2])))['skipped']==1
    asyncio.run(run())
