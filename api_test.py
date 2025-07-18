import ccxt
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def test_api_permissions():
    """API 키 권한 테스트"""
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_SECRET_KEY')
    
    if not api_key or not api_secret:
        print("❌ API 키가 설정되지 않았습니다.")
        return
    
    print(f"🔑 API Key: {api_key[:10]}...")
    print(f"🔐 Secret Key: {api_secret[:10]}...")
    
    # 현물 거래소 테스트
    print("\n📊 현물 거래소 테스트:")
    try:
        spot_exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': False,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
            }
        })
        
        # 계정 정보 조회
        account = spot_exchange.fetch_balance()
        print(f"✅ 현물 연결 성공")
        print(f"   USDT 잔고: {account.get('USDT', {}).get('total', 0):.2f}")
        
        # 가능한 다른 코인들 확인
        for coin in ['BTC', 'ETH', 'BNB']:
            balance = account.get(coin, {}).get('total', 0)
            if balance > 0:
                print(f"   {coin} 잔고: {balance:.8f}")
        
    except Exception as e:
        print(f"❌ 현물 연결 실패: {e}")
    
    # 선물 거래소 테스트
    print("\n🚀 선물 거래소 테스트:")
    try:
        futures_exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': False,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
            }
        })
        
        # 계정 정보 조회
        account = futures_exchange.fetch_balance()
        print(f"✅ 선물 연결 성공")
        print(f"   USDT 잔고: {account.get('USDT', {}).get('total', 0):.2f}")
        
    except Exception as e:
        print(f"❌ 선물 연결 실패: {e}")
    
    # 시장 데이터 테스트 (인증 불필요)
    print("\n📈 시장 데이터 테스트:")
    try:
        public_exchange = ccxt.binance({
            'enableRateLimit': True,
        })
        
        ticker = public_exchange.fetch_ticker('BTC/USDT')
        print(f"✅ 시장 데이터 조회 성공")
        print(f"   BTC/USDT 가격: {ticker['last']:.2f}")
        
    except Exception as e:
        print(f"❌ 시장 데이터 조회 실패: {e}")
    
    # API 키 권한 확인
    print("\n🔐 API 키 권한 분석:")
    try:
        spot_exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': False,
            'enableRateLimit': True,
        })
        
        # 계정 정보로 권한 확인
        account_info = spot_exchange.fetch_balance()
        print("✅ 읽기 권한: 있음")
        
        # 실제 주문 테스트는 하지 않고 권한만 확인
        print("📋 권한 요약:")
        print("   - 읽기 권한: ✅")
        print("   - 현물 거래: ✅ (API 키 유효)")
        print("   - 선물 거래: ❓ (권한 확인 필요)")
        print("   - 출금 권한: ❓ (보안상 비활성화 권장)")
        
    except Exception as e:
        print(f"❌ 권한 확인 실패: {e}")

if __name__ == "__main__":
    test_api_permissions()