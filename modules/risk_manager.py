"""
리스크 관리 모듈
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from utils.logger import logger
from utils.decorators import log_execution_time


class RiskManager:
    """리스크 관리 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # 리스크 관리 파라미터
        self.max_position_size = config.get('max_position_size', 0.2)  # 최대 포지션 크기 (20%)
        self.max_daily_loss = config.get('max_daily_loss', 0.05)  # 최대 일일 손실 (5%)
        self.max_drawdown = config.get('max_drawdown', 0.20)  # 최대 드로우다운 (20%)
        self.stop_loss_pct = config.get('stop_loss_pct', 0.05)  # 스탑로스 (5%)
        self.take_profit_pct = config.get('take_profit_pct', 0.10)  # 테이크프로핏 (10%)
        self.position_timeout_hours = config.get('position_timeout_hours', 24)  # 포지션 타임아웃 (24시간)
        self.max_leverage = config.get('max_leverage', 5)  # 최대 레버리지
        self.risk_per_trade = config.get('risk_per_trade', 0.02)  # 거래당 리스크 (2%)
        
        # 공매도 특화 리스크 관리
        self.short_position_limit = config.get('short_position_limit', 0.3)  # 공매도 포지션 한도 (30%)
        self.short_squeeze_threshold = config.get('short_squeeze_threshold', 0.10)  # 숏 스퀴즈 임계값 (10%)
        self.funding_rate_threshold = config.get('funding_rate_threshold', 0.01)  # 펀딩비 임계값 (1%)
        
        # 리스크 상태 추적
        self.daily_pnl = 0.0
        self.peak_balance = 0.0
        self.current_drawdown = 0.0
        self.positions = {}
        self.risk_alerts = []
        
        logger.info("리스크 관리자 초기화 완료")
    
    @log_execution_time
    def validate_trade(self, symbol: str, side: str, size: float, price: float, 
                      current_balance: float, exchange_type: str = 'spot') -> Dict[str, Any]:
        """거래 유효성 검증"""
        try:
            validation_result = {
                'is_valid': True,
                'warnings': [],
                'errors': [],
                'adjusted_size': size
            }
            
            # 포지션 크기 검증
            position_value = size * price
            max_position_value = current_balance * self.max_position_size
            
            if position_value > max_position_value:
                validation_result['warnings'].append(f"포지션 크기 초과: {position_value:.2f} > {max_position_value:.2f}")
                validation_result['adjusted_size'] = max_position_value / price
            
            # 일일 손실 한도 검증
            if self.daily_pnl < -current_balance * self.max_daily_loss:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"일일 손실 한도 초과: {self.daily_pnl:.2f}")
            
            # 드로우다운 검증
            if self.current_drawdown > self.max_drawdown:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"최대 드로우다운 초과: {self.current_drawdown:.2%}")
            
            # 공매도 특화 검증
            if side == 'sell' and exchange_type == 'futures':
                short_validation = self._validate_short_position(symbol, size, price, current_balance)
                validation_result['warnings'].extend(short_validation['warnings'])
                validation_result['errors'].extend(short_validation['errors'])
                if not short_validation['is_valid']:
                    validation_result['is_valid'] = False
            
            # 레버리지 검증
            if exchange_type == 'futures':
                leverage_validation = self._validate_leverage(size, price, current_balance)
                validation_result['warnings'].extend(leverage_validation['warnings'])
                validation_result['errors'].extend(leverage_validation['errors'])
            
            return validation_result
        except Exception as e:
            logger.error(f"거래 검증 실패: {e}")
            return {
                'is_valid': False,
                'warnings': [],
                'errors': [f"검증 오류: {e}"],
                'adjusted_size': 0
            }
    
    def _validate_short_position(self, symbol: str, size: float, price: float, 
                               current_balance: float) -> Dict[str, Any]:
        """공매도 포지션 검증"""
        try:
            validation_result = {
                'is_valid': True,
                'warnings': [],
                'errors': []
            }
            
            # 공매도 포지션 한도 검증
            current_short_value = sum(
                pos['size'] * pos['price'] for pos in self.positions.values()
                if pos['side'] == 'sell' and pos['exchange_type'] == 'futures'
            )
            new_short_value = current_short_value + (size * price)
            max_short_value = current_balance * self.short_position_limit
            
            if new_short_value > max_short_value:
                validation_result['is_valid'] = False
                validation_result['errors'].append(
                    f"공매도 포지션 한도 초과: {new_short_value:.2f} > {max_short_value:.2f}"
                )
            
            # 숏 스퀴즈 위험 검증
            if symbol in self.positions:
                recent_price_change = self._calculate_recent_price_change(symbol)
                if recent_price_change > self.short_squeeze_threshold:
                    validation_result['warnings'].append(
                        f"숏 스퀴즈 위험: 최근 가격 상승 {recent_price_change:.2%}"
                    )
            
            return validation_result
        except Exception as e:
            logger.error(f"공매도 포지션 검증 실패: {e}")
            return {
                'is_valid': False,
                'warnings': [],
                'errors': [f"공매도 검증 오류: {e}"]
            }
    
    def _validate_leverage(self, size: float, price: float, current_balance: float) -> Dict[str, Any]:
        """레버리지 검증"""
        try:
            validation_result = {
                'is_valid': True,
                'warnings': [],
                'errors': []
            }
            
            position_value = size * price
            required_margin = position_value / self.max_leverage
            
            if required_margin > current_balance * 0.8:  # 잔고의 80% 이상 사용
                validation_result['warnings'].append(
                    f"높은 레버리지 사용: 필요 마진 {required_margin:.2f}"
                )
            
            return validation_result
        except Exception as e:
            logger.error(f"레버리지 검증 실패: {e}")
            return {
                'is_valid': True,
                'warnings': [],
                'errors': []
            }
    
    def _calculate_recent_price_change(self, symbol: str) -> float:
        """최근 가격 변화 계산"""
        try:
            if symbol in self.positions:
                position = self.positions[symbol]
                entry_price = position['price']
                current_price = position.get('current_price', entry_price)
                return (current_price - entry_price) / entry_price
            return 0.0
        except Exception as e:
            logger.error(f"가격 변화 계산 실패: {e}")
            return 0.0
    
    @log_execution_time
    def calculate_position_size(self, symbol: str, signal_strength: float, 
                               current_balance: float, current_price: float, 
                               volatility: float = 0.02) -> float:
        """포지션 크기 계산"""
        try:
            # Kelly Criterion 기반 포지션 크기 계산
            win_rate = 0.55  # 예상 승률 (55%)
            avg_win = 0.15   # 평균 수익률 (15%)
            avg_loss = 0.08  # 평균 손실률 (8%)
            
            kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
            kelly_fraction = max(0, min(kelly_fraction, 0.25))  # 최대 25%로 제한
            
            # 신호 강도 적용
            adjusted_fraction = kelly_fraction * signal_strength
            
            # 변동성 조정
            volatility_adjustment = 1 / (1 + volatility * 10)
            adjusted_fraction *= volatility_adjustment
            
            # 최대 리스크 제한
            max_risk_amount = current_balance * self.risk_per_trade
            position_value = current_balance * adjusted_fraction
            
            if position_value > max_risk_amount:
                position_value = max_risk_amount
            
            position_size = position_value / current_price
            
            logger.debug(f"포지션 크기 계산: {symbol} - {position_size:.6f} (신호강도: {signal_strength:.2f})")
            return position_size
        except Exception as e:
            logger.error(f"포지션 크기 계산 실패: {e}")
            return 0.0
    
    @log_execution_time
    def calculate_stop_loss(self, symbol: str, side: str, entry_price: float, 
                           volatility: float = 0.02) -> float:
        """스탑로스 가격 계산"""
        try:
            # 기본 스탑로스
            basic_stop_loss = self.stop_loss_pct
            
            # 변동성 기반 조정
            volatility_adjustment = max(volatility * 2, basic_stop_loss)
            
            # ATR 기반 스탑로스 (더 정교한 방법)
            atr_multiplier = 2.0
            atr_stop_loss = volatility * atr_multiplier
            
            # 최종 스탑로스 거리 결정
            stop_loss_distance = max(basic_stop_loss, min(volatility_adjustment, atr_stop_loss))
            
            if side == 'buy':
                stop_loss_price = entry_price * (1 - stop_loss_distance)
            else:  # sell
                stop_loss_price = entry_price * (1 + stop_loss_distance)
            
            logger.debug(f"스탑로스 계산: {symbol} {side} - {stop_loss_price:.6f}")
            return stop_loss_price
        except Exception as e:
            logger.error(f"스탑로스 계산 실패: {e}")
            return entry_price
    
    @log_execution_time
    def calculate_take_profit(self, symbol: str, side: str, entry_price: float, 
                            signal_strength: float = 0.5) -> float:
        """테이크프로핏 가격 계산"""
        try:
            # 기본 테이크프로핏
            basic_take_profit = self.take_profit_pct
            
            # 신호 강도 기반 조정
            strength_adjustment = basic_take_profit * (1 + signal_strength)
            
            # 리스크 대비 수익 비율 (Risk-Reward Ratio)
            risk_reward_ratio = 2.0  # 2:1 비율
            stop_loss_distance = self.stop_loss_pct
            take_profit_distance = stop_loss_distance * risk_reward_ratio
            
            # 최종 테이크프로핏 거리 결정
            final_take_profit_distance = min(strength_adjustment, take_profit_distance)
            
            if side == 'buy':
                take_profit_price = entry_price * (1 + final_take_profit_distance)
            else:  # sell
                take_profit_price = entry_price * (1 - final_take_profit_distance)
            
            logger.debug(f"테이크프로핏 계산: {symbol} {side} - {take_profit_price:.6f}")
            return take_profit_price
        except Exception as e:
            logger.error(f"테이크프로핏 계산 실패: {e}")
            return entry_price
    
    @log_execution_time
    def update_position_risk(self, symbol: str, current_price: float, 
                           unrealized_pnl: float = 0.0):
        """포지션 리스크 업데이트"""
        try:
            if symbol not in self.positions:
                return
            
            position = self.positions[symbol]
            position['current_price'] = current_price
            position['unrealized_pnl'] = unrealized_pnl
            position['last_update'] = datetime.now()
            
            # 스탑로스 체크
            if self._should_stop_loss(position, current_price):
                self.risk_alerts.append({
                    'type': 'stop_loss',
                    'symbol': symbol,
                    'message': f"스탑로스 발생: {symbol} 현재가 {current_price:.6f}",
                    'timestamp': datetime.now()
                })
            
            # 테이크프로핏 체크
            if self._should_take_profit(position, current_price):
                self.risk_alerts.append({
                    'type': 'take_profit',
                    'symbol': symbol,
                    'message': f"테이크프로핏 발생: {symbol} 현재가 {current_price:.6f}",
                    'timestamp': datetime.now()
                })
            
            # 포지션 타임아웃 체크
            if self._is_position_timeout(position):
                self.risk_alerts.append({
                    'type': 'timeout',
                    'symbol': symbol,
                    'message': f"포지션 타임아웃: {symbol} 보유시간 초과",
                    'timestamp': datetime.now()
                })
            
        except Exception as e:
            logger.error(f"포지션 리스크 업데이트 실패: {e}")
    
    def _should_stop_loss(self, position: Dict[str, Any], current_price: float) -> bool:
        """스탑로스 여부 확인"""
        try:
            side = position['side']
            stop_loss_price = position.get('stop_loss_price', 0)
            
            if stop_loss_price == 0:
                return False
            
            if side == 'buy':
                return current_price <= stop_loss_price
            else:  # sell
                return current_price >= stop_loss_price
        except Exception as e:
            logger.error(f"스탑로스 확인 실패: {e}")
            return False
    
    def _should_take_profit(self, position: Dict[str, Any], current_price: float) -> bool:
        """테이크프로핏 여부 확인"""
        try:
            side = position['side']
            take_profit_price = position.get('take_profit_price', 0)
            
            if take_profit_price == 0:
                return False
            
            if side == 'buy':
                return current_price >= take_profit_price
            else:  # sell
                return current_price <= take_profit_price
        except Exception as e:
            logger.error(f"테이크프로핏 확인 실패: {e}")
            return False
    
    def _is_position_timeout(self, position: Dict[str, Any]) -> bool:
        """포지션 타임아웃 확인"""
        try:
            entry_time = position.get('entry_time', datetime.now())
            timeout_threshold = timedelta(hours=self.position_timeout_hours)
            return datetime.now() - entry_time > timeout_threshold
        except Exception as e:
            logger.error(f"포지션 타임아웃 확인 실패: {e}")
            return False
    
    def update_daily_pnl(self, realized_pnl: float):
        """일일 손익 업데이트"""
        try:
            self.daily_pnl += realized_pnl
            logger.debug(f"일일 손익 업데이트: {self.daily_pnl:.2f}")
        except Exception as e:
            logger.error(f"일일 손익 업데이트 실패: {e}")
    
    def update_drawdown(self, current_balance: float):
        """드로우다운 업데이트"""
        try:
            if current_balance > self.peak_balance:
                self.peak_balance = current_balance
                self.current_drawdown = 0.0
            else:
                self.current_drawdown = (self.peak_balance - current_balance) / self.peak_balance
            
            logger.debug(f"드로우다운 업데이트: {self.current_drawdown:.2%}")
        except Exception as e:
            logger.error(f"드로우다운 업데이트 실패: {e}")
    
    def add_position(self, symbol: str, side: str, size: float, price: float, 
                    exchange_type: str = 'spot', stop_loss_price: float = 0, 
                    take_profit_price: float = 0):
        """포지션 추가"""
        try:
            self.positions[symbol] = {
                'symbol': symbol,
                'side': side,
                'size': size,
                'price': price,
                'exchange_type': exchange_type,
                'stop_loss_price': stop_loss_price,
                'take_profit_price': take_profit_price,
                'entry_time': datetime.now(),
                'unrealized_pnl': 0.0,
                'current_price': price
            }
            logger.info(f"포지션 추가: {symbol} {side} {size} @ {price}")
        except Exception as e:
            logger.error(f"포지션 추가 실패: {e}")
    
    def remove_position(self, symbol: str):
        """포지션 제거"""
        try:
            if symbol in self.positions:
                del self.positions[symbol]
                logger.info(f"포지션 제거: {symbol}")
        except Exception as e:
            logger.error(f"포지션 제거 실패: {e}")
    
    def get_risk_alerts(self) -> List[Dict[str, Any]]:
        """리스크 알림 조회"""
        try:
            alerts = self.risk_alerts.copy()
            self.risk_alerts.clear()  # 조회 후 클리어
            return alerts
        except Exception as e:
            logger.error(f"리스크 알림 조회 실패: {e}")
            return []
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """리스크 요약 정보"""
        try:
            total_position_value = sum(
                pos['size'] * pos['current_price'] for pos in self.positions.values()
            )
            
            total_unrealized_pnl = sum(
                pos['unrealized_pnl'] for pos in self.positions.values()
            )
            
            short_position_value = sum(
                pos['size'] * pos['current_price'] for pos in self.positions.values()
                if pos['side'] == 'sell' and pos['exchange_type'] == 'futures'
            )
            
            return {
                'daily_pnl': self.daily_pnl,
                'current_drawdown': self.current_drawdown,
                'peak_balance': self.peak_balance,
                'total_positions': len(self.positions),
                'total_position_value': total_position_value,
                'total_unrealized_pnl': total_unrealized_pnl,
                'short_position_value': short_position_value,
                'risk_alerts_count': len(self.risk_alerts)
            }
        except Exception as e:
            logger.error(f"리스크 요약 정보 조회 실패: {e}")
            return {}
    
    def reset_daily_metrics(self):
        """일일 메트릭 초기화"""
        try:
            self.daily_pnl = 0.0
            logger.info("일일 메트릭 초기화 완료")
        except Exception as e:
            logger.error(f"일일 메트릭 초기화 실패: {e}")
    
    def emergency_stop(self, reason: str = "Emergency stop triggered"):
        """비상 정지"""
        try:
            self.risk_alerts.append({
                'type': 'emergency_stop',
                'symbol': 'ALL',
                'message': f"비상 정지: {reason}",
                'timestamp': datetime.now()
            })
            logger.critical(f"비상 정지 발생: {reason}")
        except Exception as e:
            logger.error(f"비상 정지 실패: {e}")