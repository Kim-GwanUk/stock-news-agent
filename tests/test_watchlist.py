from app.watchlist import filter_stocks
from app import db
from app.models import Stock

def test_search_and_kind_filters():
    stocks=[{'code':'005930','name':'삼성전자','kind':'관심'}, {'code':'005935','name':'삼성전자우','kind':'보유'}]
    assert len(filter_stocks(stocks,'삼성'))==2
    assert filter_stocks(stocks,'005935')[0]['name']=='삼성전자우'
    assert filter_stocks(stocks,'삼성','보유')==[stocks[1]]
    assert filter_stocks(stocks,'없는회사')==[]

def test_single_registration_and_bulk_over_five(monkeypatch,tmp_path):
    monkeypatch.setattr(db,'DATA',tmp_path)
    for i in range(12): db.add_stock(Stock(code=str(i).zfill(6),name=f'종목{i}',market='KOSPI'))
    assert len(db.stocks())==12
    assert len(db.import_stocks([{'code':str(i).zfill(6),'name':str(i),'market':'KOSPI','kind':'관심'} for i in range(10,40)]))==28
    assert len(db.stocks())==40
