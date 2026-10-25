# BMS Agent Guide

## Project

BMS is a personal Naver blog monitoring and writing-assistant project. The current app tracks Naver blog rankings by keyword and will evolve into a private blog operations assistant for pre-publish content checks, post database management, and rank feedback loops.

## Key Paths

- `core/`: business logic, Naver search parsing, storage, browser helpers
- `webapp/`: FastAPI app and static UI
- `bot/`: Discord bot entry point
- `scripts/`: local run/check scripts
- `tests/`: pytest suite
- `docs/`: product, technical, deployment, and operating docs
- `docs/development/`: active development specs and Codex harness notes

## Read First

- `docs/01-blog-monitoring-system.md`: product overview
- `docs/04-technical-design.md`: current architecture
- `docs/10-product-backlog.md`: product backlog
- `docs/development/README.md`: active development specs
- `docs/development/naver-blog-assistant-spec.md`: next product direction
- `docs/development/codex-harness-engineering.md`: Codex workflow guidance
- `docs/development/codex-hooks-and-skills.md`: hooks and skills setup

## Commands

Use the existing virtualenv when running Python commands:

```bash
source venv/bin/activate
pytest
python scripts/check_browser.py
python scripts/check_naver_blog.py "서촌 카페"
python scripts/run_web.py
```

## Engineering Rules

1. Keep `core/` independent from `webapp/` and `bot/`.
2. Prefer small, testable functions in `core/` and thin API/UI layers.
3. Do not hardcode secrets. Use `.env` and `.env.example`.
4. Treat Naver SEO scores as internal proxy scores, never official Naver scores.
5. Avoid brittle Naver DOM class dependencies; prefer URL and semantic selectors where possible.
6. Add or update tests for storage, parser, API, and user-facing behavior changes.
7. Update `docs/development/` before or alongside substantial feature work.

## Skills

- `bms-spec-harness`: Use for BMS feature work, refactors, API/DB/UI changes, hooks, automation, tests, and docs that affect product behavior.
- `planning-with-files`: Use for complex work that needs a file-backed plan or several coordinated steps.
- `hook-development`: Use when changing Codex hooks or hook scripts.
- `skill-development`: Use when creating or updating Codex skills.
- `agent-development`: Use when creating or updating agent/subagent guidance.

## Product Rules

1. The product is for one private Naver blog operator, not a generic agency SEO platform.
2. The main value is deciding what to write, what to fix, and when to re-check.
3. Do not build features that encourage keyword stuffing, copying competitors, or spammy SEO behavior.
4. UI copy should be practical and direct.
