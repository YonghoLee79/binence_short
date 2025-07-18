#!/bin/bash

# 🚀 하이브리드 트레이딩 봇 실행 스크립트 (수정된 버전)

echo "🚀 하이브리드 트레이딩 봇 시작"
echo "================================"

# 현재 디렉토리로 이동
cd /Users/yongholee/binence_short

# 올바른 가상환경 활성화 (.venv)
echo "📦 가상환경 활성화 중..."
source .venv/bin/activate

# 환경 변수 로드 확인
echo "🔑 환경 변수 확인 중..."
if [ ! -f ".env" ]; then
    echo "❌ .env 파일이 없습니다."
    exit 1
fi

# 필수 패키지 확인
echo "🔍 필수 패키지 확인 중..."
python -c "import pandas, ccxt, numpy, telegram_bot; print('✅ 모든 패키지 설치 완료')"

if [ $? -ne 0 ]; then
    echo "❌ 필수 패키지가 누락되었습니다."
    exit 1
fi

# 텔레그램 봇 연결 테스트
echo "📱 텔레그램 봇 연결 테스트 중..."
python -c "
from telegram_bot import TelegramBot
bot = TelegramBot()
if bot.enabled:
    print('✅ 텔레그램 봇 연결 가능')
else:
    print('⚠️ 텔레그램 봇 비활성화 (선택사항)')
"

echo ""
echo "🎯 모든 검사 완료!"
echo "📈 하이브리드 트레이딩 봇을 시작합니다..."
echo ""
echo "⚠️ 주의: 실제 거래가 시작됩니다!"
echo "   - 현물 거래 60% + 선물 거래 40% 비율"
echo "   - 자동 리스크 관리 시스템 활성화"
echo "   - 텔레그램 실시간 알림 전송"
echo ""

# 하이브리드 봇 실행
python hybrid_trading_bot.py

echo ""
echo "👋 하이브리드 트레이딩 봇이 종료되었습니다."