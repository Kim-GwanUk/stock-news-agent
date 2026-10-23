import json
from pathlib import Path
from html import escape
from datetime import datetime

root=Path(__file__).resolve().parents[1]
reports=json.loads((root/'output/morning-live-validation.json').read_text(encoding='utf-8'))
rows=[]
for r in reports:
    start,end=map(datetime.fromisoformat,(r['news_start'],r['news_cutoff']))
    assert all(start<=datetime.fromisoformat(n['article']['published'])<end for g in r['news'].values() for n in g)
    assert all(d['date']<r['report_date'] for d in r['prices']['days'])
    rows.append(f"<tr><td>{escape(r['stock']['name'])}</td><td>{r['prices']['last']['date']}</td><td>{len(r['prices']['days'])}</td><td>{len(r['news']['상승 요인'])}</td><td>{len(r['news']['하락 요인'])}</td><td>{r['news_counts']['incomplete']}</td></tr>")
html='''<!doctype html><html lang="ko"><meta charset="utf-8"><title>아침 보고서 연결 검증</title>
<style>body{max-width:1000px;margin:60px auto;padding:24px;font:16px/1.7 sans-serif;color:#303030;background:#f8f8f6}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:12px;border-bottom:1px solid #ccc}h1{font-size:28px}</style>
<h1>아침 보고서 실제 데이터 연결 검증</h1><p>2026-10-22 · Docker 앱에서 보고서 생성 API 실행 및 저장 확인</p>
<table><tr><th>종목</th><th>최종 시세일</th><th>그래프 거래일</th><th>긍정</th><th>부정</th><th>분석 미완료</th></tr>'''+''.join(rows)+'''</table>
<h2>확인한 동작</h2><ul><li>전일까지의 5거래일 그래프, 전 거래일 등락, 5일 누적, 평균 대비 지표 생성.</li>
<li>오후 생성 시 최신 뉴스 20건이 모두 마감 이후여서 비던 문제 수정. 최대 1,000건을 순차 조회해 기간 내 최대 20건 선별.</li>
<li>보고서에 포함된 모든 뉴스 발행 시각이 보고서 기간 안이며, 모든 가격일이 보고서 당일 이전임을 검사.</li>
<li>한국은행 기준금리, FRED 환율·미국 금리 범위·S&amp;P500·나스닥, FED 공식 통화정책 발표 조회 성공.</li></ul>
<h2>남은 제약</h2><ul><li>KRX KOSPI·KOSDAQ 지수 API는 현재 키로 권한 오류. 해당 지수 API 승인이 필요.</li>
<li>ECOS 키 미등록. 한국 기준금리는 한국은행 공개 표, 환율은 FRED 제공 관측값을 사용. 환율 기준일 10월 16일.</li>
<li>삼성전자 검색은 최대 1,000건 한도 도달. 기사 전체를 빠짐없이 수집했다는 검증이 아님.</li>
<li>긍정·부정 건수는 기존 분석기가 반환한 결과다. SK하이닉스 지분 매각 기사에 일반적인 매출 기회 설명이 붙는 등 의미 판단 품질은 추가 검토 필요. 정확도 검증 통과를 의미하지 않음.</li>
<li>미완료 기사를 억지로 분류하거나 방향별 3건을 채우지 않음.</li>
<li>현재 조회 자료의 미리보기이며 오전 8시에 수집해 보관한 당시 보고서 재현은 아님. 이메일 자동 발송은 미구현.</li></ul></html>'''
(root/'output/morning-report-validation.html').write_text(html,encoding='utf-8')
print('Report saved; cutoff and price-date assertions passed.')
