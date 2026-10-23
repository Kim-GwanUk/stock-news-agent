"""On-demand morning preview. No scheduling, email, or price predictions."""
import asyncio
import csv
import io
import os
import re
import statistics
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree
import httpx
from bs4 import BeautifulSoup
from app import db, providers, graph
from app.price_series import build_series

BOK = 'https://www.bok.or.kr/portal/singl/baseRate/list.do?dataSeCd=01&menuNo=200643'
FED_FEED = 'https://www.federalreserve.gov/feeds/press_monetary.xml'

async def fed_releases(cutoff):
    """Official titles only; do not infer a stock-specific effect from a headline."""
    try:
        async with httpx.AsyncClient(timeout=20,follow_redirects=True) as client:
            response=await client.get(FED_FEED)
            response.raise_for_status()
        items=[]
        for item in ElementTree.fromstring(response.content).findall('.//item'):
            stamp=article_time(item.findtext('pubDate'))
            link=item.findtext('link','')
            if stamp and stamp<cutoff and link.startswith('https://www.federalreserve.gov/'):
                items.append({'title':item.findtext('title',''), 'url':link, 'published':stamp.isoformat()})
        items.sort(key=lambda item:item['published'],reverse=True)
        return {'status':'ok','items':items[:3],'source':FED_FEED}
    except Exception:
        return {'status':'unavailable','items':[],'source':FED_FEED}

def article_time(value):
    try:
        try: stamp = datetime.fromisoformat(value.replace('Z','+00:00'))
        except ValueError: stamp = parsedate_to_datetime(value)
        return stamp.astimezone(providers.KST) if stamp.tzinfo else None
    except (TypeError, ValueError, AttributeError):
        return None

def indicators(raw, today):
    rows = [r for r in raw.get('items',[]) if r['date'] < today]
    daily,_ = build_series(rows,raw.get('failed_dates',[]))
    last = daily[-1] if daily else {}
    # Five daily returns need six closes; no synthetic holiday/weekend prices.
    failures = {d.replace('-','') for d in raw.get('failed_dates',[])}
    def complete(n):
        return len(daily)>=n and not any(daily[-n]['date'].replace('-','')<=d<=last['date'].replace('-','') for d in failures)
    returns = [(daily[i]['close']/daily[i-1]['close']-1)*100 for i in range(1,len(daily))]
    volume_mean = statistics.mean(r['volume'] for r in daily[-21:-1]) if complete(21) else None
    return {'days':daily[-5:], 'last':last,
            'return5':(last['close']/daily[-6]['close']-1)*100 if complete(6) else None,
            'volatility20':statistics.stdev(returns[-20:]) if complete(21) else None,
            'volume_ratio':last['volume']/volume_mean if volume_mean else None,
            'failed_dates':raw.get('failed_dates',[])}

async def fred(client, series, name, unit, today):
    source='https://fred.stlouisfed.org/series/'+series
    try:
        response=await client.get('https://fred.stlouisfed.org/graph/fredgraph.csv',params={
            'id':series,'cosd':(today-timedelta(days=45)).isoformat()})
        response.raise_for_status()
        rows=[r for r in csv.DictReader(io.StringIO(response.text))
              if r.get(series) not in (None,'','.') and r.get('observation_date','9999')<today.isoformat()]
        last=rows[-1]
        value=float(last[series])
        prev=float(rows[-2][series]) if len(rows)>1 else None
        return {'name':name,'value':value,'unit':unit,'date':last['observation_date'],
                'change':value-prev if prev is not None else None,'source':source,'status':'ok',
                'note':'최근 제공 관측값 · 실시간 시세 아님'}
    except Exception:
        return {'name':name,'status':'unavailable','source':source,'note':'공식 자료 조회 실패'}

async def bok(client,today):
    try:
        response=await client.get(BOK)
        response.raise_for_status()
        soup=BeautifulSoup(response.text,'html.parser')
        rows=[]
        for tr in soup.select('table tr'):
            text=tr.get_text(' ',strip=True)
            match=re.search(r'(20\d{2})\s+(\d{2})월\s+(\d{2})일\s+(\d+\.\d+)',text)
            if match:
                y,m,d,rate=match.groups()
                day=f'{y}-{m}-{d}'
                if day<today.isoformat(): rows.append((day,float(rate)))
        rows.sort()
        day,rate=rows[-1]
        return {'name':'한국 기준금리','value':rate,'unit':'%','date':day,'source':BOK,'status':'ok',
                'change':rate-rows[-2][1] if len(rows)>1 else None,'note':'날짜는 최근 변경일 · 변화는 직전 결정 대비 %p'}
    except Exception:
        return {'name':'한국 기준금리','status':'unavailable','source':BOK,'note':'공식 금리 표 확인 실패'}

async def krx_index(client,market,today):
    path='kospi_dd_trd' if market=='KOSPI' else 'kosdaq_dd_trd'
    source='https://openapi.krx.co.kr/'
    try:
        for offset in range(1,8):
            day=today-timedelta(days=offset)
            if day.weekday()>4: continue
            response=await client.get('https://data-dbg.krx.co.kr/svc/apis/idx/'+path,
                params={'basDd':day.strftime('%Y%m%d')},headers={'AUTH_KEY':os.environ['KRX_API_KEY']})
            if response.status_code in (401,403):
                return {'name':market,'status':'unavailable','source':source,'note':'KRX 지수 API 이용 승인·권한 확인 필요'}
            response.raise_for_status()
            row=next((r for r in response.json().get('OutBlock_1',[]) if r.get('IDX_NM') in (market, '코스피' if market=='KOSPI' else '코스닥')),None)
            if row:
                return {'name':market,'value':float(row['CLSPRC_IDX'].replace(',','')),'unit':'pt',
                        'date':day.isoformat(),'source':source,'status':'ok','change_pct':float(row['FLUC_RT']),
                        'note':'직전 제공 거래일 종가'}
        raise ValueError()
    except Exception:
        return {'name':market,'status':'unavailable','source':source,'note':'지수 조회 실패 또는 자료 없음'}

async def macro(today):
    key='morning-macro-v1:'+today.isoformat()
    cached=db.cached(key)
    if cached: return cached
    async with httpx.AsyncClient(timeout=20,follow_redirects=True) as client:
        items=await asyncio.gather(bok(client,today),
            fred(client,'DEXKOUS','원/달러 환율','원/USD',today),
            fred(client,'DFEDTARL','미국 정책금리 하단','%',today),
            fred(client,'DFEDTARU','미국 정책금리 상단','%',today),
            fred(client,'SP500','S&P 500','pt',today),
            fred(client,'NASDAQCOM','나스닥 종합','pt',today),
            krx_index(client,'KOSPI',today),krx_index(client,'KOSDAQ',today))
    db.cache_put(key,items,1800)
    return items

def news_sections(result,start,cutoff):
    groups={'상승 요인':[],'하락 요인':[]}
    findings={f['article_id']:f for f in result.get('findings',[])}
    counts={'outside_window':result.get('collection',{}).get('outside_window',0),
            'incomplete':0,'uncertain':0,'excluded':0}
    seen=set()
    for a in sorted(result.get('articles',[]),key=lambda a:a.get('published',''),reverse=True):
        stamp=article_time(a.get('published'))
        if stamp is None or not start<=stamp<cutoff:
            counts['outside_window']+=1
            continue
        f=findings.get(a['id'],{})
        if a.get('duplicate_of') or not a.get('analysis_candidate',a.get('relevant')):
            counts['excluded']+=1
            continue
        if f.get('processing_status')!='분석 완료':
            counts['incomplete']+=1
            continue
        direction=f.get('direction')
        if direction not in groups:
            counts['uncertain']+=1
            continue
        title=re.sub(r'\W','',a['title'])
        if title in seen: continue
        seen.add(title)
        groups[direction].append({'article':a,'finding':f})
    return {k:v[:3] for k,v in groups.items()},counts

async def create(stock):
    now=datetime.now(providers.KST)
    cutoff=min(now,now.replace(hour=8,minute=0,second=0,microsecond=0))
    warnings=[]
    prices,market,policy=await asyncio.gather(providers.price_history(stock,45),macro(now.date()),
                                            fed_releases(cutoff),return_exceptions=True)
    if isinstance(prices,Exception):
        prices={'items':[]}
        warnings.append('KRX 시세 조회에 실패했습니다. 가격 지표를 계산하지 않았습니다.')
    if isinstance(market,Exception):
        market=[]
        warnings.append('시장 지표 조회에 실패했습니다.')
    if isinstance(policy,Exception):
        policy={'status':'unavailable','items':[],'source':FED_FEED}
    metrics=indicators(prices,now.date().isoformat())
    # Include weekend/holiday news since the most recent observed trading day at 08:00.
    lastdate=metrics['last'].get('date',(now-timedelta(days=1)).date().isoformat())
    start=datetime.fromisoformat(lastdate).replace(hour=8,tzinfo=providers.KST)
    try:
        result=await graph.run(stock,news_window={'start':start.isoformat(),'end':cutoff.isoformat()})
    except Exception:
        result={}
        warnings.append('뉴스 분석을 완료하지 못했습니다. 이전 결과를 새 보고서 뉴스로 대체하지 않았습니다.')
    groups,counts=news_sections(result,start,cutoff)
    finding_map={f['article_id']:f for f in result.get('findings',[])}
    risk_news=[]
    for a in result.get('articles',[]):
        f=finding_map.get(a['id'],{})
        stamp=article_time(a.get('published'))
        if (stamp and start<=stamp<cutoff and not a.get('duplicate_of')
                and a.get('analysis_candidate',a.get('relevant')) and f.get('processing_status')=='분석 완료'):
            risk_news.append({'article':a,'finding':f})
    notes=[]
    if metrics['return5'] is not None:
        notes.append(f"최근 5거래일 누적 등락률은 {metrics['return5']:+.2f}%입니다. 과거 가격 변화이며 오늘 방향을 예측하지 않습니다.")
    if metrics['volatility20'] is not None:
        notes.append(f"최근 20개 일간 수익률의 변동성은 {metrics['volatility20']:.2f}%입니다. 거래량은 직전 20거래일 평균의 {metrics['volume_ratio']:.2f}배입니다." if metrics['volume_ratio'] is not None else f"최근 20개 일간 수익률 변동성은 {metrics['volatility20']:.2f}%입니다.")
    notes.append(f"확인된 부정 요인 뉴스는 {len(groups['하락 요인'])}건, 분석 미완료는 {counts['incomplete']}건입니다. 뉴스가 없다는 것이 위험이 없다는 뜻은 아닙니다.")
    report={'stock':stock,'generated_at':now.isoformat(),'report_date':now.date().isoformat(),
        'news_start':start.isoformat(),'news_cutoff':cutoff.isoformat(),'prices':metrics,'macro':market,
        'news':groups,'news_counts':counts,'notes':notes[:3],'policy':policy,'risk_news':risk_news,
        'warnings':warnings+result.get('warnings',[]),'analysis_run_id':result.get('run_id'),
        'limitations':['오전 8시 발행시각 기준 미리보기입니다. 당시 수집본을 보관한 과거 시점 재현 보고서는 아닙니다.',
                        '최신 검색 결과 최대 1,000건에서 기간 내 최대 20건을 선별하고, 영향 분석 최대 5건 중 방향별 최대 3건을 표시합니다.',
                        '오늘의 경제 발표 일정과 업종 대비 PER·PBR·ROE는 아직 연결하지 않았습니다.']}
    db.cache_put('morning-report-v1:'+stock['code'],report,86400*7)
    return report

