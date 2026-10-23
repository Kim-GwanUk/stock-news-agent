import os
import sys
from pathlib import Path
# Streamlit puts frontend/ first, where app.py shadows the backend app package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
import streamlit as st
import pandas as pd
import altair as alt
from app.news_duplicates import display_articles as group_display_articles
from datetime import datetime
from zoneinfo import ZoneInfo

BASE = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
st.set_page_config(page_title="천기누설 · 국내주식 뉴스", page_icon=":material/monitoring:", layout="wide")

def notice(title, message, icon=":material/info:"):
    with st.container(border=True, gap="small"):
        st.markdown(f"{icon} **{title}**")
        st.caption(message)

def api(method, path, show_error=True, **kwargs):
    try:
        with httpx.Client(timeout=260, trust_env=False) as client:
            response = client.request(method, BASE + path, **kwargs)
        if response.is_error:
            if show_error:
                notice("요청을 완료하지 못했습니다", "잠시 후 다시 시도해 주세요. 계속되면 앱 서버의 실행 상태를 확인해 주세요.", ":material/error_outline:")
            return None
        return response.json()
    except (httpx.HTTPError, ValueError):
        if show_error:
            notice("서버 응답을 확인하지 못했습니다", "앱 서버가 실행 중인지 확인한 뒤 다시 시도해 주세요.", ":material/cloud_off:")
        return None

def readable_date(value):
    try:
        return datetime.fromisoformat(value).astimezone(ZoneInfo("Asia/Seoul")).strftime("%m.%d %H:%M")
    except (TypeError, ValueError):
        return str(value)

@st.cache_data(ttl=1800, max_entries=30, show_spinner=False)
def load_history(code, days):
    with httpx.Client(timeout=100, trust_env=False) as client:
        response = client.get(f"{BASE}/stocks/{code}/history", params={"days": days})
        response.raise_for_status()
        return response.json()

def show_chart(stock):
    from app.price_series import build_series
    with st.container(border=False, gap="medium", key="ink_price"):
        st.markdown("#### 주가 흐름")
        with st.container(horizontal=True):
            interval = st.segmented_control("표시 단위", ["일별", "주별"], default="일별", key="chart_interval") or "일별"
            period = st.segmented_control("조회 기간", ["1개월", "3개월"], default="1개월", key="chart_period") or "1개월"
        try:
            with st.spinner("KRX 거래일 시세를 불러옵니다."):
                data = load_history(stock["code"], 90 if period == "3개월" else 30)
        except (httpx.HTTPError, ValueError):
            notice("시세를 불러오지 못했습니다", "잠시 후 다시 불러와 주세요.", ":material/show_chart:")
            if st.button("시세 다시 불러오기"):
                load_history.clear()
                st.rerun()
            return
        daily, weekly = build_series(data.get("items", []), data.get("failed_dates", []))
        if not daily:
            notice("표시할 시세가 없습니다", "최근 거래일 데이터가 제공되면 표시됩니다.")
            return
        last = daily[-1]
        if interval == "일별":
            dates = [r['date'] for r in reversed(daily)]
            chosen = st.selectbox("거래일 선택", dates, key=f"chart_day_{stock['code']}")
            last = next(r for r in daily if r['date'] == chosen)
        pct=last.get('change_pct')
        direction = "상승" if pct is not None and pct>0 else "하락" if pct is not None and pct<0 else "보합" if pct==0 else "확인 불가"
        with st.container(horizontal=True, gap="medium"):
            st.metric("선택일 종가" if interval == "일별" else "최근 종가", f"{last['close']:,.0f}원", width=190)
            st.metric("전일 대비 · " + direction, f"{pct:+.2f}%" if pct is not None else "—", width=190)
            avg=last.get('ma5_pct')
            st.metric("5일 평균 대비", f"{avg:+.2f}%" if avg is not None else "—", width=190)
        st.caption(f"{last['date']} 기준 · 5일 평균 종가 {last['ma5']:,.0f}원" if last.get('ma5') else f"{last['date']} 기준 · 연속된 5거래일 자료가 부족해 평균을 표시하지 않습니다.")
        if interval == "일별":
            frame = pd.DataFrame([last])
            for field in ('open', 'high', 'low'):
                if field not in frame:
                    frame[field] = None
            tool = [alt.Tooltip('date:N', title='거래일')] + [
                alt.Tooltip(f'{k}:Q', title=t, format=',.0f')
                for k,t in [('open','시가'),('high','고가'),('low','저가'),('close','종가')]]
            base = alt.Chart(frame).encode(x=alt.X('date:N', title=None, axis=alt.Axis(labelAngle=0)), tooltip=tool)
            wick = base.mark_rule(color='#a5aca6', strokeWidth=1.5).encode(
                y=alt.Y('low:Q', title='가격 · 원', scale=alt.Scale(zero=False)), y2='high:Q')
            body = base.mark_bar(color='#778179', size=32).encode(y='open:Q', y2='close:Q')
            close = base.mark_tick(color='#303b33', size=44, thickness=2).encode(y='close:Q')
            chart = (wick + body + close).properties(height=235, background='transparent').configure_view(strokeWidth=0).configure_axis(
                gridColor='#E8ECE8', gridOpacity=.65, domain=False, ticks=False, tickCount=4,
                labelPadding=10, titlePadding=14, labelColor='#7C847D', titleColor='#7C847D', titleFontWeight='normal')
            st.altair_chart(chart, width="stretch", alt=f"{stock['name']} {last['date']} 하루 시가·고가·저가·종가")
            st.caption("선택한 하루의 가격 범위입니다. 세로선: 고가–저가 · 막대: 시가–종가 · 진한 가로선: 종가")
            with st.container(horizontal=True, gap="medium"):
                for field, label in [('open','시가'),('high','고가'),('low','저가')]:
                    value = last.get(field)
                    st.metric(label, f"{value:,.0f}원" if value is not None else "—", width=150)
            st.caption(f"거래량 {last['volume']:,.0f}주 · 시간대별 움직임을 나타내는 그래프가 아닙니다.")
        else:
            rows = weekly
            frame=pd.DataFrame(rows)
            for field in ('open','high','low','ma5'):
                if field not in frame: frame[field]=None
            frame['date']=pd.to_datetime(frame['date'])
            x=alt.X('date:T',title=None,axis=alt.Axis(format='%m.%d',grid=False,tickCount=5))
            tool=[alt.Tooltip('date:T',title='주 시작일' if interval=='주별' else '거래일',format='%Y.%m.%d')]+[alt.Tooltip(f'{k}:Q',title=t,format=',.0f') for k,t in [('open','시가'),('high','고가'),('low','저가'),('close','종가'),('volume','거래량')]]
            base=alt.Chart(frame).encode(x=x,tooltip=tool)
            price=base.mark_line(color='#303b33',strokeWidth=2,point=alt.OverlayMarkDef(size=22,filled=True)).encode(y=alt.Y('close:Q',title='가격 · 원',scale=alt.Scale(zero=False)))
            wick=base.mark_rule(color='#a5aca6',opacity=.65).encode(y='low:Q',y2='high:Q')
            chart=wick+price
            if interval=='일별':
                chart+=base.mark_line(color='#9b9382',strokeDash=[5,4]).encode(y='ma5:Q')
            volume=base.mark_bar(color='#c4ccc5',opacity=.65).encode(y=alt.Y('volume:Q',title='거래량 · 주',axis=alt.Axis(grid=False,tickCount=2))).properties(height=65)
            combined=alt.vconcat(chart.properties(height=235),volume,spacing=20).properties(background='transparent',autosize=alt.AutoSizeParams(type='fit-x',contains='padding')).resolve_scale(x='shared').configure_view(strokeWidth=0).configure_axis(gridColor='#E8ECE8',gridOpacity=.65,domain=False,ticks=False,tickCount=4,labelPadding=10,titlePadding=14,labelColor='#7C847D',titleColor='#7C847D',titleFontWeight='normal')
            st.altair_chart(combined,width="stretch",alt=f"{stock['name']} {interval} 종가·고저 범위 및 거래량")
            st.caption("실선: 종가 · 세로선: 고가–저가" + (" · 점선: 최근 5거래일 평균" if interval=='일별' else " · 첫 주는 조회 범위 내 집계, 마지막 주는 진행 중일 수 있습니다."))
        with st.expander("일별 등락과 시세 상세"):
            detail=pd.DataFrame([last] if interval == "일별" else daily).reindex(columns=['date','open','high','low','close','change_pct','ma5','ma5_pct','volume'])
            detail.columns=['거래일','시가','고가','저가','종가','전일 대비 %','5일 평균','평균 대비 %','거래량']
            st.dataframe(detail.iloc[::-1],hide_index=True,width="stretch",alt="일별 가격과 등락률, 5일 평균 대비")
        with st.expander("시세 기준 안내"):
            st.caption("출처: 한국거래소 통계정보 · 당일 장중 시세가 아닌 전일 이전 일별 자료입니다. 전일 대비는 KRX 제공 등락률입니다.")
            st.caption("5일 평균은 해당 날짜를 포함한 최근 5거래일 종가의 산술평균입니다. 조회 초반 또는 조회 실패가 있는 구간은 표시하지 않습니다.")
            st.caption("주별은 월~금 중 조회된 거래일의 첫 시가·최고가·최저가·마지막 종가·거래량 합계입니다. 휴장일은 생성하지 않습니다. 수정주가가 아니므로 분할·배당락에 유의하세요.")
        if data.get('failed_dates'):
            st.warning(f"{len(data['failed_dates'])}개 날짜 조회 실패: 일부 주별 집계와 평균이 불완전합니다.")


def show_result(result):
    from app.news_display import presentation, exclusion, empty_reason
    window=result.get('news_window')
    scope=(f"아침 보고서 분석 · {window['start'][:16].replace('T',' ')} ~ {window['end'][:16].replace('T',' ')} KST"
           if window else '뉴스 최근 7일')
    st.caption(f"분석 시각 {result['as_of'][:19].replace('T', ' ')} · {scope}")
    memory = result.get('news_memory')
    if memory:
        with st.expander('뉴스 근거 보관 상태'):
            st.caption(f"사건·판단 기록 {len(memory.get('saved_ids', []))}건 보관")
            st.caption({'indexed':'확인된 종목 근거를 검색할 수 있도록 저장했습니다.',
                        'up_to_date':'검색 가능한 근거의 저장 상태가 최신입니다.',
                        'pending_retry':'기록은 보관했습니다. 검색 색인 저장은 재시도가 필요합니다.',
                        'storage_failed':'근거 보관을 완료하지 못했습니다.'}.get(memory.get('status'),'저장 상태 확인 필요'))
            st.caption('과거 판단은 정답이나 통계 확률이 아닙니다. 현재 분석에 자동으로 재사용하지 않습니다.')
    rag = result.get("rag", {})
    if rag and rag.get("status") != "disabled":
        with st.expander("DART 공시 배경 근거"):
            st.caption(rag.get("detail", ""))
            st.caption("과거 보고서의 사업 배경입니다. 계열사 내용·연결 실적을 해당 회사의 개별 실적으로 해석하지 않습니다.")
            for hit in rag.get("items", []):
                st.markdown(f"**{hit['title']} · {hit['corp_name']}**")
                st.caption(f"공시일 {hit['published']} · 인접 절: {hit['section']}")
                st.text(hit["text"])
                st.link_button("DART 원문", hit["url"])
    for warning in result.get("warnings", []):
        notice("분석 시 확인할 점", warning, ":material/info:")
    findings = {f["article_id"]: f for f in result["findings"]}
    sources = {a["id"]: a for a in result["articles"] + result.get("sources", [])}
    all_articles = group_display_articles(result)
    with st.expander("기사 수집·선별 내역 · 기사가 안 보이는 이유"):
        collection = result.get('collection', {})
        st.caption(f"저장된 검색 기사 {len(result['articles'])}건 · 분석 대상 {sum(bool(a.get('analysis_candidate')) for a in result['articles'])}건")
        if collection.get('identical_titles_removed'):
            st.caption(f"제목이 같은 중복 검색 결과 {collection['identical_titles_removed']}건을 수집 단계에서 제외했습니다.")
        if not result['articles']:
            st.write(empty_reason(result))
        else:
            for item in result['articles']:
                label, detail = exclusion(item)
                st.markdown(f"**{item['title']}**")
                st.caption(f"{label} · {detail}")
        st.caption("관련성 선별은 오판할 수 있습니다. 목록 밖 기사도 원문을 확인할 수 있도록 추가 검색 결과에서 제공합니다.")
    display_articles = all_articles
    hide_duplicates = st.toggle("중복 기사 숨기기", value=True,
                                help="이미 중복으로 판정된 기사를 숨깁니다. 끄면 대표 기사에 연결된 중복 보도도 표시합니다. 분석을 다시 실행하지 않습니다.")
    show_extra = False
    if any("analysis_candidate" in a for a in all_articles):
        main = [a for a in all_articles if a.get("analysis_candidate")]
        others = len(all_articles) - len(main)
        st.caption(f"분석 대상 {len(main)}건 · 추가 검색 결과 {others}건")
        show_extra = st.toggle("추가 검색 결과 함께 보기", value=False)
        if not show_extra:
            main_ids = {a["id"] for a in main}
            # Resolve chains defensively; malformed or cyclic references stay extra.
            by_id = {a["id"]: a for a in all_articles}
            def belongs_to_main(article):
                parent = article.get("duplicate_of")
                visited = {article["id"]}
                while parent and parent not in visited:
                    if parent in main_ids:
                        return True
                    visited.add(parent)
                    parent = by_id.get(parent, {}).get("duplicate_of")
                return False
            display_articles = [a for a in all_articles if a["id"] in main_ids or belongs_to_main(a)]
    duplicate_count = sum(bool(a.get("duplicate_of")) for a in display_articles)
    if hide_duplicates:
        display_articles = [a for a in display_articles if not a.get("duplicate_of")]
    st.caption(f"중복 판정 {duplicate_count}건 · {'숨김' if hide_duplicates else '표시'} · 표시 방식만 변경됩니다")
    shown_ids = {a["id"] for a in display_articles}
    views = {a['id']:presentation(a, findings[a['id']]) for a in all_articles if a['id'] in findings}
    counts = {label: sum(v['direction'] == label and aid in shown_ids for aid,v in views.items())
              for label in ("상승 요인", "하락 요인", "판단 보류", "분석 미완료")}
    with st.container(horizontal=True, gap="small"):
        for label, count in counts.items():
            symbol = {"상승 요인": "↗", "하락 요인": "↘", "판단 보류": "—", "분석 미완료":"·"}[label]
            st.badge(f"{symbol} {label} · {count}건", color="gray")
    chosen_filter = st.segmented_control("영향 요인", ["전체", *counts], default="전체")
    filters = list(counts) if chosen_filter in (None, "전체") else [chosen_filter]
    if not display_articles:
        notice("분석할 뉴스가 없습니다", empty_reason(result), ":material/search_off:")
    visible = 0
    for article in display_articles:
        finding = findings.get(article["id"])
        if not finding or views[article['id']]['direction'] not in filters:
            continue
        visible += 1
        with st.container(border=False, gap="small",key=f"ink_news_{article['id']}"):
            publisher = article.get("publisher") or article["source"]
            st.caption(f"{publisher}  ·  {readable_date(article['published'])}")
            if article.get("duplicate_of"):
                st.badge("같은 발표의 보도" if article.get("display_duplicate") else "중복 보도 · 별도 분석 제외", color="gray")
                parent = sources.get(article["duplicate_of"])
                if parent:
                    st.caption(f"대표 기사: {parent['title']}")
            # Large, complete source title; no generated summary title or HTML injection.
            st.subheader(article["title"])
            view = views[article['id']]
            st.caption(f"처리 상태 · {view['status']}")
            st.caption(view['detail'])
            st.markdown("**기사 내용 · 확인된 사실**")
            st.write(view['content'] or "검증된 기사 내용이 저장되지 않았습니다. 제목만으로 요약을 만들지 않습니다.")
            if view['conditions']:
                with st.expander("기사의 조건·제한 함께 보기"):
                    st.write(view['conditions'])
            st.markdown("**영향 판단**")
            symbol = {"상승 요인": "↗", "하락 요인": "↘", "판단 보류": "—", "분석 미완료":"·"}[view['direction']]
            with st.container(horizontal=True, vertical_alignment="center"):
                st.badge(f"{symbol} {view['direction']}", color="gray")
                st.caption(f"영향 수준 · {finding['impact']}" if view['direction'] in ("상승 요인", "하락 요인")
                           else "추가 확인 필요")
            st.write(view['effect'])
            with st.expander("판단 근거와 확인할 점"):
                st.markdown("**확인할 점**")
                st.write(finding["counterpoint"])
                st.space("small")
                st.markdown("**원문에서 확인한 근거**")
                st.caption(f"본문 상태 · {article['body_status']}")
                evidence_sources = {}
                for number, evidence in enumerate(finding["evidence"], 1):
                    source = sources.get(evidence["source_id"])
                    with st.container(border=False, gap="small"):
                        source_name = (source.get("publisher") or source.get("source") or "원문") if source else "원문"
                        st.caption(f"{number:02d} · {source_name}")
                        st.text(evidence["quote"])
                    if source and source["url"] != article["url"]:
                        evidence_sources[source["url"]] = source_name
                if not finding["evidence"]:
                    st.caption("확인된 원문 인용이 없습니다.")
                for url, source_name in evidence_sources.items():
                    st.link_button(f"추가 출처 · {source_name}", url, icon=":material/north_east:",
                                   key=f"source_{article['id']}_{url}")
            st.link_button("원문 읽기", article["url"], icon=":material/north_east:")
        st.space("small")
    if not visible and display_articles:
        notice("이 분류에 표시할 뉴스가 없습니다", "영향 요인을 ‘전체’로 바꾸면 다른 분석 결과를 볼 수 있습니다.", ":material/filter_alt_off:")
    st.caption("영향 수준은 확인된 사업 영향의 정성 평가입니다. 주가 상승 확률이나 예상 수익률이 아닙니다.")

from frontend.ink_theme import masthead
masthead()
stocks = api("GET", "/stocks")
if st.session_state.get('stock_removed_notice'):
    st.toast(st.session_state.pop('stock_removed_notice'), icon=':material/check:')
if st.session_state.get('csv_done'):
    st.success(st.session_state.pop('csv_done'))
if stocks is None:
    if st.button("다시 연결", icon=":material/refresh:"):
        st.rerun()
    st.stop()

def stock_label(stock):
    aliases = {"018260": "삼성SDS", "005380": "현대차"}
    alias = aliases.get(stock["code"])
    name = stock["name"] + (f" / {alias}" if alias and alias != stock["name"] else "")
    return f"{name} ({stock['code']}) · {stock.get('market', '')}"

with st.sidebar:
    st.caption("보유 · 관심 목록")
    st.markdown("### 내 종목")
    st.caption(f"총 {len(stocks)}종목 · 등록 개수 제한 없음")
    codes = {s["code"] for s in stocks}
    if stocks and st.session_state.get("selected_stock_code") not in codes:
        st.session_state["selected_stock_code"] = stocks[0]["code"]
    if stocks:
        from app.watchlist import filter_stocks
        kind_filter=st.segmented_control('목록 구분',['전체','보유','관심'],default='전체',key='watch_kind') or '전체'
        matches=filter_stocks(stocks,kind=kind_filter)
        bycode={s['code']:s for s in matches}
        options_codes=list(bycode)
        current_code=st.session_state['selected_stock_code']
        # A filter change never silently selects the first matching company.
        st.session_state['watch_picker']=current_code if current_code in bycode else None
        def select_watch_stock():
            if st.session_state.get('watch_picker') is not None:
                st.session_state['selected_stock_code']=st.session_state['watch_picker']
        picked=st.selectbox('분석할 종목',options_codes,
            index=options_codes.index(current_code) if current_code in bycode else None,
            format_func=lambda code:stock_label(bycode[code]),
            placeholder='목록을 열어 이름·코드 검색',filter_mode='fuzzy',
            accept_new_options=False,key='watch_picker',disabled=not matches,on_change=select_watch_stock)
        if picked is not None:
            st.session_state['selected_stock_code']=picked
            if st.button(f"{bycode[picked]['name']} 삭제", icon=':material/delete:',
                         key='remove_picked_stock', help='내 목록에서만 삭제합니다. 저장된 분석 이력은 유지됩니다.'):
                removed=api('DELETE', '/stocks/'+picked)
                if removed and removed.get('deleted')==picked:
                    remaining=[s for s in matches if s['code']!=picked]
                    if not remaining:
                        remaining=[s for s in stocks if s['code']!=picked]
                    st.session_state['selected_stock_code']=remaining[0]['code'] if remaining else None
                    st.session_state.pop('result', None)
                    st.session_state['stock_removed_notice']=f"{bycode[picked]['name']}을(를) 내 목록에서 삭제했습니다."
                    st.rerun()
        st.caption(f'{len(matches)}종목 · 목록 안에서 검색하거나 스크롤해 선택하세요.')
        if not matches: st.caption('해당 구분에 등록된 종목이 없습니다.')
        current=next(s for s in stocks if s['code']==st.session_state['selected_stock_code'])
        st.caption(f"현재 선택 · {current['name']} ({current['code']}) · {current['kind']}")
        if current['code'] not in bycode:
            st.caption('현재 선택 종목은 필터 밖에 있습니다. 새 종목을 선택하면 분석 대상이 바뀝니다.')
    st.space("small")

with st.sidebar.expander("종목 추가 · 검색", expanded=not stocks):
    import time
    if time.time() - st.session_state.get("catalog_loaded_at", 0) > 1800:
        catalog = api("GET", "/stocks/catalog")
        if catalog is not None:
            st.session_state["stock_catalog"] = catalog["items"]
            st.session_state["catalog_loaded_at"] = time.time()
    options = st.session_state.get("stock_catalog", [])
    chosen = st.selectbox(
        "종목 검색", options, index=None, format_func=stock_label,
        placeholder="회사명 또는 종목 코드",
        filter_mode="fuzzy", accept_new_options=False, key="stock_autocomplete",
        disabled=not options,
    )
    st.caption("예: 삼성 · 005930")
    st.caption("검색 결과가 없으면 짧은 회사명이나 6자리 종목 코드로 입력해 주세요.")
    if not options:
        notice("종목 목록을 불러오지 못했습니다", "목록을 다시 불러온 뒤 검색해 주세요.", ":material/search_off:")
        if st.button("종목 목록 다시 불러오기"):
            st.session_state.pop("catalog_loaded_at", None)
            st.rerun()
    if chosen is not None:
        existing = next((s for s in stocks if s["code"] == chosen["code"]), None)
        with st.form(f"register-stock-{chosen['code']}", border=False):
            st.divider()
            st.markdown("**선택한 종목**")
            st.text(chosen["name"])
            st.caption(f"{chosen['code']} · {chosen.get('market', '')}")
            kind = st.segmented_control("등록 구분", ["관심", "보유"],
                                        default=existing["kind"] if existing else "관심",
                                        key=f"kind_{chosen['code']}")
            if existing:
                st.caption("내 목록에 있는 종목입니다. 등록 구분을 변경할 수 있습니다.")
            if st.form_submit_button("구분 저장" if existing else "내 목록에 추가", type="primary",
                                     width="stretch", disabled=kind is None):
                with st.spinner("종목과 시장을 확인하고 등록합니다."):
                    saved = api("POST", "/stocks", json={"code": chosen["code"], "kind": kind})
                if saved:
                    st.session_state["selected_stock_code"] = chosen["code"]
                    st.rerun()

with st.sidebar:
    if st.button('CSV로 종목 등록',icon=':material/upload_file:',width='stretch'):
        from frontend.stock_import import show as show_csv_import
        show_csv_import(BASE)
    if st.button('사진으로 종목 등록',icon=':material/add_photo_alternate:',width='stretch'):
        from frontend.photo_import import show as show_photo_import
        show_photo_import(BASE)

if not stocks:
    notice("첫 종목을 등록해 주세요", "왼쪽에서 종목을 검색하거나 CSV·사진으로 등록해 주세요.", ":material/bookmark_add:")
    st.stop()
with st.sidebar:
    selected = next(s for s in stocks if s["code"] == st.session_state["selected_stock_code"])
    st.divider()
    st.caption("KOSPI · KOSDAQ")
    st.caption("뉴스 NAVER / Google News\n\n시세 KRX · 공시 DART")
st.header(selected["name"])
mode=st.segmented_control('화면',['뉴스와 시세','아침 보고서'],default='뉴스와 시세',key='main_view')
if mode=='아침 보고서':
    from frontend.morning import show as show_morning
    show_morning(selected,api)
    st.stop()
with st.expander("공시 자료 · 저장과 근거 검색"):
    st.caption("최근 400일 정기보고서 최대 3건을 저장합니다. 처음에는 수 분 걸릴 수 있습니다.")
    if st.button("DART 자료 동기화", key="sync_dart"):
        with st.spinner("공시 원문을 저장하고 검색 자료를 준비합니다."):
            synced = api("POST", "/rag/sync/" + selected["code"], timeout=900)
        if synced:
            st.write(f"보고서 {len(synced['documents'])}건 · 문단 {sum(d['chunks'] for d in synced['documents'])}개")
            if synced["errors"]:
                st.warning(f"{len(synced['errors'])}건 저장 실패 · 다시 동기화해 주세요.")
    with st.form("dart_search"):
        question = st.text_input("공시에서 찾을 내용", placeholder="예: 주요 제품과 원재료 가격 위험")
        searched = st.form_submit_button("근거 찾기")
    if searched and len(question.strip()) >= 2:
        found = api("GET", "/rag/search/" + selected["code"], params={"q":question})
        if found:
            st.caption("아래는 검색 후보 문단입니다. 질문의 모든 내용을 뒷받침한다는 뜻은 아니며, 연결·별도 기준과 기간을 확인해야 합니다.")
            if not found["items"]:
                st.info("검색 조건에 맞는 근거가 없습니다. 자료 동기화 여부와 검색어를 확인해 주세요.")
            for hit in found["items"]:
                st.markdown(f"**{hit['title']} · {hit['corp_name']}**")
                st.caption(f"공시일 {hit['published']} · 인접 절: {hit['section']}")
                st.text(hit["text"])
                st.link_button("DART 원문 확인", hit["url"])
st.caption(f"{selected['code']}  ·  {selected['market']}  ·  {selected['kind']}")
# Reserve both regions before any slow request so the previous stock disappears.
chart_slot = st.empty()
news_slot = st.empty()
chart_slot.empty()
news_slot.empty()
with news_slot.container():
    st.caption(f"{selected['name']}의 화면을 불러오고 있습니다.")
with chart_slot.container():
    show_chart(selected)
with news_slot.container():
    st.space("small")
    st.markdown("## 뉴스와 영향 요인")
    st.caption("최근 7일의 뉴스 · 원문에 근거한 사업 영향 분석")
    analyze_clicked = st.button("뉴스 분석하기", type="primary", icon=":material/refresh:", width="content")
    if analyze_clicked:
        with st.status("뉴스를 분석하고 있습니다", expanded=True) as progress:
            st.write(f"{selected['name']}의 뉴스와 시세를 모아 관련성과 판단 근거를 확인합니다.")
            st.caption("최대 3분 정도 걸릴 수 있습니다. 완료되면 결과가 아래에 표시됩니다.")
            result = api("POST", "/analyze", show_error=False, json={"code": selected["code"]})
            if result:
                st.session_state["result"] = result
                progress.update(label="뉴스 분석을 마쳤습니다", state="complete", expanded=False)
            else:
                progress.update(label="분석 응답을 확인하지 못했습니다", state="error", expanded=True)
                st.caption("잠시 후 ‘뉴스 분석하기’를 다시 눌러 주세요. 서버에서 처리가 완료됐을 수 있으므로 기존 이력도 확인해 주세요.")
    result = st.session_state.get("result")
    if result and result["stock"]["code"] == selected["code"]:
        show_result(result)
    else:
        history = api("GET", "/analyses/" + selected["code"])
        if history:
            show_result(history[0])
        elif history is not None:
            notice("아직 분석한 뉴스가 없습니다", "‘뉴스 분석하기’를 누르면 관련 뉴스와 판단 근거를 함께 확인할 수 있습니다.", ":material/article:")
