"""Summarize frozen replay and current production runs separately."""
import json
from pathlib import Path
from html import escape as e
from collections import Counter
from app import analysis

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

blocks = []
for label,pattern in [("동일 기사 재평가","output/batch-v7-replay-{}.json"),
                      ("실제 앱 재실행","output/live-v7-{}.json")]:
    for code in ("000660","005930"):
        data = read(pattern.format(code))
        r = data.get("result",data)
        f = {x["article_id"]:x for x in r["findings"]}
        selected = [a for a in r["articles"] if a.get("analysis_candidate")]
        counts = Counter(f[a["id"]]["direction"] for a in selected)
        rows = []
        for a in r["articles"]:
            if a.get("body_status") != "추출됨":
                continue
            status = "대표 기사로 묶음" if a.get("duplicate_of") else "분석 대상" if a.get("analysis_candidate") else "분석 제외"
            finding = f[a["id"]]
            rows.append(f"<tr><td><a href='{e(a['url'],quote=True)}'>{e(a['title'])}</a></td><td>{e(a.get('relation',''))}<br>{status}</td>"
                        f"<td>{e(finding['direction']) if a.get('analysis_candidate') else '—'}</td>"
                        f"<td>{e(finding['reason'])}<details><summary>확인할 점</summary>{e(finding['counterpoint'])}</details></td></tr>")
        blocks.append(f"<h2>{label} · {e(r['stock']['name'])}</h2><p>{e(r['as_of'])} · 검색 {len(r['articles'])}건 · "
                      f"분석 {len(selected)}건 · 중복 {sum(bool(a.get('duplicate_of')) for a in r['articles'])}건 · "
                      f"상승 {counts['상승 요인']} / 하락 {counts['하락 요인']} / 보류 {counts['판단 보류']}</p>"
                      "<div class='scroll'><table><tr><th>원문</th><th>관련성·선별</th><th>판단</th><th>설명</th></tr>"
                      +"".join(rows)+"</table></div>")
        if label == "실제 앱 재실행":
            cache = read(f"tmp/live-v7-bodies-{code}.json")
            errors = analysis.validate({"findings":[f[a["id"]] for a in selected]},cache["articles"],[])
            print(code,"final validation",errors)
            assert not errors

html = """<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>종목 선별·중복·설명 개선 검증</title><style>
body{margin:0;background:#f5f5ef;color:#243e32;font:15px/1.7 'Malgun Gothic',sans-serif}
main{max-width:1200px;margin:auto;padding:40px 24px}h1{font-size:32px}h2{margin-top:40px}
table{width:100%;border-collapse:collapse;background:white}td,th{padding:14px;text-align:left;border-bottom:1px solid #dce4d8}
th{background:#e7eee5}td:first-child{width:30%}td:nth-child(2),td:nth-child(3){min-width:85px}
a{color:#237552}.scroll{overflow:auto}.note{background:#fff8e9;border-left:3px solid #bd934c;padding:18px}
</style><main><p>2026.10.20 · 파이프라인 v7</p><h1>종목 연결과 중복 보도, 설명의 사실 범위</h1>
<p>이전 실행의 실제 본문을 고정한 비교 평가와, 운영 앱에서 다시 실행한 결과를 구분했습니다.
고정 표본은 수정에 사용한 회귀 검증이며 새로운 표본의 정확도 측정이 아닙니다.
고정 표본 재평가 이후 보류 대체 문구와 시제 검증 표현을 추가 보완했습니다. 실제 앱 결과는 아래 별도 표에 표시합니다.</p>
<ul><li>대상 기업의 역할을 별도로 판정합니다. 비교·배경으로 판정된 기업은 직접 관련 표기와 충돌해도 분석 대상에서 제외합니다.</li>
<li>동일 사건은 대표 기사와 연결하고 추가 검색 결과에 남깁니다. 특히 현장 방문은 동일 방문자·장소·날짜와 본문 유사도를 함께 확인합니다. 새 계약이 있는 기사는 이 규칙으로 묶지 않습니다.</li>
<li>보류 설명도 의미 검토하며, 최종 조건 미확정과 확인된 준비·약정을 구분합니다. 검토에서 거절해 보류로 바뀔 때도 프리IPO 진행·출자 약정 원문이 있으면 보존합니다.</li>
<li>인용은 종료 예상인데 설명은 완료로 단정하는 특정 표현을 검증 오류로 처리합니다. 모든 시제·사건을 판별하는 완전한 규칙은 아닙니다.</li></ul>
<div class="note">확인한 개선: 삼성전자에 포함되던 SK하이닉스 중심 기사를 제외하고, 같은 방문 사건 2건을 대표 1건으로 줄였습니다.
상장 기사의 설명은 미확정 조건으로 범위를 좁혔습니다. 자동 테스트 33개 통과.<br>
남은 한계: 증권사 전망의 직접 관련 여부, 간접 호재와 수급 위험의 분류는 여전히 개선 대상입니다.
고정 표본 재평가에서 엑셀리스 투자 기사를 SK하이닉스 직접 관련으로 과선택하는 사례도 남았습니다.
방문 외 사건의 중복 판단은 모델 의존성이 있고, 본문을 수집하지 않은 기사까지 정확하게 제외했다고 볼 수 없습니다.
두 모델 단계의 판단이 일치해도 사실성이 보장되지는 않습니다.</div>
""" + "".join(blocks) + """<p>뉴스 전체 원문은 재배포하지 않으며 링크와 분석 결과만 표시합니다.
검증 스냅샷: batch-v7-replay-*.json / live-v7-*.json. 과거 통합 보고서는 live-batch-validation-report.html에 보존했습니다.</p></main></html>"""
Path("output/batch-v7-validation-report.html").write_text(html,encoding="utf-8")
