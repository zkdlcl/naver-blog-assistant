# 모바일 웹앱 제품 명세

## 방향

가족가 Discord를 설치하거나 명령어를 외울 필요 없이, 아이폰 홈 화면에 추가한 웹앱 아이콘으로 순위 대시보드를 연다.

이 웹앱은 앱스토어 배포가 아니라 Safari의 "홈 화면에 추가" 방식으로 제공한다.

## 사용자 경험

### 첫 화면

목표:

1. 오늘 바로 확인할 키워드를 입력한다.
2. PC/모바일 순위를 한 번에 본다.
3. 최근에 확인한 키워드를 다시 누를 수 있다.

화면 구성:

```text
[키워드 입력창]
[순위 확인 버튼]

오늘 확인 결과
- PC 통합검색: 3위
- 모바일 통합검색: 3위
- 글 제목
- 글 URL

최근 확인 키워드
- 예시 키워드
- 성수 맛집
- 겹벚꽃
```

### 대시보드 화면

목표:

1. 자주 보는 키워드 목록을 보여준다.
2. 각 키워드의 PC/모바일 현재 순위를 보여준다.
3. 순위권 밖이면 명확히 표시한다.

예:

```text
예시 키워드
PC 3위 / 모바일 3위

겹벚꽃
PC 순위권 밖 / 모바일 12위
```

### 상세 화면

목표:

1. 키워드별 최근 조회 이력을 본다.
2. 순위가 올라갔는지 내려갔는지 확인한다.

MVP 이후 구현:

```text
최근 7일
04-19 PC 3위 / 모바일 3위
04-18 PC 4위 / 모바일 3위
04-17 PC 6위 / 모바일 5위
```

## 기능 우선순위

### MVP

1. 모바일 웹 화면
2. 키워드 직접 입력
3. 통합검색, 블로그탭, 블로그 섹션 기준별 순위 조회
4. 결과 표시
5. 간단한 비밀번호 인증
6. 아이폰 홈 화면 추가용 PWA 설정

### 다음 단계

1. 최근 조회 키워드 저장
2. 자주 보는 키워드 즐겨찾기
3. 순위 이력 저장 - 완료
4. 최근 7일 변화 표시
5. 브라우저 Web Push 알림
6. 순위 하락/상승 알림
7. 카카오톡 나에게 보내기 알림

## 앱처럼 보이게 만드는 요소

PWA 설정 파일:

```text
static/manifest.webmanifest
```

필요 항목:

```json
{
  "name": "BMS Rank",
  "short_name": "BMS",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#111111"
}
```

iPhone Safari 홈 화면 추가를 위해 HTML에 아래 메타 태그를 넣는다.

```html
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="BMS">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="apple-touch-icon" href="/static/icons/apple-touch-icon.png">
```

## 알림 전략

앱스토어 앱 없이도 PWA 브라우저 알림으로 주요 알림을 보낼 수 있다.

### 가능한 알림

1. 특정 키워드가 순위권에 진입했을 때
2. 특정 키워드의 순위가 급상승했을 때
3. 특정 키워드의 순위가 급락했을 때
4. 매일 1회 관심 키워드 추천
5. 매일 1회 주요 키워드 요약

### 중요한 구조

아이폰 브라우저가 백그라운드에서 한 시간마다 직접 네이버를 검색하는 구조가 아니다.

올바른 구조:

```text
Oracle 서버 스케줄러
  -> 1시간마다 관심 키워드 조회
  -> 순위 조건 판단
  -> 조건 충족 시 Web Push 발송
  -> 아이폰 홈 화면 웹앱에 알림 표시
```

즉 주기 실행은 서버가 담당하고, 아이폰은 알림을 받는 역할만 한다.

### iPhone Web Push 조건

iPhone에서 Web Push를 쓰려면 아래 조건이 필요하다.

1. iOS/iPadOS 16.4 이상
2. Safari에서 웹앱을 홈 화면에 추가
3. HTTPS 적용
4. Web App Manifest 설정
5. Service Worker 등록
6. 사용자가 버튼을 눌러 알림 권한 허용

알림 권한 요청은 페이지 진입 즉시 자동으로 띄우지 않는다.

사용자가 직접 누르는 버튼을 둔다.

```text
[알림 받기]
```

### 서버 구현 요소

필요한 구성:

1. `push_subscriptions` 저장소
2. Service Worker
3. Push API 구독 등록 API
4. 서버 측 Web Push 발송 모듈
5. 스케줄러
6. 키워드 조건 저장소

초기 저장소는 SQLite로 충분하다.

예상 테이블:

```text
push_subscriptions
  id
  endpoint
  p256dh
  auth
  created_at

watch_keywords
  id
  keyword
  mode
  min_rank
  interval_minutes
  enabled

rank_history
  id
  keyword
  surface
  rank
  post_url
  checked_at
```

### 알림 MVP

1차 알림 기능은 아래만 구현한다.

```text
관심 키워드 등록
1시간마다 PC/모바일 순위 확인
대상 블로그가 30위 안에 들어오면 알림
```

예시 알림:

```text
예시 키워드 순위 진입
PC 3위 / 모바일 3위
```

### 이후 확장

1. 하루 한 번 추천 키워드 알림
2. 최근 7일 대비 순위 변화 알림
3. 인기 키워드 후보 알림
4. 알림 조용한 시간 설정
5. 카카오톡 나에게 보내기 백업 알림

## 인증

초기에는 단순 비밀번호 인증으로 충분하다.

환경변수:

```env
APP_PASSWORD=...
```

MVP 방식:

1. 접속 시 비밀번호 입력
2. 세션 쿠키 발급
3. 이후 대시보드 접근 허용

주의:

비밀번호는 `.env`에 저장하고 Git에 커밋하지 않는다.

## 배포 구조

MVP 권장:

```text
Oracle Cloud Always Free VM
  FastAPI 앱
  Playwright 순위 조회
  SQLite 이력 저장
  static PWA 파일
  systemd 상시 실행
  Caddy HTTPS
```

나중에 분리:

```text
Vercel
  모바일 프론트엔드

Oracle Cloud VM
  순위 조회 API
  Playwright
  DB
```

## Discord와의 관계

Discord는 가족가 쓰는 앱이 아니다.

Discord는 개발자가 모바일에서 로컬/서버 하네스를 제어하기 위한 도구로 유지한다.

가족용 기능은 웹앱으로 제공한다.

```text
가족 -> 아이폰 홈 화면 웹앱
개발자 -> Discord 하네스
서버 -> Oracle VM
소스 -> GitHub
```

## 다음 구현 단위

1. `webapp/` 패키지 생성 - 완료
2. FastAPI 의존성 추가 - 완료
3. `/` 모바일 화면 구현 - 완료
4. `/api/rank?keyword=...` 구현 - 완료
5. `APP_PASSWORD` 인증 구현 - 완료
6. PWA manifest와 아이콘 추가 - 완료
7. Oracle VM 배포 스크립트 작성 - 진행 예정
8. SQLite 이력 저장 - 완료
9. Web Push 알림 - 진행 예정
