# MCP 수정 내역

## korea-stock-mcp

기반: jjlabsio/korea-stock-mcp npm 1.4.1, ISC.
검증 당시 소스 기준 커밋: `210595eec73a39cd04e2fb175f6e69b1516f0dd4`.
배포된 JavaScript `dist`를 보존하고 필요한 부분만 수정했습니다.

- KRX HTTP URL을 HTTPS로 변경
- 공시 조회의 sort, sort_mth, page_no, page_count 스키마 오류 수정
- 손익계산서 필터 허용
- DART 조회 결과 없음(013)을 정상 빈 결과로 취급
- 외부 요청 20초 제한
- 부모 프로세스가 전달한 키만 사용하도록 `.env` 자동 로드를 제거
- 회사명 공백 제거 검색·종목 코드 앞부분 검색, 검색 결과 없음은 빈 배열 반환
- 기본정보 조회 `codeList=["*"]` 확장: 공식 KRX 종목 목록을 가져와 검색에 사용

## korean-news-mcp

기반: SongT-50/korean-news-mcp, MIT.
기준 커밋: `a735197f55a29ac493106a64c46a6d2503c5edad`.
원본 `server.py`를 `upstream_server.py`로 보존했습니다.

- 원본 Google News RSS 검색 URL 생성기를 재사용
- 별도 서버 진입점에 NAVER API HUB 검색과 Google RSS 대체 검색을 등록
- 날짜·중복 URL 정규화, 본문 추출 품질 상태
- Trafilatura 본문 추출, 최대 크기·문자 수 제한, 잘림 여부 기록
- 공개 URL·리다이렉트 검사, 공급자 인증값을 언론사 요청에 보내지 않음
- MCP SDK 1.30.0 고정

원본의 다른 도구나 원격 HTTP 서버는 앱에서 등록·실행하지 않습니다.
