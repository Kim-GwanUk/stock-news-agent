# 천기누설

국내주식 보유·관심 종목의 뉴스 원제목을 그대로 표시하고, 상승·하락 요인과 근거를 확인하는 로컬 MVP입니다.

현재 분석 기준은 v21입니다. POSCO 한글명, 금융그룹 재무지표 범위 연결, 정확한 인용 위치 복구, 미래 전망의 제한 문맥 보존을 보완했습니다. 테스트147개 통과. 기존 실패3건 추출복구, 새4기사 선별3/4 일치이나 핵심 사건 대신 배경실적 선택·그룹/은행 범위 혼재·누락이 남았습니다. `output/coverage-v21-validation-report.html`을 참고하세요.

## 첫 버전 범위

- 회사명·종목 코드 검색 후 선택 등록(최대 5개), KRX로 시장 자동 확인
- 두 실제 MCP 서버를 stdio로 호출: NAVER 중심 뉴스 검색, KRX 일별 시세, DART 보완 공시
- 최근 7일 뉴스 최대 20건, 관련 기사 최대 8건 본문 확보 시도 후 최대 5건 분석
- 본문 단락에 근거해 직접 관련·시장/업종 맥락·단순 언급·무관을 분류한 후 분석 대상 선택
- LangGraph 병렬 수집과 명시적 합류, 근거 부족 시 공시 보완 1회
- 구조화된 OpenAI 분석, 인용문·출처 ID·설명 수치 검증, 수정 최대 1회, 사업 영향 의미 검증 1회
- 본문 접근 실패·모델 응답 실패·검증 실패는 판단 보류
- 기사별 판단 1개, 원문 조각 번호 기반 인용 복원, 방향과 영향 수준의 별도 검토. 과거 실제 기사 평가 결과는 `output/direction-validation-report.html` 참고
- 동일 종목·본문·분석 기준의 선별과 검증된 판단은 7일 재사용. 뉴스 분석 버튼은 수집 결과를 갱신하되 동일 근거를 무작위로 재판정하지 않음. 본문·모델·기준·보완 공시 변경 시 해당 판단을 새로 생성
- SQLite 관심 종목·불변 분석 이력·캐시, 토큰 사용량 및 모델/프롬프트 버전 저장
- Streamlit 일별·주별 주가 차트(1개월·3개월), 고저 범위·거래량, KRX 전일 대비 등락률, 최근 5거래일 평균 대비와 상세 표
- 원제목·언론사 카드, 방향 필터, 원문 링크, 근거와 반대 근거

기본 분석 모델은 `gpt-4.1-mini`입니다. `.env.local`의 `OPENAI_MODEL`로 변경할 수 있습니다.
뉴스 내용은 외부 입력 데이터로 취급하며 LLM에 도구 실행 권한을 부여하지 않습니다.
일별 시세는 오늘 이전 날짜에서 조회하고 실제 기준일을 표시합니다.
영향 수준은 정성 평가이며 주가 상승 확률이나 인과적 가격 영향 수치가 아닙니다.

## Windows 실행

프로젝트 경로에서 실행합니다. 현재 작업 환경에는 `.venv`와 Node 의존성을 설치해 두었습니다.

```powershell
.\scripts\start.ps1
```

- 화면: http://127.0.0.1:8501
- API 문서: http://127.0.0.1:8000/docs
- 로그: `tmp/backend-error.log`, `tmp/frontend-error.log`
- 이미 실행 중인 경우 위 명령을 중복 실행하지 않습니다.
- 서버 종료: `.\scripts\stop.ps1`

새 환경에서는 Python 3.12와 Node.js 22 이상을 준비합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
Push-Location vendor/korea-stock-mcp
npm install --omit=dev --ignore-scripts
Pop-Location
```

처음 설치할 때만 `.env.example`을 `.env.local`로 복사하고 본인의 키를 입력합니다.
기존 `.env.local`이 있다면 덮어쓰지 마세요.

```powershell
if (!(Test-Path .env.local)) { Copy-Item .env.example .env.local }
```

NAVER·KRX·DART·OpenAI 키를 설정하며, KRX는 사용할 API별 이용 승인이 필요합니다.
프런트엔드에는 키를 전달하지 않으며 두 MCP에는 해당 공급자 키만 전달합니다.

## GitHub 공유 범위

실제 키는 `.env.local`에만 보관하고, 저장소에는 값이 비어 있는 `.env.example`만 포함합니다.
`data/`, `output/`, `tmp/`, DB·백업·로그 및 개인 설정은 `.gitignore`로 제외합니다.
`output/`의 검증 보고서·스크린샷은 로컬 산출물이므로 아래 문서의 관련 경로는 복제 직후에는 존재하지 않습니다.
Docker 데이터 볼륨도 GitHub에 포함되지 않습니다. 새 환경의 관심 종목·분석 이력은 별도로 시작합니다.
GitHub 공유는 앱 배포나 데이터 백업을 대신하지 않습니다.

업로드 전에 `.venv/Scripts/python.exe scripts/audit_github.py`로 후보 파일을 검사하세요.
검사는 실제 환경변수 키와 알려진 자격증명 패턴, 개인 경로 및 별도 검토가 필요한 파일을 확인합니다.
통과는 모든 민감정보가 없다는 보증이 아니므로 `git diff --cached`도 확인해야 합니다.

## Docker Compose

명령어 없이 사용하려면 프로젝트 폴더의 **`주식 앱 시작.cmd`** 또는 **`주식 앱 종료.cmd`**를 더블클릭하세요.
시작 파일은 Docker Desktop이 꺼져 있으면 먼저 실행하고, 앱 준비가 끝나면 기본 브라우저를 엽니다.
종료 파일은 이 프로젝트의 컨테이너만 정지하며 관심 종목과 분석 이력은 유지합니다.
오류가 발생하면 창이 남아 메시지를 확인할 수 있습니다. 이 파일들의 바로가기를 바탕 화면에 만들어 사용해도 됩니다.
이미 만들어 둔 Docker 이미지를 사용하므로 코드 수정 반영에는 아래 빌드 명령이 필요합니다.

Docker Desktop의 Linux 엔진을 시작한 후 실행합니다.

```powershell
docker compose up -d --build
```

화면은 8501, 백엔드는 8000이며 호스트의 `127.0.0.1`에만 바인딩합니다.
인증을 제공하지 않는 개인 로컬 버전이므로 외부 인터넷으로 공개하지 않습니다.
2026-10-20 Docker 실제 빌드·기동, MCP 실조회, 기사 1건 분석, 컨테이너 내 테스트 79개를 확인했습니다.
로컬 앱과 포트가 같으므로 전환 전에 `.\scripts\stop.ps1`로 로컬 서버를 종료하세요.

사용 후 `docker compose stop`, 다시 사용할 때 `docker compose start`를 실행합니다.
Docker Desktop이 먼저 실행되어 있어야 합니다. 코드 수정 후에는 `docker compose up -d --build`로 다시 빌드합니다.

관심 종목·이력은 `stockproject_stock-data` 볼륨에 저장됩니다. `stop`이나 일반 `down`으로는 지워지지 않지만
`docker compose down -v`는 저장 볼륨을 삭제하므로 사용하지 마세요.
로컬 저장소와 Docker 저장소는 자동 동기화되지 않습니다.
이번 이전은 관심 종목 2개와 분석 이력 23건을 복사했으며, 재시작 후 전체 기록 해시와 API 응답을 대조했습니다.
기존 `data/app.sqlite`는 보존했고 별도 백업은 `output/docker-migration-20261020-235243.sqlite`입니다.
검증 기록은 `output/docker-migration-verification.json`을 참고하세요.

## 테스트

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

키 없이 수행하는 테스트는 외부 호출을 대체합니다. 실제 API 확인은 별도입니다.

첫 판단 추가 평가: `output/first-judgment-validation-report.html`. 신규 과거 기사 8종을 캐시 없이 평가했습니다.
방향 일치와 설명의 사실 정확성은 구분합니다. 대출 조건·리콜 영향 범위 설명에는 오류가 남아 있습니다.

후속 개선(v10c): `output/explanation-v10-validation-report.html`. 대출·리콜의 반대 근거는 범위와 집행을 구분하는 고정 안내로 제공하며 설명 본문은 별도 검토합니다. 새 기사에서 영문 금액 단위 변환으로 인한 보류와 예비 합의 조건 생략은 남아 있습니다.

금액·조건 개선(v11c): `output/financial-v11-validation-report.html`. 달러·원의 영문/한국어 금액을 같은 값으로 비교하고, 인용의 최대 한도(금액·비율)와 예비·비구속 조건을 설명에 보존합니다. 환율 환산·합산은 인정하지 않습니다. 이전 실제 기사 5건의 반복 평가이며 독립적인 정확도 평가는 아닙니다.

새 문서 평가(v12b): `output/financial-v12-validation-report.html`. 혼합 숫자 표기를 지원하며 최초 미사용 문서 평가와 보완 후 재검증을 구분했습니다. 주요 금액·한도·예비 단계는 유지했지만 세부 조건 설명에는 한계가 남아 있습니다.

```powershell
.\.venv\Scripts\python.exe scripts/smoke_live.py
```

이 명령은 실서비스 API와 뉴스 1건의 OpenAI 분석을 호출하므로 사용량이 발생합니다.
키·원문은 출력하지 않고 결과 수, 기준일, 검증 오류, 토큰 수만 출력합니다.

## 개발 구조

```text
app/api.py          HTTP API와 분석 실행 제한
app/graph.py        LangGraph 병렬·조건 분기
app/providers.py    뉴스·시세·공시 수집과 캐시
app/analysis.py     구조화 출력과 인용 검증
app/news_selection.py 본문 기반 관련성 선별
app/db.py           SQLite 저장
frontend/app.py     Streamlit 화면
vendor/             두 MCP 수정본과 원본 라이선스
tests/              오류 분기·근거 검증·화면 테스트
docs/STATUS.md      검증 결과와 후속 개발 범위
```

## 출처

### DART RAG

Docker Compose에 Qdrant가 추가되었습니다. 기존 시작·종료 바로가기로 함께 켜고 끕니다.
`qdrant-data` 볼륨에 임베딩과 공시 문단을 보관하며, `stock-data`의 관심 종목·분석 이력은 유지됩니다.
볼륨을 지우는 `docker compose down -v`는 사용하지 마세요.

- 모델: `text-embedding-3-small` (1536차원), 컬렉션 `dart_small_v1`.
- 수집: 기존 DART 키로 공식 고유번호·공시검색·원본 ZIP API를 호출합니다.
- 범위: 관심 종목별 최근 400일 정기보고서 최대 3건. 전체 공시나 실시간 정정 추적은 아닙니다.
- 앱의 **공시 자료 · 저장과 근거 검색 → DART 자료 동기화**로 갱신합니다. 임베딩 API 비용이 발생합니다.
- 저장 후 뉴스 분석에 공시 배경 검색이 자동 연결됩니다. 기사 사실·조건을 대체하지 않습니다.
- 종목코드·DART 고유번호·공시일·최근 동기화 문서 목록으로 검색을 제한합니다.
- 발행회사 격리와 문단 주체 판별은 다릅니다. 연결 보고서에는 계열사·경쟁사 내용도 포함될 수 있습니다.
- 로컬 Python 실행에서는 Qdrant를 켠 뒤 `DART_RAG_ENABLED=1`, `QDRANT_URL=http://127.0.0.1:6333`을 설정합니다.
- 검증: `scripts/validate_dart_rag.py`. 결과는 `output/dart-rag-validation.json`에 저장됩니다.


- [korea-stock-mcp](https://github.com/jjlabsio/korea-stock-mcp), ISC
- [korean-news-mcp](https://github.com/songt-50/korean-news-mcp), MIT
- [NAVER API HUB 이전 안내](https://guide.ncloud-docs.com/docs/apihub-migration)
- [LangGraph 그래프 API](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [OpenAI 구조화 출력](https://developers.openai.com/api/docs/guides/structured-outputs)

MCP 코드 라이선스와 뉴스·시장 데이터의 이용 권리는 별개입니다. 공개 배포 전 각 데이터 이용 조건을 확인해야 합니다.

지급 조건 검증(v13b): [보고서](output/payment-v13-validation-report.html). 조건 원문 보존, 줄바꿈 복원, 최종 지원과 과거 예비 합의 구분을 보완했습니다. 결과 및 평가 한계는 보고서 참조.

최신순 선택 수정 및 4종목 실제 뉴스 전체 흐름 검증(v14): [보고서](output/latest-v14-validation-report.html).
본문을 확보하고 관련성·중복 검증을 거친 대표 기사 중 최신 5건을 우선 분석합니다.
검색 전체의 누락 방지나 긍정·부정 판단 정확도를 보장하는 변경은 아닙니다.


사실 고정 구조(v16): [검증 보고서](output/locked-v16-validation-report.html).
원문 문단의 사실·금액·조건을 먼저 고정한 뒤 사업 영향 경로만 선택하고 설명을 조립합니다.
수정 재시도에서도 사실 묶음은 바뀌지 않습니다. 원문 보존과 방향 해석의 정확도는 별개이며,
혼합 실적의 비교 기준 판단과 일부 문단 추출 실패는 미해결입니다. 독립 평가와 회귀 평가를 보고서에서 구분했습니다.
