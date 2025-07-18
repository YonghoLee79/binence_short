# 🚀 Advanced Binance Trading Bot

고급 암호화폐 자동매매 봇 시스템 - 현물거래와 선물거래를 복합으로 운영하는 하이브리드 전략

## 📋 목차
- [특징](#-특징)
- [설치 및 설정](#-설치-및-설정)
- [사용 방법](#-사용-방법)
- [전략 설명](#-전략-설명)
- [리스크 관리](#-리스크-관리)
- [성과 추적](#-성과-추적)
- [파일 구조](#-파일-구조)
- [주의사항](#-주의사항)

## 🎯 특징

### 🔥 핵심 기능
- **하이브리드 전략**: 현물거래와 선물거래 동시 운영
- **머신러닝 기반 예측**: Random Forest, Gradient Boosting 활용
- **고급 기술적 분석**: 30+ 기술적 지표 활용
- **실시간 리스크 관리**: 동적 손절매 및 이익실현
- **페어 트레이딩**: 현물-선물 간 아비트라지 전략
- **자동 포트폴리오 리밸런싱**: 목표 비율 자동 조정

### 💡 고급 기능
- **감정 분석**: 시장 심리 반영 거래
- **네트워크 에러 처리**: 자동 재시도 메커니즘
- **실시간 모니터링**: 웹 대시보드 지원
- **백테스팅**: 전략 성과 검증
- **동적 파라미터 최적화**: 시장 상황에 따른 자동 조정

## 🛠 설치 및 설정

### 1. 필수 요구사항
```bash
# Python 3.8 이상
python --version

# 시스템 의존성 설치 (macOS)
brew install ta-lib

# 시스템 의존성 설치 (Ubuntu)
sudo apt-get install libta-lib-dev
```

### 2. 프로젝트 클론 및 설정
```bash
# 프로젝트 클론
git clone https://github.com/yourusername/binance-trading-bot.git
cd binance-trading-bot

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 3. API 키 설정
```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here
```

### 4. 바이낸스 API 키 생성
1. [바이낸스 계정](https://www.binance.com) 로그인
2. 계정 → API 관리 → API 키 생성
3. 권한 설정:
   - ✅ 현물 및 마진 거래
   - ✅ 선물 거래
   - ✅ 읽기 전용 (필수)
   - ❌ 출금 (보안상 비활성화 권장)

## 🚀 사용 방법

### 기본 거래 봇 실행
```bash
# 실행 권한 부여
chmod +x start_bot.sh

# 봇 실행
./start_bot.sh
```

### 하이브리드 전략 봇 실행
```bash
# 실행 권한 부여
chmod +x start_hybrid_bot.sh

# 하이브리드 봇 실행
./start_hybrid_bot.sh
```

### 잔고 테스트
```bash
# 계정 연결 및 잔고 확인
python balance_test.py
```

## 📊 전략 설명

### 1. 기본 거래 전략 (run.py)
- **대상**: 현물거래 또는 선물거래 중 선택
- **심볼**: BTC/USDT, ETH/USDT, BNB/USDT, ADA/USDT, SOL/USDT
- **지표**: RSI, MACD, 볼린저밴드, ATR, ADX 등
- **기계학습**: Random Forest, Gradient Boosting 예측 모델

### 2. 하이브리드 전략 (hybrid_trading_bot.py)
- **현물 60% / 선물 40%** 비율 운영
- **페어 트레이딩**: 현물-선물 간 가격 차이 활용
- **아비트라지**: 스프레드 거래를 통한 수익 창출
- **레버리지**: 최대 5배 제한
- **자동 헤지**: 포지션 위험 분산

### 3. 거래 신호 생성
```python
# 기술적 분석 신호
- RSI: 과매수/과매도 구간
- MACD: 모멘텀 변화
- 볼린저밴드: 변동성 돌파
- 이동평균: 추세 확인

# 머신러닝 신호
- Random Forest: 앙상블 예측
- Gradient Boosting: 그라디언트 부스팅
- 특성 엔지니어링: 30+ 기술적 지표
```

## 🛡 리스크 관리

### 손절매 시스템
- **현물거래**: -5% 손절매
- **선물거래**: -3% 손절매 (레버리지 고려)
- **동적 손절매**: ATR 기반 변동성 조정
- **트레일링 스탑**: 수익 보호

### 포지션 관리
- **거래당 리스크**: 2% 제한
- **최대 포지션 크기**: 계좌 자금의 20%
- **다각화**: 5개 심볼 분산 투자
- **상관관계 분석**: 포지션 간 위험 최소화

### 자금 관리
- **Kelly Criterion**: 최적 포지션 크기 계산
- **자동 리밸런싱**: 목표 비율 유지
- **안전 마진**: 최소 잔고 유지

## 📈 성과 추적

### 실시간 모니터링
```python
# 핵심 지표
- 총 수익률 (%)
- 샤프 비율
- 최대 손실 (MDD)
- 승률 (%)
- 평균 수익/손실 비율

# 거래 통계
- 총 거래 수
- 평균 보유 시간
- 거래 수수료 합계
- 펀딩 비용 (선물)
```

### 성과 리포트
```bash
# 성과 보고서 생성
python -c "
from run import AdvancedBinanceTradingBot
bot = AdvancedBinanceTradingBot(api_key, api_secret)
bot.run_performance_report()
"
```

## 📁 파일 구조

```
binance-trading-bot/
├── run.py                     # 메인 거래 봇
├── hybrid_trading_bot.py      # 하이브리드 전략 봇
├── balance_test.py           # 계정 연결 테스트
├── start_bot.sh              # 기본 봇 실행 스크립트
├── start_hybrid_bot.sh       # 하이브리드 봇 실행 스크립트
├── requirements.txt          # Python 의존성
├── .env.example             # 환경 변수 예시
├── .env                     # 환경 변수 (생성 필요)
├── .gitignore              # Git 무시 파일
├── trading_bot.log         # 거래 로그
├── hybrid_trading_bot.log  # 하이브리드 봇 로그
├── venv/                   # 가상환경 (생성됨)
└── README.md               # 프로젝트 설명서
```

## ⚠️ 주의사항

### 🔒 보안
- **API 키 보안**: .env 파일을 절대 공개하지 마세요
- **권한 최소화**: 출금 권한은 비활성화하세요
- **IP 제한**: 가능한 경우 IP 화이트리스트 설정
- **2FA 활성화**: 바이낸스 계정에 2단계 인증 설정

### 💰 투자 위험
- **투자 원금 손실 가능**: 암호화폐 투자는 고위험 투자입니다
- **소액 테스트**: 처음에는 소액으로 시작하세요
- **백테스팅**: 실제 거래 전 충분한 테스트 필요
- **시장 변동성**: 급격한 가격 변동에 주의하세요

### 🔧 기술적 고려사항
- **네트워크 안정성**: 안정적인 인터넷 연결 필요
- **서버 다운타임**: 24/7 운영을 위한 서버 관리
- **API 제한**: 바이낸스 API 호출 제한 준수
- **로그 모니터링**: 정기적인 로그 파일 확인

## 🎯 성능 최적화

### 시스템 요구사항
- **CPU**: 최소 2코어 (4코어 권장)
- **메모리**: 최소 4GB RAM (8GB 권장)
- **네트워크**: 안정적인 인터넷 연결
- **디스크**: 최소 1GB 여유공간

### 최적화 팁
```python
# 1. 병렬 처리
import asyncio
async def parallel_analysis():
    tasks = [analyze_symbol(symbol) for symbol in symbols]
    results = await asyncio.gather(*tasks)
    return results

# 2. 캐싱
from functools import lru_cache
@lru_cache(maxsize=128)
def get_historical_data(symbol, timeframe):
    # 캐시된 데이터 반환
    pass

# 3. 메모리 관리
import gc
gc.collect()  # 가비지 컬렉션 실행
```

## 🔧 고급 설정

### 커스텀 전략 추가
```python
# custom_strategy.py
from run import AdvancedBinanceTradingBot

class CustomStrategy(AdvancedBinanceTradingBot):
    def custom_signal_generator(self, df):
        # 커스텀 신호 로직
        return signals
```

### 알림 설정
```python
# 텔레그램 알림
import telegram
bot = telegram.Bot(token='YOUR_BOT_TOKEN')
bot.send_message(chat_id='YOUR_CHAT_ID', text='거래 완료!')

# 이메일 알림
import smtplib
from email.mime.text import MIMEText
# 이메일 전송 로직
```

## 📞 지원 및 문의

### 문제 해결
1. **로그 확인**: `trading_bot.log` 파일 확인
2. **API 연결**: `balance_test.py` 실행
3. **의존성 설치**: `pip install -r requirements.txt`
4. **권한 설정**: `chmod +x *.sh`

### 기여하기
1. Fork 프로젝트
2. 새 기능 브랜치 생성
3. 코드 변경 및 테스트
4. Pull Request 제출

---

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## ⚡ 빠른 시작

```bash
# 1. 프로젝트 설정
git clone https://github.com/yourusername/binance-trading-bot.git
cd binance-trading-bot
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. API 키 설정
echo "BINANCE_API_KEY=your_key" > .env
echo "BINANCE_SECRET_KEY=your_secret" >> .env

# 3. 테스트 실행
python balance_test.py

# 4. 봇 실행
./start_bot.sh
```

---

⚠️ **면책 조항**: 이 소프트웨어는 교육 목적으로 제공됩니다. 실제 거래 시 발생하는 모든 손실에 대해 개발자는 책임을 지지 않습니다. 투자는 본인의 판단과 책임하에 이루어져야 합니다.

🚀 **Happy Trading!**