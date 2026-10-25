# 다음 세션 핸드오프

## 한 줄 요약

가족 전용 네이버 블로그 관리 시스템 MVP는 로컬에서 동작한다. 현재는 키워드 입력 후 네이버 검색 기준별 순위와 상위 블로그 글을 모바일 웹앱에서 확인할 수 있다.

## 현재 저장소

```text
repo: https://github.com/zkdlcl/naver-blog-assistant.git
branch: main
project path: /path/to/BMS
```

최근 주요 커밋:

```text
8ea552e Split Naver search surfaces
```

## 현재 구현 상태

완료:

1. Python venv 구성
2. Playwright 설치 및 브라우저 실행 확인
3. Discord 봇 연결
4. FastAPI 모바일 웹앱
5. PWA manifest
6. 네이버 검색 결과 파싱
7. 대상 블로그 순위 계산
8. 기준별 상위 블로그 글 조회
9. SQLite 순위 이력 저장
10. 기본 문서화
11. 관심 키워드 저장/삭제
12. 관심 키워드 자동 순위 확인 스크립트
13. systemd 서비스 템플릿
14. 키워드별 최근 순위 변화 표시
15. 관심 키워드 최신 순위 대시보드
16. 오늘 요약
17. 화면 정보 구조 정리
18. 내 글 관리 MVP
19. 앱 안 알림 MVP
20. 상위글 제목 분석 MVP
21. 키워드 기회 발견 MVP

대상 블로그:

```text
TARGET_BLOG_ID=your_blog_id
```

실제 값은 `.env`에 둔다. 토큰, 비밀번호 같은 민감정보는 문서에 적지 않는다.

## 실행 명령

웹앱 실행:

```bash
cd ~/DEV/personal/BMS
venv/bin/python scripts/run_web.py
```

접속:

```text
http://127.0.0.1:8000
```

Discord 봇 실행:

```bash
cd ~/DEV/personal/BMS
venv/bin/python bot/main.py
```

테스트:

```bash
cd ~/DEV/personal/BMS
venv/bin/python -m unittest discover -s tests
```

## 현재 검색 기준

순위 조회와 상위 블로그 조회는 기준별로 분리한다.

| Surface | 의미 |
| --- | --- |
| `desktop` | PC 통합검색 |
| `mobile` | 모바일 통합검색 |
| `desktop_blog` | PC 블로그탭 |
| `mobile_blog` | 모바일 블로그탭 |
| `blog_section` | 네이버 블로그 섹션 |

중요한 사례:

```text
keyword: 호텔파리칠

PC 통합검색: 대상 블로그 없음
모바일 통합검색: 대상 블로그 없음
PC 블로그탭: 대상 블로그 1위
모바일 블로그탭: 대상 블로그 1위
네이버 블로그 섹션: 대상 블로그 없음
```

따라서 “순위권 밖”과 “상위 블로그 1위”가 동시에 나올 수 있다. 이건 버그가 아니라 네이버 검색 기준이 다른 것이다.

## Discord 명령

```text
!ping
!blog 검색어
!rank 검색어
!rank-pc 검색어
!rank-mobile 검색어
!rank-blog 검색어
!rank-mblog 검색어
!rank-section 검색어
```

`!rank`는 다섯 기준을 모두 확인한다.

## 웹앱 기능

현재 화면:

1. 키워드 입력
2. 순위 보기
3. 기준별 상위글 보기
4. 관심 키워드 저장/삭제
5. 관심 키워드 최신 순위 요약
6. 오늘 요약
7. 최근 순위 변화
8. 최근 키워드
9. 최근 저장 이력
10. 내 글 관리

화면 구조:

1. 첫 화면은 오늘 요약, 지금 검색, 관심 키워드, 내 글 관리를 우선 보여준다.
2. 키워드를 선택하거나 검색하면 키워드 상세 영역이 열린다.
3. 최근 순위 변화, 기준별 상위글, 최근 키워드, 최근 저장 이력은 접힘/펼침 구조로 둔다.
4. 오늘의 새 소식은 관심 키워드 변화에서 생성하고, 검색창 아래 흐름에 둔다.
5. 기준별 상위글을 조회하면 제목에서 자주 보이는 단어를 같이 보여준다.
6. 상위글 제목의 반복 단어를 입력 키워드에 붙여 다음 키워드 후보를 제안한다.
7. 내 글 관리는 글 URL과 목표 키워드를 저장하고, 글 URL 기준으로 순위를 확인한다.
8. 내 글 관리는 아직 보조 기능이므로 화면 맨 아래 접힘 영역에 둔다.

관심 키워드 자동 순위 확인:

```bash
cd ~/DEV/personal/BMS
venv/bin/python scripts/run_watch_ranker.py
```

서버 상시 실행:

```bash
venv/bin/python scripts/run_watch_ranker.py --loop
```

현재 UI 방향:

1. 30대 여성 아이폰 사용자 취향
2. 러블리한 핑크 계열
3. 너무 기본적인 todo 앱 느낌은 피하기
4. 카드 안에 카드가 과하게 겹치지 않도록 유지

참고 링크:

```text
https://www.figma.com/ko-kr/community/file/887892609124245416/lo-fi-wireframe-kit-free-demo
https://www.figma.com/ko-kr/community/file/861577994110006119/ios-app-wireframes
https://mobbin.com/screens/6fa1ba1e-263f-4153-a82c-5dbc3dfd1cac
```

## 다음 우선순위

1. Oracle Cloud Always Free VM 생성 및 배포
2. 화면 정보 구조 정리
3. 내 글 관리
4. 앱 안 알림
5. 상위글 제목 분석
6. 키워드 기회 발견
7. Nginx/Caddy 리버스 프록시 및 HTTPS
8. Web Push 알림

상세 백로그:

```text
docs/10-product-backlog.md
```

Discord-Codex 원격 개발 구상:

```text
docs/11-discord-codex-remote-dev.md
```

## Oracle Cloud 메모

목표는 무료 범위 안에서 최대한 활용하는 것이다.

권장:

```text
Ampere A1 Arm VM
가능하면 4 OCPU / 24 GB RAM
Ubuntu 계열 이미지
```

서울/도쿄는 A1 가용성이 부족할 수 있다. 홈 리전은 한 번 정하면 바꾸기 어렵다.

## Codex CLI 실행 정책 메모

권한 질문을 줄이고 싶으면 새 세션을 프로젝트 폴더에서 아래처럼 시작한다.

```bash
codex --sandbox danger-full-access --ask-for-approval never -C /path/to/BMS
```

더 강하게 모든 승인과 샌드박스를 끄는 옵션:

```bash
codex --dangerously-bypass-approvals-and-sandbox -C /path/to/BMS
```

두 번째는 로컬 개인 프로젝트에서만 신중하게 사용한다.

Discord 봇으로 Codex CLI를 원격 실행하는 것은 나중 단계로 둔다. 먼저 GitHub push 기반 배포와 systemd 운영을 안정화하고, Discord에는 `status`, `test`, `deploy restart` 같은 제한된 운영 명령부터 붙인다.

## 다음 세션 시작 프롬프트 예시

```text
docs/09-session-handoff.md 기준으로 이어서 진행해줘. 우선 현재 git status와 테스트 상태 확인하고, Oracle Cloud 배포 준비 또는 모바일 웹앱 다음 기능부터 진행하자.
```
