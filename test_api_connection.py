#!/usr/bin/env python3
"""
API 연결 테스트
"""

import ccxt
from config import config

def test_api_connection():
    """API 연결 테스트"""
    print("🔑 API 연결 테스트 시작...")
    
    try:
        # 현물 거래소 테스트
        spot_exchange = ccxt.binance({
            'apiKey': config.BINANCE_API_KEY,
            'secret': config.BINANCE_SECRET_KEY,
            'sandbox': config.USE_TESTNET,
            'defaultType': 'spot',
            'options': {
                'adjustForTimeDifference': True,
                'recvWindow': 60000,
            }
        })
        
        print("📊 현물 거래소 연결 시도...")
        
        # 계정 정보 조회 (권한 테스트)
        try:
            account_info = spot_exchange.fetch_balance()
            print("✅ 현물 거래소 연결 성공!")
            print(f"   USDT 잔고: {account_info.get('total', {}).get('USDT', 0):.2f}")
            
        except ccxt.AuthenticationError as e:
            print(f"❌ 인증 오류: {e}")
            return False
        except ccxt.PermissionDenied as e:
            print(f"❌ 권한 오류: {e}")
            print("   💡 API 키 권한을 확인해주세요 (Spot & Margin Trading 필요)")
            return False
        
        # 선물 거래소 테스트
        futures_exchange = ccxt.binance({
            'apiKey': config.BINANCE_API_KEY,
            'secret': config.BINANCE_SECRET_KEY,
            'sandbox': config.USE_TESTNET,
            'defaultType': 'future',
            'options': {
                'adjustForTimeDifference': True,
                'recvWindow': 60000,
            }
        })
        
        print("🚀 선물 거래소 연결 시도...")
        
        try:
            futures_balance = futures_exchange.fetch_balance()
            print("✅ 선물 거래소 연결 성공!")
            print(f"   USDT 잔고: {futures_balance.get('total', {}).get('USDT', 0):.2f}")
            
        except ccxt.AuthenticationError as e:
            print(f"❌ 인증 오류: {e}")
            return False
        except ccxt.PermissionDenied as e:
            print(f"❌ 권한 오류: {e}")
            print("   💡 API 키 권한을 확인해주세요 (Futures Trading 필요)")
            return False
        
        # 가격 데이터 테스트
        print("💰 시장 데이터 테스트...")
        ticker = spot_exchange.fetch_ticker('BTC/USDT')
        print(f"   BTC/USDT 가격: ${ticker['last']:,.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False

def main():
    print("🧪 API 연결 테스트")
    print("=" * 40)
    
    print(f"API 키: {config.BINANCE_API_KEY[:10]}...")
    print(f"테스트넷 모드: {config.USE_TESTNET}")
    print()
    
    success = test_api_connection()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 API 연결 테스트 성공!")
        print("📝 모든 API 기능이 정상적으로 작동합니다.")
    else:
        print("⚠️ API 연결에 문제가 있습니다.")
        print("💡 다음을 확인해주세요:")
        print("   1. API 키와 시크릿 키가 올바른지")
        print("   2. API 키 권한이 충분한지 (Spot Trading, Futures Trading)")
        print("   3. IP 화이트리스트 설정이 올바른지")
        print("   4. 인터넷 연결이 정상인지")

if __name__ == "__main__":
    main()