# 배포 및 운영 로드맵

## 목표 상태

가족가 휴대폰에서 언제든 접속해서 네이버 블로그 순위를 확인할 수 있는 상시 서비스를 만든다.

개발자용 원격 제어는 Discord를 유지한다.

가족용 서비스는 Discord 명령어가 아니라 모바일 웹 화면으로 제공한다.

아이폰에서는 Safari에서 접속한 뒤 "홈 화면에 추가"로 앱처럼 사용한다.

## 권장 아키텍처

```text
GitHub
  소스 형상관리
  배포 기준 브랜치 관리

Oracle Cloud Always Free VM
  Python 백엔드
  Playwright/Chromium 실행
  순위 조회 API
  간단한 모바일 웹 UI/PWA
  SQLite 또는 JSONL 순위 이력 저장
  systemd로 상시 실행

Discord Bot
  개발자용 하네스 명령
  원격 테스트/점검

선택: Vercel
  나중에 프론트엔드만 분리할 때 사용
  Playwright 스크레이핑 백엔드는 Oracle VM에 유지
```

## Oracle Cloud를 우선 추천하는 이유

이 프로젝트는 Playwright로 실제 브라우저를 띄운다.

브라우저 자동화는 아래 특성이 있다.

1. Chromium 바이너리와 OS 라이브러리가 필요하다.
2. 요청 시간이 키워드와 네이버 응답 상태에 따라 길어질 수 있다.
3. 스케줄러, 이력 저장, 장시간 프로세스 관리가 필요해질 가능성이 높다.

따라서 서버리스보다 작은 VM이 운영하기 쉽다.

Oracle Cloud Always Free의 Ampere A1 VM은 무료 범위 안에서 충분한 CPU/메모리를 제공할 수 있으므로 MVP 운영에 적합하다.

주의할 점:

1. Always Free 리소스는 홈 리전에 만들어야 한다.
2. 리전 상황에 따라 `out of host capacity`가 날 수 있다.
3. 유휴 VM은 회수 정책이 있을 수 있으므로 실제 서비스 프로세스를 상시 운영해야 한다.
4. 무료 범위를 넘는 리소스를 만들지 않도록 주의한다.

## Vercel을 바로 백엔드로 추천하지 않는 이유

Vercel은 프론트엔드와 짧은 API 요청에는 좋다.

하지만 이 프로젝트의 핵심인 Playwright 기반 순위 조회에는 아래 제약이 있다.

1. 함수 실행 시간이 제한된다.
2. 함수 번들 크기 제한이 있다.
3. Chromium/Playwright 의존성 관리가 VM보다 까다롭다.
4. 장시간 상주 프로세스, 로컬 상태 저장, systemd 같은 운영 방식과 맞지 않는다.

따라서 Vercel은 나중에 아래 구조로 쓰는 것이 낫다.

```text
Vercel 모바일 웹 프론트
  -> Oracle VM의 API 호출
  -> Oracle VM이 Playwright로 네이버 조회
```

MVP에서는 Vercel 없이 Oracle VM 하나로 웹 UI와 백엔드를 같이 운영한다.

## 단계별 개발 계획

### Phase 0: Git 형상관리

목표:

1. 로컬 프로젝트를 Git 저장소로 초기화한다.
2. `.env`, `venv`, 캐시 파일이 커밋되지 않도록 유지한다.
3. GitHub 원격 저장소에 push한다.

명령 예시:

```bash
git init
git add .
git commit -m "Initial BMS harness and rank tracker"
git branch -M main
git remote add origin git@github.com:YOUR_ID/YOUR_REPO.git
git push -u origin main
```

주의:

`.env`는 절대 커밋하지 않는다.

실제 서버에는 `.env.example`을 참고해서 서버용 `.env`를 별도로 만든다.

### Phase 1: 로컬 제품화

목표:

1. Discord 명령 외에 웹 UI를 추가한다.
2. 가족가 휴대폰 브라우저에서 키워드를 입력하고 순위를 볼 수 있게 한다.
3. 최소 비밀번호 인증을 붙인다.
4. 아이폰 홈 화면 추가용 PWA 설정을 넣는다.

권장 구현:

```text
FastAPI
  /             모바일 웹 화면
  /api/rank     키워드 순위 조회 API
  /manifest.webmanifest
```

Streamlit도 가능하지만, 장기적으로 API/프론트 분리가 쉬운 FastAPI를 우선 추천한다.

### Phase 2: Oracle VM 배포

목표:

1. Oracle Cloud Always Free VM 생성
2. Python, Playwright, Chromium 의존성 설치
3. GitHub에서 소스 clone
4. `.env` 작성
5. systemd 서비스 등록
6. 외부 접속용 방화벽/보안목록 설정

운영 명령 예시:

```bash
sudo systemctl status bms
sudo systemctl restart bms
journalctl -u bms -f
```

### Phase 3: HTTPS와 도메인

목표:

1. 도메인 또는 서브도메인 연결
2. Caddy 또는 Nginx로 HTTPS 적용
3. 모바일 접속 주소를 고정

권장:

```text
Caddy
  자동 HTTPS 발급이 단순함
```

### Phase 4: 이력 저장과 알림

목표:

1. 키워드별 순위 이력 저장
2. 최근 7일 그래프
3. PWA Web Push 알림
4. 순위 급락/급상승 알림
4. 매일 자동 체크

저장소 후보:

1. 초기: SQLite
2. 나중: PostgreSQL 또는 Google Sheets

알림 구조:

```text
Oracle VM scheduler
  -> 관심 키워드 주기 조회
  -> 조건 판단
  -> Web Push 발송
  -> 아이폰 홈 화면 웹앱 알림 수신
```

iPhone Web Push는 HTTPS, Service Worker, Web App Manifest, 홈 화면 추가, 사용자 알림 권한 허용이 필요하다.

## 운영 모드 구분

### 개발자용

Discord 명령:

```text
!rank 예시 키워드
!rank-pc 예시 키워드
!rank-mobile 예시 키워드
```

역할:

1. 원격 디버깅
2. 하네스 제어
3. 배포 후 장애 확인

### 가족용

모바일 웹:

```text
https://your-domain.example
```

역할:

1. 키워드 입력
2. PC/모바일 순위 확인
3. 최근 순위 변화 확인
4. 필요한 경우 알림 받기

## 환경변수 방향

공통:

```env
TARGET_BLOG_ID=your_blog_id
BROWSER_HEADLESS=true
```

Discord 하네스:

```env
DISCORD_TOKEN=...
```

웹 서비스:

```env
APP_PASSWORD=...
APP_HOST=0.0.0.0
APP_PORT=8000
```

나중에 카카오 알림을 붙이면:

```env
KAKAO_REST_API_KEY=...
KAKAO_ACCESS_TOKEN=...
KAKAO_REFRESH_TOKEN=...
```

## 결론

1차 운영 목표는 Oracle Cloud Always Free VM 하나에 Python 서비스를 올리는 것이다.

Vercel은 지금 당장 백엔드로 쓰지 않는다.

나중에 UI가 커지면 Vercel을 프론트엔드 전용으로 붙이고, Playwright 순위 조회는 계속 Oracle VM에서 처리한다.
