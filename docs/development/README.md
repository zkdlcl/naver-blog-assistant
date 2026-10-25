# 개발사항 문서

이 폴더는 앞으로 구현할 제품 기능과 Codex 기반 개발 운영 방식을 관리하는 전용 문서 공간이다.

## 문서 목록

1. [네이버 블로그 운영 비서 개발 명세](./naver-blog-assistant-spec.md)
2. [하네스 엔지니어링 적용안](./codex-harness-engineering.md)
3. [구현 로드맵](./implementation-roadmap.md)
4. [Codex Hooks and Skills Setup](./codex-hooks-and-skills.md)

## 운영 원칙

1. 큰 기능은 구현 전에 이 폴더에 목적, 사용자 흐름, 데이터, API, 검증 방법을 먼저 남긴다.
2. `AGENTS.md`는 짧은 목차 역할만 하고, 상세한 제품/기술 판단은 이 폴더와 기존 `docs/` 문서에 둔다.
3. 구현이 끝난 기능은 `docs/10-product-backlog.md`의 완료 목록에도 반영한다.
4. 문서 내용과 실제 코드가 달라지면 코드를 기준으로 문서를 갱신한다.
5. Codex hooks가 코드 변경 후 개발 문서 누락을 감지하면, 세션 종료 전에 관련 명세를 업데이트한다.
