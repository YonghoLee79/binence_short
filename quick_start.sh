#!/bin/bash

# 🚀 하이브리드 트레이딩 봇 빠른 시작 스크립트

echo "🚀 하이브리드 트레이딩 봇 빠른 시작"
echo "=================================="

# 현재 디렉토리로 이동
cd "$(dirname "$0")"

# 가상환경 확인
if [ ! -d "venv" ]; then
    echo "❌ 가상환경이 없습니다. 다음 명령어로 생성하세요:"
    echo "python -m venv venv"
    exit 1
fi

# 가상환경 활성화
echo "📦 가상환경 활성화 중..."
source venv/bin/activate

# .env 파일 확인
if [ ! -f ".env" ]; then
    echo "❌ .env 파일이 없습니다. .env.example을 참고하여 생성하세요."
    exit 1
fi

# 필수 패키지 설치 확인
echo "🔍 필수 패키지 확인 중..."
python -c "import pandas, ccxt, numpy" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 필수 패키지 설치 중..."
    pip install pandas ccxt numpy python-dotenv requests
fi

# API 키 테스트
echo "🔑 API 키 테스트 중..."
python api_test.py

# 하이브리드 봇 전체 테스트
echo "🧪 하이브리드 봇 테스트 중..."
python test_hybrid_bot.py

# 사용자 확인
echo ""
echo "✅ 모든 테스트가 완료되었습니다."
echo ""
echo "다음 단계를 선택하세요:"
echo "1. 하이브리드 봇 실행 (실제 거래)"
echo "2. 테스트 모드 계속"
echo "3. 종료"
echo ""
read -p "선택하세요 (1-3): " choice

case $choice in
    1)
        echo "🚀 하이브리드 봇을 시작합니다..."
        echo "주의: 실제 거래가 시작됩니다!"
        read -p "계속하시겠습니까? (YES 입력): " confirm
        if [ "$confirm" = "YES" ]; then
            python hybrid_trading_bot.py
        else
            echo "❌ 거래가 취소되었습니다."
        fi
        ;;
    2)
        echo "🧪 테스트 모드를 계속합니다..."
        python test_hybrid_bot.py
        ;;
    3)
        echo "👋 프로그램을 종료합니다."
        ;;
    *)
        echo "❌ 잘못된 선택입니다."
        ;;
esac

echo ""
echo "📚 더 많은 정보는 HYBRID_BOT_GUIDE.md를 참고하세요."
echo "🎯 성공적인 거래를 위해 항상 리스크 관리를 철저히 하세요!"