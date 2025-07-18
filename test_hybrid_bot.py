import ccxt
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os
from dotenv import load_dotenv
from functools import wraps

# .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_hybrid_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 네트워크 에러 처리 데코레이터
def retry_on_network_error(max_retries=3, delay=1):
    """네트워크 에러 발생 시 재시도하는 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ccxt.NetworkError, ccxt.ExchangeNotAvailable, ccxt.RequestTimeout) as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"네트워크 에러 발생 (시도 {attempt + 1}/{max_retries}): {e}")
                        time.sleep(delay * (2 ** attempt))
                        continue
                    else:
                        logger.error(f"네트워크 에러 - 최대 재시도 횟수 초과: {e}")
                        raise
                except Exception as e:
                    logger.error(f"예상치 못한 에러: {e}")
                    raise
            return None
        return wrapper
    return decorator

class HybridTradingBotTest:
    """하이브리드 트레이딩 봇 테스트 클래스"""
    
    def __init__(self, api_key: str, api_secret: str, use_testnet: bool = True):
        """봇 초기화"""
        self.api_key = api_key
        self.api_secret = api_secret
        self.use_testnet = use_testnet
        
        # 현물거래 및 선물거래 거래소 객체 생성
        self.spot_exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': use_testnet,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
            }
        })
        
        self.futures_exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': use_testnet,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
            }
        })
        
        # 거래 가능한 심볼들
        self.symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        
        # 전략 설정
        self.strategy_config = {
            'spot_allocation': 0.6,      # 현물 거래 비율 60%
            'futures_allocation': 0.4,   # 선물 거래 비율 40%
            'hedge_ratio': 0.3,          # 헤지 비율 30%
            'rebalance_threshold': 0.05, # 5% 이상 차이나면 리밸런싱
            'max_leverage': 5,           # 최대 레버리지 5배
            'risk_per_trade': 0.02,      # 거래당 리스크 2%
        }
        
        logger.info(f"하이브리드 트레이딩 봇 테스트 초기화 완료")
    
    @retry_on_network_error()
    def test_spot_connection(self) -> bool:
        """현물 거래소 연결 테스트"""
        try:
            balance = self.spot_exchange.fetch_balance()
            logger.info(f"현물 연결 성공: USDT 잔고 {balance.get('USDT', {}).get('total', 0):.2f}")
            return True
        except Exception as e:
            logger.error(f"현물 연결 실패: {e}")
            return False
    
    @retry_on_network_error()
    def test_futures_connection(self) -> bool:
        """선물 거래소 연결 테스트"""
        try:
            balance = self.futures_exchange.fetch_balance()
            logger.info(f"선물 연결 성공: USDT 잔고 {balance.get('USDT', {}).get('total', 0):.2f}")
            return True
        except Exception as e:
            logger.error(f"선물 연결 실패: {e}")
            return False
    
    @retry_on_network_error()
    def test_market_data(self) -> bool:
        """시장 데이터 조회 테스트"""
        try:
            for symbol in self.symbols:
                # 현물 가격
                spot_ticker = self.spot_exchange.fetch_ticker(symbol)
                spot_price = spot_ticker['last']
                
                # 선물 가격
                futures_ticker = self.futures_exchange.fetch_ticker(symbol)
                futures_price = futures_ticker['last']
                
                spread = (futures_price - spot_price) / spot_price * 100
                
                logger.info(f"{symbol} - 현물: {spot_price:.2f}, 선물: {futures_price:.2f}, 스프레드: {spread:.3f}%")
            
            return True
        except Exception as e:
            logger.error(f"시장 데이터 조회 실패: {e}")
            return False
    
    @retry_on_network_error()
    def test_historical_data(self) -> bool:
        """과거 데이터 조회 테스트"""
        try:
            for symbol in self.symbols:
                ohlcv = self.spot_exchange.fetch_ohlcv(symbol, '1h', limit=10)
                if len(ohlcv) > 0:
                    logger.info(f"{symbol} 과거 데이터 조회 성공: {len(ohlcv)}개 캔들")
                else:
                    logger.warning(f"{symbol} 과거 데이터 조회 실패")
            
            return True
        except Exception as e:
            logger.error(f"과거 데이터 조회 실패: {e}")
            return False
    
    def test_technical_analysis(self) -> bool:
        """기술적 분석 테스트"""
        try:
            symbol = 'BTC/USDT'
            ohlcv = self.spot_exchange.fetch_ohlcv(symbol, '1h', limit=50)
            
            if len(ohlcv) < 50:
                logger.warning(f"충분한 데이터가 없습니다: {len(ohlcv)}")
                return False
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # 이동평균 계산
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            
            # RSI 계산
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            latest = df.iloc[-1]
            logger.info(f"{symbol} 기술적 분석:")
            logger.info(f"  현재가: {latest['close']:.2f}")
            logger.info(f"  SMA20: {latest['sma_20']:.2f}")
            logger.info(f"  SMA50: {latest['sma_50']:.2f}")
            logger.info(f"  RSI: {latest['rsi']:.2f}")
            
            return True
        except Exception as e:
            logger.error(f"기술적 분석 실패: {e}")
            return False
    
    def run_comprehensive_test(self) -> None:
        """전체 테스트 실행"""
        logger.info("=" * 50)
        logger.info("하이브리드 트레이딩 봇 종합 테스트 시작")
        logger.info("=" * 50)
        
        tests = [
            ("현물 거래소 연결", self.test_spot_connection),
            ("선물 거래소 연결", self.test_futures_connection),
            ("시장 데이터 조회", self.test_market_data),
            ("과거 데이터 조회", self.test_historical_data),
            ("기술적 분석", self.test_technical_analysis),
        ]
        
        results = []
        for test_name, test_func in tests:
            logger.info(f"\n🔍 {test_name} 테스트 중...")
            try:
                result = test_func()
                if result:
                    logger.info(f"✅ {test_name} 성공")
                else:
                    logger.error(f"❌ {test_name} 실패")
                results.append((test_name, result))
            except Exception as e:
                logger.error(f"❌ {test_name} 오류: {e}")
                results.append((test_name, False))
        
        # 테스트 결과 요약
        logger.info("\n" + "=" * 50)
        logger.info("테스트 결과 요약")
        logger.info("=" * 50)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ 성공" if result else "❌ 실패"
            logger.info(f"{test_name}: {status}")
        
        logger.info(f"\n총 {total}개 테스트 중 {passed}개 성공 ({passed/total*100:.1f}%)")
        
        if passed == total:
            logger.info("🎉 모든 테스트 통과! 하이브리드 봇이 정상적으로 작동할 수 있습니다.")
        else:
            logger.warning("⚠️ 일부 테스트가 실패했습니다. 설정을 확인하세요.")

def main():
    """메인 실행 함수"""
    # 환경 변수에서 API 키 로드
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_SECRET_KEY')
    
    if not api_key or not api_secret:
        logger.error("API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")
        return
    
    # 테스트넷 사용 여부
    use_testnet = False  # 실제 계정으로 테스트 (거래하지 않음)
    
    logger.info(f"테스트 모드: {'테스트넷' if use_testnet else '실제 거래'}")
    
    # 봇 초기화 및 테스트 실행
    bot = HybridTradingBotTest(api_key, api_secret, use_testnet=use_testnet)
    bot.run_comprehensive_test()

if __name__ == "__main__":
    main()