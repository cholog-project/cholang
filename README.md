# 촐랑이 봇

촐랑이 봇을 구동하기 위한 코드입니다.

# 기능

- `/remind` : 리마인드를 생성합니다. `reminder.json` 파일에 해당 정보가 영구저장됩니다.
- `/remind-list` : 리마인드 정보를 확인합니다.

# 환경설정

아래 설명을 참고해 서버를 구동할 수 있습니다.

## 설정파일

`discord_config.json`에 디스코드 봇 토큰정보를 담아주세요.

## Python 설치 및 구동 (Ubuntu)

python3 가상환경 구동을 위해 아래 패키지를 설치해주세요

```shell
sudo apt install python3-venv
```

## pip install

```shell
python3 -m venv venv

source venv/bin/activate

pip install -r requirements.txt

deactivate
```

## run.sh

포함된 run.sh를 실행하여 구동할 수 있습니다.

```shell
chmod +x run.sh

./run.sh
```

## 기타

Timezone이 Asia/Seoul로 설정되어있어야합니다 🙏

```shell
# KST 설정 참고 명령어
echo "Asia/Seoul" | sudo tee /etc/timezone
sudo ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime
```