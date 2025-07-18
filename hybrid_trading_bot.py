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
import asyncio

# .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hybrid_trading_bot.log'),
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

class HybridTradingBot:
    """현물거래와 선물거래를 복합으로 운영하는 하이브리드 전략 봇"""
    
    def __init__(self, api_key: str, api_secret: str, initial_balance: float = None, use_testnet: bool = False):
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
        self.symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT']
        
        # 잔고 초기화
        self.spot_balance = self.get_spot_balance()
        self.futures_balance = self.get_futures_balance()
        
        if initial_balance is None:
            self.initial_balance = self.spot_balance + self.futures_balance
        else:
            self.initial_balance = initial_balance
            
        self.current_balance = self.initial_balance
        
        # 포지션 및 거래 기록
        self.spot_positions = {}
        self.futures_positions = {}
        self.trade_history = []
        
        # 전략 설정
        self.strategy_config = {
            'spot_allocation': 0.6,      # 현물 거래 비율 60%
            'futures_allocation': 0.4,   # 선물 거래 비율 40%
            'hedge_ratio': 0.3,          # 헤지 비율 30%
            'rebalance_threshold': 0.05, # 5% 이상 차이나면 리밸런싱
            'max_leverage': 5,           # 최대 레버리지 5배
            'risk_per_trade': 0.02,      # 거래당 리스크 2%
        }
        
        # 성능 추적
        self.performance_metrics = {
            'total_trades': 0,
            'profitable_trades': 0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
        }
        
        # 수수료 설정
        self.fees = {
            'spot_maker': 0.001,    # 현물 maker 0.1%
            'spot_taker': 0.001,    # 현물 taker 0.1%
            'futures_maker': 0.0002, # 선물 maker 0.02%
            'futures_taker': 0.0004, # 선물 taker 0.04%
        }
        
        logger.info(f"하이브리드 트레이딩 봇 초기화 완료")
        logger.info(f"현물 잔고: {self.spot_balance:.2f} USDT")
        logger.info(f"선물 잔고: {self.futures_balance:.2f} USDT")
        logger.info(f"총 시작 자금: {self.initial_balance:.2f} USDT")
    
    @retry_on_network_error()
    def get_spot_balance(self) -> float:
        """현물 계정 잔고 조회"""
        try:
            balance = self.spot_exchange.fetch_balance()
            return float(balance.get('USDT', {}).get('total', 0))
        except Exception as e:
            logger.error(f"현물 잔고 조회 실패: {e}")
            return 0.0
    
    @retry_on_network_error()
    def get_futures_balance(self) -> float:
        """선물 계정 잔고 조회"""
        try:
            balance = self.futures_exchange.fetch_balance()
            return float(balance.get('USDT', {}).get('total', 0))
        except Exception as e:
            logger.error(f"선물 잔고 조회 실패: {e}")
            return 0.0
    
    @retry_on_network_error()
    def get_current_price(self, symbol: str) -> float:
        """현재 가격 조회"""
        try:
            ticker = self.spot_exchange.fetch_ticker(symbol)
            return float(ticker['last'])
        except Exception as e:
            logger.error(f"가격 조회 실패 ({symbol}): {e}")
            return 0.0
    
    @retry_on_network_error()
    def get_historical_data(self, symbol: str, timeframe: str = '1h', limit: int = 200) -> pd.DataFrame:
        """과거 데이터 조회"""
        try:
            ohlcv = self.spot_exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            logger.error(f"과거 데이터 조회 실패 ({symbol}): {e}")
            return pd.DataFrame()
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        if df.empty:
            return df
            
        # 이동평균
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 볼린저 밴드
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # 변동성
        df['volatility'] = df['close'].pct_change().rolling(window=20).std()
        
        return df
    
    def analyze_market_trend(self, symbol: str) -> Dict:
        """시장 트렌드 분석"""
        df = self.get_historical_data(symbol)
        if df.empty:
            return {'trend': 'neutral', 'strength': 0.0, 'volatility': 0.0}
            
        df = self.calculate_technical_indicators(df)
        latest = df.iloc[-1]
        
        # 트렌드 분석
        trend_signals = []
        
        # 이동평균 신호
        if latest['sma_20'] > latest['sma_50']:
            trend_signals.append(1)
        elif latest['sma_20'] < latest['sma_50']:
            trend_signals.append(-1)
        else:
            trend_signals.append(0)
        
        # MACD 신호
        if latest['macd'] > latest['macd_signal']:
            trend_signals.append(1)
        elif latest['macd'] < latest['macd_signal']:
            trend_signals.append(-1)
        else:
            trend_signals.append(0)
            
        # RSI 신호
        if latest['rsi'] > 70:
            trend_signals.append(-1)  # 과매수
        elif latest['rsi'] < 30:
            trend_signals.append(1)   # 과매도
        else:
            trend_signals.append(0)
        
        # 전체 신호 계산
        total_signal = sum(trend_signals)
        signal_strength = abs(total_signal) / len(trend_signals)
        
        if total_signal > 0:
            trend = 'bullish'
        elif total_signal < 0:
            trend = 'bearish'
        else:
            trend = 'neutral'
            
        return {
            'trend': trend,
            'strength': signal_strength,
            'volatility': latest['volatility'],
            'rsi': latest['rsi'],
            'macd_signal': latest['macd'] - latest['macd_signal']
        }
    
    def calculate_position_size(self, symbol: str, market_type: str, signal_strength: float) -> float:
        """포지션 크기 계산"""
        current_price = self.get_current_price(symbol)
        if current_price <= 0:
            return 0.0
            
        # 시장 타입에 따른 할당 비율
        if market_type == 'spot':
            allocation = self.strategy_config['spot_allocation']
            available_balance = self.spot_balance
        else:  # futures
            allocation = self.strategy_config['futures_allocation']
            available_balance = self.futures_balance
            
        # 리스크 기반 포지션 크기
        risk_amount = available_balance * self.strategy_config['risk_per_trade']
        base_position_size = (available_balance * allocation) / len(self.symbols)
        
        # 신호 강도에 따른 조정
        adjusted_size = base_position_size * signal_strength
        
        # 최대 리스크 제한
        max_size = risk_amount / (current_price * 0.02)  # 2% 손실 제한
        
        return min(adjusted_size, max_size) / current_price
    
    @retry_on_network_error()
    def execute_spot_trade(self, symbol: str, side: str, amount: float, price: float) -> Dict:
        """현물 거래 실행"""
        try:
            if side == 'buy':
                order = self.spot_exchange.create_market_buy_order(symbol, amount)
            else:
                order = self.spot_exchange.create_market_sell_order(symbol, amount)
                
            logger.info(f"현물 거래 실행: {side} {amount:.6f} {symbol} @ {price:.2f}")
            return order
            
        except Exception as e:
            logger.error(f"현물 거래 실행 실패: {e}")
            return None
    
    @retry_on_network_error()
    def execute_futures_trade(self, symbol: str, side: str, amount: float, price: float, leverage: int = 5) -> Dict:
        """선물 거래 실행"""
        try:
            # 레버리지 설정
            self.futures_exchange.set_leverage(leverage, symbol)
            
            if side == 'buy':
                order = self.futures_exchange.create_market_buy_order(symbol, amount)
            else:
                order = self.futures_exchange.create_market_sell_order(symbol, amount)
                
            logger.info(f"선물 거래 실행: {side} {amount:.6f} {symbol} @ {price:.2f} (레버리지: {leverage}x)")
            return order
            
        except Exception as e:
            logger.error(f"선물 거래 실행 실패: {e}")
            return None
    
    def implement_pairs_trading_strategy(self, symbol: str) -> None:
        """페어 트레이딩 전략 구현"""
        analysis = self.analyze_market_trend(symbol)
        current_price = self.get_current_price(symbol)
        
        if current_price <= 0:
            return
            
        logger.info(f"페어 트레이딩 분석 - {symbol}: {analysis['trend']} (강도: {analysis['strength']:.2f})")
        
        # 현물과 선물 간 가격 차이 분석
        spot_price = current_price
        futures_price = self.get_futures_price(symbol)
        
        if futures_price <= 0:
            return
            
        price_spread = (futures_price - spot_price) / spot_price
        
        logger.info(f"가격 스프레드: {price_spread:.4f} ({spot_price:.2f} vs {futures_price:.2f})")
        
        # 트렌드에 따른 전략 실행
        if analysis['trend'] == 'bullish' and analysis['strength'] > 0.6:
            # 강한 상승 트렌드: 현물 매수 + 선물 매수 (레버리지 활용)
            self.execute_bullish_strategy(symbol, analysis['strength'])
            
        elif analysis['trend'] == 'bearish' and analysis['strength'] > 0.6:
            # 강한 하락 트렌드: 현물 매도 + 선물 매도 (숏 포지션)
            self.execute_bearish_strategy(symbol, analysis['strength'])
            
        elif abs(price_spread) > 0.01:  # 1% 이상 스프레드
            # 아비트라지 기회: 스프레드 거래
            self.execute_arbitrage_strategy(symbol, price_spread)
    
    def execute_bullish_strategy(self, symbol: str, strength: float) -> None:
        """강세 전략 실행"""
        # 현물 매수
        spot_amount = self.calculate_position_size(symbol, 'spot', strength)
        if spot_amount > 0:
            current_price = self.get_current_price(symbol)
            spot_order = self.execute_spot_trade(symbol, 'buy', spot_amount, current_price)
            
            if spot_order:
                self.spot_positions[symbol] = {
                    'side': 'long',
                    'amount': spot_amount,
                    'entry_price': current_price,
                    'timestamp': datetime.now()
                }
        
        # 선물 매수 (레버리지 활용)
        futures_amount = self.calculate_position_size(symbol, 'futures', strength)
        if futures_amount > 0:
            current_price = self.get_current_price(symbol)
            futures_order = self.execute_futures_trade(symbol, 'buy', futures_amount, current_price)
            
            if futures_order:
                self.futures_positions[symbol] = {
                    'side': 'long',
                    'amount': futures_amount,
                    'entry_price': current_price,
                    'timestamp': datetime.now(),
                    'leverage': self.strategy_config['max_leverage']
                }
    
    def execute_bearish_strategy(self, symbol: str, strength: float) -> None:
        """약세 전략 실행"""
        # 현물 매도 (보유 중인 경우)
        if symbol in self.spot_positions:
            position = self.spot_positions[symbol]
            if position['side'] == 'long':
                current_price = self.get_current_price(symbol)
                spot_order = self.execute_spot_trade(symbol, 'sell', position['amount'], current_price)
                
                if spot_order:
                    self.close_spot_position(symbol, current_price)
        
        # 선물 매도 (숏 포지션)
        futures_amount = self.calculate_position_size(symbol, 'futures', strength)
        if futures_amount > 0:
            current_price = self.get_current_price(symbol)
            futures_order = self.execute_futures_trade(symbol, 'sell', futures_amount, current_price)
            
            if futures_order:
                self.futures_positions[symbol] = {
                    'side': 'short',
                    'amount': futures_amount,
                    'entry_price': current_price,
                    'timestamp': datetime.now(),
                    'leverage': self.strategy_config['max_leverage']
                }
    
    def execute_arbitrage_strategy(self, symbol: str, price_spread: float) -> None:
        """아비트라지 전략 실행"""
        current_price = self.get_current_price(symbol)
        
        if price_spread > 0.01:  # 선물 > 현물
            # 현물 매수, 선물 매도
            amount = self.calculate_position_size(symbol, 'spot', 0.5)  # 중간 강도
            
            if amount > 0:
                # 현물 매수
                spot_order = self.execute_spot_trade(symbol, 'buy', amount, current_price)
                # 선물 매도
                futures_order = self.execute_futures_trade(symbol, 'sell', amount, current_price)
                
                if spot_order and futures_order:
                    logger.info(f"아비트라지 실행: {symbol} 스프레드 {price_spread:.4f}")
                    
        elif price_spread < -0.01:  # 현물 > 선물
            # 현물 매도, 선물 매수
            if symbol in self.spot_positions:
                position = self.spot_positions[symbol]
                if position['side'] == 'long':
                    # 현물 매도
                    spot_order = self.execute_spot_trade(symbol, 'sell', position['amount'], current_price)
                    # 선물 매수
                    futures_order = self.execute_futures_trade(symbol, 'buy', position['amount'], current_price)
                    
                    if spot_order and futures_order:
                        logger.info(f"아비트라지 실행: {symbol} 스프레드 {price_spread:.4f}")
    
    @retry_on_network_error()
    def get_futures_price(self, symbol: str) -> float:
        """선물 가격 조회"""
        try:
            ticker = self.futures_exchange.fetch_ticker(symbol)
            return float(ticker['last'])
        except Exception as e:
            logger.error(f"선물 가격 조회 실패 ({symbol}): {e}")
            return 0.0
    
    def close_spot_position(self, symbol: str, current_price: float) -> None:
        """현물 포지션 종료"""
        if symbol in self.spot_positions:
            position = self.spot_positions[symbol]
            pnl = (current_price - position['entry_price']) * position['amount']
            
            # 거래 기록
            trade_record = {
                'timestamp': datetime.now(),
                'symbol': symbol,
                'type': 'spot',
                'side': position['side'],
                'amount': position['amount'],
                'entry_price': position['entry_price'],
                'exit_price': current_price,
                'pnl': pnl,
                'duration': datetime.now() - position['timestamp']
            }
            
            self.trade_history.append(trade_record)
            del self.spot_positions[symbol]
            
            logger.info(f"현물 포지션 종료: {symbol} PnL: {pnl:.2f} USDT")
    
    def close_futures_position(self, symbol: str, current_price: float) -> None:
        """선물 포지션 종료"""
        if symbol in self.futures_positions:
            position = self.futures_positions[symbol]
            
            if position['side'] == 'long':
                pnl = (current_price - position['entry_price']) * position['amount'] * position['leverage']
            else:  # short
                pnl = (position['entry_price'] - current_price) * position['amount'] * position['leverage']
                
            # 거래 기록
            trade_record = {
                'timestamp': datetime.now(),
                'symbol': symbol,
                'type': 'futures',
                'side': position['side'],
                'amount': position['amount'],
                'entry_price': position['entry_price'],
                'exit_price': current_price,
                'pnl': pnl,
                'leverage': position['leverage'],
                'duration': datetime.now() - position['timestamp']
            }
            
            self.trade_history.append(trade_record)
            del self.futures_positions[symbol]
            
            logger.info(f"선물 포지션 종료: {symbol} PnL: {pnl:.2f} USDT (레버리지: {position['leverage']}x)")
    
    def manage_risk(self) -> None:
        """리스크 관리"""
        current_time = datetime.now()
        
        # 현물 포지션 리스크 관리
        for symbol, position in list(self.spot_positions.items()):
            current_price = self.get_current_price(symbol)
            if current_price <= 0:
                continue
                
            # 손절매 (-5%)
            if position['side'] == 'long':
                loss_pct = (current_price - position['entry_price']) / position['entry_price']
                if loss_pct < -0.05:
                    self.execute_spot_trade(symbol, 'sell', position['amount'], current_price)
                    self.close_spot_position(symbol, current_price)
                    logger.warning(f"현물 손절매 실행: {symbol} ({loss_pct:.2%})")
        
        # 선물 포지션 리스크 관리
        for symbol, position in list(self.futures_positions.items()):
            current_price = self.get_current_price(symbol)
            if current_price <= 0:
                continue
                
            # 손절매 (-3% 레버리지 고려)
            if position['side'] == 'long':
                loss_pct = (current_price - position['entry_price']) / position['entry_price']
            else:  # short
                loss_pct = (position['entry_price'] - current_price) / position['entry_price']
                
            if loss_pct < -0.03:
                side = 'sell' if position['side'] == 'long' else 'buy'
                self.execute_futures_trade(symbol, side, position['amount'], current_price)
                self.close_futures_position(symbol, current_price)
                logger.warning(f"선물 손절매 실행: {symbol} ({loss_pct:.2%})")
    
    def rebalance_portfolio(self) -> None:
        """포트폴리오 리밸런싱"""
        # 현재 잔고 업데이트
        current_spot_balance = self.get_spot_balance()
        current_futures_balance = self.get_futures_balance()
        total_balance = current_spot_balance + current_futures_balance
        
        # 목표 비율과 현재 비율 비교
        current_spot_ratio = current_spot_balance / total_balance if total_balance > 0 else 0
        current_futures_ratio = current_futures_balance / total_balance if total_balance > 0 else 0
        
        target_spot_ratio = self.strategy_config['spot_allocation']
        target_futures_ratio = self.strategy_config['futures_allocation']
        
        spot_diff = abs(current_spot_ratio - target_spot_ratio)
        futures_diff = abs(current_futures_ratio - target_futures_ratio)
        
        # 리밸런싱 필요 여부 확인
        if spot_diff > self.strategy_config['rebalance_threshold'] or futures_diff > self.strategy_config['rebalance_threshold']:
            logger.info(f"포트폴리오 리밸런싱 필요: 현물 {current_spot_ratio:.2%} -> {target_spot_ratio:.2%}")
            # 실제 리밸런싱 로직 구현 (자금 이동 등)
            # 여기서는 로그만 출력
    
    def run_hybrid_strategy(self) -> None:
        """하이브리드 전략 실행"""
        logger.info("하이브리드 트레이딩 전략 시작")
        
        iteration = 0
        while True:
            try:
                iteration += 1
                logger.info(f"=== 전략 실행 {iteration}회차 ===")
                
                # 각 심볼에 대해 페어 트레이딩 전략 실행
                for symbol in self.symbols:
                    self.implement_pairs_trading_strategy(symbol)
                    time.sleep(1)  # API 호출 간격 조절
                
                # 리스크 관리
                self.manage_risk()
                
                # 포트폴리오 리밸런싱 (10회차마다)
                if iteration % 10 == 0:
                    self.rebalance_portfolio()
                
                # 성과 보고 (20회차마다)
                if iteration % 20 == 0:
                    self.report_performance()
                
                # 대기 시간 (5분)
                logger.info("5분 대기...")
                time.sleep(300)
                
            except KeyboardInterrupt:
                logger.info("전략 중단됨")
                break
            except Exception as e:
                logger.error(f"전략 실행 중 오류 발생: {e}")
                time.sleep(60)  # 오류 발생 시 1분 대기
    
    def report_performance(self) -> None:
        """성과 보고"""
        current_spot_balance = self.get_spot_balance()
        current_futures_balance = self.get_futures_balance()
        total_balance = current_spot_balance + current_futures_balance
        
        total_pnl = total_balance - self.initial_balance
        total_pnl_pct = (total_pnl / self.initial_balance) * 100 if self.initial_balance > 0 else 0
        
        logger.info("=" * 50)
        logger.info("하이브리드 트레이딩 성과 보고")
        logger.info("=" * 50)
        logger.info(f"시작 자금: {self.initial_balance:,.0f} USDT")
        logger.info(f"현재 자금: {total_balance:,.0f} USDT")
        logger.info(f"  - 현물 잔고: {current_spot_balance:,.0f} USDT")
        logger.info(f"  - 선물 잔고: {current_futures_balance:,.0f} USDT")
        logger.info(f"총 수익: {total_pnl:+,.0f} USDT ({total_pnl_pct:+.2f}%)")
        logger.info(f"활성 포지션:")
        logger.info(f"  - 현물 포지션: {len(self.spot_positions)}개")
        logger.info(f"  - 선물 포지션: {len(self.futures_positions)}개")
        logger.info(f"총 거래 수: {len(self.trade_history)}회")
        
        if self.trade_history:
            profitable_trades = sum(1 for trade in self.trade_history if trade['pnl'] > 0)
            win_rate = (profitable_trades / len(self.trade_history)) * 100
            logger.info(f"승률: {win_rate:.1f}% ({profitable_trades}/{len(self.trade_history)})")
        
        logger.info("=" * 50)

# 실행 함수
def main():
    """메인 실행 함수"""
    # 환경 변수에서 API 키 로드
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_SECRET_KEY')
    
    if not api_key or not api_secret:
        logger.error("API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")
        return
    
    # 실제 거래 확인
    confirmation = input("실제 거래를 시작하시겠습니까? (YES 입력): ")
    if confirmation != "YES":
        logger.info("거래가 취소되었습니다.")
        return
    
    # 봇 초기화 및 실행
    bot = HybridTradingBot(api_key, api_secret, use_testnet=False)
    bot.run_hybrid_strategy()

if __name__ == "__main__":
    main()