# 구현 로드맵

## Phase 0: 하네스 정리

목표: Codex가 매번 같은 기준으로 개발하고 검증할 수 있게 만든다.

작업:

1. 루트 `AGENTS.md` 추가
2. 문서 색인 정리
3. `pytest` 전체 통과 확인
4. 웹앱 실행 명령 확인
5. 네이버 파서 점검 명령 확인

출시 기준:

```bash
pytest
```

### 2026-04-22 로컬 실행 표준화

목표: 다른 PC에서 저장소를 내려받은 뒤 `.env`만 채우고 바로 기동할 수 있게 한다.

완료 내용:

1. 루트 `.env.example`을 추가했다.
2. `scripts/bootstrap_local.sh`로 가상환경, requirements, Playwright Chromium 설치를 한 번에 수행한다.
3. `scripts/start_local_services.sh`는 기본으로 웹앱과 Discord 봇을 함께 올리고, watch-ranker는 `START_WATCH_RANKER=1`일 때만 켠다.
4. `scripts/stop_local_services.sh`는 웹앱, Discord 봇, watch-ranker pid를 모두 정리한다.
5. 루트 `README.md`와 사용 문서를 clone 후 실행 흐름 기준으로 갱신한다.

검증:

```bash
bash -n scripts/bootstrap_local.sh
bash -n scripts/start_local_services.sh
bash -n scripts/stop_local_services.sh
pytest tests/test_config.py
```

### 2026-04-22 화면 정보 구조 정리

목표: 순위 탭 첫 화면에서 정보 밀도를 낮추고, 오늘 다시 볼 키워드와 수동 검색 흐름을 더 먼저 보이게 한다.

완료 내용:

1. 순위 탭 상단에 `관심 키워드`, `눈에 띈 변화`, `최근 검색` 요약 스트립을 추가했다.
2. Today 미니 영역은 최대 3개 키워드와 축약 순위만 보여주고 변화 배지는 제거했다.
3. `오늘의 새 소식`은 기본 접힘 영역으로 바꿨다.
4. 보조 정보는 여전히 유지하되, 첫 진입 시 `오늘 요약`, `지금 검색`, `관심 키워드`가 먼저 보이도록 정리했다.

검증:

```bash
pytest tests/test_webapp.py
```

### 2026-04-22 로컬 운영 안정화

목표: 로컬 PC나 소형 VM에서 Playwright 작업이 겹쳐도 서버가 흔들리지 않게 한다.

완료 내용:

1. Playwright 기반 웹앱 API에 공용 브라우저 작업 락을 추가했다.
2. `/api/rank`, `/api/blogs`, `/api/posts/import-target-blog`, `/api/my-posts/{id}/check`는 동시에 하나만 수행한다.
3. 브라우저 작업 중복 시 `409`와 사용자용 안내 문구를 반환한다.
4. 브라우저 작업 실패 시 raw 예외 대신 사용자용 `502` 메시지를 반환한다.

검증:

```bash
pytest tests/test_webapp.py
```

### 2026-04-22 내 글 관리 카드 보강

목표: 내 글 목록 카드 안에서 목표 키워드 관리와 최근 결과 확인을 끝낼 수 있게 한다.

완료 내용:

1. 글 카드에 목표 키워드 입력창과 추가 버튼을 넣었다.
2. 각 목표 키워드 행에 삭제 버튼을 넣었다.
3. 각 키워드 행은 기존처럼 순위 탭 검색으로 이어진다.
4. 글 카드 하단에 최근 순위 확인 결과화면 링크를 surface별로 표시한다.

검증:

```bash
pytest tests/test_webapp.py
```

### 2026-04-23 발행 전 분석 고도화

목표: 발행 전 분석 결과를 점수/누락 경고에서 끝내지 않고, 실제 작성 행동으로 이어지게 만든다.

완료 내용:

1. 분석 응답에 `photo_checklist`를 추가했다.
2. 분석 응답에 `differentiation_guidance`를 추가했다.
3. 사진 체크리스트는 의도별로 필요한 장면과 현재 사진 수 추정을 함께 안내한다.
4. 차별화 가이드는 상위글 반복 항목, 기존 글 중복, 내부 링크 후보를 묶어 새 글의 역할을 제안한다.
5. 발행 전 분석 화면에 두 결과 블록을 추가했다.

검증:

```bash
pytest tests/test_content_analyzer.py
pytest tests/test_webapp.py
```

### 2026-04-23 발행 전 분석 결과 정리

목표: 실제 작성 결정에 덜 도움이 되는 노이즈를 줄이고, 사용자에게 행동 가능한 정보만 우선 보여준다.

완료 내용:

1. SERP 누락 후보는 본문 누락 항목과 직접 연결된 주제만 남겼다.
2. SERP 누락 후보는 상위글 제목/요약에서 2회 이상 반복된 주제만 남긴다.
3. 내부 링크 후보는 키워드/목표 주제가 실제로 가까운 글만 남기도록 엄격하게 걸렀다.
4. 발행 전 분석 화면에서 본문 줄 수와 벤치마크 메모는 기본 노출에서 제거했다.
5. 항목별 점수는 부족한 항목만 보여주고, 제목/소제목/사진/차별화 가이드는 상위 몇 개만 보여준다.

검증:

```bash
pytest tests/test_content_analyzer.py
pytest tests/test_webapp.py
```

### 2026-04-23 외부 AI 보강 분석

목표: 규칙 기반 분석 위에 외부 AI의 짧고 실무적인 편집 피드백을 추가한다.

완료 내용:

1. `core/ai_content_advisor.py`를 추가했다.
2. 기본 제공자 설정은 `Groq / qwen/qwen3-32b`로 두고, OpenAI 호환 API 기반으로 교체 가능하게 만들었다.
3. `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL`, `AI_BASE_URL` 환경변수를 추가했다.
4. `/api/content-analysis` 응답에 선택적 `ai_feedback` 블록을 추가했다.
5. 발행 전 분석 화면에 `AI 보강 분석` 섹션을 추가했다.

검증:

```bash
pytest tests/test_config.py
pytest tests/test_webapp.py
```

### 2026-04-23 퍼블릭 공개용 스냅샷 정리

목표: 현재 로컬 저장소를 그대로 퍼블릭으로 전환하지 않고, 비밀값과 오래된 히스토리를 분리한 새 공개 저장소를 만들 수 있게 한다.

완료 내용:

1. `scripts/export_public_snapshot.sh`를 추가했다.
2. 새 스크립트는 `.git`, `.env`, `venv`, `logs`, `data`, `.codex`를 제외한 공개용 작업 트리를 별도 폴더로 내보낸다.
3. 기본값으로 새 폴더에서 `git init -b main`을 수행해 히스토리를 끊는다.
4. `README.md`와 `docs/13-public-repo-release.md`에 공개용 스냅샷 생성, 새 원격 저장소 연결, 다른 노트북 설치 흐름을 정리했다.

검증:

```bash
bash -n scripts/export_public_snapshot.sh
bash scripts/export_public_snapshot.sh /tmp/bms-public-test
```

### 2026-04-23 v1.0.0 문서 마감

목표: 새 노트북 이전 절차와 현재 제품 종료선을 문서로 명확히 남기고, 로컬 개인용 제품으로서 `v1.0.0` 기준을 고정한다.

완료 내용:

1. `README.md`에 새 노트북 셋업과 `v1.0.0` 범위를 추가했다.
2. `docs/01-blog-monitoring-system.md`에 `v1.0.0` 구현 상태와 운영 권장 상태를 정리했다.
3. `docs/02-usage-manual.md`에 새 노트북 준비 리스트와 SQLite DB 이전 절차를 추가했다.
4. `docs/10-product-backlog.md`에 `v1.0.0` 종료 판단과 후속 백로그 구분을 추가했다.
5. `docs/14-v1.0-release.md`를 추가해 릴리즈 기준과 제외 범위를 따로 남겼다.

검증:

```bash
pytest
```

### 2026-04-23 Discord 봇 기본 비활성 전환

목표: 실제 운영 사용자가 웹앱만 쓰는 경우를 기본값으로 두고, Discord 봇은 필요할 때만 선택적으로 켜도록 바꾼다.

완료 내용:

1. `scripts/start_local_services.sh`의 기본값을 `START_DISCORD_BOT=0`으로 변경했다.
2. README, 사용 매뉴얼, Windows 자동 시작 문서에서 Discord 봇이 기본 비활성임을 명시했다.
3. Discord 봇은 `START_DISCORD_BOT=1`일 때만 함께 실행하도록 운영 기준을 정리했다.

검증:

```bash
bash -n scripts/start_local_services.sh
```

### 2026-04-23 watch-ranker 기본 활성 전환

목표: 메인 노트북 운영 기준으로 자동 순위 감시를 기본값으로 두고, 필요할 때만 끌 수 있게 한다.

완료 내용:

1. `scripts/start_local_services.sh`의 기본값을 `START_WATCH_RANKER=1`로 변경했다.
2. README, 사용 매뉴얼, Windows 자동 시작 문서에서 watch-ranker가 기본 포함임을 반영했다.
3. 웹앱만 쓰고 싶을 때는 `START_WATCH_RANKER=0`으로 끄는 운영 기준을 추가했다.

검증:

```bash
bash -n scripts/start_local_services.sh
```

### 2026-04-23 Windows 자동 시작 해제 즉시 중지 보강

목표: Windows 자동 시작 해제 시 다음 로그인만 막는 데서 끝나지 않고, 현재 떠 있는 로컬 서비스도 즉시 함께 내려 혼동을 줄인다.

완료 내용:

1. `scripts/windows/unregister-bms-startup.ps1`가 작업 스케줄러와 시작프로그램 등록 제거 후 WSL 안의 `scripts/stop_local_services.sh`도 실행하게 했다.
2. `docs/12-windows-autostart.md`에 자동 시작 해제가 향후 로그인 해제와 현재 실행 중 서비스 중지를 함께 수행한다고 명시했다.
3. 수동 중지가 필요할 때 WSL에서 `bash scripts/stop_local_services.sh`를 직접 실행하는 백업 절차를 문서에 추가했다.

검증:

```bash
bash scripts/stop_local_services.sh
ps -ef | rg "run_web.py|run_watch_ranker.py|bot/main.py"
```

### 2026-04-23 본문 분석 사진 추정 및 후기형 피드백 보정

목표: 네이버 블로그 에디터 붙여넣기 본문에서 사진 자리 추정을 더 현실에 가깝게 만들고, 후기형 글 피드백이 실제 작성 흐름에 맞게 나오도록 보정한다.

완료 내용:

1. `core/content_analyzer.py`가 `AI 활용 설정`, `사진 설명을 입력하세요.`, `동영상 설명을 입력하세요.`, `출처 입력` 같은 편집기 잔여 문구를 사진 자리 신호로 함께 세고 분석 본문에서는 제거하게 했다.
2. 후기형의 `내돈내산`, `경험`, `단점` 판정은 단어 일치만 보지 않고 1인칭 경험, 가격/요금 근거, 주의/아쉬움 표현까지 함께 보도록 보정했다.
3. 제목 후보는 해시태그 찌꺼기를 그대로 앞에 붙이지 않도록 압축했고, 소제목 후보는 `~ 확인` 대신 실제 섹션 제목으로 더 바로 쓸 수 있게 바꿨다.
4. 관련 회귀 테스트를 `tests/test_content_analyzer.py`에 추가했다.

검증:

```bash
source venv/bin/activate
python -m pytest tests/test_content_analyzer.py
```

### 2026-04-23 본문 분석 점수 완화 보정

목표: 현재 프로젝트가 실제 사진 내용을 읽지 못하는 한계를 반영해, 기본 정보와 경험 근거가 충분한 실사용 후기 초안이 70점대 초반에 과하게 묶이지 않도록 점수를 완화한다.

완료 내용:

1. `검색 의도 일치도`는 본문 길이 가점을 조금 더 빨리 주고, 짧은 실사용 초안에도 일부 가점을 주도록 완화했다.
2. `제목/첫문단 명확성`은 허용 제목 길이를 넓히고 기본점을 1점 올렸다.
3. `구조와 가독성`은 소제목 1개만 있어도 일부 가점을 주도록 완화했다.
4. `경험/신뢰 요소`는 1인칭 경험, 가격/요금 근거, 주의/아쉬움 신호를 더 직접 반영하도록 보정했다.
5. 관련 회귀 테스트로 현실적인 후기형 초안이 80점 이상 나오는 케이스를 추가했다.

검증:

```bash
source venv/bin/activate
python -m pytest tests/test_content_analyzer.py
```

## Phase 1: 발행 전 본문 분석 코치 MVP

목표: 키워드, 제목, 본문을 입력하면 발행 전 보강점을 알려준다.

상태: 2026-04-20 구현 완료. 이번 단계는 입력 본문만으로 동작하는 결정적 휴리스틱 MVP이며, 상위글 실제 본문/제목 수집 기반 비교는 Phase 3로 남긴다. `독자 기대 정보 누락`은 경쟁글 URL 직접 비교가 아니라 키워드 의도별 체크리스트 기반 추정이다.

수용 기준:

1. 점수는 네이버 공식 점수가 아니라 내부 프록시 점수로 응답과 UI에 명시한다.
2. 분석 로직은 `core/`에 두고 `webapp/`은 JSON 입출력만 담당한다.
3. `독자 기대 정보 누락`은 베끼기 목적이 아닌 키워드 의도별 기대 정보 누락 탐지로 제한한다.
4. 빈 키워드/제목/본문은 400 오류로 처리한다.

백엔드:

1. `core/content_analyzer.py`
2. `ContentAnalysisRequest`
3. `ContentAnalysisResult`
4. 점수 항목별 계산
5. 위험 표현/키워드 반복/누락 섹션 탐지

API:

```text
POST /api/content-analysis
```

입력:

```json
{
  "keyword": "서촌 카페",
  "title": "서촌 카페 스태픽스 후기",
  "body": "..."
}
```

출력:

```json
{
  "score": 74,
  "summary": "...",
  "score_label": "네이버 공식 점수가 아닌 BMS 내부 프록시 점수입니다.",
  "intent": "지역형",
  "checks": [
    {"name": "검색 의도 일치도", "score": 14, "max_score": 20, "suggestions": []}
  ],
  "priority_actions": [],
  "title_suggestions": [],
  "heading_suggestions": [],
  "risk_warnings": [],
  "missing_topics": [],
  "input_warnings": [],
  "benchmark_notes": [],
  "content_stats": {
    "estimated_photo_count": 0,
    "map_place_count": 0,
    "line_count": 0
  }
}
```

UI:

1. 키워드 입력
2. 제목 입력
3. 본문 textarea
4. 분석 결과 카드
5. 우선 수정 항목 표시

후속 UX 보완:

1. 첫 화면은 랭크 기능 중심으로 두고 `순위`, `발행 전 분석`, `내 글` 메뉴로 화면을 나눈다.
2. 발행 전 분석 textarea는 이미지 붙여넣기 자체를 지원하지 않으므로, 네이버 블로그 편집기에서 복사된 이미지 자리의 과도한 빈 줄을 분석 전 정리한다.
3. 네이버 지도 붙여넣기에서 거리 표기와 `© NAVER Corp.` 같은 UI 문구는 정리하고 장소명/주소는 보존한다.
4. 응답에는 내부 프록시 점수 외에 공개 가이드/실무 벤치마크 메모를 담는 `benchmark_notes`, 입력 정리 안내를 담는 `input_warnings`, 사진/지도 추정치를 담는 `content_stats`를 포함한다.
5. 벤치마크 메모는 네이버 공식 점수나 순위 보장으로 표현하지 않는다.
6. 발행 전 분석 화면 상단에는 네이버 공식 SEO 기본 가이드와 웹 콘텐츠 스팸사례 링크를 노출한다.

검증:

```bash
pytest tests/test_content_analyzer.py
pytest tests/test_webapp.py
```

완료 검증:

```bash
source venv/bin/activate && python -m pytest tests/test_content_analyzer.py tests/test_webapp.py
# 20 passed

source venv/bin/activate && python -m pytest
# 55 passed
```

## Phase 2: 기존 포스팅 DB화

목표: 저장한 내 글을 콘텐츠 자산으로 관리한다.

상태: 2026-04-20 보강 구현 완료. 기존 `내 글` 저장/순위 확인 흐름을 유지하면서 명세의 메타데이터와 `/api/posts` 계열을 추가했다.

이번 구현 수용 기준:

1. 기존 `/api/my-posts` API와 UI는 계속 동작한다.
2. `/api/posts` 표준 API를 추가한다.
3. `my_posts` 저장소에 `blog_id`, `post_id`, `category`, `published_at`, `content_summary`, `content_hash`를 추가한다.
4. `post_keywords`에 `keyword_type`을 추가하고 기본값은 `target`으로 둔다.
5. 글 수정, 키워드 추가, 키워드 삭제를 지원한다.
6. UI에서 카테고리, 발행일, 요약을 입력하고 목록에서 확인한다.

DB:

```text
posts
  id
  post_url
  blog_id
  post_id
  title
  category
  published_at
  content_summary
  content_hash
  created_at
  updated_at

post_keywords
  id
  post_id
  keyword
  keyword_type
  created_at
```

현재 구현 테이블명은 기존 호환성을 위해 `my_posts`를 유지하되, Phase 2의 `posts` 역할을 담당한다.

API:

```text
GET /api/posts
POST /api/posts
GET /api/posts/{id}
PATCH /api/posts/{id}
DELETE /api/posts/{id}
POST /api/posts/{id}/keywords
DELETE /api/posts/{id}/keywords/{keyword_id}
```

호환 API:

```text
GET /api/my-posts
POST /api/my-posts
POST /api/my-posts/{id}/check
DELETE /api/my-posts/{id}
```

완료 내용:

1. `my_posts`에 `blog_id`, `post_id`, `category`, `published_at`, `content_summary`, `content_hash`, `updated_at`을 추가했다.
2. `post_keywords`에 `keyword_type`을 추가했다.
3. 기존 DB를 위한 컬럼 마이그레이션과 URL 파생 필드 backfill을 추가했다.
4. `GET/POST /api/posts`, `GET/PATCH/DELETE /api/posts/{id}`, `POST /api/posts/{id}/keywords`, `DELETE /api/posts/{id}/keywords/{keyword_id}`를 추가했다.
5. 기존 `/api/my-posts`와 글별 순위 확인 흐름은 유지했다.
6. UI는 카테고리, 발행일, 요약을 입력하고 목록에서 파생 메타데이터를 표시한다.

검증:

```bash
pytest tests/test_storage.py
pytest tests/test_webapp.py
```

완료 검증:

```bash
source venv/bin/activate && python -m pytest tests/test_storage.py tests/test_webapp.py
# 24 passed

source venv/bin/activate && python -m pytest
# 60 passed
```

## Phase 2.5: 내 블로그 공개 글 가져오기

목표: 고정된 내 네이버 블로그의 공개 글을 한 번 가져와 기존 포스팅 DB를 자동으로 채운다.

상태: 2026-04-20 구현 완료. 수동 `내 글` 입력 UI를 제거하고, 기본 행동은 `TARGET_BLOG_ID` 기준 공개 글 가져오기로 바꿨다.

수용 기준:

1. 대상은 설정된 내 블로그 공개 글만이다.
2. 로그인, 마이페이지, 비공개/서로이웃 글 수집은 이번 단계에서 하지 않는다.
3. 경쟁글 본문 수집은 하지 않는다.
4. 증분 스케줄링은 만들지 않고, 버튼 실행 시 URL 기준 upsert한다.
5. 본문 텍스트를 저장해 향후 기존 글 중복/내부 링크/리라이트 판단에 쓴다.
6. UI는 `내 블로그 글 가져오기`를 `내 글 관리`의 주 행동으로 보여주고 수동 입력 폼은 제거한다.
7. 스케줄 실행은 기존 글을 갱신하지 않고 새 글만 insert한다.

DB 추가:

```text
my_posts
  content_text
  content_length
  imported_at
```

API:

```text
POST /api/posts/import-target-blog
```

완료 내용:

1. `core/naver_blog_importer.py`를 추가했다.
2. 공개 글 목록에서 URL, 글 번호, 제목, 카테고리 번호/이름, 발행일 문자열을 가져온다.
3. `include_body=true`일 때 모바일 공개 글 페이지에서 OpenGraph 요약과 SmartEditor 본문 텍스트를 가져온다.
4. `my_posts`에 `content_text`, `content_length`, `imported_at`을 추가하고 기존 DB 마이그레이션을 지원한다.
5. `store.import_my_blog_posts()`는 canonical URL 기준으로 생성/갱신한다.
6. `POST /api/posts/import-target-blog`를 추가했다.
7. `내 글 관리` UI는 `내 블로그 글 가져오기`를 주 행동으로 보여주고 수동 입력 폼은 제거했다.
8. 소량 실서비스 확인: `your_blog_id` 공개 목록 2건 수집 성공, 본문 포함 1건 수집 성공.
9. `scripts/import_target_blog.py`를 추가해 cron/systemd timer에서 새 글만 insert할 수 있게 했다.

검증:

```bash
pytest tests/test_naver_blog_importer.py
pytest tests/test_storage.py
pytest tests/test_webapp.py
```

완료 검증:

```bash
source venv/bin/activate && python -m pytest tests/test_naver_blog_importer.py tests/test_storage.py tests/test_webapp.py
# 32 passed

source venv/bin/activate && python -m pytest
# 68 passed
```

스케줄 예시:

```bash
source venv/bin/activate && python scripts/import_target_blog.py
```

운영 확인:

```text
최초 전체 마이그레이션:
found_count=636
imported_count=636
created_count=618
updated_count=18
failed_count=0

현재 로컬 DB:
data/bms.sqlite3
my_posts enabled=618
with_body=618

스케줄용 새 글 insert:
source venv/bin/activate && python scripts/import_target_blog.py --no-body
target_blog_id=your_blog_id found=636 imported=0 created=0 skipped=636 failed=0
```

## Phase 3: 상위글 비교 분석기

목표: 타깃 키워드의 상위 글에서 독자가 기대하는 정보 요소를 추출한다.

상태: 2026-04-20 구현 완료. 이번 단계는 검색 결과의 제목/요약만 발행 전 본문 분석에 연결한다. 경쟁글 본문 복사/우회 수집은 하지 않는다.

이번 구현 수용 기준:

1. `GET /api/blogs`와 현재 UI의 `기준별 상위글 보기` 결과를 재사용한다.
2. 경쟁글 본문 복사/우회 수집은 하지 않는다.
3. 상위글 제목과 검색 결과 요약에서 반복되는 명사/토픽을 추출한다.
4. 본문 분석 코치의 `missing_topics`와 연결해 `상위글 제목/요약 기반 누락 후보`를 별도 섹션으로 보여준다.
5. API는 우선 `POST /api/content-analysis`에 선택 입력 `reference_posts`를 받는다.
6. 응답은 `serp_missing_topic_candidates`를 포함한다.
7. 결과 문구는 `상위글을 베끼기 위한 자료가 아니라 독자 기대 정보 확인용`으로 유지한다.

작업:

1. 기존 상위글 조회 결과 재사용
2. 제목 토큰 빈도 개선
3. 지역/가격/주차/예약/후기/비교 등 의도 단어 사전 추가
4. 본문 분석 코치와 연결

API:

```text
GET /api/serp-analysis?keyword=서촌%20카페&surface=mobile_blog
POST /api/content-analysis
```

이번 구현에서는 별도 `GET /api/serp-analysis`를 만들지 않고, UI가 기존 `GET /api/blogs` 결과의 제목/요약을 `POST /api/content-analysis`의 `reference_posts` 선택 입력으로 전달한다.

완료 내용:

1. `core/content_analyzer.py`에 상위글 제목/요약 기반 반복 토픽 후보 추출을 추가했다.
2. `POST /api/content-analysis`가 `reference_posts`를 받아 `serp_missing_topic_candidates`를 반환한다.
3. 웹앱 발행 전 분석 흐름이 `기준별 상위글 보기` 캐시 또는 기존 `GET /api/blogs` 응답을 재사용한다.
4. UI 결과에 `상위글 제목/요약 기반 누락 후보` 섹션을 추가했다.
5. 문구는 독자 기대 정보 확인용이며 상위글 복제 목적이 아니라고 명시한다.

검증:

```bash
pytest tests/test_naver_blog_monitor.py
pytest tests/test_webapp.py
pytest tests/test_content_analyzer.py
```

완료 검증:

```bash
source venv/bin/activate && python -m pytest tests/test_content_analyzer.py tests/test_webapp.py
# 22 passed

source venv/bin/activate && python -m pytest
# 57 passed
```

## Phase 3.5: 내 글 DB 기반 발행 전 컨텍스트

목표: 가져온 내 블로그 공개 글 DB를 발행 전 분석에 연결해 내부 링크 후보와 기존 글 중복 가능성을 보여준다.

상태: 2026-04-20 구현 완료.

수용 기준:

1. `POST /api/content-analysis`는 저장된 활성 내 글 컨텍스트를 자동으로 분석에 포함한다.
2. 분석 로직은 `core/content_analyzer.py`에 두고 `webapp/`은 저장소 조회와 JSON 입출력만 담당한다.
3. 응답에는 `internal_link_candidates`와 `existing_post_overlap_warnings`를 포함한다.
4. 저장된 내 글이 없어도 기존 분석 결과는 유지한다.
5. UI는 발행 전 분석 결과에서 내부 링크 후보와 중복 확인을 분리해 보여준다.
6. 문구는 내부 링크와 차별화 점검 중심이며, 키워드 도배나 기존 글 복제를 유도하지 않는다.

API:

```text
POST /api/content-analysis
```

추가 출력:

```json
{
  "internal_link_candidates": [],
  "existing_post_overlap_warnings": []
}
```

검증:

```bash
pytest tests/test_content_analyzer.py
pytest tests/test_storage.py
pytest tests/test_webapp.py
```

완료 내용:

1. `ContentAnalysisRequest`에 `owner_posts`를 추가했다.
2. `core/content_analyzer.py`가 `internal_link_candidates`와 `existing_post_overlap_warnings`를 반환한다.
3. 중복 경고는 `target_keyword`, `similar_keyword`, `topic_overlap`로 구분한다.
4. `RankHistoryStore.owner_post_contexts()`가 활성 내 글의 분석용 필드를 반환한다.
5. `POST /api/content-analysis`가 저장된 내 글 컨텍스트를 자동으로 붙인다.
6. 발행 전 분석 UI에 `내 글 내부 링크 후보`와 `기존 글 중복 확인` 섹션을 추가했다.

완료 검증:

```bash
source venv/bin/activate && python -m py_compile core/content_analyzer.py core/storage.py webapp/main.py && python -m pytest tests/test_content_analyzer.py tests/test_storage.py tests/test_webapp.py
# 37 passed

source venv/bin/activate && python -m pytest
# 71 passed
```

후속 보정:

1. `위시리스트`/`모음`/`쇼핑리스트` 글은 목록형 의도로 판단해 비교, 차이, 순위 같은 누락 피드백을 줄인다.
2. 키워드 입력에 해시태그 묶음과 제목이 함께 들어와도 분석용 핵심 키워드를 짧게 정리한다.
3. 내부 링크/기존 글 중복 근거에서 `ㅋㅋ`, `ㅠㅠ`, `000원`, `같다` 등 의미 약한 토큰을 제외한다.
4. 광범위한 본문 주제 중복은 강한 토픽 겹침이 있을 때만 제한적으로 보여준다.
5. 순위탭의 키워드 상세/상위글 결과 영역을 검색 카드 바로 아래로 이동한다.

후속 보정 검증:

```bash
source venv/bin/activate && python -m py_compile core/content_analyzer.py webapp/main.py && python -m pytest tests/test_content_analyzer.py tests/test_webapp.py -q
# 27 passed

source venv/bin/activate && python -m pytest
# 72 passed
```

실발행 쇼핑 글 보정:

1. 의류 위시리스트 글에서 `후보`와 `수납`을 무조건 누락 항목으로 표시하지 않게 했다.
2. 쉼표 가격 숫자, 지그재그 링크, 착샷, 기장/핏, 코디 표현을 이미 제공된 정보로 인식한다.
3. 제목/첫문단 키워드 판단은 긴 복합 키워드 완전 일치 대신 핵심 토큰 일부 일치도 허용한다.
4. 상위글/내 글 토픽 근거에서 `후보`, `같음`, `가지`, `갠적으로`, `게시글의` 같은 일반 표현을 제외한다.

실발행 쇼핑 글 보정 검증:

```bash
source venv/bin/activate && python -m py_compile core/content_analyzer.py webapp/main.py && python -m pytest tests/test_content_analyzer.py tests/test_webapp.py -q
# 28 passed
```

내 글 관리 UX 보정:

1. 내 글 목록은 발행일 최신순으로 정렬한다.
2. 글 순위확인은 키워드 상세 패널을 열지 않고 해당 글 카드 안에 키워드별 최고 순위만 표시한다.
3. Today 요약은 큰 대시보드에서 헤더 우측 미니 영역으로 축소하고 순위 화면에서만 보이게 했다.
4. 헤더의 로그아웃 버튼은 제거했다.
5. 네이버에서 `2시간 전`, `분 전`, `일 전`, `어제`처럼 상대 발행일이 저장된 글도 가져온 시각 기준으로 환산해 발행일 내림차순에 포함한다.

내 글 관리 UX 보정 검증:

```bash
source venv/bin/activate && python -m pytest tests/test_storage.py tests/test_webapp.py -q
# 29 passed
```

## Phase 3.6: 인기 키워드 탭

목표: 다음 글감 탐색을 위해 Signal 실시간 검색어와 네이버 데이터랩 쇼핑인사이트 분야별 인기 검색어를 한 화면에서 확인한다.

상태: 2026-04-21 구현 완료.

완료 내용:

1. `core/signal_realtime.py`를 추가해 `https://api.signal.bz/news/realtime`의 Top 10 키워드를 읽는다.
2. `core/naver_datalab.py`를 추가해 네이버 데이터랩 홈 공개 HTML에서 쇼핑인사이트 분야별 일간 인기 검색어를 파싱한다.
3. `GET /api/signal/realtime-keywords`와 `GET /api/datalab/shopping-keywords`를 추가했다.
4. 순위탭에 있던 인기 키워드 영역을 별도 `인기 키워드` 탭으로 분리했다.
5. 데이터랩 카테고리는 `패션의류`, `패션잡화`, `화장품/미용`을 우선 노출한다.
6. Today 헤더는 최대 3개 관심 키워드를 가로로 보여주고 축약 순위 라벨을 쓴다.
7. 내 글 순위확인에서 목표 키워드가 없으면 키워드를 입력받아 저장한 뒤 순위 확인을 재시도한다.

검증:

```bash
source venv/bin/activate && python -m pytest tests/test_naver_datalab.py tests/test_signal_realtime.py tests/test_webapp.py -q
# 21 passed

source venv/bin/activate && python -m py_compile core/naver_datalab.py core/signal_realtime.py webapp/main.py && python -m pytest
# 79 passed
```

후속:

1. 네이버 Developers 쇼핑인사이트 API 키를 설정하면 클릭 추이 조회를 추가한다.
2. 데이터랩 주간/월간 인기 검색어는 공개 화면 또는 공식 API로 안정 경로를 확인한 뒤 확장한다.

## Phase 4: 발행 후 피드백 루프

목표: 글 발행 후 순위 이력을 바탕으로 다음 액션을 추천한다.

작업:

1. 글별 키워드를 자동 순위 확인 대상에 포함
2. 1일/3일/7일/14일/30일 체크포인트 계산
3. 정체/상승/하락/이탈 상태 분류
4. 리라이트 추천 문구 생성

추천 예시:

```text
"모바일 블로그탭 18위에서 7일째 정체 중입니다. 상위 글 제목에는 주차와 예약 정보가 자주 보이지만 이 글에는 없습니다."
```

검증:

```bash
pytest tests/test_watch_ranker.py
pytest tests/test_storage.py
```

## Phase 5: 콘텐츠 캘린더

목표: 다음 글 소재와 리라이트 대상을 일정으로 관리한다.

상태:

```text
idea
writing
published
tracking
needs_update
done
```

검증:

```bash
pytest tests/test_webapp.py
```
