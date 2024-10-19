#!/bin/bash

# 현재 작업 디렉토리를 프로젝트 디렉토리로 설정
PROJECT_DIR=$(pwd)

# 로그 파일 경로 정의
LOG_FILE="$PROJECT_DIR/bot.log"

# 이미 실행 중인 스크립트가 있는지 확인하고 종료
PID=$(pgrep -f "python main.py")
if [ -n "$PID" ]; then
    echo "기존에 실행 중인 main.py 프로세스(PID $PID)를 종료합니다..."
    kill -9 $PID
fi

# 가상 환경 활성화
source venv/bin/activate

# Python 스크립트를 백그라운드에서 실행하고 로그 파일로 출력 리디렉션
nohup python main.py > "$LOG_FILE" 2>&1 &

# 가상 환경 비활성화
deactivate

echo "봇이 실행되었습니다. 로그를 확인하려면 아래 명령어를 사용하세요."
echo "tail -f $LOG_FILE"
