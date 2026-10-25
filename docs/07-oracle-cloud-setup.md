# Oracle Cloud 배포 준비 체크리스트

## 1. VM 생성 권장값

Oracle Cloud Console에서 Compute Instance를 만든다.

무료 범위 최대 활용 권장:

```text
Shape: VM.Standard.A1.Flex
OCPU: 4
Memory: 24 GB
OS: Ubuntu 24.04 또는 Ubuntu 22.04
Boot volume: 100 GB
Public IP: 필요
```

Oracle Always Free의 Ampere A1 무료 범위는 총 4 OCPU / 24 GB RAM 수준이다.

이 프로젝트는 앞으로 Playwright, 순위 이력 저장, 대시보드, 알림, 스케줄러가 붙을 수 있으므로 무료 범위 안에서 한 대에 최대 스펙을 몰아 쓰는 구성이 좋다.

AMD Micro는 RAM이 작아서 Playwright/Chromium 운영에는 비추천한다.

Always Free 리소스는 홈 리전에 만들어야 한다.

생성 전 반드시 Console에서 `Always Free eligible` 표시를 확인한다.

주의:

```text
OCPU 4 초과 금지
Memory 24 GB 초과 금지
Boot volume + 추가 block volume 합산 200 GB 초과 금지
유료 Load Balancer 생성 금지
유료 Database 생성 금지
```

처음에는 Boot volume 100 GB만 사용하고, 나중에 데이터가 늘면 추가 block volume 100 GB를 붙일 수 있다.

## 1.1. Capacity 부족 시 대처

`Out of host capacity` 또는 유사한 오류가 나면 설정이 틀린 것이 아니라 해당 리전에 Always Free A1 자리가 부족한 상태일 수 있다.

대처:

1. 다른 Availability Domain을 선택해 본다.
2. 시간을 두고 다시 시도한다.
3. 처음에는 더 작은 A1 스펙으로 만들고 나중에 resize한다.
4. 그래도 안 되면 Micro는 임시 SSH/설정 테스트용으로만 고려한다.

가능하면 최종 운영은 `VM.Standard.A1.Flex 4 OCPU / 24 GB`로 맞춘다.

## 2. SSH 접속

로컬에서:

```bash
ssh ubuntu@서버_PUBLIC_IP
```

Oracle Linux로 만들었다면 기본 사용자가 다를 수 있다.

```bash
ssh opc@서버_PUBLIC_IP
```

## 3. 서버 기본 패키지

Ubuntu 기준:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip curl
```

## 4. 소스 clone

```bash
git clone https://github.com/zkdlcl/naver-blog-assistant.git
cd blog-management-system
```

Private repo라면 GitHub 로그인/토큰 또는 SSH key 설정이 필요하다.

## 5. Python 가상환경

```bash
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
```

## 6. Playwright 브라우저 설치

```bash
venv/bin/playwright install chromium
sudo venv/bin/playwright install-deps chromium
```

확인:

```bash
venv/bin/python scripts/check_browser.py
```

정상:

```text
Playwright browser check passed: playwright-ok
```

## 7. 환경변수 작성

```bash
cp .env.example .env
nano .env
```

최소값:

```env
TARGET_BLOG_ID=your_blog_id
BROWSER_HEADLESS=true
APP_PASSWORD=원하는_비밀번호
APP_HOST=0.0.0.0
APP_PORT=8000
WATCH_RANK_INTERVAL_MINUTES=60
```

Discord 하네스를 서버에서도 쓸 거면:

```env
DISCORD_TOKEN=...
```

## 8. 포트 열기

MVP는 `8000` 포트로 먼저 확인한다.

Oracle Cloud Console:

```text
Virtual Cloud Network
-> Security Lists 또는 Network Security Groups
-> Ingress Rules
-> TCP 8000 허용
```

서버 방화벽을 쓴다면:

```bash
sudo ufw allow 8000/tcp
```

## 9. 웹앱 실행

구현 완료 후 아래 명령으로 실행할 예정이다.

```bash
venv/bin/python scripts/run_web.py
```

접속:

```text
http://서버_PUBLIC_IP:8000
```

## 10. systemd 등록

저장소에 서비스 템플릿이 들어 있다.

```bash
sudo cp deploy/bms-web.service /etc/systemd/system/bms-web.service
sudo cp deploy/bms-watch-ranker.service /etc/systemd/system/bms-watch-ranker.service
```

서버 경로 또는 사용자명이 다르면 서비스 파일의 아래 값을 수정한다.

```text
WorkingDirectory=/home/ubuntu/blog-management-system
EnvironmentFile=/home/ubuntu/blog-management-system/.env
User=ubuntu
```

활성화:

```bash
sudo systemctl daemon-reload
sudo systemctl enable bms-web
sudo systemctl start bms-web
sudo systemctl status bms-web
```

관심 키워드 자동 순위 확인도 켠다.

```bash
sudo systemctl enable bms-watch-ranker
sudo systemctl start bms-watch-ranker
sudo systemctl status bms-watch-ranker
```

로그:

```bash
journalctl -u bms-web -f
journalctl -u bms-watch-ranker -f
```

## 11. HTTPS는 다음 단계

처음에는 `http://IP:8000`으로 확인한다.

정상 동작 후 Caddy로 HTTPS를 붙인다.

```bash
sudo apt install -y caddy
```

도메인 연결 후 Caddyfile을 설정한다.

```text
your-domain.example {
    reverse_proxy 127.0.0.1:8000
}
```

## 12. 서버 업데이트 절차

새 코드 push 후 서버에서:

```bash
cd ~/blog-management-system
git pull
venv/bin/pip install -r requirements.txt
sudo systemctl restart bms-web
sudo systemctl restart bms-watch-ranker
```
