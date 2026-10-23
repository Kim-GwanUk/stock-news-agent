import pytest
from app.price_series import build_series

def rows():
    return [dict(date=f'2026-10-{d:02}',open=100+i,high=110+i,low=90+i,close=100+10*i,volume=10+i,change_pct=1) for i,d in enumerate([12,13,14,15,16,19])]

def test_average_and_week_boundaries():
    daily,weekly=build_series(rows())
    assert daily[3]['ma5'] is None
    assert daily[4]['ma5']==120
    assert daily[5]['ma5']==130
    assert daily[4]['ma5_pct']==pytest.approx((140/120-1)*100)
    assert len(weekly)==2
    assert weekly[0]['open']==100 and weekly[0]['close']==140
    assert weekly[0]['high']==114 and weekly[0]['low']==90
    assert weekly[0]['volume']==60
    assert weekly[1]['close']==150

def test_failed_day_disables_average_and_week_extremes():
    data=rows();data.pop(2)
    daily,weekly=build_series(data,['20261014'])
    assert daily[-1]['ma5'] is None
    assert weekly[0]['high'] is None and weekly[0]['status']=='일부 조회 실패'

def test_missing_ohlc_does_not_invent_prices():
    _,weeks=build_series([dict(date='2026-10-19',close=100,volume=0)])
    assert weeks[0]['open'] is None and weeks[0]['low'] is None
