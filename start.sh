#!/bin/bash

# 트레이딩 봇 실행 스크립트

echo "🚀 암호화폐 트레이딩 봇 시작"
echo "================================"

# 가상환경 활성화
if [ -d "venv" ]; then
    echo "📦 가상환경 활성화 중..."
    source venv/bin/activate
else
    echo "❌ 가상환경을 찾을 수 없습니다. 먼저 setup.sh를 실행하세요."
    exit 1
fi

# .env 파일 확인
if [ ! -f ".env" ]; then
    echo "⚠️ .env 파일이 없습니다."
    echo "API 키를 설정해주세요:"
    read -p "BINANCE_API_KEY: " api_key
    read -p "BINANCE_SECRET_KEY: " secret_key
    
    cat > .env << EOF
BINANCE_API_KEY=$api_key
BINANCE_SECRET_KEY=$secret_key
USE_TESTNET=false
EOF
    echo "✅ .env 파일 생성 완료"
fi

# Python 스크립트 실행
echo "🤖 트레이딩 봇 실행 중..."
python run_trading_bot.py

echo "👋 트레이딩 봇 종료"