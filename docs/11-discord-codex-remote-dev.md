# Discord-Codex 원격 개발 구상

## 결론

Discord 봇에서 Codex CLI를 호출해 외부에서도 개발하는 구조는 가능하다.

다만 바로 붙이는 것은 위험하다. Discord 메시지가 곧 로컬/서버 쉘 실행 권한이 되기 때문이다.

권장 순서:

1. 가족용 웹앱을 Oracle VM에 먼저 안정 배포한다.
2. GitHub 기반 배포 흐름을 만든다.
3. Discord에서는 제한된 개발 명령만 허용한다.
4. Codex 실행은 별도 작업 큐와 로그를 남기는 방식으로 붙인다.

## 하지 말아야 할 방식

아래 구조는 피한다.

```text
Discord 메시지
-> 바로 codex --dangerously-bypass-approvals-and-sandbox 실행
-> 바로 git push 또는 서버 재시작
```

문제:

1. 권한이 너무 크다.
2. 실수로 `.env` 같은 민감 파일을 읽거나 출력할 수 있다.
3. 봇 토큰이 노출되면 서버 제어권이 넘어간다.
4. 실행 중인 서비스나 DB를 망가뜨릴 수 있다.
5. 긴 작업의 상태를 추적하기 어렵다.

## 안전한 최소 구조

Discord는 명령 접수와 상태 확인만 담당한다.

```text
Discord Bot
  -> 허용된 사용자 확인
  -> 작업 요청 저장
  -> Codex worker가 작업 수행
  -> 결과 요약을 Discord로 전송
```

허용 명령 예:

```text
!dev status
!dev test
!dev diff
!dev task 오늘요약 화면을 더 단순하게 정리해줘
!dev deploy-status
```

처음에는 아래 명령만 허용한다.

```text
!dev status
!dev test
!dev diff
```

코드 수정까지 허용하는 `!dev task`는 나중에 붙인다.

## 권한 제한

필수 조건:

1. Discord user id allowlist
2. 특정 채널에서만 명령 허용
3. 명령별 rate limit
4. 작업 로그 저장
5. `.env`, `data/*.sqlite3`, 토큰 출력 금지
6. `git reset --hard`, `rm -rf`, `sudo`, `chmod 777` 같은 명령 금지

## 추천 구현 단계

### Phase 1: 읽기 전용 원격 점검

명령:

```text
!dev status
!dev test
!dev logs
```

동작:

1. `git status --short`
2. `venv/bin/python -m unittest discover -s tests`
3. systemd 로그 마지막 N줄

이 단계는 안전하고 유용하다.

### Phase 2: 배포 제어

명령:

```text
!deploy status
!deploy pull
!deploy restart
```

동작:

1. 서버에서 `git pull`
2. 테스트 실행
3. 성공 시 `systemctl restart bms-web bms-watch-ranker`

주의:

배포는 Codex가 코드를 직접 고치는 것보다 안전하다. 이미 GitHub에 들어간 코드만 서버에 반영하기 때문이다.

### Phase 3: Codex 작업 큐

명령:

```text
!dev task <요청>
```

동작:

1. 요청을 SQLite 또는 JSONL 큐에 저장
2. worker가 작업 디렉터리를 확인
3. Codex CLI 실행
4. 테스트 실행
5. 변경 파일과 요약을 Discord에 전송
6. 사용자가 승인하면 commit/push

초기에는 자동 commit/push를 하지 않는다.

## Codex 실행 정책

원격 Codex는 로컬 개발 세션보다 제한적으로 실행한다.

권장:

```bash
codex -C /home/ubuntu/blog-management-system
```

비권장:

```bash
codex --dangerously-bypass-approvals-and-sandbox
```

원격 자동화에서는 `dangerously-bypass`를 기본값으로 쓰지 않는다.

## 이 프로젝트에서의 권장 결정

지금 당장은 Discord-Codex 원격 개발보다 아래 순서가 낫다.

1. Oracle A1 Flex VM 확보
2. GitHub push 기준 배포
3. systemd로 web/ranker 상시 실행
4. Discord 봇에 `!deploy status`, `!deploy restart`, `!dev test` 추가
5. 충분히 안정화되면 Codex 작업 큐 추가

즉, Discord는 먼저 운영 도구로 쓰고, 개발 자동화는 마지막에 붙인다.
