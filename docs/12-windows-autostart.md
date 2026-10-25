# Windows 자동 실행

이 PC에서 Windows 로그인 후 BMS를 바로 쓰려면 Windows 작업 스케줄러가 WSL 안의 실행 스크립트를 호출하게 등록한다.

## 실행 구조

```text
Windows 로그인
-> 작업 스케줄러
-> wsl.exe
-> scripts/start_local_services.sh
-> bms-web 백그라운드 실행
```

접속 주소:

```text
http://localhost:8000
```

## 1. WSL에서 먼저 수동 확인

```bash
cd /path/to/BMS
bash scripts/start_local_services.sh
```

로그:

```bash
tail -f logs/bms-web.log
tail -f logs/bms-discord-bot.log
```

Discord 봇까지 같이 켜려면:

```bash
START_DISCORD_BOT=1 bash scripts/start_local_services.sh
tail -f logs/bms-discord-bot.log
```

기본 자동 시작에는 watch-ranker도 포함된다.

watch-ranker를 끄고 웹앱만 올리려면:

```bash
START_WATCH_RANKER=0 bash scripts/start_local_services.sh
```

중지:

```bash
bash scripts/stop_local_services.sh
```

## 2. Windows 자동 시작 등록

Windows PowerShell에서 실행한다.

```powershell
powershell -ExecutionPolicy Bypass -File "\\wsl.localhost\Ubuntu\home\zkdlcl\DEV\personal\BMS\scripts\windows\register-bms-startup.ps1"
```

등록 직후 한 번 실행되며, 이후부터는 Windows 로그인 시 자동 실행된다.

작업 스케줄러 등록 권한이 없으면 같은 스크립트가 Windows 시작프로그램 폴더에 `bms-local-services.cmd`를 만들어 대신 자동 실행한다.

## 3. 자동 시작 해제

```powershell
powershell -ExecutionPolicy Bypass -File "\\wsl.localhost\Ubuntu\home\zkdlcl\DEV\personal\BMS\scripts\windows\unregister-bms-startup.ps1"
```

이 스크립트는 두 가지를 함께 처리한다.

1. 다음 Windows 로그인부터 자동 시작되지 않게 작업 스케줄러 또는 시작프로그램 등록을 제거한다.
2. 이미 실행 중인 현재 WSL BMS 서비스도 `scripts/stop_local_services.sh`로 바로 중지한다.

만약 PowerShell에서 등록만 해제하고 서비스가 남아 있으면 WSL에서 아래 명령으로 한 번 더 직접 멈출 수 있다.

```bash
bash scripts/stop_local_services.sh
```

## 4. 주의

1. WSL 배포판 이름은 현재 `Ubuntu` 기준이다.
2. 프로젝트 경로는 `/path/to/BMS` 기준이다.
3. `.env`의 `APP_HOST`는 `127.0.0.1` 또는 `0.0.0.0` 모두 로컬 접속에 사용할 수 있다.
4. PC가 절전 상태면 자동 순위 확인도 멈춘다. 항상 켜져 있어야 계속 돈다.
