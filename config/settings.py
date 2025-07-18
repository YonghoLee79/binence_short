"""
거래 봇 설정 관리 모듈
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class TradingConfig:
    """거래 봇 설정 클래스"""
    
    def __init__(self):
        self.load_config()
    
    def load_config(self):
        """환경 변수에서 설정 로드"""
        # API 설정
        self.BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
        self.BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
        self.USE_TESTNET = os.getenv('USE_TESTNET', 'False').lower() == 'true'
        
        # 텔레그램 설정
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        self.TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
        
        # 거래 설정
        self.INITIAL_BALANCE = float(os.getenv('INITIAL_BALANCE', '1000'))
        self.MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '0.2'))
        self.RISK_PER_TRADE = float(os.getenv('RISK_PER_TRADE', '0.02'))
        
        # 기술적 분석 설정
        self.RSI_PERIOD = int(os.getenv('RSI_PERIOD', '14'))
        self.RSI_OVERSOLD = float(os.getenv('RSI_OVERSOLD', '30'))
        self.RSI_OVERBOUGHT = float(os.getenv('RSI_OVERBOUGHT', '70'))
        self.MACD_FAST = int(os.getenv('MACD_FAST', '12'))
        self.MACD_SLOW = int(os.getenv('MACD_SLOW', '26'))
        self.MACD_SIGNAL = int(os.getenv('MACD_SIGNAL', '9'))
        self.BB_PERIOD = int(os.getenv('BB_PERIOD', '20'))
        self.BB_STDDEV = float(os.getenv('BB_STDDEV', '2'))
        
        # 리스크 관리
        self.STOP_LOSS_PCT = float(os.getenv('STOP_LOSS_PCT', '0.05'))
        self.TAKE_PROFIT_PCT = float(os.getenv('TAKE_PROFIT_PCT', '0.10'))
        self.MAX_DRAWDOWN = float(os.getenv('MAX_DRAWDOWN', '0.20'))
        self.POSITION_TIMEOUT_HOURS = int(os.getenv('POSITION_TIMEOUT_HOURS', '24'))
        
        # 하이브리드 전략 설정
        self.SPOT_ALLOCATION = float(os.getenv('SPOT_ALLOCATION', '0.6'))
        self.FUTURES_ALLOCATION = float(os.getenv('FUTURES_ALLOCATION', '0.4'))
        self.HEDGE_RATIO = float(os.getenv('HEDGE_RATIO', '0.3'))
        self.REBALANCE_THRESHOLD = float(os.getenv('REBALANCE_THRESHOLD', '0.05'))
        self.MAX_LEVERAGE = int(os.getenv('MAX_LEVERAGE', '5'))
        
        # 거래 심볼
        self.TRADING_SYMBOLS = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT'
        ]
        
        # 수수료 설정
        self.FEES = {
            'spot_maker': 0.001,    # 현물 maker 0.1%
            'spot_taker': 0.001,    # 현물 taker 0.1%
            'futures_maker': 0.0002, # 선물 maker 0.02%
            'futures_taker': 0.0004, # 선물 taker 0.04%
            'slippage': 0.0005      # 슬리피지 0.05%
        }
        
        # 로깅 설정
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FILE = os.getenv('LOG_FILE', 'trading_bot.log')
        self.LOG_MAX_SIZE = os.getenv('LOG_MAX_SIZE', '10MB')
        self.LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    
    def validate_config(self) -> bool:
        """설정 유효성 검증"""
        if not self.BINANCE_API_KEY or not self.BINANCE_SECRET_KEY:
            return False
        
        if self.SPOT_ALLOCATION + self.FUTURES_ALLOCATION != 1.0:
            return False
        
        if self.RISK_PER_TRADE > 0.1:  # 10% 이상 리스크 방지
            return False
        
        return True
    
    def get_strategy_config(self) -> Dict[str, Any]:
        """전략 설정 반환"""
        return {
            'spot_allocation': self.SPOT_ALLOCATION,
            'futures_allocation': self.FUTURES_ALLOCATION,
            'hedge_ratio': self.HEDGE_RATIO,
            'rebalance_threshold': self.REBALANCE_THRESHOLD,
            'max_leverage': self.MAX_LEVERAGE,
            'risk_per_trade': self.RISK_PER_TRADE,
        }
    
    def get_technical_config(self) -> Dict[str, Any]:
        """기술적 분석 설정 반환"""
        return {
            'rsi_period': self.RSI_PERIOD,
            'rsi_oversold': self.RSI_OVERSOLD,
            'rsi_overbought': self.RSI_OVERBOUGHT,
            'macd_fast': self.MACD_FAST,
            'macd_slow': self.MACD_SLOW,
            'macd_signal': self.MACD_SIGNAL,
            'bb_period': self.BB_PERIOD,
            'bb_stddev': self.BB_STDDEV,
        }
    
    def get_risk_config(self) -> Dict[str, Any]:
        """리스크 관리 설정 반환"""
        return {
            'stop_loss_pct': self.STOP_LOSS_PCT,
            'take_profit_pct': self.TAKE_PROFIT_PCT,
            'max_drawdown': self.MAX_DRAWDOWN,
            'position_timeout_hours': self.POSITION_TIMEOUT_HOURS,
        }

# 전역 설정 인스턴스
config = TradingConfig()