# Codex Hooks and Skills Setup

## 목적

Claude Code의 hooks/skills 기반 개발 습관을 Codex CLI에 맞게 가져온다.

원하는 동작:

1. 개발 프롬프트가 들어오면 Codex가 먼저 개발 명세 문서를 확인한다.
2. 코드, 테스트, API, DB, UI 변경이 생기면 관련 명세 MD를 갱신한다.
3. 세션이 끝나기 전에 코드만 바뀌고 문서가 바뀌지 않았는지 검사한다.
4. 반복되는 작업 절차는 스킬로 재사용한다.

## 설치/설정된 항목

### 1. Codex hooks feature flag

Codex hooks는 실험 기능이므로 `~/.codex/config.toml`에 아래 플래그가 필요하다.

```toml
[features]
codex_hooks = true
```

### 2. Project hooks

프로젝트 hooks 파일:

```text
.codex/hooks.json
```

실행 스크립트:

```text
scripts/codex_hooks/bms_harness_hook.py
```

설정된 이벤트:

| Event | 역할 |
| --- | --- |
| `SessionStart` | BMS 개발 문서와 작업 규칙을 추가 컨텍스트로 주입 |
| `UserPromptSubmit` | 개발 관련 프롬프트일 때 명세 문서 확인/갱신을 추가 컨텍스트로 주입 |
| `PostToolUse` | 테스트/검증 명령 이후 문서 갱신 필요성을 추가 컨텍스트로 주입 |
| `Stop` | 코드가 바뀌었는데 개발 문서가 안 바뀌었으면 한 번 더 계속하도록 요청 |

Codex 공식 hooks 문서 기준으로, hooks는 `~/.codex/hooks.json` 또는 `<repo>/.codex/hooks.json`에서 발견되며 `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop` 이벤트를 지원한다.

참고: https://developers.openai.com/codex/hooks

### 3. Installed skill: planning-with-files

설치 위치:

```text
~/.codex/skills/planning-with-files
```

설치 명령:

```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo mxyhi/ok-skills \
  --path planning-with-files
```

이 스킬은 복잡한 작업에서 파일 기반 계획을 만들고 유지하는 데 사용한다.

### 4. Installed community skills from codex-skills

설치 위치:

```text
~/.codex/skills/hook-development
~/.codex/skills/skill-development
~/.codex/skills/agent-development
```

설치 명령:

```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo troykelly/codex-skills \
  --path external/skills/hook-development external/skills/skill-development external/skills/agent-development
```

용도:

1. `hook-development`: Codex hook 작성/수정 시 사용
2. `skill-development`: Codex skill 작성/수정 시 사용
3. `agent-development`: agent/subagent 지침 작성 시 사용

전체 autonomous wrapper는 설치하지 않았다. 일부 래퍼는 승인/샌드박스 우회 기본값을 전제로 하므로, 이 프로젝트에는 필요한 스킬만 선별 설치한다.

### 5. Local skill: bms-spec-harness

설치 위치:

```text
~/.codex/skills/bms-spec-harness
```

이 스킬은 BMS 프로젝트에서 기능 개발, 리팩터링, API/DB/UI 변경을 할 때 개발 명세 문서를 계속 갱신하도록 한다.

## 훅 동작 방식

### 개발 프롬프트 감지

`UserPromptSubmit` hook은 프롬프트에 아래 성격의 단어가 있으면 개발 작업으로 본다.

```text
개발, 구현, 수정, 추가, 리팩터링, 명세, 문서, api, db, ui, test, hook, skill
```

감지되면 Codex에게 아래 원칙을 추가 컨텍스트로 넣는다.

```text
Before editing code, identify whether a development spec in docs/development/ needs to be created or updated.
After editing, reconcile the spec with the actual implementation.
```

### 종료 전 문서 갱신 강제

`Stop` hook은 `git status --porcelain`을 확인한다.

아래 경로가 바뀌었는데:

```text
core/
webapp/
bot/
scripts/
tests/
requirements.txt
deploy/
```

아래 경로가 바뀌지 않았으면:

```text
docs/development/
AGENTS.md
```

Codex에게 한 번 더 계속하도록 요청한다.

## 주의

1. Codex hooks는 현재 실험 기능이다.
2. 공식 문서 기준 Windows에서는 hooks가 비활성화되어 있다.
3. 현재 Codex의 `PreToolUse`/`PostToolUse`는 Bash 중심으로 동작한다.
4. Hook은 코드 변경을 대신 잘 판단하는 만능 장치가 아니라, 누락을 줄이는 안전장치다.
5. 문서 갱신이 정말 필요 없는 변경이라면 `docs/development/implementation-roadmap.md`에 짧게 예외 사유를 남긴다.

## 검증 의존성

프로젝트에는 `tests/`가 있으므로 Codex 하네스 검증 명령이 동작하려면 `pytest`가 설치되어야 한다. `requirements.txt`에 `pytest`를 포함해 새 환경에서도 아래 명령이 바로 동작하게 한다.

```bash
source venv/bin/activate
python -m pytest
```
