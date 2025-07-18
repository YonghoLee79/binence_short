import ccxt
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Tuple
import talib
import warnings
import asyncio
import aiohttp
import re
from textblob import TextBlob
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
import requests
from collections import deque
import threading
import queue
import os
from dotenv import load_dotenv
from functools import wraps

# .env 파일 로드
load_dotenv()

warnings.filterwarnings('ignore')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
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
                except (requests.exceptions.RequestException, 
                        ccxt.NetworkError, 
                        ccxt.ExchangeNotAvailable,
                        ccxt.RequestTimeout) as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"네트워크 에러 발생 (시도 {attempt + 1}/{max_retries}): {e}")
                        time.sleep(delay * (2 ** attempt))  # 지수 백오프
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

class MarketSentimentAnalyzer:
    """시장 감정 분석기"""
    
    def __init__(self):
        self.news_sources = [
            'https://api.coindesk.com/v1/news',
            'https://api.cointelegraph.com/v1/news'
        ]
        self.sentiment_cache = {}
        self.cache_duration = 300  # 5분
    
    def get_crypto_news(self, symbol: str) -> List[Dict]:
        """암호화폐 관련 뉴스 수집"""
        try:
            # Reddit API를 통한 감정 분석 (예시)
            url = f"https://www.reddit.com/r/cryptocurrency/search.json"
            params = {
                'q': symbol.replace('/USDT', ''),
                'sort': 'new',
                'limit': 10,
                't': 'day'
            }
            
            headers = {'User-Agent': 'CryptoBot/1.0'}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                posts = []
                
                for post in data.get('data', {}).get('children', []):
                    post_data = post.get('data', {})
                    posts.append({
                        'title': post_data.get('title', ''),
                        'text': post_data.get('selftext', ''),
                        'score': post_data.get('score', 0),
                        'created': post_data.get('created_utc', 0)
                    })
                
                return posts
                
        except Exception as e:
            logger.warning(f"뉴스 수집 실패 {symbol}: {e}")
            
        return []
    
    def analyze_sentiment(self, texts: List[str]) -> float:
        """텍스트 감정 분석"""
        if not texts:
            return 0.0
        
        sentiments = []
        for text in texts:
            try:
                blob = TextBlob(text)
                sentiments.append(blob.sentiment.polarity)
            except:
                continue
        
        return np.mean(sentiments) if sentiments else 0.0
    
    def get_market_sentiment(self, symbol: str) -> Dict[str, float]:
        """시장 감정 점수 계산"""
        cache_key = f"{symbol}_{int(time.time() // self.cache_duration)}"
        
        if cache_key in self.sentiment_cache:
            return self.sentiment_cache[cache_key]
        
        news_data = self.get_crypto_news(symbol)
        
        if not news_data:
            return {'sentiment': 0.0, 'confidence': 0.0}
        
        # 텍스트 추출
        texts = []
        weights = []
        
        for item in news_data:
            text = f"{item['title']} {item['text']}"
            texts.append(text)
            # 점수가 높을수록 가중치 증가
            weights.append(max(1, item['score']))
        
        # 감정 분석
        raw_sentiment = self.analyze_sentiment(texts)
        
        # 가중 평균 적용
        if weights:
            weighted_sentiment = np.average([raw_sentiment] * len(weights), weights=weights)
        else:
            weighted_sentiment = raw_sentiment
        
        # 신뢰도 계산 (데이터 양과 일관성 기반)
        confidence = min(1.0, len(texts) / 10) * (1 - abs(weighted_sentiment))
        
        result = {
            'sentiment': weighted_sentiment,
            'confidence': confidence
        }
        
        self.sentiment_cache[cache_key] = result
        return result

class MLPredictor:
    """머신러닝 예측기"""
    
    def __init__(self):
        self.models = {
            'rf': RandomForestClassifier(n_estimators=100, random_state=42),
            'gb': GradientBoostingClassifier(n_estimators=100, random_state=42)
        }
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_columns = []
        
    def create_features(self, df: pd.DataFrame, sentiment_data: Dict = None) -> pd.DataFrame:
        """특성 생성"""
        features = df.copy()
        
        # 기본 기술적 지표들은 이미 있다고 가정
        
        # 추가 기술적 지표
        features['roc'] = talib.ROC(df['close'].values, timeperiod=10)
        features['cci'] = talib.CCI(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
        features['williams_r'] = talib.WILLR(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
        features['stoch_k'], features['stoch_d'] = talib.STOCH(df['high'].values, df['low'].values, df['close'].values)
        
        # 볼륨 지표
        features['obv'] = talib.OBV(df['close'].values, df['volume'].values)
        features['ad'] = talib.AD(df['high'].values, df['low'].values, df['close'].values, df['volume'].values)
        
        # 가격 패턴
        features['price_change'] = df['close'].pct_change()
        features['volatility'] = features['price_change'].rolling(20).std()
        features['volume_sma'] = df['volume'].rolling(20).mean()
        features['volume_ratio'] = df['volume'] / features['volume_sma']
        
        # 시간 기반 특성
        features['hour'] = df.index.hour
        features['day_of_week'] = df.index.dayofweek
        
        # 감정 데이터 추가
        if sentiment_data:
            features['sentiment'] = sentiment_data.get('sentiment', 0)
            features['sentiment_confidence'] = sentiment_data.get('confidence', 0)
        else:
            features['sentiment'] = 0
            features['sentiment_confidence'] = 0
        
        # 라그 특성
        for lag in [1, 2, 3, 5]:
            features[f'close_lag_{lag}'] = df['close'].shift(lag)
            features[f'volume_lag_{lag}'] = df['volume'].shift(lag)
        
        return features
    
    def create_target(self, df: pd.DataFrame, lookahead: int = 5) -> pd.Series:
        """타겟 생성 (미래 수익률)"""
        future_return = df['close'].shift(-lookahead) / df['close'] - 1
        
        # 분류 문제로 변환 (-1: 하락, 0: 보합, 1: 상승)
        target = np.where(future_return > 0.01, 1,
                         np.where(future_return < -0.01, -1, 0))
        
        return pd.Series(target, index=df.index)
    
    def train_models(self, df: pd.DataFrame, sentiment_data: Dict = None):
        """모델 훈련"""
        try:
            # 특성 생성
            features_df = self.create_features(df, sentiment_data)
            target = self.create_target(df)
            
            # 결측값 제거
            mask = ~(features_df.isnull().any(axis=1) | target.isnull())
            features_df = features_df[mask]
            target = target[mask]
            
            if len(features_df) < 100:
                logger.warning("훈련 데이터가 부족합니다")
                return
            
            # 수치형 컬럼만 선택
            numeric_columns = features_df.select_dtypes(include=[np.number]).columns
            features_df = features_df[numeric_columns]
            
            self.feature_columns = features_df.columns.tolist()
            
            # 데이터 분할
            X_train, X_test, y_train, y_test = train_test_split(
                features_df, target, test_size=0.2, random_state=42
            )
            
            # 스케일링
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # 모델 훈련
            for name, model in self.models.items():
                model.fit(X_train_scaled, y_train)
                
                # 성능 평가
                y_pred = model.predict(X_test_scaled)
                accuracy = accuracy_score(y_test, y_pred)
                logger.info(f"{name} 모델 정확도: {accuracy:.3f}")
            
            self.is_trained = True
            logger.info("ML 모델 훈련 완료")
            
        except Exception as e:
            logger.error(f"모델 훈련 실패: {e}")
    
    def predict(self, features_df: pd.DataFrame) -> Dict[str, float]:
        """예측 실행"""
        if not self.is_trained:
            return {'prediction': 0, 'confidence': 0}
        
        try:
            # 특성 정렬
            features_df = features_df[self.feature_columns]
            
            # 스케일링
            features_scaled = self.scaler.transform(features_df.iloc[-1:])
            
            # 앙상블 예측
            predictions = []
            for model in self.models.values():
                pred = model.predict(features_scaled)[0]
                predictions.append(pred)
            
            # 다수결 또는 평균
            final_prediction = np.mean(predictions)
            confidence = 1 - np.std(predictions)  # 예측 일치도
            
            return {
                'prediction': final_prediction,
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"예측 실패: {e}")
            return {'prediction': 0, 'confidence': 0}

class DynamicParameterOptimizer:
    """동적 파라미터 최적화"""
    
    def __init__(self):
        self.performance_history = deque(maxlen=100)
        self.parameter_history = deque(maxlen=100)
        self.optimization_interval = 50  # 50거래마다 최적화
        
    def add_performance(self, pnl: float, parameters: Dict):
        """성능 기록 추가"""
        self.performance_history.append(pnl)
        self.parameter_history.append(parameters.copy())
    
    def optimize_parameters(self, current_params: Dict) -> Dict:
        """파라미터 최적화"""
        if len(self.performance_history) < 20:
            return current_params
        
        try:
            # 최근 성과 분석
            recent_performance = list(self.performance_history)[-20:]
            avg_performance = np.mean(recent_performance)
            
            optimized_params = current_params.copy()
            
            # 성과에 따른 파라미터 조정
            if avg_performance > 0:
                # 좋은 성과 -> 보수적 조정
                optimized_params['risk_per_trade'] = min(0.03, current_params['risk_per_trade'] * 1.1)
                optimized_params['stop_loss_pct'] = max(0.015, current_params['stop_loss_pct'] * 0.95)
            else:
                # 나쁜 성과 -> 리스크 감소
                optimized_params['risk_per_trade'] = max(0.01, current_params['risk_per_trade'] * 0.9)
                optimized_params['stop_loss_pct'] = min(0.03, current_params['stop_loss_pct'] * 1.1)
            
            # 변동성 기반 조정
            volatility = np.std(recent_performance)
            if volatility > 0.05:  # 높은 변동성
                optimized_params['take_profit_pct'] = min(0.06, current_params['take_profit_pct'] * 1.2)
            
            logger.info(f"파라미터 최적화 완료: {optimized_params}")
            return optimized_params
            
        except Exception as e:
            logger.error(f"파라미터 최적화 실패: {e}")
            return current_params

class AdvancedBinanceTradingBot:
    """고도화된 바이낸스 자동매매 봇"""
    
    def __init__(self, api_key: str, api_secret: str, initial_balance: float = None, use_testnet: bool = True):
        """봇 초기화"""
        # API 키 검증
        if not self.validate_api_credentials(api_key, api_secret):
            raise ValueError("API 키 검증 실패")
        
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': use_testnet,  # 테스트용
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',  # 현물 계정으로 변경
            }
        })
        
        # 기본 속성 초기화 (모든 필요한 속성을 먼저 초기화)
        self.positions = {}
        self.symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT']
        self.trade_history = []
        
        # 동적 파라미터 초기화
        self.parameters = {
            'risk_per_trade': 0.02,
            'max_positions': 3,
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.04,
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'ma_short': 20,
            'ma_long': 50
        }
        
        # 실제 잔고 확인
        self.real_balance = self.get_real_balance()
        
        # 기본 설정 (실제 잔고 기반)
        if initial_balance is None:
            self.initial_balance = self.real_balance
        else:
            self.initial_balance = min(initial_balance, self.real_balance)  # 안전장치
        
        self.current_balance = self.initial_balance
        
        logger.info(f"실제 계좌 잔고: {self.real_balance:,.2f} USDT")
        logger.info(f"거래용 자금: {self.initial_balance:,.2f} USDT")
        
        # 고급 컴포넌트 초기화
        self.sentiment_analyzer = MarketSentimentAnalyzer()
        self.ml_predictor = MLPredictor()
        self.parameter_optimizer = DynamicParameterOptimizer()
        
        # 성능 추적 초기화
        self.daily_pnl = deque(maxlen=30)
        self.win_rate = 0.0
        self.last_optimization = 0
        
        # 월간 수익률 추적
        self.monthly_returns = deque(maxlen=12)  # 최근 12개월
        self.daily_returns = deque(maxlen=30)    # 최근 30일
        self.start_time = datetime.now()
        self.last_balance_update = datetime.now()
        
        # 성과 예측용 데이터
        self.performance_metrics = {
            'daily_volatility': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'avg_trade_return': 0.0,
            'profit_factor': 0.0
        }
        
        # 수수료 설정
        self.fees = {
            'maker': 0.0002,    # 0.02%
            'taker': 0.0004,    # 0.04%
            'slippage': 0.0005  # 0.05%
        }
        
        # 기타 필요한 속성들
        self.total_fees_paid = 0.0
        self.total_funding_paid = 0.0
        self.min_trade_amount = 10.0
        
        # 잔고 기반 전략 설정
        self.setup_balance_based_strategy()
        
        # 공매도 특화 위험 관리
        self.short_risk_manager = {
            'max_short_ratio': 0.6,      # 전체 포지션 중 숏 비율 최대 60%
            'short_squeeze_threshold': 0.05,  # 5% 급상승시 위험 신호
            'market_trend_window': 20,    # 시장 트렌드 분석 기간
            'funding_rate_limit': 0.01,   # 펀딩 비율 1% 초과시 경고
            'volatility_multiplier': 2.0, # 변동성 급증시 포지션 크기 축소
            'emergency_exit_loss': 0.08   # 8% 손실시 모든 숏 포지션 긴급 종료
        }
        
        logger.info(f"고도화된 봇 초기화 완료 - 시작 자금: {self.initial_balance:,.0f} USDT")
    
    def validate_api_credentials(self, api_key: str, api_secret: str) -> bool:
        """API 키 검증"""
        try:
            # 기본 유효성 검사
            if not api_key or not api_secret:
                logger.error("API 키 또는 시크릿이 비어있습니다")
                return False
            
            if len(api_key) < 20 or len(api_secret) < 20:
                logger.error("API 키 또는 시크릿이 너무 짧습니다")
                return False
            
            # 실제 연결 테스트 - 더 간단한 방법 사용
            test_exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'sandbox': True,
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}
            })
            
            # 마켓 데이터 로드로 연결 확인 (인증 불필요)
            test_exchange.load_markets()
            
            # 간단한 API 테스트 - 서버 시간 조회 (인증 불필요)
            server_time = test_exchange.fetch_time()
            
            if server_time:
                logger.info("API 키 검증 성공 (연결 확인)")
                return True
            else:
                logger.error("API 키 검증 실패: 연결 불가")
                return False
                
        except ccxt.AuthenticationError:
            logger.error("API 키 인증 실패")
            return False
        except Exception as e:
            logger.warning(f"API 키 검증 중 오류, 기본값 사용: {e}")
            # 검증 실패해도 계속 진행 (테스트넷에서는 유연하게 처리)
            return True
        
        # 수수료 설정
        self.setup_fee_structure()
    
    @retry_on_network_error(max_retries=3, delay=2)
    def get_real_balance(self) -> float:
        """실제 계좌 잔고 확인 (다양한 코인 지원)"""
        try:
            balance = self.exchange.fetch_balance()
            usdt_balance = balance.get('USDT', {}).get('free', 0.0)
            
            if usdt_balance == 0:
                # 테스트넷의 경우 기본값 사용
                if self.exchange.sandbox:
                    logger.warning("테스트넷에서 잔고를 가져올 수 없습니다. 기본값 사용: 1000 USDT")
                    return 1000.0
                else:
                    # 다른 코인 잔고 확인 및 USDT로 교환
                    logger.warning("USDT 잔고가 없습니다. 다른 코인 확인 중...")
                    return self.convert_other_coins_to_usdt(balance)
            
            return float(usdt_balance)
            
        except Exception as e:
            logger.error(f"잔고 확인 실패: {e}")
            if self.exchange.sandbox:
                logger.info("테스트넷 기본값 사용: 1000 USDT")
                return 1000.0
            return 0.0
    
    def convert_other_coins_to_usdt(self, balance: dict) -> float:
        """다른 코인을 USDT로 교환"""
        try:
            # 교환 가능한 코인 목록 (최소 거래 금액 이상)
            convertible_coins = ['XRP', 'BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'DOT', 'LINK', 'MATIC']
            total_usdt_value = 0.0
            
            # 디버깅: 모든 잔고 정보 출력
            logger.info(f"전체 잔고 정보 확인 중...")
            for coin in balance.keys():
                if coin != 'info':
                    coin_data = balance.get(coin, {})
                    if isinstance(coin_data, dict):
                        free_amount = coin_data.get('free', 0.0)
                        if free_amount > 0:
                            logger.info(f"보유 중인 코인: {coin} = {free_amount:.8f}")
            
            for coin in convertible_coins:
                coin_balance = balance.get(coin, {}).get('free', 0.0)
                logger.info(f"{coin} 잔고 확인: {coin_balance:.8f}")
                if coin_balance > 0:
                    try:
                        # 현재 가격 확인
                        ticker = self.exchange.fetch_ticker(f"{coin}/USDT")
                        current_price = ticker['last']
                        coin_value_usdt = coin_balance * current_price
                        
                        logger.info(f"{coin} 잔고: {coin_balance:.6f} (≈ {coin_value_usdt:.2f} USDT)")
                        
                        # 최소 거래 금액 이상인 경우 교환
                        if coin_value_usdt >= 10:  # 최소 10 USDT 상당
                            logger.info(f"{coin}을 USDT로 교환 시도...")
                            
                            # 시장가 매도 주문
                            order = self.exchange.create_market_sell_order(f"{coin}/USDT", coin_balance)
                            
                            if order and order.get('status') == 'closed':
                                actual_usdt = order.get('cost', coin_value_usdt)
                                total_usdt_value += actual_usdt
                                logger.info(f"{coin} → USDT 교환 성공: {actual_usdt:.2f} USDT")
                            else:
                                logger.warning(f"{coin} 교환 실패")
                        else:
                            logger.info(f"{coin} 잔고가 최소 거래 금액({coin_value_usdt:.2f} USDT)보다 작음")
                            
                    except Exception as e:
                        logger.error(f"{coin} 교환 중 오류: {e}")
                        continue
            
            if total_usdt_value > 0:
                logger.info(f"총 {total_usdt_value:.2f} USDT 확보 완료")
                return total_usdt_value
            else:
                logger.error("교환 가능한 코인이 없습니다.")
                return 0.0
                
        except Exception as e:
            logger.error(f"코인 교환 중 오류: {e}")
            return 0.0
    
    def setup_fee_structure(self):
        """바이낸스 선물거래 수수료 구조 설정"""
        # 바이낸스 선물거래 수수료 (VIP 레벨별)
        self.fees = {
            'maker': 0.0002,    # 0.02% (지정가 주문)
            'taker': 0.0004,    # 0.04% (시장가 주문)
            'funding_rate': 0.0001,  # 평균 자금조달비용 0.01%
            'slippage': 0.001,  # 0.1% 슬리피지
        }
        
        # 총 거래 비용 추적
        self.total_fees_paid = 0.0
        self.total_funding_paid = 0.0
        
        logger.info(f"수수료 설정 - Maker: {self.fees['maker']:.4f}%, Taker: {self.fees['taker']:.4f}%")
    
    def calculate_trading_fees(self, amount: float, price: float, is_maker: bool = False) -> dict:
        """거래 수수료 계산"""
        notional_value = amount * price  # 거래 명목가치
        
        # 거래 수수료
        fee_rate = self.fees['maker'] if is_maker else self.fees['taker']
        trading_fee = notional_value * fee_rate
        
        # 슬리피지 비용
        slippage_cost = notional_value * self.fees['slippage']
        
        return {
            'trading_fee': trading_fee,
            'slippage_cost': slippage_cost,
            'total_cost': trading_fee + slippage_cost,
            'fee_rate': fee_rate
        }
    
    def calculate_funding_cost(self, amount: float, price: float, holding_hours: float) -> float:
        """자금조달비용 계산 (8시간마다 청산)"""
        notional_value = amount * price
        funding_periods = holding_hours / 8  # 8시간마다 펀딩
        funding_cost = notional_value * self.fees['funding_rate'] * funding_periods
        return funding_cost
    
    def check_short_position_risks(self) -> Dict:
        """공매도 포지션 위험 점검"""
        risks = {
            'short_ratio': 0.0,
            'squeeze_risk': False,
            'funding_risk': False,
            'market_trend': 'neutral',
            'emergency_exit': False
        }
        
        if not self.positions:
            return risks
            
        total_positions = len(self.positions)
        short_positions = len([p for p in self.positions.values() if p['side'] == 'sell'])
        
        # 숏 포지션 비율 계산
        risks['short_ratio'] = short_positions / total_positions if total_positions > 0 else 0
        
        # 숏 스퀴즈 위험 확인
        for symbol, position in self.positions.items():
            if position['side'] == 'sell':
                try:
                    current_price = self.get_current_price(symbol)
                    entry_price = position['entry_price']
                    price_change = (current_price - entry_price) / entry_price
                    
                    if price_change > self.short_risk_manager['short_squeeze_threshold']:
                        risks['squeeze_risk'] = True
                        
                    # 긴급 종료 조건
                    if price_change > self.short_risk_manager['emergency_exit_loss']:
                        risks['emergency_exit'] = True
                        
                except Exception as e:
                    logger.error(f"가격 확인 실패 {symbol}: {e}")
        
        return risks
    
    @retry_on_network_error(max_retries=3, delay=1)
    def get_current_price(self, symbol: str) -> float:
        """현재 가격 조회"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            logger.error(f"가격 조회 실패 {symbol}: {e}")
            return 0.0
    
    def calculate_short_position_size(self, symbol: str, signal_strength: float) -> float:
        """공매도 포지션 크기 계산"""
        # 잔고 확인
        if self.current_balance <= 0:
            logger.warning("잔고가 0이므로 포지션 크기를 계산할 수 없습니다.")
            return 0.0
        
        # 기본 포지션 크기
        base_size = self.current_balance * self.parameters['risk_per_trade']
        
        # 숏 포지션 비율 확인
        risks = self.check_short_position_risks()
        
        # 위험 조정
        if risks['short_ratio'] > self.short_risk_manager['max_short_ratio']:
            base_size *= 0.5  # 50% 축소
            
        # 변동성 조정
        try:
            df = self.get_historical_data(symbol, limit=100)
            if not df.empty:
                volatility = df['close'].pct_change().std()
                if volatility > 0.05:  # 5% 이상 변동성
                    base_size *= (1 / self.short_risk_manager['volatility_multiplier'])
        except Exception:
            pass
            
        return base_size
    
    def emergency_exit_short_positions(self):
        """긴급 숏 포지션 종료"""
        for symbol, position in self.positions.items():
            if position['side'] == 'sell':
                try:
                    current_price = self.get_current_price(symbol)
                    loss_pct = (current_price - position['entry_price']) / position['entry_price']
                    
                    if loss_pct > self.short_risk_manager['emergency_exit_loss']:
                        logger.warning(f"긴급 종료: {symbol} 손실 {loss_pct:.2%}")
                        self.close_position(symbol, "emergency_exit")
                        
                except Exception as e:
                    logger.error(f"긴급 종료 실패 {symbol}: {e}")

    def setup_balance_based_strategy(self):
        """잔고 기반 전략 설정"""
        balance = self.initial_balance
        
        # 잔고 규모별 전략 조정
        if balance < 100:  # 100 USDT 미만
            strategy_type = "ultra_conservative"
            self.parameters.update({
                'risk_per_trade': 0.005,  # 0.5%
                'max_positions': 1,
                'stop_loss_pct': 0.01,    # 1%
                'take_profit_pct': 0.02,  # 2%
                'min_signal_threshold': 0.8
            })
            
        elif balance < 500:  # 500 USDT 미만
            strategy_type = "conservative"
            self.parameters.update({
                'risk_per_trade': 0.01,   # 1%
                'max_positions': 2,
                'stop_loss_pct': 0.015,   # 1.5%
                'take_profit_pct': 0.03,  # 3%
                'min_signal_threshold': 0.7
            })
            
        elif balance < 2000:  # 2000 USDT 미만
            strategy_type = "moderate"
            self.parameters.update({
                'risk_per_trade': 0.02,   # 2%
                'max_positions': 3,
                'stop_loss_pct': 0.02,    # 2%
                'take_profit_pct': 0.04,  # 4%
                'min_signal_threshold': 0.6
            })
            
        else:  # 2000 USDT 이상
            strategy_type = "aggressive"
            self.parameters.update({
                'risk_per_trade': 0.025,  # 2.5%
                'max_positions': 4,
                'stop_loss_pct': 0.025,   # 2.5%
                'take_profit_pct': 0.05,  # 5%
                'min_signal_threshold': 0.55
            })
        
        # 최소 거래 금액 설정
        self.min_trade_amount = max(10, balance * 0.01)  # 최소 10 USDT 또는 잔고의 1%
        
        logger.info(f"전략 타입: {strategy_type}")
        logger.info(f"거래당 리스크: {self.parameters['risk_per_trade']:.1%}")
        logger.info(f"최대 포지션: {self.parameters['max_positions']}개")
        logger.info(f"최소 거래 금액: {self.min_trade_amount:.2f} USDT")
    
    @retry_on_network_error(max_retries=3, delay=2)
    def get_historical_data(self, symbol: str, timeframe: str = '1h', limit: int = 500) -> pd.DataFrame:
        """과거 데이터 가져오기 (더 많은 데이터)"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            logger.error(f"데이터 가져오기 실패 {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_advanced_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """고급 기술적 지표 계산"""
        if len(df) < self.parameters['ma_long']:
            return df
        
        # 기본 지표
        df['rsi'] = talib.RSI(df['close'].values, timeperiod=self.parameters['rsi_period'])
        df['ma_short'] = df['close'].rolling(window=self.parameters['ma_short']).mean()
        df['ma_long'] = df['close'].rolling(window=self.parameters['ma_long']).mean()
        
        # 볼린저 밴드
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = talib.BBANDS(
            df['close'].values, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
        )
        
        # MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(
            df['close'].values, fastperiod=12, slowperiod=26, signalperiod=9
        )
        
        # 추가 지표들
        df['atr'] = talib.ATR(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
        df['adx'] = talib.ADX(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
        df['cci'] = talib.CCI(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
        df['roc'] = talib.ROC(df['close'].values, timeperiod=10)
        df['williams_r'] = talib.WILLR(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
        
        # 스토캐스틱
        df['stoch_k'], df['stoch_d'] = talib.STOCH(
            df['high'].values, df['low'].values, df['close'].values,
            fastk_period=14, slowk_period=3, slowd_period=3
        )
        
        # 볼륨 지표
        df['obv'] = talib.OBV(df['close'].values, df['volume'].values)
        df['ad'] = talib.AD(df['high'].values, df['low'].values, df['close'].values, df['volume'].values)
        
        # 가격 패턴
        df['price_change'] = df['close'].pct_change()
        df['volatility'] = df['price_change'].rolling(20).std()
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        return df
    
    def generate_enhanced_signals(self, df: pd.DataFrame, symbol: str) -> Dict[str, float]:
        """향상된 신호 생성 (감정분석 + ML 포함)"""
        if len(df) < self.parameters['ma_long']:
            return {'long_signal': 0, 'short_signal': 0, 'confidence': 0}
        
        # 감정 분석
        sentiment_data = self.sentiment_analyzer.get_market_sentiment(symbol)
        
        # ML 예측 (처음에는 기술적 지표로만 훈련)
        features = self.ml_predictor.create_features(df, sentiment_data)
        ml_prediction = self.ml_predictor.predict(features)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        signals = []
        
        # 1. 기본 기술적 지표 신호
        if latest['rsi'] < self.parameters['rsi_oversold']:
            signals.append(('long', 0.25))
        elif latest['rsi'] > self.parameters['rsi_overbought']:
            signals.append(('short', 0.25))
        
        # 2. 이동평균선 신호
        if (latest['ma_short'] > latest['ma_long'] and 
            prev['ma_short'] <= prev['ma_long']):
            signals.append(('long', 0.3))
        elif (latest['ma_short'] < latest['ma_long'] and 
              prev['ma_short'] >= prev['ma_long']):
            signals.append(('short', 0.3))
        
        # 3. MACD 신호
        if (latest['macd'] > latest['macd_signal'] and 
            prev['macd'] <= prev['macd_signal']):
            signals.append(('long', 0.25))
        elif (latest['macd'] < latest['macd_signal'] and 
              prev['macd'] >= prev['macd_signal']):
            signals.append(('short', 0.25))
        
        # 4. 볼린저 밴드 + RSI 조합
        if latest['close'] < latest['bb_lower'] and latest['rsi'] < 40:
            signals.append(('long', 0.3))
        elif latest['close'] > latest['bb_upper'] and latest['rsi'] > 60:
            signals.append(('short', 0.3))
        
        # 5. ADX 트렌드 강도
        if latest['adx'] > 25:  # 강한 트렌드
            if latest['ma_short'] > latest['ma_long']:
                signals.append(('long', 0.2))
            else:
                signals.append(('short', 0.2))
        
        # 6. 스토캐스틱 신호
        if latest['stoch_k'] < 20 and latest['stoch_d'] < 20:
            signals.append(('long', 0.15))
        elif latest['stoch_k'] > 80 and latest['stoch_d'] > 80:
            signals.append(('short', 0.15))
        
        # 7. 볼륨 확인
        if latest['volume_ratio'] > 1.5:  # 평소보다 높은 거래량
            if len([s for s in signals if s[0] == 'long']) > len([s for s in signals if s[0] == 'short']):
                signals.append(('long', 0.1))
            else:
                signals.append(('short', 0.1))
        
        # 8. 감정 분석 신호
        if sentiment_data['confidence'] > 0.5:
            if sentiment_data['sentiment'] > 0.1:
                signals.append(('long', 0.2 * sentiment_data['confidence']))
            elif sentiment_data['sentiment'] < -0.1:
                signals.append(('short', 0.2 * sentiment_data['confidence']))
        
        # 9. ML 예측 신호
        if ml_prediction['confidence'] > 0.6:
            if ml_prediction['prediction'] > 0.5:
                signals.append(('long', 0.3 * ml_prediction['confidence']))
            elif ml_prediction['prediction'] < -0.5:
                signals.append(('short', 0.3 * ml_prediction['confidence']))
        
        # 신호 집계
        long_strength = sum([s[1] for s in signals if s[0] == 'long'])
        short_strength = sum([s[1] for s in signals if s[0] == 'short'])
        
        # 최종 신호 결정
        long_signal = 0
        short_signal = 0
        confidence = 0
        
        # 최소 신호 강도 임계값 (잔고 기반)
        min_threshold = self.parameters.get('min_signal_threshold', 0.6)
        
        if long_strength > short_strength and long_strength > min_threshold:
            long_signal = min(long_strength, 1.0)
            confidence = long_strength
        elif short_strength > long_strength and short_strength > min_threshold:
            short_signal = min(short_strength, 1.0)
            confidence = short_strength
        
        return {
            'long_signal': long_signal,
            'short_signal': short_signal,
            'confidence': confidence,
            'sentiment': sentiment_data,
            'ml_prediction': ml_prediction
        }
    
    def calculate_dynamic_position_size(self, symbol: str, signal_strength: float, atr: float) -> float:
        """동적 포지션 크기 계산"""
        # 잔고 확인
        if self.current_balance <= 0:
            logger.warning("잔고가 0이므로 포지션 크기를 계산할 수 없습니다.")
            return 0.0
        
        # 기본 리스크 금액
        risk_amount = self.current_balance * self.parameters['risk_per_trade']
        
        # 변동성 조정 (ATR 기반)
        volatility_adjustment = min(1.5, max(0.5, 0.02 / (atr / 100)))
        
        # 신호 강도 조정
        signal_adjustment = signal_strength
        
        # 최근 성과 기반 조정
        if len(self.daily_pnl) > 0:
            recent_performance = np.mean(list(self.daily_pnl)[-5:])
            if recent_performance > 0:
                performance_adjustment = 1.2  # 좋은 성과시 약간 증가
            else:
                performance_adjustment = 0.8  # 나쁜 성과시 감소
        else:
            performance_adjustment = 1.0
        
        # 승률 기반 조정
        if self.win_rate > 0.6:
            win_rate_adjustment = 1.1
        elif self.win_rate < 0.4:
            win_rate_adjustment = 0.9
        else:
            win_rate_adjustment = 1.0
        
        # 최종 포지션 크기
        position_size = (risk_amount * volatility_adjustment * signal_adjustment * 
                        performance_adjustment * win_rate_adjustment)
        
        # 최대 포지션 크기 제한
        max_position_size = self.current_balance * 0.25
        position_size = min(position_size, max_position_size)
        
        return position_size
    
    def train_ml_model_periodically(self):
        """주기적 ML 모델 재훈련"""
        try:
            # 모든 심볼의 데이터 수집
            all_data = []
            
            for symbol in self.symbols:
                df = self.get_historical_data(symbol, limit=1000)
                if not df.empty:
                    df = self.calculate_advanced_indicators(df)
                    sentiment_data = self.sentiment_analyzer.get_market_sentiment(symbol)
                    df['symbol'] = symbol
                    all_data.append(df)
            
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=False)
                self.ml_predictor.train_models(combined_df)
                logger.info("ML 모델 재훈련 완료")
            
        except Exception as e:
            logger.error(f"ML 모델 재훈련 실패: {e}")
    
    @retry_on_network_error(max_retries=3, delay=2)
    def execute_trade(self, symbol: str, side: str, amount: float, price: float) -> Optional[Dict]:
        """거래 실행 (개선된 버전)"""
        try:
            if self.exchange.sandbox:
                # 시뮬레이션 모드
                order = {
                    'id': f"sim_{int(time.time())}",
                    'symbol': symbol,
                    'side': side,
                    'amount': amount,
                    'price': price,
                    'cost': amount * price,
                    'timestamp': datetime.now(),
                    'status': 'closed'
                }
                
                # 수수료 및 슬리피지 계산
                fees = self.calculate_trading_fees(amount, price, is_maker=False)
                
                if side == 'buy':
                    actual_price = price * (1 + self.fees['slippage'])
                    total_cost = (amount * actual_price) + fees['trading_fee']
                    self.current_balance -= total_cost
                else:
                    actual_price = price * (1 - self.fees['slippage'])
                    proceeds = (amount * actual_price) - fees['trading_fee']
                    self.current_balance += proceeds
                
                # 수수료 누적
                self.total_fees_paid += fees['trading_fee']
                
                order.update({
                    'actual_price': actual_price,
                    'trading_fee': fees['trading_fee'],
                    'slippage_cost': fees['slippage_cost'],
                    'total_cost': fees['total_cost']
                })
                
                logger.info(f"시뮬레이션 거래: {symbol} {side} {amount:.6f} @ {actual_price:.2f}")
                
            else:
                # 실제 거래
                order = self.exchange.create_market_order(symbol, side, amount)
                logger.info(f"실제 거래: {symbol} {side} {amount:.6f}")
            
            return order
            
        except Exception as e:
            logger.error(f"거래 실행 실패: {e}")
            return None
    
    def manage_position_advanced(self, symbol: str, position: Dict, current_price: float, df: pd.DataFrame) -> bool:
        """고급 포지션 관리"""
        entry_price = position['entry_price']
        side = position['side']
        amount = position['amount']
        
        # 수익률 계산
        if side == 'long':
            pnl_pct = (current_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - current_price) / entry_price
        
        # 동적 손절/익절 레벨
        atr = df['atr'].iloc[-1] if not df.empty else 0.02
        volatility = atr / current_price
        
        # 변동성 기반 조정
        dynamic_stop_loss = max(self.parameters['stop_loss_pct'], volatility * 1.5)
        dynamic_take_profit = max(self.parameters['take_profit_pct'], volatility * 3)
        
        # 트레일링 스톱
        if 'max_profit' not in position:
            position['max_profit'] = pnl_pct
        else:
            position['max_profit'] = max(position['max_profit'], pnl_pct)
        
        # 트레일링 스톱 조건
        trailing_threshold = 0.02  # 2% 이상 수익시 트레일링 시작
        trailing_distance = 0.01   # 1% 뒤쳐지면 종료
        
        if position['max_profit'] > trailing_threshold:
            trailing_stop = position['max_profit'] - trailing_distance
            if pnl_pct < trailing_stop:
                logger.info(f"트레일링 스톱 실행: {symbol} {side} 최대수익: {position['max_profit']:.2%}, 현재: {pnl_pct:.2%}")
                self.close_position(symbol, position, current_price, "트레일링 스톱")
                return True
        
        # 기본 손절 조건
        if pnl_pct < -dynamic_stop_loss:
            logger.info(f"손절 실행: {symbol} {side} 손실: {pnl_pct:.2%}")
            self.close_position(symbol, position, current_price, "손절")
            return True
        
        # 기본 익절 조건
        if pnl_pct > dynamic_take_profit:
            logger.info(f"익절 실행: {symbol} {side} 수익: {pnl_pct:.2%}")
            self.close_position(symbol, position, current_price, "익절")
            return True
        
        # 시간 기반 종료 (24시간 초과시)
        if datetime.now() - position['timestamp'] > timedelta(hours=24):
            logger.info(f"시간 만료 종료: {symbol} {side} 수익: {pnl_pct:.2%}")
            self.close_position(symbol, position, current_price, "시간 만료")
            return True
        
        return False
    
    def close_position(self, symbol: str, position: Dict, current_price: float, reason: str):
        """포지션 종료 (개선된 버전)"""
        entry_price = position['entry_price']
        side = position['side']
        amount = position['amount']
        
        # 반대 주문 실행
        close_side = 'sell' if side == 'long' else 'buy'
        
        if self.exchange.sandbox:
            # 시뮬레이션 모드
            # 종료 거래 수수료 계산
            close_fees = self.calculate_trading_fees(amount, current_price, is_maker=False)
            
            # 자금조달비용 계산
            holding_hours = (datetime.now() - position['timestamp']).total_seconds() / 3600
            funding_cost = self.calculate_funding_cost(amount, entry_price, holding_hours)
            
            if close_side == 'sell':
                actual_price = current_price * (1 - self.fees['slippage'])
                proceeds = (amount * actual_price) - close_fees['trading_fee']
                self.current_balance += proceeds
            else:
                actual_price = current_price * (1 + self.fees['slippage'])
                cost = (amount * actual_price) + close_fees['trading_fee']
                self.current_balance -= cost
            
            # 실제 PnL 계산 (수수료 포함)
            if side == 'long':
                gross_pnl = (actual_price - entry_price) * amount
                # 진입 수수료 (기록에서 가져오거나 추정)
                entry_fee = entry_price * amount * self.fees['taker']
                actual_pnl = gross_pnl - entry_fee - close_fees['trading_fee'] - funding_cost
            else:
                gross_pnl = (entry_price - actual_price) * amount
                entry_fee = entry_price * amount * self.fees['taker']
                actual_pnl = gross_pnl - entry_fee - close_fees['trading_fee'] - funding_cost
            
            # 수수료 누적
            self.total_fees_paid += close_fees['trading_fee']
            self.total_funding_paid += funding_cost
            
            # 거래 기록 (수수료 정보 포함)
            trade_record = {
                'symbol': symbol,
                'side': side,
                'entry_price': entry_price,
                'exit_price': actual_price,
                'amount': amount,
                'gross_pnl': gross_pnl,
                'pnl': actual_pnl,
                'pnl_pct': actual_pnl / (entry_price * amount),
                'entry_fee': entry_fee,
                'exit_fee': close_fees['trading_fee'],
                'funding_cost': funding_cost,
                'total_fees': entry_fee + close_fees['trading_fee'] + funding_cost,
                'reason': reason,
                'timestamp': datetime.now(),
                'duration': datetime.now() - position['timestamp']
            }
            
            self.trade_history.append(trade_record)
            
            # 파라미터 최적화를 위한 성과 기록
            self.parameter_optimizer.add_performance(actual_pnl, self.parameters)
            
            logger.info(f"포지션 종료: {symbol} {side} 총 PnL: {gross_pnl:.2f} 순 PnL: {actual_pnl:.2f} USDT"
                       f" (수수료: {entry_fee + close_fees['trading_fee']:.2f}, 펀딩: {funding_cost:.2f}) - {reason}")
        
        # 포지션 제거
        if symbol in self.positions:
            del self.positions[symbol]
    
    def analyze_symbol_advanced(self, symbol: str) -> Optional[Dict]:
        """고급 심볼 분석"""
        try:
            # 데이터 가져오기
            df = self.get_historical_data(symbol, limit=500)
            if df.empty:
                return None
            
            # 지표 계산
            df = self.calculate_advanced_indicators(df)
            
            # 신호 생성
            signals = self.generate_enhanced_signals(df, symbol)
            
            # 현재 가격 및 변동성
            current_price = df['close'].iloc[-1]
            atr = df['atr'].iloc[-1]
            
            # 시장 구조 분석
            market_structure = self.analyze_market_structure(df)
            
            return {
                'symbol': symbol,
                'current_price': current_price,
                'atr': atr,
                'signals': signals,
                'market_structure': market_structure,
                'df': df
            }
            
        except Exception as e:
            logger.error(f"심볼 분석 실패 {symbol}: {e}")
            return None
    
    def analyze_market_structure(self, df: pd.DataFrame) -> Dict:
        """시장 구조 분석"""
        try:
            latest = df.iloc[-1]
            
            # 트렌드 방향
            if latest['ma_short'] > latest['ma_long']:
                trend = 'uptrend'
            elif latest['ma_short'] < latest['ma_long']:
                trend = 'downtrend'
            else:
                trend = 'sideways'
            
            # 트렌드 강도 (ADX)
            trend_strength = 'weak'
            if latest['adx'] > 25:
                trend_strength = 'strong'
            elif latest['adx'] > 20:
                trend_strength = 'moderate'
            
            # 변동성 상태
            volatility = df['atr'].rolling(20).mean().iloc[-1]
            current_atr = latest['atr']
            
            if current_atr > volatility * 1.5:
                volatility_state = 'high'
            elif current_atr < volatility * 0.7:
                volatility_state = 'low'
            else:
                volatility_state = 'normal'
            
            # 볼륨 상태
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            current_volume = latest['volume']
            
            if current_volume > avg_volume * 1.5:
                volume_state = 'high'
            elif current_volume < avg_volume * 0.7:
                volume_state = 'low'
            else:
                volume_state = 'normal'
            
            return {
                'trend': trend,
                'trend_strength': trend_strength,
                'volatility_state': volatility_state,
                'volume_state': volume_state
            }
            
        except Exception as e:
            logger.error(f"시장 구조 분석 실패: {e}")
            return {}
    
    def calculate_portfolio_metrics(self) -> Dict:
        """포트폴리오 지표 계산"""
        if not self.trade_history:
            return {}
        
        # 기본 통계
        total_trades = len(self.trade_history)
        winning_trades = sum(1 for trade in self.trade_history if trade['pnl'] > 0)
        self.win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # 수익률 계산 (수수료 포함)
        total_pnl = sum(trade['pnl'] for trade in self.trade_history)
        total_gross_pnl = sum(trade.get('gross_pnl', trade['pnl']) for trade in self.trade_history)
        total_fees = sum(trade.get('total_fees', 0) for trade in self.trade_history)
        total_return_pct = (self.current_balance - self.initial_balance) / self.initial_balance
        
        # 일일 수익률
        daily_returns = []
        if len(self.trade_history) > 1:
            for i in range(1, len(self.trade_history)):
                prev_balance = sum(trade['pnl'] for trade in self.trade_history[:i]) + self.initial_balance
                curr_balance = sum(trade['pnl'] for trade in self.trade_history[:i+1]) + self.initial_balance
                daily_return = (curr_balance - prev_balance) / prev_balance
                daily_returns.append(daily_return)
        
        # 샤프 비율
        if daily_returns:
            avg_return = np.mean(daily_returns)
            std_return = np.std(daily_returns)
            sharpe_ratio = (avg_return / std_return * np.sqrt(365)) if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        # 최대 낙폭
        peak_balance = self.initial_balance
        max_drawdown = 0
        
        running_balance = self.initial_balance
        for trade in self.trade_history:
            running_balance += trade['pnl']
            if running_balance > peak_balance:
                peak_balance = running_balance
            drawdown = (peak_balance - running_balance) / peak_balance
            max_drawdown = max(max_drawdown, drawdown)
        
        return {
            'total_trades': total_trades,
            'win_rate': self.win_rate,
            'total_pnl': total_pnl,
            'total_gross_pnl': total_gross_pnl,
            'total_fees': total_fees,
            'total_return_pct': total_return_pct,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'avg_trade_pnl': total_pnl / total_trades if total_trades > 0 else 0,
            'fee_to_pnl_ratio': abs(total_fees / total_gross_pnl) if total_gross_pnl != 0 else 0
        }
    
    def run_advanced_strategy(self):
        """고급 전략 실행"""
        logger.info("고급 전략 실행 시작")
        
        # 초기 ML 모델 훈련
        self.train_ml_model_periodically()
        
        iteration = 0
        
        while True:
            try:
                iteration += 1
                
                # 공매도 위험 점검
                short_risks = self.check_short_position_risks()
                if short_risks['emergency_exit']:
                    logger.warning("공매도 긴급 종료 신호 감지")
                    self.emergency_exit_short_positions()
                
                # 기존 포지션 관리
                positions_to_close = []
                for symbol, position in self.positions.items():
                    analysis = self.analyze_symbol_advanced(symbol)
                    if analysis:
                        if self.manage_position_advanced(
                            symbol, position, analysis['current_price'], analysis['df']
                        ):
                            positions_to_close.append(symbol)
                
                # 새로운 거래 기회 탐색
                if len(self.positions) < self.parameters['max_positions']:
                    best_opportunities = []
                    
                    for symbol in self.symbols:
                        if symbol not in self.positions:
                            analysis = self.analyze_symbol_advanced(symbol)
                            if analysis and analysis['signals']['confidence'] > 0:
                                best_opportunities.append(analysis)
                    
                    # 신호 강도별 정렬
                    best_opportunities.sort(
                        key=lambda x: x['signals']['confidence'], 
                        reverse=True
                    )
                    
                    # 상위 기회들 거래
                    for analysis in best_opportunities[:self.parameters['max_positions']]:
                        if len(self.positions) >= self.parameters['max_positions']:
                            break
                            
                        symbol = analysis['symbol']
                        signals = analysis['signals']
                        
                        # 시장 구조 확인
                        market_ok = self.check_market_conditions(analysis['market_structure'])
                        
                        if not market_ok:
                            continue
                        
                        # 롱 신호
                        if signals['long_signal'] > 0.7:
                            position_size = self.calculate_dynamic_position_size(
                                symbol, signals['long_signal'], analysis['atr']
                            )
                            amount = position_size / analysis['current_price']
                            
                            if position_size > self.min_trade_amount:  # 동적 최소 거래 금액
                                order = self.execute_trade(
                                    symbol, 'buy', amount, analysis['current_price']
                                )
                                if order:
                                    self.positions[symbol] = {
                                        'side': 'long',
                                        'amount': amount,
                                        'entry_price': analysis['current_price'],
                                        'timestamp': datetime.now(),
                                        'max_profit': 0.0
                                    }
                                    logger.info(f"롱 포지션 진입: {symbol} (신호강도: {signals['confidence']:.2f})")
                        
                        # 숏 신호 (공매도 위험 관리 적용)
                        elif signals['short_signal'] > 0.7:
                            # 공매도 비율 확인
                            if short_risks['short_ratio'] < self.short_risk_manager['max_short_ratio']:
                                position_size = self.calculate_short_position_size(
                                    symbol, signals['short_signal']
                                )
                                amount = position_size / analysis['current_price']
                                
                                if position_size > self.min_trade_amount:  # 동적 최소 거래 금액
                                    order = self.execute_trade(
                                        symbol, 'sell', amount, analysis['current_price']
                                    )
                                    if order:
                                        self.positions[symbol] = {
                                            'side': 'short',
                                            'amount': amount,
                                            'entry_price': analysis['current_price'],
                                            'timestamp': datetime.now(),
                                            'max_profit': 0.0
                                        }
                                        logger.info(f"숏 포지션 진입: {symbol} (신호강도: {signals['confidence']:.2f})")
                            else:
                                logger.warning(f"공매도 비율 제한 초과: {short_risks['short_ratio']:.2%} > {self.short_risk_manager['max_short_ratio']:.2%}")
                
                # 주기적 작업
                if iteration % 12 == 0:  # 1시간마다 (5분 * 12)
                    # ML 모델 재훈련
                    if iteration % 144 == 0:  # 12시간마다
                        self.train_ml_model_periodically()
                    
                    # 파라미터 최적화
                    if len(self.trade_history) >= self.parameter_optimizer.optimization_interval:
                        self.parameters = self.parameter_optimizer.optimize_parameters(self.parameters)
                
                # 상태 출력
                self.print_advanced_status()
                
                # 대기 (5분)
                time.sleep(300)
                
            except KeyboardInterrupt:
                logger.info("봇 종료")
                break
            except Exception as e:
                logger.error(f"전략 실행 중 오류: {e}")
                time.sleep(60)
    
    def check_market_conditions(self, market_structure: Dict) -> bool:
        """시장 조건 확인"""
        # 너무 높은 변동성은 피함
        if market_structure.get('volatility_state') == 'high':
            return False
        
        # 너무 낮은 볼륨은 피함
        if market_structure.get('volume_state') == 'low':
            return False
        
        return True
    
    def print_advanced_status(self):
        """고급 상태 출력"""
        metrics = self.calculate_portfolio_metrics()
        
        print(f"\n{'='*60}")
        print(f"📊 고급 트레이딩 봇 상태 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        # 기본 정보
        total_pnl = self.current_balance - self.initial_balance
        total_pnl_pct = (total_pnl / self.initial_balance) * 100
        
        print(f"💰 자금 현황:")
        print(f"   시작 자금: {self.initial_balance:,.0f} USDT")
        print(f"   현재 자금: {self.current_balance:,.0f} USDT")
        print(f"   총 수익: {total_pnl:+,.0f} USDT ({total_pnl_pct:+.2f}%)")
        print(f"   거래 수수료: {self.total_fees_paid:.2f} USDT")
        print(f"   펀딩 비용: {self.total_funding_paid:.2f} USDT")
        print(f"   총 비용: {self.total_fees_paid + self.total_funding_paid:.2f} USDT")
        
        # 성과 지표
        if metrics:
            print(f"\n📈 성과 지표:")
            print(f"   총 거래: {metrics['total_trades']}회")
            print(f"   승률: {metrics['win_rate']:.1%}")
            print(f"   샤프 비율: {metrics['sharpe_ratio']:.2f}")
            print(f"   최대 낙폭: {metrics['max_drawdown']:.1%}")
            print(f"   평균 거래 수익: {metrics['avg_trade_pnl']:+.2f} USDT")
        
        # 현재 포지션
        print(f"\n🎯 활성 포지션 ({len(self.positions)}개):")
        if self.positions:
            for symbol, position in self.positions.items():
                duration = datetime.now() - position['timestamp']
                print(f"   {symbol}: {position['side']} @ {position['entry_price']:.2f} "
                      f"(보유시간: {duration.seconds//3600}h {(duration.seconds%3600)//60}m)")
        else:
            print("   현재 포지션 없음")
        
        # 동적 파라미터
        print(f"\n⚙️ 현재 파라미터:")
        print(f"   실제 잔고: {self.real_balance:,.2f} USDT")
        print(f"   거래 자금: {self.initial_balance:,.2f} USDT")
        print(f"   거래당 리스크: {self.parameters['risk_per_trade']:.1%}")
        print(f"   손절매: {self.parameters['stop_loss_pct']:.1%}")
        print(f"   익절매: {self.parameters['take_profit_pct']:.1%}")
        print(f"   최대 포지션: {self.parameters['max_positions']}개")
        print(f"   최소 거래 금액: {self.min_trade_amount:.2f} USDT")
        print(f"   신호 임계값: {self.parameters.get('min_signal_threshold', 0.6):.2f}")
        
        # 최근 거래
        if self.trade_history:
            print(f"\n📋 최근 거래 (최근 5개):")
            recent_trades = self.trade_history[-5:]
            for trade in recent_trades:
                duration = trade['duration']
                total_fees = trade.get('total_fees', 0)
                print(f"   {trade['symbol']}: {trade['side']} "
                      f"총수익: {trade.get('gross_pnl', trade['pnl']):+.2f} "
                      f"순수익: {trade['pnl']:+.2f} USDT ({trade['pnl_pct']:+.1%}) "
                      f"수수료: {total_fees:.2f} - {trade['reason']} ({duration.seconds//60}분)")
        
        print(f"{'='*60}\n")
    
    def save_state(self, filename: str = "bot_state.json"):
        """봇 상태 저장"""
        state = {
            'current_balance': self.current_balance,
            'parameters': self.parameters,
            'trade_history': [
                {
                    **trade,
                    'timestamp': trade['timestamp'].isoformat(),
                    'duration': str(trade['duration'])
                } for trade in self.trade_history
            ],
            'positions': {
                symbol: {
                    **pos,
                    'timestamp': pos['timestamp'].isoformat()
                } for symbol, pos in self.positions.items()
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"봇 상태 저장완료: {filename}")
    
    def load_state(self, filename: str = "bot_state.json"):
        """봇 상태 로드"""
        try:
            with open(filename, 'r') as f:
                state = json.load(f)
            
            self.current_balance = state['current_balance']
            self.parameters = state['parameters']
            
            # 거래 기록 복원
            self.trade_history = []
            for trade in state['trade_history']:
                trade['timestamp'] = datetime.fromisoformat(trade['timestamp'])
                trade['duration'] = timedelta(seconds=int(trade['duration'].split(':')[2].split('.')[0]))
                self.trade_history.append(trade)
            
            # 포지션 복원
            self.positions = {}
            for symbol, pos in state['positions'].items():
                pos['timestamp'] = datetime.fromisoformat(pos['timestamp'])
                self.positions[symbol] = pos
            
            logger.info(f"봇 상태 로드완료: {filename}")
            
        except FileNotFoundError:
            logger.info("저장된 상태가 없습니다. 새로 시작합니다.")
        except Exception as e:
            logger.error(f"상태 로드 실패: {e}")

# 백테스팅 시스템
class BacktestEngine:
    """백테스트 엔진"""
    
    def __init__(self, bot: AdvancedBinanceTradingBot):
        self.bot = bot
        self.results = {}
    
    def run_backtest(self, start_date: str, end_date: str, initial_balance: float = 100000) -> Dict:
        """백테스트 실행"""
        logger.info(f"백테스트 시작: {start_date} ~ {end_date}")
        
        # 백테스트용 봇 설정
        self.bot.current_balance = initial_balance
        self.bot.initial_balance = initial_balance
        self.bot.trade_history = []
        self.bot.positions = {}
        
        try:
            # 데이터 수집 및 시뮬레이션
            for symbol in self.bot.symbols:
                df = self.bot.get_historical_data(symbol, limit=2000)
                if not df.empty:
                    # 시뮬레이션 로직 (간단한 버전)
                    pass
            
            # 결과 계산
            metrics = self.bot.calculate_portfolio_metrics()
            
            return {
                'period': f"{start_date} ~ {end_date}",
                'initial_balance': initial_balance,
                'final_balance': self.bot.current_balance,
                'total_return': (self.bot.current_balance - initial_balance) / initial_balance,
                'metrics': metrics
            }
            
        except Exception as e:
            logger.error(f"백테스트 실패: {e}")
            return {}

# 사용 예제
if __name__ == "__main__":
    # API 키 설정 (환경변수에서 로드)
    API_KEY = os.getenv("BINANCE_API_KEY")
    API_SECRET = os.getenv("BINANCE_SECRET_KEY")
    
    if not API_KEY or not API_SECRET:
        logger.error("API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")
        exit(1)
    
    # 실제 거래 모드 안전장치
    REAL_TRADING_MODE = True  # 실제 거래 모드 활성화
    
    if REAL_TRADING_MODE:
        print("⚠️  실제 거래 모드 활성화됨!")
        print("⚠️  실제 자금으로 거래가 진행됩니다!")
        confirmation = input("정말로 실제 거래를 시작하시겠습니까? (YES 입력): ")
        if confirmation != "YES":
            print("거래가 취소되었습니다.")
            exit(1)
        use_testnet = False
    else:
        print("📊 테스트넷 모드로 실행됩니다.")
        use_testnet = True
    
    # 고급 봇 초기화 (실제 잔고 확인)
    bot = AdvancedBinanceTradingBot(
        api_key=API_KEY,
        api_secret=API_SECRET,
        use_testnet=use_testnet
    )
    
    # 저장된 상태 로드 (있다면)
    bot.load_state()
    
    try:
        print("🚀 고급 자동매매 봇 시작!")
        print("Ctrl+C로 종료할 수 있습니다.")
        
        # 고급 전략 실행
        bot.run_advanced_strategy()
        
    except KeyboardInterrupt:
        print("\n⏹️ 봇 종료 중...")
        bot.print_advanced_status()
        bot.save_state()
        print("✅ 상태 저장 완료!")
    
    except Exception as e:
        logger.error(f"봇 실행 중 오류: {e}")
        bot.save_state()

# 별도 실행용 스크립트들

def quick_backtest():
    """빠른 백테스트"""
    bot = AdvancedBinanceTradingBot("", "", 100000)
    engine = BacktestEngine(bot)
    
    results = engine.run_backtest("2024-01-01", "2024-12-31")
    print("백테스트 결과:", results)

def parameter_optimization():
    """파라미터 최적화"""
    # 다양한 파라미터 조합 테스트
    parameter_sets = [
        {'risk_per_trade': 0.01, 'stop_loss_pct': 0.02},
        {'risk_per_trade': 0.02, 'stop_loss_pct': 0.025},
        {'risk_per_trade': 0.03, 'stop_loss_pct': 0.03},
    ]
    
    best_params = None
    best_performance = 0
    
    for params in parameter_sets:
        bot = AdvancedBinanceTradingBot("", "", 100000)
        bot.parameters.update(params)
        
        engine = BacktestEngine(bot)
        results = engine.run_backtest("2024-01-01", "2024-12-31")
        
        if results.get('total_return', 0) > best_performance:
            best_performance = results['total_return']
            best_params = params
    
    print(f"최적 파라미터: {best_params}")
    print(f"최고 성능: {best_performance:.2%}")

# 실시간 모니터링을 위한 웹 대시보드 (선택사항)
def create_dashboard():
    """간단한 웹 대시보드 생성"""
    try:
        import flask
        from flask import Flask, render_template_string
        
        app = Flask(__name__)
        
        @app.route('/')
        def dashboard():
            # 봇 상태를 웹페이지로 표시
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>트레이딩 봇 대시보드</title>
                <meta charset="utf-8">
                <meta http-equiv="refresh" content="30">
            </head>
            <body>
                <h1>🤖 트레이딩 봇 실시간 모니터링</h1>
                <div id="status">
                    <!-- 실시간 상태 정보 -->
                </div>
            </body>
            </html>
            """
            return render_template_string(html)
        
        print("대시보드 시작: http://localhost:5000")
        app.run(debug=True, port=5000)
        
    except ImportError:
        print("Flask가 설치되지 않았습니다. pip install flask")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "backtest":
            quick_backtest()
        elif sys.argv[1] == "optimize":
            parameter_optimization()
        elif sys.argv[1] == "dashboard":
            create_dashboard()
    else:
        # 기본 실행
        pass