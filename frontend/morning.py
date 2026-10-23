import streamlit as st
import pandas as pd
import altair as alt
from app.news_display import presentation

def number(value, suffix='',signed=False):
    if value is None: return '확인 불가'
    return (f'{value:+,.2f}' if signed else f'{value:,.2f}')+suffix

def show(stock,api):
    st.subheader('아침 보고서')
    st.caption('오전 8시 기준 뉴스 · 전일까지 제공된 거래일 시세 · 자동 발송 없는 미리보기')
    if st.button('보고서 생성 · 새로고침',type='primary',key='morning_generate'):
        with st.status('시세·시장 지표·뉴스를 확인하고 있습니다',expanded=True) as progress:
            st.write('최대 5분 정도 걸릴 수 있습니다. 검증된 뉴스만 방향별 최대 3건 포함합니다.')
            report=api('POST','/reports/morning/'+stock['code'],timeout=330)
            progress.update(label='보고서 생성 완료' if report else '보고서 생성 실패',state='complete' if report else 'error',expanded=False)
    report=api('GET','/reports/morning/'+stock['code'])
    if not report:
        st.info('보고서를 생성하면 이곳에서 종목별 내용을 확인할 수 있습니다.')
        return
    st.markdown(f"### {report['report_date']} · {stock['name']}")
    st.caption('실제 생성 시각 '+report['generated_at'][:19].replace('T',' ')+' KST')
    from datetime import datetime
    from zoneinfo import ZoneInfo
    if report['report_date']!=datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat():
        st.warning('이전 날짜의 보고서입니다. 오늘 자료는 새로고침해 주세요.')
    p=report['prices']; last=p['last']
    with st.container(border=True):
        st.markdown('#### 최근 5거래일')
        if last:
            with st.container(horizontal=True):
                st.metric('종가',number(last['close'],'원'),width=170)
                st.metric('전 거래일 대비',number(last.get('change_pct'),'%',True),width=170)
                st.metric('5거래일 누적',number(p['return5'],'%',True),width=170)
            st.caption('KRX · 마지막 관측일 '+last['date']+' · 수정주가 아님')
            chart=alt.Chart(pd.DataFrame(p['days'])).mark_line(color='#353535',point=True).encode(
                x=alt.X('date:N',title=None,axis=alt.Axis(labelAngle=0)),
                y=alt.Y('close:Q',title='종가 · 원',scale=alt.Scale(zero=False)),
                tooltip=['date:N',alt.Tooltip('close:Q',format=',.0f'),alt.Tooltip('change_pct:Q',format='.2f')]
            ).properties(height=220).configure_view(strokeWidth=0)
            st.altair_chart(chart,width='stretch')
            st.caption('5거래일 누적은 표시 첫날의 직전 거래일 종가부터 계산합니다.')
        else: st.info('확보한 일별 시세가 없습니다.')
        if p['failed_dates']: st.warning('일부 거래일 조회에 실패해 해당 구간의 계산을 생략했습니다.')
    from app.risk_outlook import outlook
    risk=outlook(report)
    st.markdown('#### 오늘의 리스크 전망')
    st.caption('보고서 기준 '+report['news_cutoff'][:16].replace('T',' ')+' KST · 조건부 전망')
    for item in risk['items']:
        with st.container(border=True):
            st.markdown('**'+item['factor']+'** · '+item['summary'])
            with st.expander('근거 보기'):
                st.write(item['scenario'])
                if item.get('news_title'): st.caption('연결 뉴스 · '+item['news_title'])
                st.caption('근거 · '+item['evidence'])
                st.caption('확인 · '+item['watch'])
                for fact in item.get('facts',[]): st.write(fact)
                if item.get('connection'): st.caption(item['connection'])
                if item.get('url'): st.link_button('근거 기사',item['url'])
    if risk['gaps']: st.caption('전망의 빈틈 · '+' / '.join(risk['gaps']))
    with st.expander('계산 지표와 기준'):
        st.caption(risk['method'])
        st.write('5일 평균 대비 '+number(last.get('ma5_pct'),'%',True))
        st.write('20일 일간 수익률 변동성 '+number(p['volatility20'],'%'))
        st.write('직전 20거래일 평균 대비 거래량 '+number(p['volume_ratio'],'배'))
        st.caption('변동성은 일간 수익률의 표본 표준편차이며 연율화하지 않습니다. 오늘의 등락 확률을 예측하는 수치가 아닙니다.')
    st.markdown('#### 시장 배경')
    st.caption('최근 제공 수치 · 지표명을 누르면 공식 출처로 이동합니다.')
    market_rows=[]
    for item in report['macro']:
        available=item['status']=='ok'
        change='—'
        if available and item.get('change_pct') is not None:
            change=number(item['change_pct'],'%',True)
        elif available and item.get('change') is not None:
            unit=' %p' if item['unit']=='%' else ' 원' if item['unit']=='원/USD' else ' '+item['unit']
            change='변동 없음' if item['change']==0 else number(item['change'],unit,True)
        market_rows.append({'지표':f"[{item['name']}]({item['source']})",
            '수치':number(item.get('value'),' '+item.get('unit','')) if available else '확인 불가',
            '직전 대비':change,'기준일':item.get('date','—')})
    if market_rows:
        st.table(pd.DataFrame(market_rows),hide_index=True,border='horizontal',
                 alt='금리·환율·증시 지표의 최근 수치, 직전 대비 변화와 기준일')
    else:
        st.info('시장 지표를 불러오지 못했습니다.')
    st.caption('기준일은 지표마다 다릅니다. 실시간 시세가 아니며, 한국 금리의 기준일은 최근 변경일입니다.')
    with st.expander('지표 기준 · 조회 상태'):
        for item in report['macro']:
            st.caption(item['name']+' · '+item['note'])
        st.caption('직전 대비는 직전 제공 관측값 기준입니다. 한국 금리는 직전 변경 대비이며, 금리 변화의 단위는 %p입니다.')
    st.markdown('#### 미국 통화정책 발표')
    policy=report.get('policy',{})
    st.caption('연준 공식 발표 · 오전 8시 이전 최근 3건 · 종목별 영향 판단과 별도')
    for item in policy.get('items',[]):
        with st.container(border=True):
            st.link_button(item['title'],item['url'])
            st.caption(item['published'][:16].replace('T',' ')+' KST')
    if not policy.get('items'):
        st.info('공식 발표 자료를 확인하지 못했습니다.' if policy.get('status')!='ok' else '조회 범위에 해당하는 발표가 없습니다.')
    st.markdown('#### 뉴스와 영향 요인')
    st.caption(report['news_start'][:16].replace('T',' ')+' ~ '+report['news_cutoff'][:16].replace('T',' ')+' KST · 발행 시각 기준')
    for direction,label in [('상승 요인','긍정 요인'),('하락 요인','부정 요인')]:
        items=report['news'][direction]
        st.markdown(f'##### {label} · {len(items)}건')
        if not items: st.info('이 기간 수집·검증 범위에서 해당 방향으로 확정한 기사가 없습니다.')
        for item in items:
            a,f=item['article'],item['finding']; view=presentation(a,f)
            with st.container(border=True):
                st.markdown('**'+a['title']+'**')
                st.caption(a.get('publisher',a.get('source',''))+' · '+a.get('published',''))
                st.write(view['content'] or '별도로 검증된 내용 요약이 없습니다.')
                st.write('영향: '+view['effect'])
                if view['conditions']: st.caption('조건·확인할 점: '+view['conditions'])
                st.link_button('기사 원문',a['url'])
    with st.expander('수집 상태와 보고서 범위'):
        labels={'outside_window':'기준 시간 밖·발행 시각 확인 불가', 'incomplete':'분석 미완료',
                'uncertain':'방향 판단 보류', 'excluded':'선별·본문 확보·분석 대상 제한으로 제외'}
        for key,label in labels.items():
            st.caption(f"{label}: {report['news_counts'].get(key,0)}건")
        for warning in report['warnings']: st.caption(warning)
        for text in report['limitations']: st.caption(text)
