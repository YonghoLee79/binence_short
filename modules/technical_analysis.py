"""
기술적 분석 모듈
"""
import pandas as pd
import numpy as np
import talib
from typing import Dict, Any, List, Optional
from utils.logger import logger
from utils.decorators import cache_result, log_execution_time


class TechnicalAnalyzer:
    """기술적 분석 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_oversold = config.get('rsi_oversold', 30)
        self.rsi_overbought = config.get('rsi_overbought', 70)
        self.macd_fast = config.get('macd_fast', 12)
        self.macd_slow = config.get('macd_slow', 26)
        self.macd_signal = config.get('macd_signal', 9)
        self.bb_period = config.get('bb_period', 20)
        self.bb_stddev = config.get('bb_stddev', 2)
    
    @log_execution_time
    def calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """RSI 계산"""
        try:
            if len(prices) < self.rsi_period + 10:
                logger.warning(f"RSI 계산용 데이터 부족: {len(prices)} < {self.rsi_period + 10}")
                return pd.Series([50] * len(prices))
            
            # 데이터 타입 확인 및 변환
            price_values = prices.values.astype(float)
            rsi_values = talib.RSI(price_values, timeperiod=self.rsi_period)
            
            # NaN 값 처리
            rsi_series = pd.Series(rsi_values)
            rsi_series = rsi_series.fillna(50)
            
            return rsi_series
        except Exception as e:
            logger.error(f"RSI 계산 오류: {e}")
            return pd.Series([50] * len(prices))
    
    @log_execution_time 
    def calculate_macd(self, prices: pd.Series) -> Dict[str, pd.Series]:
        """MACD 계산"""
        try:
            min_length = max(self.macd_slow, self.macd_signal) + 20
            if len(prices) < min_length:
                logger.warning(f"MACD 계산용 데이터 부족: {len(prices)} < {min_length}")
                return {
                    'macd': pd.Series([0] * len(prices)),
                    'signal': pd.Series([0] * len(prices)),
                    'histogram': pd.Series([0] * len(prices))
                }
            
            # 데이터 타입 확인 및 변환
            price_values = prices.values.astype(float)
            macd_line, macd_signal, macd_histogram = talib.MACD(
                price_values, 
                fastperiod=self.macd_fast,
                slowperiod=self.macd_slow, 
                signalperiod=self.macd_signal
            )
            
            # NaN 값 처리
            return {
                'macd': pd.Series(macd_line).fillna(0),
                'signal': pd.Series(macd_signal).fillna(0),
                'histogram': pd.Series(macd_histogram).fillna(0)
            }
        except Exception as e:
            logger.error(f"MACD 계산 오류: {e}")
            return {
                'macd': pd.Series([0] * len(prices)),
                'signal': pd.Series([0] * len(prices)),
                'histogram': pd.Series([0] * len(prices))
            }
    
    @log_execution_time
    def calculate_bollinger_bands(self, prices: pd.Series) -> Dict[str, pd.Series]:
        """볼린저 밴드 계산"""
        try:
            upper, middle, lower = talib.BBANDS(
                prices.values,
                timeperiod=self.bb_period,
                nbdevup=self.bb_stddev,
                nbdevdn=self.bb_stddev,
                matype=0
            )
            return {
                'upper': pd.Series(upper),
                'middle': pd.Series(middle),
                'lower': pd.Series(lower)
            }
        except Exception as e:
            logger.error(f"볼린저 밴드 계산 오류: {e}")
            return {
                'upper': pd.Series(prices),
                'middle': pd.Series(prices),
                'lower': pd.Series(prices)
            }
    
    @log_execution_time
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """ATR (Average True Range) 계산"""
        try:
            return talib.ATR(high.values, low.values, close.values, timeperiod=period)
        except Exception as e:
            logger.error(f"ATR 계산 오류: {e}")
            return pd.Series([0.01] * len(close))
    
    @log_execution_time
    def calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series) -> Dict[str, pd.Series]:
        """스토캐스틱 계산"""
        try:
            slowk, slowd = talib.STOCH(
                high.values, low.values, close.values,
                fastk_period=14, slowk_period=3, slowk_matype=0,
                slowd_period=3, slowd_matype=0
            )
            return {
                'slowk': pd.Series(slowk),
                'slowd': pd.Series(slowd)
            }
        except Exception as e:
            logger.error(f"스토캐스틱 계산 오류: {e}")
            return {
                'slowk': pd.Series([50] * len(close)),
                'slowd': pd.Series([50] * len(close))
            }
    
    @log_execution_time
    def calculate_williams_r(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Williams %R 계산"""
        try:
            return talib.WILLR(high.values, low.values, close.values, timeperiod=period)
        except Exception as e:
            logger.error(f"Williams %R 계산 오류: {e}")
            return pd.Series([-50] * len(close))
    
    @log_execution_time
    def calculate_volume_indicators(self, prices: pd.Series, volume: pd.Series) -> Dict[str, pd.Series]:
        """거래량 지표 계산"""
        try:
            # OBV (On-Balance Volume)
            obv = talib.OBV(prices.values, volume.values)
            
            # VWAP (Volume Weighted Average Price)
            vwap = (prices * volume).cumsum() / volume.cumsum()
            
            return {
                'obv': pd.Series(obv),
                'vwap': pd.Series(vwap)
            }
        except Exception as e:
            logger.error(f"거래량 지표 계산 오류: {e}")
            return {
                'obv': pd.Series([0] * len(prices)),
                'vwap': pd.Series(prices)
            }
    
    @log_execution_time
    def calculate_moving_averages(self, prices: pd.Series) -> Dict[str, pd.Series]:
        """이동평균 계산"""
        try:
            return {
                'sma_5': talib.SMA(prices.values, timeperiod=5),
                'sma_10': talib.SMA(prices.values, timeperiod=10),
                'sma_20': talib.SMA(prices.values, timeperiod=20),
                'sma_50': talib.SMA(prices.values, timeperiod=50),
                'ema_5': talib.EMA(prices.values, timeperiod=5),
                'ema_10': talib.EMA(prices.values, timeperiod=10),
                'ema_20': talib.EMA(prices.values, timeperiod=20),
                'ema_50': talib.EMA(prices.values, timeperiod=50)
            }
        except Exception as e:
            logger.error(f"이동평균 계산 오류: {e}")
            return {}
    
    @cache_result(cache_time=300)
    def get_all_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """모든 지표 계산"""
        try:
            indicators = {}
            
            # 기본 지표
            indicators['rsi'] = self.calculate_rsi(df['close'])
            indicators['macd'] = self.calculate_macd(df['close'])
            indicators['bb'] = self.calculate_bollinger_bands(df['close'])
            indicators['atr'] = self.calculate_atr(df['high'], df['low'], df['close'])
            indicators['stoch'] = self.calculate_stochastic(df['high'], df['low'], df['close'])
            indicators['williams_r'] = self.calculate_williams_r(df['high'], df['low'], df['close'])
            
            # 거래량 지표
            if 'volume' in df.columns:
                indicators['volume'] = self.calculate_volume_indicators(df['close'], df['volume'])
            
            # 이동평균
            indicators['ma'] = self.calculate_moving_averages(df['close'])
            
            return indicators
        except Exception as e:
            logger.error(f"지표 계산 오류: {e}")
            return {}
    
    def generate_signals(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """거래 신호 생성"""
        try:
            signals = {}
            
            # RSI 신호
            if 'rsi' in indicators and len(indicators['rsi']) > 0:
                rsi_current = indicators['rsi'].iloc[-1] if hasattr(indicators['rsi'], 'iloc') else indicators['rsi'][-1]
                
                # NaN 또는 무효한 값 처리
                if pd.isna(rsi_current) or not isinstance(rsi_current, (int, float)):
                    rsi_current = 50
                
                if rsi_current < self.rsi_oversold:
                    signals['rsi_signal'] = 1.0  # 매수
                elif rsi_current > self.rsi_overbought:
                    signals['rsi_signal'] = -1.0  # 매도
                else:
                    signals['rsi_signal'] = 0.0  # 중립
            else:
                signals['rsi_signal'] = 0.0
            
            # MACD 신호
            if 'macd' in indicators and 'histogram' in indicators['macd']:
                macd_hist = indicators['macd']['histogram']
                if len(macd_hist) >= 2:
                    hist_current = macd_hist.iloc[-1] if hasattr(macd_hist, 'iloc') else macd_hist[-1]
                    hist_prev = macd_hist.iloc[-2] if hasattr(macd_hist, 'iloc') else macd_hist[-2]
                    
                    # NaN 또는 무효한 값 처리
                    if pd.isna(hist_current) or pd.isna(hist_prev):
                        signals['macd_signal'] = 0.0
                    elif hist_current > 0 and hist_prev <= 0:
                        signals['macd_signal'] = 1.0  # 매수
                    elif hist_current < 0 and hist_prev >= 0:
                        signals['macd_signal'] = -1.0  # 매도
                    else:
                        signals['macd_signal'] = 0.0  # 중립
                else:
                    signals['macd_signal'] = 0.0
            else:
                signals['macd_signal'] = 0.0
            
            # 볼린저 밴드 신호
            if 'bb' in indicators:
                bb_data = indicators['bb']
                if (len(bb_data.get('lower', [])) > 0 and 
                    len(bb_data.get('upper', [])) > 0 and 
                    len(bb_data.get('middle', [])) > 0):
                    
                    current_price = bb_data['middle'].iloc[-1] if hasattr(bb_data['middle'], 'iloc') else bb_data['middle'][-1]
                    upper_band = bb_data['upper'].iloc[-1] if hasattr(bb_data['upper'], 'iloc') else bb_data['upper'][-1]
                    lower_band = bb_data['lower'].iloc[-1] if hasattr(bb_data['lower'], 'iloc') else bb_data['lower'][-1]
                    
                    # NaN 또는 무효한 값 처리
                    if pd.isna(current_price) or pd.isna(upper_band) or pd.isna(lower_band):
                        signals['bb_signal'] = 0.0
                    elif current_price <= lower_band:
                        signals['bb_signal'] = 1.0  # 매수
                    elif current_price >= upper_band:
                        signals['bb_signal'] = -1.0  # 매도
                    else:
                        signals['bb_signal'] = 0.0  # 중립
                else:
                    signals['bb_signal'] = 0.0
            else:
                signals['bb_signal'] = 0.0
            
            # 스토캐스틱 신호
            if 'stoch' in indicators and 'slowk' in indicators['stoch']:
                stoch_data = indicators['stoch']
                if len(stoch_data['slowk']) > 0:
                    slowk = stoch_data['slowk'].iloc[-1] if hasattr(stoch_data['slowk'], 'iloc') else stoch_data['slowk'][-1]
                    
                    # NaN 또는 무효한 값 처리
                    if pd.isna(slowk) or not isinstance(slowk, (int, float)):
                        signals['stoch_signal'] = 0.0
                    elif slowk < 20:
                        signals['stoch_signal'] = 1.0  # 매수
                    elif slowk > 80:
                        signals['stoch_signal'] = -1.0  # 매도
                    else:
                        signals['stoch_signal'] = 0.0  # 중립
                else:
                    signals['stoch_signal'] = 0.0
            else:
                signals['stoch_signal'] = 0.0
            
            # 종합 신호 계산 - 모든 신호 포함하여 평균 계산
            valid_signals = [v for k, v in signals.items() if k.endswith('_signal') and isinstance(v, (int, float)) and not pd.isna(v)]
            
            if valid_signals:
                signals['combined_signal'] = sum(valid_signals) / len(valid_signals)
            else:
                signals['combined_signal'] = 0.0
            
            # 안전 검증: 모든 신호가 유효한 숫자인지 확인
            for key, value in signals.items():
                if pd.isna(value) or not isinstance(value, (int, float)):
                    signals[key] = 0.0
            
            return signals
        except Exception as e:
            logger.error(f"신호 생성 오류: {e}")
            # 완전히 안전한 기본 신호 반환
            return {
                'rsi_signal': 0.0,
                'macd_signal': 0.0,
                'bb_signal': 0.0,
                'stoch_signal': 0.0,
                'combined_signal': 0.0
            }
    
    def get_market_strength(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """시장 강도 분석"""
        try:
            strength = {}
            
            # 트렌드 강도
            if 'ma' in indicators:
                ma_data = indicators['ma']
                if 'sma_20' in ma_data and 'sma_50' in ma_data:
                    sma_20 = ma_data['sma_20'][-1] if len(ma_data['sma_20']) > 0 else 0
                    sma_50 = ma_data['sma_50'][-1] if len(ma_data['sma_50']) > 0 else 0
                    
                    if sma_20 > sma_50:
                        strength['trend_strength'] = (sma_20 - sma_50) / sma_50
                    else:
                        strength['trend_strength'] = (sma_20 - sma_50) / sma_50
            
            # 변동성 강도
            if 'atr' in indicators:
                atr_current = indicators['atr'][-1] if len(indicators['atr']) > 0 else 0
                strength['volatility_strength'] = atr_current
            
            # 모멘텀 강도
            if 'rsi' in indicators:
                rsi_current = indicators['rsi'][-1] if len(indicators['rsi']) > 0 else 50
                strength['momentum_strength'] = abs(rsi_current - 50) / 50
            
            return strength
        except Exception as e:
            logger.error(f"시장 강도 분석 오류: {e}")
            return {}