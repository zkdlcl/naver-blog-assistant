# BMS 사용 매뉴얼

현재 문서는 `v1.0.0` 기준 로컬 운영 매뉴얼이다.

## 현재 운영 방식

현재 BMS는 웹앱 중심의 로컬 PC 운영 방식이 가장 단순하다.

1. 웹앱: 브라우저에서 순위, 인기 키워드, 발행 전 분석, 내 글을 확인
2. Discord 봇: 필요할 때만 선택적으로 켜는 보조 기능

PC가 켜져 있고 웹앱 프로세스가 실행 중일 때만 사용할 수 있다.

## 빠른 시작

프로젝트 루트에서 기존 가상환경을 활성화한다.

```bash
source venv/bin/activate
```

### 1. 최초 준비

```bash
bash scripts/bootstrap_local.sh
```

`.env`에 최소한 아래 값을 채운다.

```env
DISCORD_TOKEN=...
TARGET_BLOG_ID=내_네이버_블로그_ID
APP_PASSWORD=선택
```

AI 보강 분석까지 쓰려면 추가:

```env
AI_PROVIDER=groq
AI_API_KEY=...
AI_MODEL=qwen/qwen3-32b
```

## 새 노트북 준비 리스트

개발환경이 전혀 없는 새 노트북이면 아래 순서로 준비한다.

1. Windows라면 WSL Ubuntu 설치
2. `git` 설치
3. 저장소 clone
4. `bash scripts/bootstrap_local.sh`
5. `.env.example` -> `.env`
6. 기존 PC에서 `data/bms.sqlite3` 복사
7. `bash scripts/start_local_services.sh`

실행 예시:

```bash
git clone <public-repo-url>
cd BMS
bash scripts/bootstrap_local.sh
cp .env.example .env
bash scripts/start_local_services.sh
```

## 기존 운영 데이터 옮기기

같은 블로그를 같은 상태로 이어서 쓰려면 코드만 clone하면 안 되고, 기존 SQLite DB도 같이 옮겨야 한다.

옮길 파일:

1. `.env`
2. `data/bms.sqlite3`

옮기지 않을 것:

1. `venv/`
2. `logs/`
3. `data/pids/`

주의:

1. GitHub는 코드만 동기화한다.
2. `data/bms.sqlite3`는 자동 동기화되지 않는다.
3. 두 PC에서 각자 다른 DB 복사본을 동시에 메인처럼 쓰면 데이터가 갈라질 수 있다.
4. 노트북을 메인 운영 장비로 정하면 watch-ranker 같은 주기 실행도 그 장비에서만 켜는 편이 안전하다.

### 2. 웹앱 실행

```bash
python scripts/run_web.py
```

기본 접속 주소:

```text
http://127.0.0.1:8000
```

다른 포트로 실행:

```bash
APP_PORT=8010 python scripts/run_web.py
```

비밀번호 로그인까지 쓰려면 `.env`에 아래 값을 둔다.

```env
APP_PASSWORD=원하는_비밀번호
```

### 3. Discord 봇 실행

```bash
python bot/main.py
```

`.env`에 `DISCORD_TOKEN`이 있어야 한다.

### 4. 브라우저 동작 점검

```bash
python scripts/check_browser.py
```

정상 예시:

```text
Playwright browser check passed: playwright-ok
```

### 5. 검색 파서 개발 점검

```bash
python scripts/check_naver_blog.py "서촌 카페"
```

## 필수 환경 변수

```env
DISCORD_TOKEN=...
TARGET_BLOG_ID=내_네이버_블로그_ID
APP_PASSWORD=선택
APP_HOST=127.0.0.1
APP_PORT=8000
APP_DATA_DIR=data
```

`TARGET_BLOG_ID` 대신 `TARGET_BLOG_URL`을 써도 된다.

## 한 번에 같이 실행

기본 웹앱만 올리려면:

```bash
bash scripts/start_local_services.sh
```

기본 동작:

1. `bms-web` 시작
2. `bms-discord-bot`은 기본 비활성
3. `bms-watch-ranker`는 기본 활성

Discord 봇까지 같이 돌리려면:

```bash
START_DISCORD_BOT=1 bash scripts/start_local_services.sh
```

watch-ranker를 끄고 웹앱만 쓰려면:

```bash
START_WATCH_RANKER=0 bash scripts/start_local_services.sh
```

중지:

```bash
bash scripts/stop_local_services.sh
```

## Discord에서 하는 일

봇이 실행 중일 때 아래 명령을 쓴다.

### 도움말

```text
!help
```

### 봇 상태 확인

```text
!ping
```

### 최신 블로그 글 3개 확인

```text
!blog 서촌 카페
```

### 전체 표면 순위 확인

```text
!rank 서촌 카페
```

### 표면별 순위 확인

```text
!rank-pc 서촌 카페
!rank-mobile 서촌 카페
!rank-blog 서촌 카페
!rank-mblog 서촌 카페
!rank-section 서촌 카페
```

`!rank*` 명령은 `.env`에 대상 블로그 설정이 있어야 동작한다.

## 웹앱에서 하는 일

로그인 후 상단 탭으로 기능을 나눠 쓴다.

### 1. 순위

할 수 있는 일:

1. 키워드 직접 순위 조회
2. 기준별 상위 블로그 글 보기
3. 최근 저장 이력 확인
4. 관심 키워드 저장/삭제
5. 오늘 요약과 앱 안 새 소식 확인

순위 조회 결과는 `data/bms.sqlite3`에 저장된다.

### 2. 인기 키워드

할 수 있는 일:

1. 네이버 데이터랩 쇼핑인사이트 인기 키워드 보기
2. Signal 실시간 검색어 보기
3. 글감 탐색용 참고 키워드 확인

### 3. 발행 전 분석

입력:

1. 키워드
2. 제목
3. 본문

출력:

1. 내부 프록시 점수
2. 항목별 개선 제안
3. 우선 수정 항목
4. 제목 후보와 소제목 후보
5. 위험 경고
6. 상위글 제목/요약 기반 누락 후보
7. 내 글 DB 기반 내부 링크 후보와 중복 주제 경고

주의:

이 점수는 네이버 공식 점수가 아니라 BMS 내부 프록시 점수다.

### 4. 내 글

할 수 있는 일:

1. 내 블로그 공개 글 가져오기
2. 저장된 글 목록 확인
3. 글별 목표 키워드 추가/삭제
4. 글 URL 기준 순위 확인
5. 글 삭제

가져오기는 설정된 `TARGET_BLOG_ID`의 공개 글만 대상으로 한다.

## 데이터 저장 위치

기본 경로:

```text
data/bms.sqlite3
```

바꾸려면:

```env
APP_DATA_DIR=원하는_경로
```

기본 SQLite DB:

```text
data/bms.sqlite3
```

## 로컬 운영 팁

1. 기본 운영은 웹앱만으로 충분하다.
2. Playwright는 메모리를 쓰므로 너무 많은 조회를 동시에 누르지 않는 편이 안전하다.
3. 소형 서버 배포 전에는 로컬 PC 운영으로 기능 마감을 먼저 끝내는 것이 가장 단순하다.
4. watch-ranker는 자동 순위 감시용이므로, 메인 운영 장비에서만 켜는 편이 안전하다.
5. 노트북을 메인 장비로 정했다면, 자동 시작과 watch-ranker는 그 노트북에서 기본 운영으로 둔다.
6. Discord 봇은 실제 사용자가 쓰지 않으면 켤 필요가 없다.

## 테스트

전체 테스트:

```bash
pytest
```

웹앱만 빠르게 확인:

```bash
python scripts/run_web.py
```
