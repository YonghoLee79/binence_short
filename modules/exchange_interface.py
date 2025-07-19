"""
거래소 인터페이스 모듈
"""
import ccxt
import pandas as pd
import time
from typing import Dict, Any, List, Optional, Tuple
from utils.logger import logger
from utils.decorators import retry_on_network_error, rate_limit, log_execution_time


class ExchangeInterface:
    """거래소 인터페이스 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.spot_exchange = None
        self.futures_exchange = None
        self.setup_exchanges()
    
    def setup_exchanges(self):
        """거래소 연결 설정"""
        try:
            # 현물 거래소 설정
            self.spot_exchange = ccxt.binance({
                'apiKey': self.config['api_key'],
                'secret': self.config['secret_key'],
                'sandbox': self.config.get('use_testnet', False),
                'defaultType': 'spot',
                'options': {
                    'adjustForTimeDifference': True,
                    'recvWindow': 60000,
                }
            })
            
            # 선물 거래소 설정
            self.futures_exchange = ccxt.binance({
                'apiKey': self.config['api_key'],
                'secret': self.config['secret_key'],
                'sandbox': self.config.get('use_testnet', False),
                'defaultType': 'future',
                'options': {
                    'adjustForTimeDifference': True,
                    'recvWindow': 60000,
                }
            })
            
            # 사용 가능한 심볼 목록 캐시
            self._available_symbols = {'spot': set(), 'future': set()}
            self._load_available_symbols()
            
            logger.info("거래소 연결 설정 완료")
        except Exception as e:
            logger.error(f"거래소 연결 설정 실패: {e}")
            raise
    
    def _load_available_symbols(self):
        """사용 가능한 심볼 목록 로드"""
        try:
            # 현물 심볼 로드
            if self.spot_exchange:
                spot_markets = self.spot_exchange.load_markets()
                self._available_symbols['spot'] = set(spot_markets.keys())
                logger.info(f"현물 심볼 {len(self._available_symbols['spot'])}개 로드됨")
            
            # 선물 심볼 로드
            if self.futures_exchange:
                futures_markets = self.futures_exchange.load_markets()
                self._available_symbols['future'] = set(futures_markets.keys())
                logger.info(f"선물 심볼 {len(self._available_symbols['future'])}개 로드됨")
                
        except Exception as e:
            logger.error(f"심볼 목록 로드 실패: {e}")
            # 실패 시 빈 set 유지
    
    def _is_symbol_available(self, symbol: str, exchange_type: str) -> bool:
        """심볼이 해당 거래소에서 사용 가능한지 확인"""
        try:
            if exchange_type not in self._available_symbols:
                return False
            return symbol in self._available_symbols[exchange_type]
        except Exception:
            # 확인할 수 없으면 True 반환 (기존 동작 유지)
            return True
    
    @retry_on_network_error(max_retries=3)
    @rate_limit(calls_per_second=0.5)
    def get_spot_balance(self) -> Dict[str, float]:
        """현물 잔고 조회"""
        try:
            if not self.spot_exchange:
                logger.error("현물 거래소 연결이 설정되지 않았습니다")
                return {'total': {}, 'free': {}, 'used': {}}
            
            balance = self.spot_exchange.fetch_balance()
            return {
                'total': balance['total'],
                'free': balance['free'],
                'used': balance['used']
            }
        except ccxt.AuthenticationError as e:
            logger.error(f"API 키 인증 오류: {e}")
            # API 키 문제일 때는 재시도하지 않고 빈 잔고 반환
            return {'total': {'USDT': 0}, 'free': {'USDT': 0}, 'used': {'USDT': 0}}
        except ccxt.PermissionDenied as e:
            logger.error(f"API 키 권한 오류: {e}")
            return {'total': {'USDT': 0}, 'free': {'USDT': 0}, 'used': {'USDT': 0}}
        except Exception as e:
            logger.error(f"현물 잔고 조회 실패: {e}")
            return {'total': {}, 'free': {}, 'used': {}}
    
    @retry_on_network_error(max_retries=3)
    @rate_limit(calls_per_second=0.5)
    def get_futures_balance(self) -> Dict[str, float]:
        """선물 잔고 조회"""
        try:
            if not self.futures_exchange:
                logger.error("선물 거래소 연결이 설정되지 않았습니다")
                return {'total': {}, 'free': {}, 'used': {}}
            
            balance = self.futures_exchange.fetch_balance()
            return {
                'total': balance['total'],
                'free': balance['free'],
                'used': balance['used']
            }
        except ccxt.AuthenticationError as e:
            logger.error(f"API 키 인증 오류: {e}")
            return {'total': {'USDT': 0}, 'free': {'USDT': 0}, 'used': {'USDT': 0}}
        except ccxt.PermissionDenied as e:
            logger.error(f"API 키 권한 오류: {e}")
            return {'total': {'USDT': 0}, 'free': {'USDT': 0}, 'used': {'USDT': 0}}
        except Exception as e:
            logger.error(f"선물 잔고 조회 실패: {e}")
            return {'total': {}, 'free': {}, 'used': {}}
    
    @retry_on_network_error(max_retries=3)
    @rate_limit(calls_per_second=1.0)
    def get_ticker(self, symbol: str, exchange_type: str = 'spot') -> Dict[str, Any]:
        """심볼 가격 정보 조회"""
        try:
            exchange = self.spot_exchange if exchange_type == 'spot' else self.futures_exchange
            
            # 심볼 유효성 검사
            if not self._is_symbol_available(symbol, exchange_type):
                logger.warning(f"심볼이 존재하지 않음: {symbol} ({exchange_type})")
                return {}
            
            ticker = exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'last': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'volume': ticker['baseVolume'],
                'change': ticker['change'],
                'percentage': ticker['percentage'],
                'timestamp': ticker['timestamp']
            }
        except ccxt.BadSymbol as e:
            logger.warning(f"잘못된 심볼: {symbol} ({exchange_type}) - {e}")
            return {}
        except Exception as e:
            logger.error(f"가격 정보 조회 실패 ({symbol}): {e}")
            return {}
    
    @retry_on_network_error(max_retries=3)
    @rate_limit(calls_per_second=0.5)
    def get_orderbook(self, symbol: str, limit: int = 100, exchange_type: str = 'spot') -> Dict[str, Any]:
        """호가창 정보 조회"""
        try:
            exchange = self.spot_exchange if exchange_type == 'spot' else self.futures_exchange
            orderbook = exchange.fetch_order_book(symbol, limit)
            return {
                'symbol': symbol,
                'bids': orderbook['bids'],
                'asks': orderbook['asks'],
                'timestamp': orderbook['timestamp']
            }
        except Exception as e:
            logger.error(f"호가창 조회 실패 ({symbol}): {e}")
            return {}
    
    @retry_on_network_error(max_retries=3)
    @rate_limit(calls_per_second=0.2)
    def get_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 500, exchange_type: str = 'spot') -> pd.DataFrame:
        """캔들 데이터 조회"""
        try:
            exchange = self.spot_exchange if exchange_type == 'spot' else self.futures_exchange
            
            # 심볼 유효성 검사
            if not self._is_symbol_available(symbol, exchange_type):
                logger.warning(f"심볼이 존재하지 않음: {symbol} ({exchange_type})")
                return pd.DataFrame()
            
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv:
                logger.warning(f"OHLCV 데이터가 비어있음: {symbol}")
                return pd.DataFrame()
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
        except ccxt.BadSymbol as e:
            logger.warning(f"잘못된 심볼: {symbol} ({exchange_type}) - {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"캔들 데이터 조회 실패 ({symbol}): {e}")
            return pd.DataFrame()
    
    @retry_on_network_error(max_retries=3)
    @rate_limit(calls_per_second=0.5)
    def place_order(self, symbol: str, side: str, amount: float, price: float = None, 
                   order_type: str = 'market', exchange_type: str = 'spot') -> Dict[str, Any]:
        """주문 생성"""
        try:
            exchange = self.spot_exchange if exchange_type == 'spot' else self.futures_exchange
            
            if order_type == 'market':
                order = exchange.create_market_order(symbol, side, amount)
            else:
                order = exchange.create_limit_order(symbol, side, amount, price)
            
            logger.info(f"주문 생성 완료: {symbol} {side} {amount} @ {price}")
            return {
                'id': order['id'],
                'symbol': order['symbol'],
                'side': order['side'],
                'amount': order['amount'],
                'price': order['price'],
                'type': order['type'],
                'status': order['status'],
                'timestamp': order['timestamp']
            }
        except Exception as e:
            logger.error(f"주문 생성 실패 ({symbol} {side} {amount}): {e}")
            return {}
    
    @retry_on_network_error(max_retries=3)
    @rate_limit(calls_per_second=0.5)
    def cancel_order(self, order_id: str, symbol: str, exchange_type: str = 'spot') -> bool:
        """주문 취소"""
        try:
            exchange = self.spot_exchange if exchange_type == 'spot' else self.futures_exchange
            exchange.cancel_order(order_id, symbol)
            logger.info(f"주문 취소 완료: {order_id}")
            return True
        except Exception as e:
            logger.error(f"주문 취소 실패 ({order_id}): {e}")
            return False
    
    @retry_on_network_error(max_retries=3)
    @rate_limit(calls_per_second=0.5)
    def get_order_status(self, order_id: str, symbol: str, exchange_type: str = 'spot') -> Dict[str, Any]:
        """주문 상태 조회"""
        try:
            exchange = self.spot_exchange if exchange_type == 'spot' else self.futures_exchange
            order = exchange.fetch_order(order_id, symbol)
            return {
                'id': order['id'],
                'symbol': order['symbol'],
                'side': order['side'],
                'amount': order['amount'],
                'filled': order['filled'],
                'remaining': order['remaining'],
                'price': order['price'],
                'status': order['status'],
                'timestamp': order['timestamp']
            }
        except Exception as e:
            logger.error(f"주문 상태 조회 실패 ({order_id}): {e}")
            return {}
    
    @retry_on_network_error(max_retries=3)
    @rate_limit(calls_per_second=0.5)
    def get_open_orders(self, symbol: str = None, exchange_type: str = 'spot') -> List[Dict[str, Any]]:
        """미체결 주문 조회"""
        try:
            exchange = self.spot_exchange if exchange_type == 'spot' else self.futures_exchange
            orders = exchange.fetch_open_orders(symbol)
            return [
                {
                    'id': order['id'],
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'amount': order['amount'],
                    'price': order['price'],
                    'type': order['type'],
                    'status': order['status'],
                    'timestamp': order['timestamp']
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"미체결 주문 조회 실패: {e}")
            return []
    
    @retry_on_network_error(max_retries=3)
    @rate_limit(calls_per_second=0.5)
    def get_trading_fees(self, symbol: str, exchange_type: str = 'spot') -> Dict[str, float]:
        """거래 수수료 조회"""
        try:
            exchange = self.spot_exchange if exchange_type == 'spot' else self.futures_exchange
            fees = exchange.fetch_trading_fees()
            
            if symbol in fees:
                return {
                    'maker': fees[symbol]['maker'],
                    'taker': fees[symbol]['taker']
                }
            else:
                # 기본 수수료 반환
                return {
                    'maker': 0.001 if exchange_type == 'spot' else 0.0002,
                    'taker': 0.001 if exchange_type == 'spot' else 0.0004
                }
        except Exception as e:
            logger.error(f"거래 수수료 조회 실패: {e}")
            return {
                'maker': 0.001 if exchange_type == 'spot' else 0.0002,
                'taker': 0.001 if exchange_type == 'spot' else 0.0004
            }
    
    @retry_on_network_error(max_retries=3)
    @rate_limit(calls_per_second=0.5)
    def get_positions(self, symbol: str = None) -> List[Dict[str, Any]]:
        """선물 포지션 조회"""
        try:
            if not self.futures_exchange:
                logger.warning("선물 거래소 연결이 설정되지 않았습니다")
                return []
            
            positions = self.futures_exchange.fetch_positions(symbol)
            return [
                {
                    'symbol': pos['symbol'],
                    'side': pos['side'],
                    'size': pos['size'],
                    'contracts': pos['contracts'],
                    'contractSize': pos['contractSize'],
                    'unrealizedPnl': pos['unrealizedPnl'],
                    'percentage': pos['percentage'],
                    'entryPrice': pos['entryPrice'],
                    'markPrice': pos['markPrice'],
                    'timestamp': pos['timestamp']
                }
                for pos in positions if pos['contracts'] > 0
            ]
        except ccxt.AuthenticationError as e:
            logger.error(f"API 키 인증 오류: {e}")
            return []
        except ccxt.PermissionDenied as e:
            logger.error(f"API 키 권한 오류: {e}")
            return []
        except Exception as e:
            logger.error(f"포지션 조회 실패: {e}")
            return []
    
    @retry_on_network_error(max_retries=3)
    @rate_limit(calls_per_second=0.5)
    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """레버리지 설정"""
        try:
            if self.futures_exchange:
                self.futures_exchange.set_leverage(leverage, symbol)
                logger.info(f"레버리지 설정 완료: {symbol} {leverage}x")
                return True
            return False
        except Exception as e:
            logger.error(f"레버리지 설정 실패 ({symbol} {leverage}x): {e}")
            return False
    
    @retry_on_network_error(max_retries=3)
    @rate_limit(calls_per_second=0.5)
    def set_margin_mode(self, symbol: str, margin_mode: str = 'isolated') -> bool:
        """마진 모드 설정"""
        try:
            if self.futures_exchange:
                self.futures_exchange.set_margin_mode(margin_mode, symbol)
                logger.info(f"마진 모드 설정 완료: {symbol} {margin_mode}")
                return True
            return False
        except Exception as e:
            logger.error(f"마진 모드 설정 실패 ({symbol} {margin_mode}): {e}")
            return False
    
    @log_execution_time
    def get_market_info(self, symbol: str) -> Dict[str, Any]:
        """시장 정보 조회"""
        try:
            spot_ticker = self.get_ticker(symbol, 'spot')
            futures_ticker = self.get_ticker(symbol, 'future')
            
            # 프리미엄 계산
            premium = 0
            if spot_ticker.get('last') and futures_ticker.get('last'):
                premium = (futures_ticker['last'] - spot_ticker['last']) / spot_ticker['last']
            
            return {
                'symbol': symbol,
                'spot_price': spot_ticker.get('last', 0),
                'futures_price': futures_ticker.get('last', 0),
                'premium': premium,
                'spot_volume': spot_ticker.get('volume', 0),
                'futures_volume': futures_ticker.get('volume', 0),
                'timestamp': time.time()
            }
        except Exception as e:
            logger.error(f"시장 정보 조회 실패 ({symbol}): {e}")
            return {}
    
    def is_exchange_available(self, exchange_type: str = 'both') -> bool:
        """거래소 연결 상태 확인"""
        try:
            if exchange_type == 'spot' or exchange_type == 'both':
                if self.spot_exchange:
                    self.spot_exchange.fetch_balance()
            
            if exchange_type == 'futures' or exchange_type == 'both':
                if self.futures_exchange:
                    self.futures_exchange.fetch_balance()
            
            return True
        except Exception as e:
            logger.error(f"거래소 연결 상태 확인 실패: {e}")
            return False