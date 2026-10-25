# 기술 설계

## 구성 요소

```text
bot/
  main.py                    Discord 명령 수신 및 순위/검색 응답

core/
  browser_helper.py          Playwright 브라우저 세션 관리
  config.py                  .env 설정 로드
  content_analyzer.py        발행 전 본문 분석 코치
  naver_blog_importer.py     내 블로그 공개 글 가져오기
  naver_blog_monitor.py      네이버 검색 URL 생성, 글 추출, 순위 계산
  naver_datalab.py           네이버 데이터랩 인기 키워드 조회
  signal_realtime.py         Signal 실시간 검색어 조회
  storage.py                 SQLite 저장소와 마이그레이션
  watch_ranker.py            관심 키워드 자동 확인 루프

webapp/
  main.py                    FastAPI 앱과 API 라우트
  static/                    모바일 웹 UI

scripts/
  check_browser.py           Playwright 실행 점검
  check_naver_blog.py        검색 파서 점검
  import_target_blog.py      내 블로그 공개 글 일괄 가져오기
  run_web.py                 웹앱 실행

tests/
  test_*.py                  단위 테스트와 API 테스트
```

## 검색 표면

| Surface | 설명 | URL |
| --- | --- | --- |
| `desktop` | PC 통합검색 | `https://search.naver.com/search.naver?where=nexearch...` |
| `desktop_blog` | PC 블로그탭 | `https://search.naver.com/search.naver?where=blog...` |
| `mobile` | 모바일 통합검색 | `https://m.search.naver.com/search.naver?where=m...` |
| `mobile_blog` | 모바일 블로그탭 | `https://m.search.naver.com/search.naver?where=m_blog...` |
| `blog_section` | 네이버 블로그 섹션 | `https://section.blog.naver.com/Search/Post.naver...` |

기본 순위 조회는 위 다섯 표면을 모두 확인한다.

## 순위 계산 알고리즘

현재 순위 확인은 surface별 `limit=30`으로 동작한다.

처리 순서:

1. 검색 표면별 URL을 생성한다.
2. Playwright로 페이지를 연다.
3. `a[href*="blog.naver.com"]` 링크를 수집한다.
4. 개별 글 URL만 남긴다.
5. `m.blog.naver.com` URL은 `blog.naver.com`으로 정규화한다.
6. 같은 글 URL은 중복 제거한다.
7. 위에서부터 최대 30개까지 확인한다.
8. 대상 블로그 ID 또는 특정 글 URL과 일치하는 첫 번째 결과를 순위로 반환한다.

찾지 못하면 `rank=None`으로 반환한다.

## URL 정규화

모바일 검색 결과는 `m.blog.naver.com` 링크를 반환할 수 있다.

내부 비교와 중복 제거를 위해 아래처럼 정규화한다.

```text
https://m.blog.naver.com/{blogId}/{postNo}
-> https://blog.naver.com/{blogId}/{postNo}
```

## 브라우저 전략

PC 검색:

1. 데스크톱 User-Agent
2. 1366x768 viewport

모바일 검색:

1. 모바일 검색 URL
2. iPhone 계열 User-Agent
3. 390x844 viewport

네이버가 User-Agent에 따라 DOM을 바꿀 수 있으므로 모바일 surface에서는 모바일 User-Agent를 함께 사용한다.

## 웹앱 구조

모바일 웹앱은 로그인 후 아래 흐름을 제공한다.

1. `순위` 탭
2. `인기 키워드` 탭
3. `발행 전 분석` 탭
4. `내 글` 탭

주요 API:

```text
POST /api/login
POST /api/logout
GET  /api/session

GET  /api/rank
GET  /api/blogs
GET  /api/history
GET  /api/trends

GET  /api/watch-keywords
POST /api/watch-keywords
DELETE /api/watch-keywords/{id}
GET  /api/today-summary

GET  /api/datalab/shopping-keywords
GET  /api/signal/realtime-keywords

POST /api/content-analysis

GET  /api/my-posts
GET  /api/posts
POST /api/posts
GET  /api/posts/{id}
PATCH /api/posts/{id}
DELETE /api/posts/{id}
POST /api/posts/{id}/keywords
DELETE /api/posts/{id}/keywords/{keyword_id}
POST /api/posts/import-target-blog
POST /api/my-posts/{id}/check
```

`APP_PASSWORD`가 설정되면 모든 API와 메인 화면은 로그인 세션을 요구한다.

## Discord 봇 구조

Discord 봇은 개발자용 원격 진입점으로 유지한다.

현재 명령:

```text
!help
!ping
!blog 검색어
!rank 검색어
!rank-pc 검색어
!rank-mobile 검색어
!rank-blog 검색어
!rank-mblog 검색어
!rank-section 검색어
```

`!rank*` 명령은 `.env`에 `TARGET_BLOG_ID` 또는 `TARGET_BLOG_URL`이 있어야 동작한다.

## 저장 구조

기본 DB 경로:

```text
data/bms.sqlite3
```

핵심 테이블:

```text
rank_history
  keyword
  target_blog_id
  surface
  rank
  checked_count
  post_title
  post_url
  collected_at

watch_keywords
  keyword
  enabled
  created_at

my_posts
  title
  url
  blog_id
  post_id
  category
  published_at
  content_summary
  content_text
  content_length
  content_hash
  imported_at
  enabled
  created_at
  updated_at

post_keywords
  post_id
  keyword
  keyword_type
  enabled
  created_at

post_rank_history
  post_id
  keyword
  surface
  rank
  checked_count
  result_url
  matched_title
  matched_url
  collected_at
```

## 장애 지점

네이버 검색 결과 DOM은 자주 바뀔 수 있다. 따라서 파서는 class name보다 URL과 의미 기반 선택자를 우선한다.

현재 파서 기준:

1. `a[href*="blog.naver.com"]`를 수집한다.
2. 개별 글 URL 패턴만 통과시킨다.
3. 프로필, 블로그 홈, 섹션 링크는 제외한다.
4. `m.blog.naver.com`은 `blog.naver.com`으로 정규화한다.

## 현재 운영 판단

Playwright가 핵심이므로 상시 운영은 서버리스보다 로컬 PC 또는 작은 VM이 더 적합하다.

현재 우선 운영 모드:

1. 로컬 PC에서 웹앱과 Discord 봇을 필요할 때 실행
2. 소형 VM은 후속 배포 옵션으로 검토
