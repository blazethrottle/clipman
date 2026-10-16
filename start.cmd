@echo off
chcp 65001 >nul
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
    echo 클립맨 처리 프로그램의 설치가 필요합니다. 개발 환경 설치 안내를 확인해 주세요.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m app.launch
if errorlevel 1 (
    echo 클립맨을 열지 못했습니다. 위 오류를 확인해 주세요.
    pause
)
