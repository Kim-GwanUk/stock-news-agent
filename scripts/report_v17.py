"""Render the frozen, independent v17 audit without rewriting failed results."""
import hashlib
import json
from html import escape
from pathlib import Path

OUT = Path("output")
def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))

snapshot = read("v17-pre-holdout-code.json")
assert snapshot == read("v17-holdout-code.json")
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in snapshot.items())
labels = read("v17-holdout-labels.json")
rows = []
for run in read("v17-holdout-results.json"):
    findings = {f["article_id"]: f for f in run["result"]["findings"]}
    for article in run["result"]["articles"]:
        key = article["id"]
        finding = findings.get(key)
        if finding and "required" in labels[key]:
            text = finding["reason"] + "\n" + finding["counterpoint"]
            missing = [v for v in labels[key]["required"] if v.lower() not in text.lower()]
            detail = "미보존 조건: " + ", ".join(missing) if missing else "사전 지정 핵심 사실·조건 문자열 보존"
            direction = finding["direction"]
            assert direction == labels[key]["direction"]
        else:
            direction, detail = "평가 제외", "본문 접근 실패 — 분석 성공에 포함하지 않음"
        rows.append(f"<tr><td>{escape(run['result']['stock']['name'])}</td><td><a href='{escape(article.get('url', ''), quote=True)}'>{escape(article['title'])}</a></td><td>{escape(direction)}</td><td>{escape(detail)}</td></tr>")

page = """<!doctype html><html lang="ko"><meta charset="utf-8"><title>v17 분석 검증</title>
<style>body{max-width:1080px;margin:56px auto;padding:0 24px;font:16px/1.8 system-ui;color:#203047;background:#f7f9fc}h1{font-size:32px}section{background:white;padding:24px 30px;margin:20px 0;border:1px solid #dde3ec;border-radius:12px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;vertical-align:top;padding:14px;border-bottom:1px solid #ddd}a{color:#2457a6}.note{border-left:4px solid #c88923}small{color:#5e6b7b}</style>
<h1>실적 비교 기준과 영문 사실 추출 · v17</h1><small>2026-10-21 · 새 자료 평가 후 분석 코드 변경 없음</small>
<section><h2>무엇을 바꿨나</h2>
<p>실현된 전사 이익의 전년 대비 변화를 우선하고, 없으면 전분기 비교를 사용합니다. 시장 예상 상회나 일부 사업부 성장을 전사 실적 개선과 구분합니다. 이 기준은 주가 예측이 아닌 기사 속 사업 영향 분류 정책입니다.</p>
<p>짧은 본문은 문단 전체를 보존합니다. 긴 본문은 기사별로 추출하여 한 기사 실패가 다른 기사 결과를 없애지 않도록 했습니다. 영향 해석에서는 이미 고정된 문단 번호만 선택할 수 있으며, 실패 단계와 재시도를 기록합니다.</p>
<p>사실이 근거로 뒷받침된다는 검토를 통과한 경우에만 명시적인 비교 기준을 적용합니다. 사실 불일치가 발견되면 판단 보류를 유지합니다.</p></section>
<section><h2>기존 오류 회귀 검증</h2><p>기존 LG전자 혼합 실적은 하락 요인, 삼성SDI 영문 조건부 대출은 상승 요인으로 최종 코드에서 각각 두 번 일치했습니다. 처음 실패한 결과도 별도 파일에 보존했습니다. 과거 영문 추출 실패의 정확한 원인은 확정하지 못했으며, 이번에는 실패 격리와 관측 가능성을 개선했습니다.</p></section>
<section><h2>수정에 사용하지 않은 실제 자료</h2><p>2024~2025년 공식 영문 발표 3건을 새로 확보하고 코드와 기대 결과를 먼저 고정했습니다. 세 건 모두 첫 시도에 사실을 추출했고 방향은 사전 기준과 일치했습니다. 아래 필수 사실 확인은 문자열 검사와 원문 대조이며 전체 정확도 지표가 아닙니다.</p>
<table><tr><th>종목</th><th>자료</th><th>방향</th><th>조건 확인</th></tr>""" + "".join(rows) + """</table></section>
<section class="note"><h2>남은 문제</h2><p>SK하이닉스 발표 끝부분의 ‘잠정(preliminary)’ 조건이 선택된 사실 문단에 포함되지 않았습니다. 방향은 맞아도 조건 보존은 완전하지 않습니다. 선택된 사실을 고정하는 것만으로 선택되지 않은 조건의 누락까지 막을 수 없다는 한계입니다.</p>
<p>다음 개선 대상은 긴 본문의 조건 문단 누락 검사입니다. 이번 자료를 대상으로 추가 튜닝하지 않아 독립 평가 결과를 그대로 유지했습니다. 영향 크기는 정성 판단이며 별도로 보정되지 않았습니다.</p>
<p>계약 해지 보도는 두 배포처 모두 본문 접근에 실패했습니다. 수집 실패와 모델 추출 실패를 구분했습니다. 이번 평가는 과거 URL 직접 수집 이후의 선별·분석 경로이며 최신 검색 재현율 또는 전체 종목의 정확도를 검증한 것은 아닙니다.</p></section>
<section><h2>실행 확인</h2><p>로컬·Docker 테스트 각각 117개 통과. Docker 앱 v17 반영. 관심 종목 2개와 분석 이력 23건의 전후 레코드 해시 일치.</p>
<p>추출은 기사당 최대 두 번, 동시 처리 세 건으로 제한합니다. 추출·해석 단계에 각각 시간 제한을 두고 전체 180초 제한을 유지합니다. 기사별 호출로 호출 수는 v16보다 늘 수 있으며 실패 요청의 토큰 비용은 완전히 집계되지 않습니다.</p>
<p><a href="v17-holdout-results.json">독립 평가 원본</a> · <a href="v17-holdout-labels.json">사전 기준</a> · <a href="v17-holdout-manifest.json">수집 기록</a> · <a href="v17-pre-holdout-code.json">코드 해시</a> · <a href="v17-development-repeat-results.json">기존 오류 반복 검증</a> · <a href="v17-deployment.json">배포 검증</a></p></section></html>"""
(OUT / "v17-validation-report.html").write_text(page, encoding="utf-8")
