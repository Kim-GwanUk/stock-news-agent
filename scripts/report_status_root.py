import json, html
from pathlib import Path
rows=json.loads(Path('output/status-holdout-results.json').read_text(encoding='utf-8'))
notes={
'317d70a725c8e9c7':'타사 배당·자사주 소각을 CJ에 귀속하지 않아 제외 기준 통과.',
'5d56b930e88e781f':'CJ CGV 실적을 CJ 지주 실적으로 귀속하지 않아 제외 기준 통과.',
'e4b61807463fb6b0':'추출·해석 응답은 생성됐으나 최종 설명 검증 실패. 현재 실적 감소의 보존도 추가 점검 필요.',
'41667ec683f4769e':'분석 완료·하락 요인. 실제 영업이익 감소와 등급 하향 가능성 조건을 구분. 원문의 “자동 강등은 아님” 안내를 더 명확히 보존할 여지는 있음.',
'264c53e16e2cbe23':'추출·해석 응답 생성 후 최종 검증 실패. 사업자 선정·11월 운행 예정 문단이 설명에서 빠짐. 중복 연결도 실패.',
'3556d10a401b704f':'추출·해석 응답 생성 후 최종 검증 실패. 11대·사업자 선정·11월 운행 예정은 보존. 같은 사건 중복 연결 실패.'}
cards=[]
for row in rows:
    result=row['result']; findings={f['article_id']:f for f in result['findings']}
    for a in result['articles']:
        f=findings[a['id']]
        cards.append(f"<article><small>{html.escape(result['stock']['name'])} · {html.escape(f['processing_status'])}</small><h3><a href='{html.escape(a['url'],quote=True)}'>{html.escape(a['title'])}</a></h3><p>{html.escape(notes[a['id']])}</p></article>")
page='''<!doctype html><html lang="ko"><meta charset="utf-8"><title>추출·해석 실패 원인과 독립 검증</title><style>body{max-width:900px;margin:48px auto;padding:24px;background:#f7f6f2;color:#303030;font:16px/1.8 sans-serif}article{border-top:1px solid #ccc;padding:18px 0}a{color:inherit}small{color:#666}</style><h1>추출·해석 실패 원인과 독립 검증</h1>
<p>2026-10-21 · 평가 자료는 이번 수정 전 사용한 URL·제목과 중복되지 않는 실제 기사 6건. 원문 수집 후 평가 기준과 코드 해시를 고정하고 평가 결과에 맞춰 코드를 재수정하지 않았습니다. 개발자 작성 기준이며 외부 전문가 정확도 인증은 아닙니다.</p>
<h2>원인 및 수정</h2><ul><li>CJ: CJ ENM·CJ제일제당 사건의 본문상 지주 연결 미확인을 일반 사실 추출 실패로 처리. 이제 연결 미확인으로 선별 결과를 조정하고 추가 검색 결과에서 사유를 제공합니다. 계열사 뉴스를 지주 자체 호재로 강제 변환하지 않습니다.</li><li>현대차 혼합 기사: 고정 사건 유형과 허용 영향 유형이 불일치. 구조화 응답의 허용 유형을 사실 묶음에 맞게 제한하고, 실패 사유를 재시도 단계에 전달합니다. 재현 기사에서 응답 생성 성공, 방향은 판단 보류.</li><li>현대차·기아: 공동 주체를 정확한 구분자로 나눠 인식. CJ를 CJ ENM의 접두어로 인식하지 않음. 기존 공모전 기사의 사실 추출 성공.</li><li>추출·해석 진단에 검증 사유와 시간 초과를 남겨 포괄적 ValueError만 남던 문제 개선.</li></ul>
<h2>새 기사 결과: 성공과 실패를 함께 기록</h2><p>6건 중 연결·관련성 제외 2건, 최종 분석 완료 1건, 최종 설명 검증 실패 3건. 추출·해석 단계의 구조 검증 오류는 0건이지만, 전체 품질 통과를 뜻하지 않습니다. 동일 사건 중복 연결 및 무주어 조건 문단 보존은 남은 과제입니다.</p>'''+''.join(cards)+'</html>'
Path('output/status-root-validation-report.html').write_text(page,encoding='utf-8')
print('output/status-root-validation-report.html')
