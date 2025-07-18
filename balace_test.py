import ccxt
import requests
import hmac
import hashlib
import time
from datetime import datetime

def check_binance_account(api_key, api_secret):
    """
    바이낸스 계좌 상태 확인 (읽기 전용)
    거래는 하지 않고 정보만 확인
    """
    print("🔍 바이낸스 계좌 상태 확인 중...")
    print("=" * 50)
    
    try:
        # 바이낸스 거래소 객체 생성
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': False,  # 실제 계정
            'enableRateLimit': True,
            'timeout': 10000,
        })
        
        print("1️⃣ API 연결 테스트...")
        
        # 계좌 정보 가져오기
        balance = exchange.fetch_balance()
        
        print("✅ API 연결 성공!\n")
        
        # 2. 계좌 기본 정보
        print("📊 계좌 기본 정보:")
        account_info = exchange.fetch_balance()
        
        print(f"   계정 타입: 현물 거래 계정")
        print(f"   확인 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 3. 자산 현황 (0이 아닌 것만)
        print("\n💰 보유 자산 현황:")
        
        total_assets = 0
        asset_count = 0
        
        # 주요 자산들 확인
        for currency, balance_info in balance.items():
            if currency == 'info':  # 메타데이터 스킵
                continue
                
            total = balance_info.get('total', 0)
            free = balance_info.get('free', 0)
            used = balance_info.get('used', 0)
            
            # 0이 아닌 자산만 표시
            if total > 0:
                asset_count += 1
                print(f"\n   {currency}:")
                print(f"     총 보유량: {total:.8f}")
                print(f"     사용 가능: {free:.8f}")
                print(f"     주문 중: {used:.8f}")
                
                # USDT면 총 가치에 추가
                if currency == 'USDT':
                    total_assets += total
        
        print(f"\n📈 요약:")
        print(f"   보유 자산 종류: {asset_count}개")
        print(f"   USDT 보유량: {balance.get('USDT', {}).get('total', 0):.2f}")
        
        # 4. 최근 거래 내역 (옵션)
        try:
            print("\n📋 최근 거래 내역 확인...")
            # BTC/USDT 최근 거래 내역 (있다면)
            trades = exchange.fetch_my_trades('BTC/USDT', limit=5)
            
            if trades:
                print(f"   최근 BTC/USDT 거래: {len(trades)}건")
                for trade in trades[-3:]:  # 최근 3건만
                    trade_time = datetime.fromtimestamp(trade['timestamp']/1000)
                    print(f"     {trade_time.strftime('%m-%d %H:%M')} | "
                          f"{trade['side']} | "
                          f"{trade['amount']:.6f} BTC | "
                          f"${trade['price']:.2f}")
            else:
                print("   최근 BTC/USDT 거래 내역 없음")
                
        except:
            print("   거래 내역 조회 권한 없음 또는 오류")
        
        # 5. API 권한 확인
        print("\n🔐 API 권한 상태:")
        try:
            # 직접 API 호출로 권한 확인
            timestamp = int(time.time() * 1000)
            params = f"timestamp={timestamp}"
            signature = hmac.new(
                api_secret.encode('utf-8'),
                params.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            headers = {'X-MBX-APIKEY': api_key}
            url = f"https://api.binance.com/api/v3/account?{params}&signature={signature}"
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                account_data = response.json()
                print(f"   읽기 권한: ✅")
                print(f"   거래 권한: {'✅' if account_data.get('canTrade', False) else '❌'}")
                print(f"   출금 권한: {'✅' if account_data.get('canWithdraw', False) else '❌'}")
            else:
                print(f"   권한 확인 실패: {response.status_code}")
                
        except Exception as e:
            print(f"   권한 확인 중 오류: {e}")
        
        return True
        
    except ccxt.AuthenticationError as e:
        print(f"❌ 인증 실패: {e}")
        print("\n해결 방법:")
        print("1. API Key와 Secret Key 재확인")
        print("2. API 키에 'Enable Reading' 권한 확인")
        return False
        
    except ccxt.PermissionDenied as e:
        print(f"❌ 권한 거부: {e}")
        print("\n해결 방법:")
        print("1. API 키 권한 설정 확인")
        print("2. IP 제한 해제 또는 현재 IP 추가")
        return False
        
    except ccxt.NetworkError as e:
        print(f"❌ 네트워크 오류: {e}")
        print("\n해결 방법:")
        print("1. 인터넷 연결 확인")
        print("2. VPN 사용 중이면 해제 후 재시도")
        return False
        
    except Exception as e:
        print(f"❌ 알 수 없는 오류: {e}")
        return False

def get_current_ip():
    """현재 IP 주소 확인"""
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        if response.status_code == 200:
            ip = response.json()['ip']
            return ip
    except:
        pass
    return "확인 불가"

def quick_check():
    """빠른 확인 실행"""
    print("🚀 바이낸스 계좌 상태 확인 도구")
    print("=" * 50)
    
    # 현재 IP 표시
    current_ip = get_current_ip()
    print(f"📍 현재 IP 주소: {current_ip}")
    print()
    
    # API 키 입력
    api_key = input("API Key 입력: ").strip()
    api_secret = input("Secret Key 입력: ").strip()
    
    # 입력값 검증
    if len(api_key) != 64:
        print(f"❌ API Key 길이 오류: {len(api_key)}자 (64자여야 함)")
        return
    
    if len(api_secret) != 64:
        print(f"❌ Secret Key 길이 오류: {len(api_secret)}자 (64자여야 함)")
        return
    
    print("\n" + "=" * 50)
    
    # 계좌 상태 확인 실행
    success = check_binance_account(api_key, api_secret)
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 계좌 상태 확인 완료!")
        print("\n다음 단계:")
        print("1. API 연결이 정상적으로 작동합니다")
        print("2. 거래 권한이 있다면 자동매매 봇 사용 가능")
        print("3. 소액으로 테스트 거래 진행 권장")
    else:
        print("❌ 계좌 상태 확인 실패")
        print("\n문제 해결 후 다시 시도해주세요")

# 미리 입력된 키로 테스트 (선택사항)
def test_with_predefined_key():
    """API 키가 이미 있는 경우 사용"""
    # 여기에 실제 키 입력 (보안 주의!)
    API_KEY = "Xp88yq3rFKo3OJhfboNMv2JIJ6VLQvf52M0BapE7PVFBEZjdliy0lq5HSqtpe5Zt"
    API_SECRET = "42qdzk4ErH94bhhandb0L4BOKvRIh6IvCJDAl96UeeMF44eKXXGkFCibkjZLdZjw"  # 64자 문자열
    
    if API_SECRET == "42qdzk4ErH94bhhandb0L4BOKvRIh6IvCJDAl96UeeMF44eKXXGkFCibkjZLdZjw":
        print("❌ Secret Key를 입력해주세요!")
        return
    
    print("🔍 미리 설정된 키로 테스트 중...")
    check_binance_account(API_KEY, API_SECRET)

if __name__ == "__main__":
    # 대화형 입력으로 실행
    quick_check()
    
    # 또는 미리 입력된 키로 테스트
    # test_with_predefined_key()




