# 📱 텔레그램 봇 설정 가이드

하이브리드 트레이딩 봇에 텔레그램 알림 기능을 설정하는 방법

## 📋 목차
- [텔레그램 봇 생성](#-텔레그램-봇-생성)
- [채팅 ID 확인](#-채팅-id-확인)
- [환경 변수 설정](#-환경-변수-설정)
- [테스트 실행](#-테스트-실행)
- [알림 기능](#-알림-기능)

## 🤖 텔레그램 봇 생성

### 1. BotFather와 대화 시작
1. 텔레그램 앱에서 `@BotFather` 검색
2. `/start` 명령어 입력
3. `/newbot` 명령어로 새 봇 생성

### 2. 봇 이름 설정
```
봇 이름 입력 (예: My Trading Bot)
사용자명 입력 (예: MyTradingBot_bot)
```

### 3. 봇 토큰 받기
```
BotFather가 다음과 같은 토큰을 제공합니다:
1234567890:ABCdefGHIjklMNOpqrSTUvwxyz
```

## 🔍 채팅 ID 확인

### 방법 1: 웹 브라우저 사용
1. 생성한 봇과 대화 시작
2. 아무 메시지 전송 (예: "Hello")
3. 브라우저에서 접속:
   ```
   https://api.telegram.org/bot[봇토큰]/getUpdates
   ```
4. 응답에서 `chat.id` 값 확인

### 방법 2: Python 스크립트 사용
```python
import requests

bot_token = "YOUR_BOT_TOKEN"
url = f"https://api.telegram.org/bot{bot_token}/getUpdates"

response = requests.get(url)
data = response.json()

for update in data['result']:
    chat_id = update['message']['chat']['id']
    print(f"Chat ID: {chat_id}")
```

## ⚙️ 환경 변수 설정

### .env 파일 수정
```bash
# .env 파일 편집
nano .env

# 다음 내용 추가
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxyz
TELEGRAM_CHAT_ID=123456789
```

### 설정 예시
```env
# 바이낸스 API
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key

# 텔레그램 알림
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxyz
TELEGRAM_CHAT_ID=123456789
```

## 🧪 테스트 실행

### 텔레그램 봇 연결 테스트
```bash
# 가상환경 활성화
source venv/bin/activate

# 텔레그램 봇 테스트
python telegram_bot.py
```

### 예상 출력
```
텔레그램 봇 연결 테스트 중...
✅ 텔레그램 봇 연결 성공!
```

### 텔레그램에서 확인할 메시지
```
🧪 텔레그램 봇 연결 테스트

✅ 연결이 정상적으로 작동합니다!
🤖 알림 시스템이 준비되었습니다.

⏰ 테스트 시간: 2025-07-19 00:30:15
```

## 📱 알림 기능

### 1. 거래 알림
```
🟢 거래 실행 알림 📊

🪙 심볼: BTC/USDT
📈 타입: SPOT
🎯 주문: BUY
💰 수량: 0.001000
💵 가격: $45,000.00
📊 총액: $45.00

⏰ 시간: 2025-07-19 00:30:15
```

### 2. 잔고 업데이트
```
💰 잔고 업데이트

🏦 총 잔고: $1,150.00
📊 현물: $690.00
🚀 선물: $460.00

📈 손익: +150.00 USDT (+15.00%)

⏰ 시간: 2025-07-19 00:30:15
```

### 3. 시스템 상태
```
🤖 시스템 상태

🟢 상태: RUNNING
🎯 활성 포지션: 5개
📊 총 거래: 47회
🏆 승률: 68.1%

⏰ 시간: 2025-07-19 00:30:15
```

### 4. 에러 알림
```
🚨 에러 알림

⚠️ 타입: NETWORK_ERROR
💬 메시지: API 연결 실패 - 재시도 중

⏰ 시간: 2025-07-19 00:30:15
```

## 🔧 고급 설정

### 알림 빈도 조정
```python
# telegram_bot.py에서 수정
class TelegramBot:
    def __init__(self):
        self.notification_interval = 300  # 5분마다 알림
        self.last_notification = {}
```

### 선택적 알림 설정
```python
# 특정 알림만 활성화
TELEGRAM_TRADE_ALERTS = True
TELEGRAM_BALANCE_ALERTS = True
TELEGRAM_ERROR_ALERTS = True
TELEGRAM_SYSTEM_ALERTS = False
```

## 🚨 보안 주의사항

### 1. 봇 토큰 보안
- 절대로 코드에 하드코딩하지 마세요
- .env 파일을 GitHub에 업로드하지 마세요
- 정기적으로 봇 토큰을 재생성하세요

### 2. 채팅 ID 보안
- 개인 채팅 ID만 사용하세요
- 그룹 채팅 사용 시 주의하세요
- 알 수 없는 사용자와 봇을 공유하지 마세요

## 🔧 문제 해결

### 봇이 메시지를 받지 못하는 경우
```bash
# 봇 토큰 확인
curl https://api.telegram.org/bot[봇토큰]/getMe

# 채팅 ID 확인
curl https://api.telegram.org/bot[봇토큰]/getUpdates
```

### 환경 변수 확인
```bash
# .env 파일 내용 확인
cat .env | grep TELEGRAM

# Python에서 확인
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('BOT_TOKEN:', os.getenv('TELEGRAM_BOT_TOKEN'))
print('CHAT_ID:', os.getenv('TELEGRAM_CHAT_ID'))
"
```

## 🎯 통합 테스트

### 하이브리드 봇과 함께 테스트
```bash
# 텔레그램 알림과 함께 테스트
python test_hybrid_bot.py

# 실제 봇 실행 (텔레그램 알림 포함)
python hybrid_trading_bot.py
```

---

## 📞 지원

### 문제 발생 시
1. 로그 파일 확인: `telegram_bot.log`
2. 네트워크 연결 확인
3. API 토큰 재생성
4. 봇 권한 확인

### 추가 기능 요청
- 커스텀 알림 메시지
- 이미지 차트 전송
- 음성 알림
- 다중 채팅 지원

---

**텔레그램 알림으로 24/7 트레이딩 봇을 안전하게 모니터링하세요! 📱🚀**