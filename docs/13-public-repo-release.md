# Public Repo Release

이 프로젝트를 다른 노트북에서도 쉽게 설치하고, 동시에 기존 로컬 히스토리나 비밀값 노출 위험을 줄이려면 현재 저장소를 그대로 공개하지 말고 새 스냅샷 저장소를 만드는 편이 안전하다.

## 권장 흐름

1. 기존 토큰과 API 키는 새로 발급하고, 필요하면 이전 키를 폐기한다.
2. 현재 작업 트리에서 공개용 스냅샷을 새 폴더로 내보낸다.
3. 새 폴더에서만 퍼블릭 GitHub 저장소를 초기화한다.
4. 각 PC에서는 `clone -> .env 작성 -> bootstrap -> start_local_services.sh` 흐름으로 사용한다.

## 공개용 스냅샷 내보내기

프로젝트 루트에서 실행:

```bash
bash scripts/export_public_snapshot.sh ../BMS-public
```

기본 동작:

1. git 추적 파일과 현재 비무시 파일만 새 폴더로 복사한다.
2. `.git`, `.env`, `venv`, `logs`, `data`, `.codex`는 제거한다.
3. 빈 `data/`, `logs/` 디렉터리만 다시 만든다.
4. 새 폴더에서 `git init -b main`까지 수행한다.

## 새 퍼블릭 저장소로 올리기

```bash
cd ../BMS-public
cp .env.example .env
bash scripts/bootstrap_local.sh
git remote add origin <new-public-repo-url>
git add .
git commit -m "Initial public snapshot"
git push -u origin main
```

`.env`에는 각 PC에 맞는 로컬 비밀값만 넣는다.

예시:

```env
DISCORD_TOKEN=...
TARGET_BLOG_ID=your_naver_blog_id
APP_PASSWORD=
AI_PROVIDER=groq
AI_API_KEY=...
AI_MODEL=qwen/qwen3-32b
```

## 다른 노트북에서 설치

```bash
git clone <public-repo-url>
cd BMS-public
cp .env.example .env
bash scripts/bootstrap_local.sh
bash scripts/start_local_services.sh
```

Windows 자동 시작은 기존 문서([12-windows-autostart.md](./12-windows-autostart.md)) 흐름을 그대로 따르면 된다.
