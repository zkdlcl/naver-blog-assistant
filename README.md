# BMS — 네이버 블로그 운영 비서

> 블로그를 운영하는 가족이 **매일 부담 없이 확인하는 개인용 앱**입니다.
> "내 글이 실제 네이버 화면 어디에 보이는지"를 확인하고, 발행 전 글을 점검하며, 다음 글감을 제안합니다. (v1.0.0)

```
키워드 순위 확인 → 관심 키워드 변화 → 인기 키워드·상위글로 글감 찾기 → 발행 전 본문 점검 → 내 글 DB와 연결해 내부 링크·중복 주제 확인
```

## 핵심 기능
- **순위 확인**: Playwright로 PC·모바일 통합검색, PC·모바일 블로그탭, 블로그 섹션 **5개 검색 표면**의 상위 30개를 읽어 내 글 순위를 판정
- **관심 키워드**: 저장해 두면 자동 확인 루프가 순위를 기록하고, 오늘 요약·키워드별 변화·앱 안 새 소식으로 보여줌
- **글감 탐색**: 네이버 데이터랩 인기 키워드, 실시간 검색어, 상위 글 제목 분석으로 키워드 기회 발견
- **발행 전 분석 코치**: 본문을 점검하고, 내 글 DB 기준 **내부 링크 후보·기존 글 중복 주제**를 알려주며, 선택적으로 외부 AI(Groq 등)로 보강
- **내 글 관리**: 공개 글 가져오기, 글별 목표 키워드와 URL 기준 순위 확인
- **모바일 웹앱(PWA)**: 비밀번호 로그인, 홈 화면 추가. Discord 봇은 필요할 때만 켜는 보조 수단

## 설계에서 신경 쓴 부분
- **로컬 우선·무료 운영**: 데이터는 SQLite 한 파일. PC에서 바로 돌리고, 서버로 옮길 때를 위한 systemd 템플릿(Oracle Cloud)과 Windows 자동 시작 스크립트도 준비했습니다.
- **정규화된 순위 판정**: `m.blog.naver.com`을 `blog.naver.com`으로 정규화하고 같은 글을 중복 제거한 뒤, 대상 블로그 ID 또는 특정 글 URL과 처음 일치하는 위치를 순위로 반환합니다.
- **스펙 우선 개발**: 기능마다 의도·수락 기준·API 응답 필드를 `docs/development/`에 먼저 적고 구현했으며, 구현 후 문서를 실제 동작에 맞게 다시 맞췄습니다.
- **테스트**: 파서·저장소·분석기·웹 API를 pytest로 검증합니다(2026-04-20 기록 기준 71개 통과).
- **공개 안전장치**: `.env`와 DB, 로그를 제외한 **공개용 스냅샷 생성 스크립트**(`scripts/export_public_snapshot.sh`)로 이력 없이 깨끗한 저장소를 만들 수 있습니다.
- **AI 협업 하네스**: Codex 훅·스킬과 세션 인계 문서(`docs/09-session-handoff.md`, `task_plan.md`, `progress.md`)로 여러 세션에 걸친 작업을 이어갔습니다.

## 기술 스택
Python · FastAPI · Playwright · SQLite · discord.py · httpx · pytest / 바닐라 JS 모바일 웹(PWA) / systemd

## 구조
```
core/      순위 판정, 글 분석, 블로그 가져오기, 데이터랩·Signal 조회, SQLite 저장소, 관심 키워드 자동 확인
webapp/    FastAPI 앱(/api/*)과 모바일 웹 UI
bot/       Discord 명령 봇(선택)
scripts/   실행·점검·가져오기, Windows 자동 시작, 공개 스냅샷 생성
deploy/    systemd 서비스 템플릿
docs/      개요·매뉴얼·요구사항·기술 설계·배포 로드맵·백로그
tests/     단위·API 테스트
```

---

# 실행 방법

## 빠른 시작

```bash
git clone <your-repo-url>
cd BMS
bash scripts/bootstrap_local.sh
cp .env.example .env  # if bootstrap did not create it
```

Fill in `.env`:

```env
DISCORD_TOKEN=...
TARGET_BLOG_ID=your_naver_blog_id
APP_PASSWORD=optional
AI_PROVIDER=groq
AI_API_KEY=...
AI_MODEL=qwen/qwen3-32b
```

Start local services:

```bash
bash scripts/start_local_services.sh
```

Default behavior:

- starts the web app
- does not start the Discord bot unless `START_DISCORD_BOT=1`
- starts the watch-ranker loop by default

Open:

```text
http://127.0.0.1:8000
```

## 새 노트북 설정

If the new laptop has no development environment yet, follow this order:

1. Install WSL Ubuntu or a local Linux shell environment.
2. Install `git`.
3. Clone the repository.
4. Run `bash scripts/bootstrap_local.sh`.
5. Copy `.env.example` to `.env` and fill in your real values.
6. If you want the same local history and imported posts, copy `data/bms.sqlite3` from the old machine.
7. Start with `bash scripts/start_local_services.sh`.

Minimum files to bring over from the old machine:

- `.env`
- `data/bms.sqlite3`

Do not copy these:

- `venv/`
- `logs/`
- `data/pids/`

Stop:

```bash
bash scripts/stop_local_services.sh
```

## 공개용 스냅샷

If you want a fresh public repository without old local history, export a clean snapshot first:

```bash
bash scripts/export_public_snapshot.sh ../BMS-public
```

This creates a new directory that:

- excludes `.git`, `.env`, `venv`, `logs`, and `data`
- keeps `.env.example` and startup scripts
- initializes a fresh `main` branch by default

Then move into the exported directory and publish that one instead of the current local repo:

```bash
cd ../BMS-public
cp .env.example .env
bash scripts/bootstrap_local.sh
git remote add origin <new-public-repo-url>
git add .
git commit -m "Initial public snapshot"
git push -u origin main
```

## Version

Current close-out target:

```text
v1.0.0
```

v1.0.0 means the project is ready for personal daily use on a local PC or laptop with:

- web app
- optional Discord bot
- local SQLite data
- watch-ranker loop
- pre-publish analysis with external AI boost

## Optional toggles

```bash
START_DISCORD_BOT=1 bash scripts/start_local_services.sh
START_WATCH_RANKER=0 bash scripts/start_local_services.sh
```
