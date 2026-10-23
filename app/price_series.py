"""Daily observations only; never interpolate intraday prices."""
from datetime import date, timedelta


def build_series(rows, failed_dates=()):
    daily = [dict(r) for r in sorted(rows, key=lambda r:r['date'])]
    failures = {x.replace('-', '') for x in failed_dates}
    for i,r in enumerate(daily):
        window=daily[max(0,i-4):i+1]
        complete=len(window)==5 and not any(window[0]['date'].replace('-','') <= d <= r['date'].replace('-','') for d in failures)
        r['ma5']=sum(x['close'] for x in window)/5 if complete else None
        r['ma5_pct']=(r['close']/r['ma5']-1)*100 if r['ma5'] else None
    groups={}
    for r in daily:
        day=date.fromisoformat(r['date']); monday=day-timedelta(days=day.weekday())
        groups.setdefault(monday.isoformat(),[]).append(r)
    weekly=[]
    for start,part in groups.items():
        end=(date.fromisoformat(start)+timedelta(days=4)).isoformat()
        missing=any(start.replace('-','')<=d<=end.replace('-','') for d in failures)
        weekly.append({'date':start,'end':part[-1]['date'],'open':part[0].get('open'),
          'high':max((r['high'] for r in part),default=None) if all(r.get('high') is not None for r in part) and not missing else None,
          'low':min((r['low'] for r in part),default=None) if all(r.get('low') is not None for r in part) and not missing else None,
          'close':part[-1]['close'],'volume':sum(r['volume'] for r in part),
          'status':'일부 조회 실패' if missing else '조회 범위 내 집계', 'ma5':None})
    return daily,weekly
