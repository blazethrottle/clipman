#!/bin/bash
cd "$(dirname "$0")/backend" || exit 1
if [ ! -x .venv/bin/python ]; then
    echo "클립맨 처리 프로그램의 설치가 필요합니다. 개발 환경 설치 안내를 확인해 주세요."
    read -r -p "종료하려면 Enter를 누르세요."
    exit 1
fi
.venv/bin/python -m app.launch
if [ "$?" -ne 0 ]; then
    read -r -p "클립맨을 열지 못했습니다. 종료하려면 Enter를 누르세요."
fi
