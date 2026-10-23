# 천기누설

국내 상장주식의 뉴스·공시를 바탕으로 내 종목의 긍정·부정 요인과 근거를 확인하는 로컬 앱입니다.

## 시작하기

**준비물:** Docker Desktop(Linux 컨테이너 모드), 저장소 접근 권한, NAVER·KRX·DART·OpenAI API 키.
Python·Node.js는 Docker에 포함되므로 따로 설치하지 않아도 됩니다.

```powershell
git clone https://github.com/Kim-GwanUk/stock-news-agent.git
cd stock-news-agent
if (!(Test-Path .env.local)) { Copy-Item .env.example .env.local }
notepad .env.local
```

Git 대신 GitHub의 **Code → Download ZIP**으로 받아도 됩니다.
`.env.local`에 아래 값을 입력합니다. 기존 키 파일은 덮어쓰지 마세요.

| 설정 | 용도 |
|---|---|
| `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` | NAVER API HUB 뉴스 검색 |
| `KRX_API_KEY` | 종목 기본정보·일별 시세·코스피/코스닥 지수 |
| `DART_API_KEY` | 공시 조회 |
| `OPENAI_API_KEY` | 뉴스·사진 분석, 임베딩 |

KRX는 사용하는 API별 승인이 필요합니다. 지수는 `kospi_dd_trd`, `kosdaq_dd_trd`를 사용합니다.
OpenAI API에는 사용 가능한 결제·한도와 모델 접근 권한이 필요하며, 호출 비용이 발생합니다.
macOS/Linux에서는 `test -f .env.local || cp .env.example .env.local`로 설정 파일을 복사하세요.

Docker Desktop을 켜고 프로젝트 폴더에서 실행합니다.

```powershell
docker compose up -d --build --wait --wait-timeout 180
```

앱: **http://127.0.0.1:8501** · API 문서: http://127.0.0.1:8000/docs

첫 빌드에는 인터넷 연결과 다운로드 시간이 필요합니다. 새 컴퓨터에서는 관심 종목이 비어 있는 상태로 시작합니다.

2026-10-23 검증: GitHub 신규 복제·캐시 없는 빌드·빈 볼륨에서 화면, 종목 등록, MCP/API, 임베딩·Qdrant, 재시작 후 저장 유지 확인.
동일 Windows 호스트의 독립 Linux 컨테이너 검증이며 다른 실제 컴퓨터·모든 CPU 환경을 시험한 것은 아닙니다.

## 주요 기능

- **내 종목:** 검색·CSV·사진으로 등록, 등록 전 확인 및 중복·비상장 검사, 개수 제한 없는 목록, 선택한 종목 바로 삭제
- **뉴스 분석:** 원제목·언론사 표시, 관련 뉴스 선별, 중복 숨김 전환, 긍정·부정 판단과 사실·금액·조건 근거
- **주가 차트:** KRX 일별·주별 시세, 하루 OHLC, 전일 등락률·5거래일 평균 대비
- **아침 보고서:** 최근 5거래일 그래프, 금리·환율·증시 표, 조건부 리스크 전망, 방향별 뉴스 최대 3건
- **근거 검색:** DART 공시 RAG, 뉴스 사건·판별 근거 저장, 회사 코드별 Qdrant 검색

일별 차트는 **실시간·분봉 차트가 아닙니다.** 지표별 기준일을 확인하세요.
분석 미완료와 판단 보류는 구분해 표시하며, 긍정·부정은 주가 상승 확률이나 수익률 예측이 아닙니다.
저장한 과거 판단은 아직 통계적 정답으로 검증하거나 이후 판단에 자동 사용하지 않습니다.
이메일 자동 발송·시간대별 시세·업종 대비 PER/PBR/ROE 비교는 미지원입니다.

## 종료와 업데이트

```powershell
docker compose stop          # 종료: 데이터 유지
docker compose up -d         # 다시 시작
git pull --ff-only           # 코드 업데이트
docker compose up -d --build # 업데이트 반영
```

Windows에서는 **최초 빌드 후** `주식 앱 시작.cmd` / `주식 앱 종료.cmd`를 더블클릭해도 됩니다.
오류가 나면 `docker compose ps`와 `docker compose logs --tail 100 backend frontend`를 확인하세요.

## 데이터 보존

- 실제 키는 `.env.local`에만 보관합니다. GitHub에는 빈 설정 예시만 포함합니다.
- 관심 종목·분석 이력은 `stockproject_stock-data`, 벡터는 `stockproject_qdrant-data` 볼륨에 저장됩니다.
- **`docker compose down -v`나 Docker 공장 초기화는 데이터를 삭제할 수 있습니다.**
- GitHub에는 DB·백업·로그·`data/`·`output/`·`tmp/`가 포함되지 않습니다. 다른 컴퓨터로 데이터가 자동 이전되지 않습니다.
- Compose 이름은 `stockproject`로 고정되어 폴더명이 달라도 더블클릭 실행과 같은 데이터를 사용합니다.
- 인증 없는 개인 로컬 앱입니다. 포트는 `127.0.0.1`에만 연결되며 인터넷 공개용이 아닙니다.

## 기술 구성

Streamlit · FastAPI · LangGraph · SQLite · Qdrant · OpenAI · 뉴스/주식 MCP

코드: `app/`, `frontend/` · 테스트: `tests/` · 실행·검증: `scripts/` · [MCP 수정 및 라이선스](vendor/README.md)

개발용 Python 환경에서는 `requirements.lock.txt` 설치 후 `python -m pytest tests -q`로 테스트합니다.
업로드 전 `python scripts/audit_github.py`로 키·제외 파일을 검사하고 커밋 내용도 확인하세요.
Docker 패키지는 버전 범위를 사용하므로 장래의 빌드까지 동일 버전을 보장하지는 않습니다.
