#!/usr/bin/env python3
"""Codex hooks for keeping BMS development specs current."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


DEVELOPMENT_HINT = """BMS development harness:
- For feature, refactor, API, storage, parser, UI, or deployment work, read AGENTS.md and docs/development/README.md first.
- Keep docs/development/*.md updated with the feature intent, data/API/UI changes, validation steps, and follow-up work.
- Treat Naver SEO scores as internal proxy scores, never official Naver quality scores.
- Before finalizing code changes, run relevant tests or state exactly why they were not run.
"""

DEV_KEYWORDS = (
    "개발",
    "구현",
    "수정",
    "고쳐",
    "추가",
    "리팩",
    "명세",
    "문서",
    "api",
    "db",
    "ui",
    "test",
    "테스트",
    "hook",
    "hooks",
    "skill",
    "스킬",
)

CODE_PREFIXES = (
    "core/",
    "webapp/",
    "bot/",
    "scripts/",
    "tests/",
    "requirements.txt",
    "deploy/",
)

DOC_PREFIXES = (
    "docs/development/",
    "AGENTS.md",
)


def read_input() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def emit_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def repo_root(cwd: str | None) -> Path | None:
    if not cwd:
        return None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            text=True,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return Path(result.stdout.strip())


def git_status(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    return [line[3:] for line in result.stdout.splitlines() if len(line) > 3]


def is_bms_repo(root: Path | None) -> bool:
    if root is None:
        return False
    return (root / "docs/development/README.md").exists() and (root / "core").is_dir()


def has_path(paths: list[str], prefixes: tuple[str, ...]) -> bool:
    return any(path.startswith(prefix) or path == prefix.rstrip("/") for path in paths for prefix in prefixes)


def handle_session_start(payload: dict) -> None:
    root = repo_root(payload.get("cwd"))
    if not is_bms_repo(root):
        return
    print(DEVELOPMENT_HINT)


def handle_prompt_submit(payload: dict) -> None:
    root = repo_root(payload.get("cwd"))
    if not is_bms_repo(root):
        return

    prompt = str(payload.get("prompt") or "").lower()
    if not any(keyword in prompt for keyword in DEV_KEYWORDS):
        return

    emit_json(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": (
                    DEVELOPMENT_HINT
                    + "\nThis prompt looks development-related. Before editing code, identify whether a "
                    "development spec in docs/development/ needs to be created or updated. After editing, "
                    "reconcile the spec with the actual implementation."
                ),
            }
        }
    )


def handle_post_tool_use(payload: dict) -> None:
    root = repo_root(payload.get("cwd"))
    if not is_bms_repo(root):
        return

    command = (((payload.get("tool_input") or {}).get("command")) or "").strip()
    if not command:
        return

    interesting = ("pytest", "scripts/", "run_web.py", "check_naver_blog.py", "check_browser.py")
    if any(token in command for token in interesting):
        emit_json(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": (
                        "BMS harness note: a validation or project script just ran. If the result changes "
                        "implementation assumptions, update docs/development/implementation-roadmap.md or the "
                        "relevant spec before finalizing."
                    ),
                }
            }
        )


def handle_stop(payload: dict) -> None:
    root = repo_root(payload.get("cwd"))
    if not is_bms_repo(root):
        emit_json({"continue": True})
        return

    if payload.get("stop_hook_active"):
        emit_json({"continue": True})
        return

    changed = git_status(root)
    code_changed = has_path(changed, CODE_PREFIXES)
    docs_changed = has_path(changed, DOC_PREFIXES)

    if code_changed and not docs_changed:
        emit_json(
            {
                "decision": "block",
                "reason": (
                    "BMS harness check: code or tests changed, but docs/development or AGENTS.md did not. "
                    "Before finalizing, update the relevant development spec/roadmap with what changed and "
                    "how it was verified. If no documentation change is appropriate, add a brief note to "
                    "docs/development/implementation-roadmap.md explaining why."
                ),
            }
        )
        return

    emit_json({"continue": True})


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    payload = read_input()

    if event == "session-start":
        handle_session_start(payload)
    elif event == "prompt-submit":
        handle_prompt_submit(payload)
    elif event == "post-tool-use":
        handle_post_tool_use(payload)
    elif event == "stop":
        handle_stop(payload)
    else:
        emit_json({"continue": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
