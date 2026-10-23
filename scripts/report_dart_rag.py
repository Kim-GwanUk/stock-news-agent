import json
import html
from pathlib import Path

root=Path('output')
data=json.loads((root/'dart-rag-validation.json').read_text(encoding='utf8'))
hold=json.loads((root/'dart-rag-validation-holdout.json').read_text(encoding='utf8'))
esc=lambda value:html.escape(str(value))
sections=[]
for title,group in [('보완 후 회귀 질문 8개',data),('보완에 쓰지 않은 추가 질문 4개',hold)]:
    rows=[]
    for c in group['cases']:
        note='관련 주제 근거 포함. 상위 5개 전체가 관련 있다는 의미는 아님.'
        if c['query']=='배당 정책과 주주 환원':
            note='부분 충족: 배당 결의·지급 내역은 있으나 배당 정책 자체의 직접 근거 검색은 미흡.'
        if c['query']=='연구개발과 전기차 투자':
            note='미흡: 연구개발 관계회사·지분 투자표 중심. 전기차 투자 계획을 직접 답하기에 부족.'
        details=''.join('<details><summary>'+esc(h['title'])+' · '+esc(h['corp_name'])+' · '+str(h['published'])+'</summary><p>인접 절: '+esc(h['section'])+'</p><pre>'+esc(h['text'])+'</pre><a href="'+esc(h['url'])+'">DART 원문</a></details>' for h in c['hits'])
        rows.append('<article><h3>'+esc(c['code']+' · '+c['query'])+'</h3><p>'+note+'</p><p>키워드 포함: '+str(c['topic_hit'])+' / 발행회사 일치: '+str(c['issuer_clean'])+'</p>'+details+'</article>')
    sections.append('<h2>'+title+'</h2>'+''.join(rows))
docs=sum(len(s['documents']) for s in data['sync'])
chunks=sum(d['chunks'] for s in data['sync'] for d in s['documents'])
body=f'''<!doctype html><html lang="ko"><meta charset="utf-8"><title>DART RAG 검증</title>
<style>body{{font:16px/1.7 sans-serif;background:#f5f4ef;color:#282828;max-width:1050px;margin:50px auto;padding:24px}}article{{background:white;padding:24px;margin:20px 0;border:1px solid #ddd}}pre{{white-space:pre-wrap;font:14px/1.7 sans-serif}}summary{{cursor:pointer;padding:10px}}a{{color:#444}}h1,h2{{font-weight:650}}</style>
<h1>DART RAG 적용·실제 공시 검증</h1><p>Qdrant + text-embedding-3-small · 2026-10-21</p>
<p>4종목 · 정기보고서 {docs}건 · 문단 {chunks:,}개. 원본 ZIP SHA-256, 접수번호, 발행회사, 공시일, 파일명·문단번호를 보관.</p>
<h2>결과와 해석</h2><ul><li>최초 8질문: 키워드 포함 7/8. 의미 검색에 키워드 조건 검색·재정렬·동일 문단 제거를 보완한 뒤 8/8.</li>
<li>수정에 쓰지 않은 4질문: 주제 근거 포함 4/4. 정답 문단 전체를 라벨링한 재현율 측정이나 독립 전문가 평가는 아님.</li>
<li>타사 이름을 넣은 교차 검색 12조합: 다른 발행회사 공시 혼입 0건. 동일 조합 반복 검증은 새로운 표본으로 계산하지 않음.</li>
<li>내용 검토: CJ 배당 정책은 부분 충족, 현대차 전기차 투자는 미흡. 키워드 통과를 의미 정확도 100%로 해석하면 안 됨.</li>
<li>연결 보고서 안의 계열사·경쟁사 문장은 남아 있음. 발행회사 필터만으로 문단 주체 혼동이 해결되지는 않음.</li></ul>
<h2>실제 앱 분석 실행</h2><p>삼성전자 분석 API HTTP 200. RAG retrieved, 삼성전자 발행 공시 후보 5개 전달·저장 확인. 뉴스 20개 중 19개 분석 제외, 1개 최종 검증 실패. RAG 작동 검증이며 뉴스 방향 판단 정확도 개선을 입증한 결과가 아닙니다.</p>
<p>기존 자동 테스트 161개 통과 후, 추가한 미래 공시 차단·미색인 종목 검색 차단을 포함한 RAG 테스트 6개 통과.</p>
<h2>적용 범위</h2><p>최근 400일 정기보고서 최대 3건을 수동 동기화. 모든 공시·최신 정정 자동 추적은 미구현. 종목코드+DART 고유번호+공시일+성공적으로 동기화한 문서 목록으로 검색 제한. 저장 실패 문서는 검색에서 제외.</p>
<p>뉴스→공시 검색→기사 사실 고정→영향 해석→검증. 공시 검색 후보는 사업 맥락으로 전달하지만 방향 근거는 기사 자체의 고정 사실에서만 선택. 과거 AI 분석은 색인하지 않음.</p>
<p>자료 검색 실패 시 기존 뉴스 분석을 유지하고 상태를 기록. 최초 저장은 기존 DART 및 OpenAI 키를 사용하며 키를 결과에 저장하지 않음.</p>
{''.join(sections)}<h2>검증 데이터</h2><p>dart-rag-validation-baseline.json / dart-rag-validation.json / dart-rag-validation-holdout.json / dart-rag-live-analysis.json</p></html>'''
(root/'dart-rag-validation-report.html').write_text(body,encoding='utf8')
print('output/dart-rag-validation-report.html')
