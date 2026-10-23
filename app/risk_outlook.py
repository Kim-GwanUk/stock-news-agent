"""Conditional risk scenarios from report observations, not calibrated predictions."""
from datetime import date
import re


def news_scenarios(report, fresh):
    """Join issuer-owned frozen event quotes to dated observations, never title keywords."""
    stock=report.get('stock',{})
    name=stock.get('name','해당 종목')
    last=report.get('prices',{}).get('last',{})
    market=[]
    if fresh(last.get('date')) and last.get('change_pct') is not None:
        market.append(f"{name} {last['date']} 종가 {last['change_pct']:+.2f}%")
    for item in report.get('macro',[]):
        if item.get('status')=='ok' and item['name'] in ('KOSPI','KOSDAQ','나스닥 종합') and fresh(item.get('date')):
            delta=item.get('change_pct',item.get('change'))
            if delta is not None:
                market.append(f"{item['name']} {delta:+.2f}{'%' if 'change_pct' in item else 'pt'} ({item['date']})")
    context=' · '.join(market[:3]) or '연결할 최신 가격·시장 지표 미확보'
    patterns={
        'shareholder_return':('주주환원 집행 조건 확인', '주주환원 계획의 집행이 지연되거나 범위가 축소되면 기대와 실제 효과가 달라질 수 있습니다.', '매입·소각·배당 중 무엇이 완료됐고 무엇이 예정인지, 실제 집행 공시를 확인하세요.'),
        'earnings':('실적과 시장 흐름의 괴리', '시장 전체가 반등하더라도 이 실적 이슈가 해소됐다고 볼 수 없습니다. 후속 실적 전망이 기사에 나온 기대보다 낮아지면 종목의 부담이 커질 수 있습니다.', '실제 발표 실적과 전망치를 구분하고, 매출보다 영업이익·이익률 변화도 확인하세요.'),
        'development':('투자 집행과 성과 사이의 간격', '투자·개발이 진행돼도 매출과 이익 발생은 별도입니다. 비용 집행이 앞서고 사업 성과 확인이 늦어지면 기대 조정이 생길 수 있습니다.', '투자 확정 여부, 집행 일정과 수익 발생 조건을 확인하세요.'),
        'funding':('자금 수령 조건과 일정', '보도된 조달 계획이 실제 수령으로 이어지지 않거나 지급 조건이 남아 있다면 자금 확보 기대가 조정될 수 있습니다.', '확정 금액과 최대 한도, 선급금과 단계별 지급액, 승인·종결 조건을 구분하세요.'),
        'sales':('계약·수요의 실적 반영 조건', '계약·수요 기대가 있더라도 인도·검수·대금 지급 조건이 남아 있다면 매출 인식이 늦어질 수 있습니다.', '확정 계약인지 전망인지, 실제 납품 일정과 기사에 명시된 조건을 확인하세요.'),
        'cost_risk':('사건의 비용·운영 영향 확대', '기사의 사건이 추가 비용이나 운영 차질로 확대되면 시장 반등과 별개로 종목에 부담이 될 수 있습니다.', '적용 대상·지역·기간과 실제 손실 확정 여부, 회사의 후속 공시를 확인하세요.')}
    cards=[]; seen=set()
    entries=report.get('risk_news',[n for direction in ('하락 요인','상승 요인') for n in report.get('news',{}).get(direction,[])])
    for entry in entries:
        f=entry.get('finding',{}); a=entry.get('article',{})
        ledger=f.get('fact_ledger',{})
        if f.get('processing_status')!='분석 완료' or ledger.get('target_stock',{}).get('code')!=stock.get('code'):
            continue
        norm=lambda s:re.sub(r'\s','',s).casefold()
        facts=[x for x in ledger.get('facts',[]) if x.get('target_eligible') is True
               and norm(x.get('subject',''))==norm(name) and x.get('event_quote')
               and x['event_quote'] in x.get('quote','')]
        main=next((x for x in facts if x.get('role')=='main' and x.get('event_kind') in patterns),None)
        if not main: continue
        kind=main['event_kind']; quote=main['event_quote']
        signals={'shareholder_return':('자사주','배당','소각'), 'earnings':('매출','영업이익','순이익','실적'),
                 'development':('투자','개발','증설','착공','인프라','구축','연구','조직'), 'funding':('대출','조달','회사채','유상증자','보조금'),
                 'sales':('공급 계약','수주','납품','판매','수요'), 'cost_risk':('리콜','제재','벌금','사고','중단','손실','소송')}
        if not any(term in quote for term in signals[kind]): continue
        if kind=='sales' and any(term in quote for term in ('지분','주식 매각')): continue
        # One representative per event category, so syndicated buyback reports do not fill the outlook.
        category=kind
        if kind=='development':
            category+=':infrastructure' if any(t in quote for t in ('인프라','용수','도로')) else ':research' if any(t in quote for t in ('조직','연구','코어팀')) else ':investment'
        if category in seen: continue
        seen.add(category)
        title,scenario,watch=patterns[kind]
        if kind=='development' and any(t in quote for t in ('인프라','용수','도로')):
            title='인프라 확보와 사업 진행 조건'
            scenario='기사에서 확인된 것은 인프라 구축 요청입니다. 필요한 인프라의 승인·공급 일정이 정해지지 않으면 사업 진행 시점을 확정할 수 없습니다. 이미 지연이 발생했다는 뜻은 아닙니다.'
            watch='요청에 대한 당국의 답변과 확정된 인프라 공급 일정, 회사의 사업 일정을 확인하세요.'
        elif kind=='development' and any(t in quote for t in ('조직','연구','코어팀')):
            title='연구 조직 신설과 사업 성과의 간격'
            scenario='개발 조직 신설·운영은 확인되지만 제품 개발 성공이나 양산·이익 발생까지 확인된 것은 아닙니다. 조직 개편 소식을 곧바로 실적 개선으로 반영하는 기대에는 불확실성이 남습니다.'
            watch='조직 신설 이후 실제 개발 성과·양산 발표가 나오는지 확인하세요.'
        if kind=='shareholder_return' and '매입' in quote and any(w in quote for w in ('완료','마무리','종료')):
            title='자사주 매입 완료 이후 수급 확인'
            scenario='기사에 나온 자사주 매입이 끝난 만큼, 그 매입 수요가 오늘도 계속된다고 가정하면 안 됩니다. 소각 예정은 실제 소각 완료와 구분해야 합니다.' if '소각' in quote and '예정' in quote else '기사에 나온 자사주 매입이 끝난 만큼, 그 매입 수요가 오늘도 계속된다고 가정하면 안 됩니다.'
            watch='회사 매입 종료 후에도 거래량과 가격 흐름이 유지되는지, 추가 주주환원은 확정 공시인지 확인하세요.'
        conditions=[x['event_quote'] for x in facts if x.get('role')=='condition']
        if fresh(last.get('date')) and last.get('change_pct') is not None:
            delta=last['change_pct']
            scenario=f"최근 거래일 {name}는 {delta:+.2f}% 움직였습니다. "+scenario
        nasdaq=next((x for x in report.get('macro',[]) if x.get('name')=='나스닥 종합'
                     and x.get('status')=='ok' and fresh(x.get('date'))),None)
        if nasdaq and nasdaq.get('change',0)>0:
            scenario+=' 나스닥 상승은 시장 배경이지만, 이 사건의 집행·성과를 보장하는 근거는 아닙니다.'
        elif nasdaq and nasdaq.get('change',0)<0:
            scenario+=' 나스닥 약세까지 국내 투자심리에 이어진다면 사건의 불확실성과 시장 부담이 겹칠 수 있습니다.'
        summaries={
            'shareholder_return':'주주환원 계획의 집행 지연·축소 시 기대 조정 가능성이 있습니다.',
            'earnings':'보도된 실적과 후속 이익 전망이 어긋나면 기대 조정 가능성이 있습니다.',
            'development':'투자·개발 비용이 성과보다 앞서면 실적 기대에 부담이 될 수 있습니다.',
            'funding':'조달 금액의 실제 수령 여부는 남은 지급·승인 조건에 달려 있습니다.',
            'sales':'계약·수요 기대가 실제 매출로 이어지는 시점과 조건은 별도 확인이 필요합니다.',
            'cost_risk':'보도된 사건의 비용·운영 영향이 확대되면 추가 부담이 될 수 있습니다.'}
        summary=summaries[kind]
        if category.endswith(':infrastructure'):
            summary='인프라 구축은 요청 단계로, 승인·공급 일정에 따라 사업 진행 시점이 달라질 수 있습니다.'
        elif category.endswith(':research'):
            summary='연구 조직 신설이 제품 개발·양산 성과로 이어질지는 아직 확인되지 않았습니다.'
        if title=='자사주 매입 완료 이후 수급 확인':
            summary='자사주 매입이 완료돼 해당 매수 수요의 지속을 전제하기 어렵습니다.'
            if '소각' in quote and '예정' in quote: summary+=' 소각은 아직 예정입니다.'
        cards.append({'title':name+' · '+title,'scenario':scenario,'factor':title,'summary':summary,
                      'evidence':context,'watch':watch,'url':a.get('url'),
                      'news_title':a.get('title',''),'facts':[quote]+conditions,
                      'connection':'종목 사건의 이행 위험을 가격·시장 흐름과 함께 보는 시나리오입니다. 해당 뉴스가 등락의 원인이라는 판단은 아닙니다.'})
    return cards[:3]


def outlook(report):
    prices=report.get('prices',{})
    last=prices.get('last',{})
    today=date.fromisoformat(report['report_date'])
    items=[]
    gaps=[]
    def fresh(day):
        try: return 0<(today-date.fromisoformat(day)).days<=4
        except (ValueError,TypeError): return False
    vol=prices.get('volatility20')
    change=last.get('change_pct')
    if fresh(last.get('date')) and vol is not None:
        elevated=vol>=3 or (change is not None and abs(change)>=3)
        items.append({'title':'장중 가격 변동 주의' if elevated else '가격 흐름 변화 주의',
            'scenario':('최근처럼 큰 가격 움직임이 이어진다면 오늘도 장중 등락 폭이 커질 수 있습니다.'
                        if elevated else '최근 변동 폭은 비교적 작지만, 새 뉴스가 나오면 기존 흐름이 달라질 수 있습니다.'),
            'evidence':f"{last['date']} 기준 일간 수익률 변동성 {vol:.2f}%"+(f" · 최근 거래일 {change:+.2f}%" if change is not None else ''),
            'watch':'장 초반 등락 폭과 거래량이 최근 수준보다 커지는지 확인하세요.'})
    else: gaps.append('최근 가격·변동성 근거 부족')
    negative=report.get('news',{}).get('하락 요인',[])
    if negative:
        article=negative[0]['article']
        items.append({'title':'부정 이슈 재부각 가능성',
            'scenario':'해당 부정 이슈가 오늘 추가 보도로 확대되거나 실제 사업 차질로 확인되면 매도 압력이 커질 수 있습니다.',
            'evidence':article['title'],'url':article.get('url'),
            'watch':'회사의 공식 해명, 실제 발생 여부와 영향 범위를 함께 확인하세요.'})
    macro={x['name']:x for x in report.get('macro',[]) if x.get('status')=='ok'}
    market_name='KOSDAQ' if report.get('stock',{}).get('market')=='KOSDAQ' else 'KOSPI'
    domestic=macro.get(market_name)
    if domestic and fresh(domestic.get('date')) and domestic.get('change_pct',domestic.get('change',0))<0:
        delta=domestic.get('change_pct',domestic.get('change'))
        unit='%' if domestic.get('change_pct') is not None else 'pt'
        items.append({'title':'국내 증시 약세','factor':market_name+' 하락',
            'summary':f'{market_name} {delta:+.2f}{unit}; 시장 약세가 이어지면 종목에도 매도 압력이 전해질 수 있습니다.',
            'scenario':'지수 약세의 지속 여부를 보는 조건부 전망이며 개별 종목의 하락을 확정하지 않습니다.',
            'evidence':f"{domestic['date']} · {market_name} {delta:+.2f}{unit}",
            'watch':'종목과 시장의 등락이 같은 방향인지 확인하세요.'})
    for rate_name in ('한국 기준금리','미국 정책금리 상단'):
        rate=macro.get(rate_name)
        if rate and fresh(rate.get('date')) and (rate.get('change') or 0)>0:
            items.append({'title':'금리 상승','factor':rate_name,
                'summary':f"{rate['value']:.2f}%로 상승; 높은 조달 비용이 이어지면 기업의 이자 부담이 커질 수 있습니다.",
                'scenario':'금리 상승에 대한 조건부 전망입니다. 이 종목의 순부채·고정금리 비중을 확인하기 전에는 실제 비용 증가를 단정하지 않습니다.',
                'evidence':f"{rate['date']} · 직전 관측 대비 {rate['change']:+.2f}%p",
                'watch':'회사의 차입 규모와 금리 조건을 확인하세요.'})
    falling=[x for name,x in macro.items() if name in ('S&P 500','나스닥 종합')
             and fresh(x.get('date')) and x.get('change',0)<0]
    if falling:
        items.append({'title':'해외 증시 약세 전이 가능성',
            'scenario':'미국 증시의 약세가 국내 투자심리로 이어진다면 오늘 장 초반 부담이 될 수 있습니다. 이 종목의 하락을 뜻하지는 않습니다.',
            'evidence':' · '.join(f"{x['name']} {x['change']:+.2f}pt ({x['date']})" for x in falling),
            'watch':'국내 시장·동종 업종도 함께 약세를 보이는지 확인하세요.'})
    fx=macro.get('원/달러 환율')
    if fx and fresh(fx.get('date')) and fx.get('change',0)>0:
        items.append({'title':'환율 상승에 따른 비용 변수',
            'scenario':'원화 약세가 이어진다면 달러 비용·외화부채 부담이 커질 수 있습니다. 수출 매출과 환헤지에 따라 순영향은 달라집니다.',
            'evidence':f"원/달러 {fx['value']:,.2f}원 · 직전 관측 대비 {fx['change']:+.2f}원 ({fx['date']})",
            'watch':'종목의 외화 매출·비용과 환헤지 근거가 없으면 순악재로 단정하지 않습니다.'})
    elif not fx or not fresh(fx.get('date')): gaps.append('환율 자료 지연 또는 미확보')
    if report.get('news_counts',{}).get('incomplete'): gaps.append('일부 뉴스 분석 미완료')
    if any(x.get('status')!='ok' for x in report.get('macro',[])): gaps.append('일부 시장 지표 미확보')
    if len(items)<2:
        items.append({'title':'새 이슈에 따른 전망 변경 가능성',
            'scenario':'현재 확보한 자료만으로 추가적인 하락 위험을 구체화하기 어렵습니다. 장 시작 전후 새 공시·뉴스가 나오면 전망을 다시 확인해야 합니다.',
            'evidence':'분석 완료된 부정 뉴스 '+str(len(negative))+'건 · 조회 범위 내 결과',
            'watch':'부정 뉴스가 없다는 사실을 저위험 신호로 해석하지 않습니다.'})
    specific=news_scenarios(report,fresh)
    if specific:
        market_items=[x for x in items if x['title'] not in ('부정 이슈 재부각 가능성','새 이슈에 따른 전망 변경 가능성','장중 가격 변동 주의','가격 흐름 변화 주의')]
        items=(specific[:2]+market_items[:1]) if market_items else specific
    else:
        gaps.append('종목 주체가 확인된 사건·조건 근거 부족: 뉴스와 지표를 직접 연결하지 않음')
        if len(items)>1:
            items=[x for x in items if x['title']!='새 이슈에 따른 전망 변경 가능성']
    summaries={
        '장중 가격 변동 주의':('주가 변동',f'최근 거래일 {change:+.2f}% 등락; 큰 가격 움직임이 이어질 경우 장중 변동에 주의가 필요합니다.' if change is not None else '최근 변동성이 커 오늘도 장중 등락 폭이 커질 수 있습니다.'),
        '가격 흐름 변화 주의':('주가 흐름','최근 변동 폭이 작아도 새로운 공시·뉴스에 따라 흐름이 달라질 수 있습니다.'),
        '해외 증시 약세 전이 가능성':('미국 증시','미국 지수 약세가 국내 투자심리로 이어지면 종목에도 부담이 될 수 있습니다.'),
        '환율 상승에 따른 비용 변수':('환율 상승','원화 약세가 이어지면 달러 비용 부담이 커질 수 있으나 수출·환헤지에 따라 순영향은 달라집니다.'),
        '새 이슈에 따른 전망 변경 가능성':('근거 부족','확보한 자료만으로 종목의 추가 하락 위험을 구체화하기 어렵습니다.')}
    for item in items:
        if 'summary' not in item:
            item['factor'],item['summary']=summaries.get(item['title'],(item['title'],item['scenario']))
    return {'items':items[:3],'gaps':gaps,
            'method':'관측값 기반 조건부 시나리오입니다. 예측 정확도를 검증한 모델이나 하락 확률이 아닙니다. 가격 주의 기준: 20일 변동성 또는 최근 거래일 절대 등락률 3% 이상. 최신성은 보고서 전 4일 이내 관측으로 제한합니다.'}
