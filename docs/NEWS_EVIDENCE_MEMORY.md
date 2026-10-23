# 뉴스 이벤트·판별 근거 보관

## 범위
뉴스 분석의 finish 다음 remember 노드가 사건 기록을 SQLite에 보관하고, 검색 가능한 원문 사실을 OpenAI text-embedding-3-small로 임베딩해 Qdrant news_evidence_small_v1에 저장한다. DART 컬렉션과 분리한다. 기존 판단에 과거 결과를 자동 주입하지 않으며 통계 확률도 계산하지 않는다.

## 저장 단위와 관계
- 종목코드 + 기사 ID + 고정 사실 해시 + 판단/모델/프롬프트/저장 스키마 버전으로 불변 기록 ID 생성. 같은 내용을 재실행하면 추가 기록 대신 실행 ID를 연결한다.
- news_events: 출처 URL/언론사/발행 시각, 원문 해시, 기업 주체, 사건 유형, 금액과 단계 표현을 포함한 사실, 조건 문맥, 원래 설명·반론·인용 및 판단 상태. 원문 본문 전체는 이 저장소에 복제하지 않는다.
- news_event_runs: 기록과 분석 실행 연결.
- news_event_relations: about_company, reported_by_article, supported_by_fact, duplicate_of_article. 기사 간 동일 사건을 모두 통합한 통계용 사건 ID는 아직 아니다.
- facts는 직접 주체 근거, joint_context는 공동 주체, excluded_context는 계열사·타사 등 직접 귀속에서 제외한 문맥. condition_context와 article_caveats는 누락을 막기 위해 보존하지만 단독 기업 실적으로 취급하지 않는다.

## 재사용 경계
reusable은 사실 검색 가능 여부다. decision_reusable은 과거 판단의 자동 검증 통과 여부다. 서로 다르며 둘 다 인간이 확인한 정답을 뜻하지 않는다. 판단 실패여도 원문·주체를 확인한 사실은 검색 가능하지만 검색 응답에는 방향/영향 판단을 노출하지 않는다. human_reviewed=false, statistical_label=null로 보관한다.

벡터에는 회사명과 직접 주체 사건의 원문 문장만 넣는다. 모델의 긍정/부정 설명은 임베딩하지 않는다. 검색은 code/reusable/available_at 필터를 항상 사용하고 SQLite에서 같은 종목 및 기준 시점의 최신 수정본인지 다시 확인한다. 검색 점수는 문장 유사도이며 확률·신뢰도나 최종 관련성 판정이 아니다.

facts.quote는 원문 문단 전체이므로 다른 회사 언급이 들어갈 수 있다. subject와 event_quote를 구분해야 하며 문단 전체 숫자를 그 주체에게 귀속하면 안 된다. 공동 주체·조건 문맥은 별도 필드로 반환한다. 자동 주체 추출의 의미적 오류 가능성은 남아 있다.

## 장애와 API
벡터 저장 실패 시 SQLite 기록을 유지하며 pending_retry를 표시한다. 같은 ID로 재색인하므로 중복 벡터를 만들지 않는다. 검색 서비스 장애는 빈 결과로 숨기지 않고 503으로 반환한다.
- GET /stocks/{code}/news-memory : 최근 보관 기록
- POST /stocks/{code}/news-memory/search : query, 선택 as_of(시간대 포함 ISO 시각), limit(1~20)
- POST /stocks/{code}/news-memory/sync : 해당 종목의 미색인 기록 최대 50건 재시도

분석 API는 최대 220초, 화면 요청은 260초까지 기다린다. 과거 결과 백필은 원래 보관된 본문의 해시가 분석 당시 해시와 일치할 때만 허용했다. 과거 분석 시점 이전 검색은 차단한다. 실제 거래 성과를 평가하려면 수집 가능 시각, 수정주가, 중복 사건 통합, 시장 대비 수익률과 표본 수를 별도 검증해야 한다.

## 검증
tests/test_news_memory.py와 tests/test_fact_ledger.py: 조건 유지, 변조 차단, 회사 코드 필터 및 SQL 재확인, 재실행 중복 방지, 공동 주체 분리, 잘못된 판단 비노출, 최신 수정본/시점 필터, 벡터 장애 시 원본 보관.
실제 기사 결과: output/news-memory-validation-report.html 및 JSON. 새로운 현재 기사 분석과 기존 실제 기사 원문 해시 대조 백필을 구분해 기록했다.
