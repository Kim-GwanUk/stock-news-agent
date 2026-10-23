import html
import json
from pathlib import Path

r=json.loads(Path('output/news-memory-validation.json').read_text(encoding='utf-8'))
esc=lambda value:html.escape(str(value),quote=True)
rows=[]; cards=[]
for code,items in r['final_records'].items():
    current=[e for e in items if e['schema_version']==2]
    rows.append(f'<tr><td>{esc(current[0]["company"] if current else code)}</td><td>{len(current)}</td><td>{sum(e["reusable"] for e in current)}</td><td>{sum(e["decision_reusable"] for e in current)}</td></tr>')
    for e in current:
        facts=''.join(f'<li><b>{esc(f["subject"])}</b> · {esc(f["event_kind"])}<br>{esc(f["event_quote"])}</li>' for f in e['facts'])
        cards.append(f'<article><small>{esc(e["company"])} · {esc(e["published"])} · 사실 검색 {"가능" if e["reusable"] else "제외"} · 판단 재사용 {"자동 검증 통과" if e["decision_reusable"] else "제외"}</small><h3><a href="{esc(e["url"])}">{esc(e["title"])}</a></h3><ul>{facts}</ul><p>조건 문맥 {len(e["condition_context"])}건 · 공동 주체 {len(e.get("joint_context",[]))}건 · 직접 귀속 제외 {len(e["excluded_context"])}건</p></article>')
checks=''.join(f'<tr><td>{esc(s["code"])}</td><td>{esc(s["query"])}</td><td>{len(s["hits"])}</td><td>{"통과" if s["company_clean"] else "실패"}</td></tr>' for s in r['searches'])
page='''<!doctype html><html lang="ko"><meta charset="utf-8"><title>뉴스 근거 저장 검증</title>
<style>body{max-width:960px;margin:48px auto;padding:0 24px;background:#fafbfa;color:#26312a;font:15px/1.8 system-ui}h1,h2,h3{font-family:serif}table{width:100%;border-collapse:collapse;margin:24px 0}th,td{text-align:left;border-bottom:1px solid #dce1dc;padding:12px}article{padding:28px 0;border-top:1px solid #e1e5e1}a{color:inherit}small{color:#687469}li{margin:14px 0}.note{padding:18px;background:#eff2ef}</style>
<h1>뉴스 이벤트·판별 근거 저장 검증</h1><p>2026-10-22 · SQLite + OpenAI 임베딩 + Qdrant · 저장 스키마 v2</p>
<p>현재 실제 기사 3종목 분석과, 원문 해시가 일치하는 기존 실제 기사 기록의 백필을 함께 검사했습니다. 아래 건수는 종목별 기사 기록 수이며, 중복 사건을 통합한 통계 표본 수가 아닙니다.</p>
<table><tr><th>기업</th><th>보관</th><th>사실 검색 가능</th><th>과거 판단 자동 검증 통과</th></tr>'''+''.join(rows)+'''</table>
<div class="note">자동 검증 통과는 정답·전문가 승인·투자 확률을 뜻하지 않습니다. 기존 AI 판단의 의미적 오류가 남을 수 있어 현재 뉴스 분석에는 자동 주입하지 않습니다. 검색 가능한 사실과 재사용 제외 판단을 분리했습니다.</div>
<h2>회사별 교차 검색</h2><p>다른 회사 이름이 섞인 질문에도 요청한 종목코드의 기록만 반환했습니다. 이는 회사별 저장 공간의 분리 검증이며, 모든 문장의 기업 귀속 정확도가 100%라는 의미는 아닙니다.</p>
<table><tr><th>종목코드</th><th>질문</th><th>조회 건수</th><th>회사코드 분리</th></tr>'''+checks+'''</table>
<h2>추가 검사</h2><p>자동 테스트 27개 통과(저장·원문 검증 25개, LangGraph 흐름 2개). 원문·회사코드 변조 차단, 금액·조건 보존, 반복 저장 중복 방지, 실패 판단 방향 비노출, 과거 시점 제한, 최신 수정본 선택, 벡터 저장 장애 시 원본 보관을 확인했습니다. 실제 검색에서 미등록 자료 코드와 2000년 이전 기준 조회는 모두 0건이었습니다.</p>
<h2>실제 기사 근거</h2><p>공동 주체는 joint_context에 따로 보관합니다. 원문 문단 전체에는 다른 회사의 설명이 함께 있을 수 있으므로 subject·event_quote와 조건 문맥을 구분해야 합니다. 원문 전체 문단의 수치를 선택한 종목에 일괄 귀속하면 안 됩니다.</p>'''+''.join(cards)+'''<h2>남은 범위</h2><p>새 기사에 과거 판단 자동 적용, 동일 사건의 다중 보도 통합, 사후 수익률 통계, 사람이 검토한 정답 라벨은 이번 구현에 포함되지 않습니다. 의미적 기업 귀속과 과거 판단의 정확도는 별도 평가가 필요합니다.</p></html>'''
Path('output/news-memory-validation-report.html').write_text(page,encoding='utf-8')
print('output/news-memory-validation-report.html')

