# 하네스 엔지니어링 적용안

## 참고 자료

OpenAI의 Harness engineering 글은 Codex 시대의 엔지니어 역할을 코드 직접 작성보다 환경, 명세, 피드백 루프 설계로 설명한다. 특히 이 프로젝트에 적용할 핵심은 아래다.

1. 짧은 `AGENTS.md`를 목차로 두고 상세 지식은 `docs/`에 둔다.
2. 저장소 안의 문서를 시스템 오브 레코드로 만든다.
3. 에이전트가 실행할 수 있는 검증 명령을 명확히 제공한다.
4. UI, 로그, 테스트 결과처럼 에이전트가 직접 읽을 수 있는 피드백을 늘린다.
5. 큰 목표는 작은 실행 계획과 검증 가능한 단계로 쪼갠다.
6. 반복되는 판단은 문서가 아니라 테스트, 스크립트, 린트로 강제한다.

참고:

- OpenAI, Harness engineering: https://openai.com/index/harness-engineering/
- OpenAI, Unrolling the Codex agent loop: https://openai.com/index/unrolling-the-codex-agent-loop/
- OpenAI, Codex use cases: https://developers.openai.com/codex/explore/

## 현재 프로젝트에 바로 적용한 것

1. `docs/development/`를 제품 개발사항 전용 폴더로 추가했다.
2. OpenAI Developer Docs MCP를 Codex CLI에 추가했다.
3. Codex hooks feature flag를 켰다.
4. 프로젝트 로컬 hooks 파일을 추가했다.
5. BMS 개발 명세 갱신용 로컬 스킬을 추가했다.
6. 커뮤니티 Codex 스킬 일부를 설치했다.

설치된 MCP:

```bash
codex mcp add openaiDeveloperDocs --url https://developers.openai.com/mcp
```

확인:

```bash
codex mcp list
```

현재 출력 기준:

```text
openaiDeveloperDocs  https://developers.openai.com/mcp  enabled
```

Hooks:

```bash
codex features enable codex_hooks
```

Project hook config:

```text
.codex/hooks.json
scripts/codex_hooks/bms_harness_hook.py
```

Installed skills:

```text
~/.codex/skills/bms-spec-harness
~/.codex/skills/planning-with-files
~/.codex/skills/hook-development
~/.codex/skills/skill-development
~/.codex/skills/agent-development
```

설치 출처:

1. `planning-with-files`: `mxyhi/ok-skills`
2. `hook-development`, `skill-development`, `agent-development`: `troykelly/codex-skills`

## 추가 적용할 하네스 구조

### 1. 표준 `AGENTS.md`

현재 저장소에는 `.AGENTS.md`가 있지만 Codex CLI 표준 진입점은 `AGENTS.md`다. 루트에 짧은 `AGENTS.md`를 두고, 상세 설명은 기존 문서로 연결한다.

권장 역할:

```text
AGENTS.md
-> 프로젝트 목적
-> 주요 경로
-> 실행/테스트 명령
-> 문서 색인
-> 작업 규칙
```

### 2. 실행 가능한 검증 명령

에이전트가 매번 추측하지 않도록 검증 명령을 고정한다.

```bash
source venv/bin/activate
pytest
python scripts/check_browser.py
python scripts/check_naver_blog.py "서촌 카페"
python scripts/run_web.py
```

### 3. 작업 명세 템플릿

큰 기능은 구현 전 아래 형식으로 문서화한다.

```text
목표
사용자 흐름
데이터 변경
API 변경
UI 변경
검증 방법
리스크
출시 기준
```

### 4. 에이전트가 읽기 쉬운 로그

웹앱과 자동 순위 확인 스크립트는 아래 형식의 구조적 로그를 남긴다.

```text
event=rank_check keyword="서촌 카페" surface=mobile_blog rank=7 elapsed_ms=1320
event=parser_error surface=desktop_blog reason="no_blog_links"
```

초기에는 Python logging의 key=value 문자열로 충분하다. JSON 로그는 필요해질 때 도입한다.

### 5. 구조 테스트

기능이 늘어나면 아래 규칙을 테스트로 강제한다.

1. `core/`는 `webapp/`에 의존하지 않는다.
2. `core/`는 Discord 봇에 의존하지 않는다.
3. DB 스키마 변경은 저장소 테스트를 동반한다.
4. 네이버 URL 정규화는 테스트 케이스를 추가한다.
5. 모든 새 API는 최소 1개의 FastAPI 테스트를 추가한다.

## 이번 기능군에 맞는 Codex 작업 프롬프트 예시

```text
docs/development/naver-blog-assistant-spec.md를 기준으로 발행 전 본문 분석 코치 MVP를 구현해줘.

범위:
- core/content_analyzer.py 추가
- webapp에 POST /api/content-analysis 추가
- UI에는 간단한 제목/키워드/본문 입력 폼 추가
- 네이버 공식 점수처럼 표현하지 말고 내부 프록시 점수로 표시
- 테스트 추가

검증:
- pytest
```

## 아직 설치하지 않은 것

서드파티 autonomous wrapper 전체는 이번 단계에서 설치하지 않았다. 이유는 아래와 같다.

1. 일부 커뮤니티 래퍼는 기본값이 승인/샌드박스 우회를 전제로 한다.
2. 이 프로젝트는 우선 명세 문서 갱신과 검증 루프가 목적이다.
3. Codex native hooks가 이미 필요한 최소 기능을 제공한다.

필요해지면 별도 검토할 후보:

1. 브라우저/DOM 검증용 MCP
2. 로그 조회용 로컬 CLI
3. 반복 작업용 Codex skill
4. PR 리뷰 자동화 스크립트
