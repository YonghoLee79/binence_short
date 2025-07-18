#!/usr/bin/env python3
"""
현물 + 선물 하이브리드 포트폴리오 전략
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import logger


class HybridPortfolioStrategy:
    """현물 + 선물 하이브리드 포트폴리오 전략 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # 포트폴리오 할당
        self.spot_allocation = config.get('spot_allocation', 0.6)  # 현물 60%
        self.futures_allocation = config.get('futures_allocation', 0.4)  # 선물 40%
        
        # 전략 설정
        self.arbitrage_threshold = config.get('arbitrage_threshold', 0.002)  # 0.2% 프리미엄
        self.rebalance_threshold = config.get('rebalance_threshold', 0.05)  # 5% 편차시 리밸런싱
        self.max_leverage = config.get('max_leverage', 3)  # 최대 3배 레버리지
        
        # 리스크 관리
        self.max_position_size = config.get('max_position_size', 0.2)  # 단일 포지션 최대 20%
        self.correlation_limit = config.get('correlation_limit', 0.7)  # 상관관계 한계
        
        # 상태 추적
        self.current_positions = {'spot': {}, 'futures': {}}
        self.portfolio_history = []
        self.last_rebalance = datetime.now()
        
        logger.info("하이브리드 포트폴리오 전략 초기화 완료")
    
    def analyze_market_opportunity(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """시장 기회 분석"""
        try:
            opportunities = {
                'arbitrage': [],
                'trend_following': [],
                'hedging': [],
                'momentum': []
            }
            
            for symbol in market_data.keys():
                if symbol not in market_data:
                    continue
                
                data = market_data[symbol]
                spot_price = data.get('spot_ticker', {}).get('last', 0)
                futures_price = data.get('futures_ticker', {}).get('last', 0)
                
                if spot_price <= 0 or futures_price <= 0:
                    continue
                
                # 1. 아비트라지 기회 분석
                premium = (futures_price - spot_price) / spot_price
                if abs(premium) > self.arbitrage_threshold:
                    opportunities['arbitrage'].append({
                        'symbol': symbol,
                        'premium': premium,
                        'spot_price': spot_price,
                        'futures_price': futures_price,
                        'opportunity_type': 'long_spot_short_futures' if premium > 0 else 'short_spot_long_futures',
                        'expected_profit': abs(premium),
                        'confidence': min(abs(premium) / self.arbitrage_threshold, 1.0)
                    })
                
                # 2. 트렌드 추종 기회
                spot_signals = data.get('spot_signals', {})
                futures_signals = data.get('futures_signals', {})
                
                if spot_signals and futures_signals:
                    spot_strength = spot_signals.get('combined_signal', 0)
                    futures_strength = futures_signals.get('combined_signal', 0)
                    
                    # 현물과 선물 신호가 같은 방향이면 트렌드 추종
                    if abs(spot_strength) > 0.3 and abs(futures_strength) > 0.3:
                        if (spot_strength > 0 and futures_strength > 0) or (spot_strength < 0 and futures_strength < 0):
                            opportunities['trend_following'].append({
                                'symbol': symbol,
                                'direction': 'bullish' if spot_strength > 0 else 'bearish',
                                'spot_strength': spot_strength,
                                'futures_strength': futures_strength,
                                'confidence': (abs(spot_strength) + abs(futures_strength)) / 2
                            })
                
                # 3. 헤징 기회 (현물 보유시 선물로 헤지)
                current_spot_position = self.current_positions['spot'].get(symbol, {})
                if current_spot_position and abs(futures_strength) > 0.5:
                    if (current_spot_position.get('side') == 'buy' and futures_strength < -0.5) or \
                       (current_spot_position.get('side') == 'sell' and futures_strength > 0.5):
                        opportunities['hedging'].append({
                            'symbol': symbol,
                            'hedge_type': 'protective_short' if current_spot_position.get('side') == 'buy' else 'protective_long',
                            'spot_position': current_spot_position,
                            'futures_strength': futures_strength,
                            'confidence': abs(futures_strength)
                        })
                
                # 4. 모멘텀 기회 (급격한 가격 변동 활용)
                spot_indicators = data.get('spot_indicators', {})
                futures_indicators = data.get('futures_indicators', {})
                
                if spot_indicators and futures_indicators:
                    spot_rsi = spot_indicators.get('rsi', {}).get('current', 50)
                    futures_rsi = futures_indicators.get('rsi', {}).get('current', 50)
                    
                    # RSI 극값에서 모멘텀 기회
                    if (spot_rsi < 30 and futures_rsi < 30) or (spot_rsi > 70 and futures_rsi > 70):
                        opportunities['momentum'].append({
                            'symbol': symbol,
                            'type': 'oversold_bounce' if spot_rsi < 30 else 'overbought_correction',
                            'spot_rsi': spot_rsi,
                            'futures_rsi': futures_rsi,
                            'confidence': abs(50 - spot_rsi) / 50
                        })
            
            return opportunities
            
        except Exception as e:
            logger.error(f"시장 기회 분석 실패: {e}")
            return {'arbitrage': [], 'trend_following': [], 'hedging': [], 'momentum': []}
    
    def generate_portfolio_signals(self, opportunities: Dict[str, Any], 
                                 portfolio_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """포트폴리오 전략 신호 생성"""
        try:
            signals = []
            current_balance = portfolio_state.get('total_balance', 0)
            spot_balance = current_balance * self.spot_allocation
            futures_balance = current_balance * self.futures_allocation
            
            # 1. 아비트라지 신호 (최우선)
            for arb in sorted(opportunities['arbitrage'], key=lambda x: x['expected_profit'], reverse=True):
                if arb['confidence'] > 0.7:
                    position_size = min(spot_balance * 0.3, futures_balance * 0.3)  # 30%까지
                    
                    if arb['opportunity_type'] == 'long_spot_short_futures':
                        signals.extend([
                            {
                                'strategy': 'arbitrage',
                                'symbol': arb['symbol'],
                                'exchange_type': 'spot',
                                'action': 'buy',
                                'size': position_size / arb['spot_price'],
                                'confidence': arb['confidence'],
                                'expected_return': arb['expected_profit'],
                                'priority': 1
                            },
                            {
                                'strategy': 'arbitrage',
                                'symbol': arb['symbol'],
                                'exchange_type': 'futures',
                                'action': 'sell',
                                'size': position_size / arb['futures_price'],
                                'confidence': arb['confidence'],
                                'expected_return': arb['expected_profit'],
                                'priority': 1
                            }
                        ])
                    else:
                        signals.extend([
                            {
                                'strategy': 'arbitrage',
                                'symbol': arb['symbol'],
                                'exchange_type': 'spot',
                                'action': 'sell',
                                'size': position_size / arb['spot_price'],
                                'confidence': arb['confidence'],
                                'expected_return': arb['expected_profit'],
                                'priority': 1
                            },
                            {
                                'strategy': 'arbitrage',
                                'symbol': arb['symbol'],
                                'exchange_type': 'futures',
                                'action': 'buy',
                                'size': position_size / arb['futures_price'],
                                'confidence': arb['confidence'],
                                'expected_return': arb['expected_profit'],
                                'priority': 1
                            }
                        ])
            
            # 2. 트렌드 추종 신호
            for trend in sorted(opportunities['trend_following'], key=lambda x: x['confidence'], reverse=True):
                if trend['confidence'] > 0.6:
                    # 현물은 주요 포지션, 선물은 레버리지 활용
                    spot_size = spot_balance * 0.2 / portfolio_state.get('avg_price', {}).get(trend['symbol'], 1)
                    futures_size = futures_balance * 0.3 / portfolio_state.get('avg_price', {}).get(trend['symbol'], 1)
                    
                    action = 'buy' if trend['direction'] == 'bullish' else 'sell'
                    
                    signals.extend([
                        {
                            'strategy': 'trend_following',
                            'symbol': trend['symbol'],
                            'exchange_type': 'spot',
                            'action': action,
                            'size': spot_size,
                            'confidence': trend['confidence'],
                            'priority': 2
                        },
                        {
                            'strategy': 'trend_following',
                            'symbol': trend['symbol'],
                            'exchange_type': 'futures',
                            'action': action,
                            'size': futures_size * min(self.max_leverage, 2),  # 2배 레버리지
                            'confidence': trend['confidence'],
                            'priority': 2
                        }
                    ])
            
            # 3. 헤징 신호
            for hedge in opportunities['hedging']:
                if hedge['confidence'] > 0.7:
                    spot_position = hedge['spot_position']
                    hedge_size = spot_position.get('size', 0) * 0.8  # 80% 헤지
                    
                    hedge_action = 'sell' if hedge['hedge_type'] == 'protective_short' else 'buy'
                    
                    signals.append({
                        'strategy': 'hedging',
                        'symbol': hedge['symbol'],
                        'exchange_type': 'futures',
                        'action': hedge_action,
                        'size': hedge_size,
                        'confidence': hedge['confidence'],
                        'priority': 3
                    })
            
            # 4. 모멘텀 신호 (소규모)
            for momentum in sorted(opportunities['momentum'], key=lambda x: x['confidence'], reverse=True):
                if momentum['confidence'] > 0.8:
                    momentum_size = min(spot_balance, futures_balance) * 0.1  # 10%만
                    
                    if momentum['type'] == 'oversold_bounce':
                        # 과매도 반등 기대 - 롱 포지션
                        signals.extend([
                            {
                                'strategy': 'momentum',
                                'symbol': momentum['symbol'],
                                'exchange_type': 'spot',
                                'action': 'buy',
                                'size': momentum_size / portfolio_state.get('avg_price', {}).get(momentum['symbol'], 1),
                                'confidence': momentum['confidence'],
                                'priority': 4
                            },
                            {
                                'strategy': 'momentum',
                                'symbol': momentum['symbol'],
                                'exchange_type': 'futures',
                                'action': 'buy',
                                'size': momentum_size * 1.5 / portfolio_state.get('avg_price', {}).get(momentum['symbol'], 1),
                                'confidence': momentum['confidence'],
                                'priority': 4
                            }
                        ])
                    else:
                        # 과매수 조정 기대 - 숏 포지션
                        signals.append({
                            'strategy': 'momentum',
                            'symbol': momentum['symbol'],
                            'exchange_type': 'futures',
                            'action': 'sell',
                            'size': momentum_size * 2 / portfolio_state.get('avg_price', {}).get(momentum['symbol'], 1),
                            'confidence': momentum['confidence'],
                            'priority': 4
                        })
            
            # 우선순위별 정렬
            signals.sort(key=lambda x: x['priority'])
            
            return signals[:10]  # 최대 10개 신호만
            
        except Exception as e:
            logger.error(f"포트폴리오 신호 생성 실패: {e}")
            return []
    
    def check_rebalancing_needed(self, portfolio_state: Dict[str, Any]) -> bool:
        """리밸런싱 필요 여부 확인"""
        try:
            total_balance = portfolio_state.get('total_balance', 0)
            spot_value = portfolio_state.get('spot_balance', 0)
            futures_value = portfolio_state.get('futures_balance', 0)
            
            if total_balance <= 0:
                return False
            
            current_spot_ratio = spot_value / total_balance
            current_futures_ratio = futures_value / total_balance
            
            spot_deviation = abs(current_spot_ratio - self.spot_allocation)
            futures_deviation = abs(current_futures_ratio - self.futures_allocation)
            
            # 임계값 초과 또는 일정 시간 경과시 리밸런싱
            time_passed = datetime.now() - self.last_rebalance
            time_threshold = timedelta(hours=12)  # 12시간마다
            
            needs_rebalancing = (
                spot_deviation > self.rebalance_threshold or
                futures_deviation > self.rebalance_threshold or
                time_passed > time_threshold
            )
            
            if needs_rebalancing:
                logger.info(f"리밸런싱 필요: 현물비율 {current_spot_ratio:.2%} (목표: {self.spot_allocation:.2%}), "
                          f"선물비율 {current_futures_ratio:.2%} (목표: {self.futures_allocation:.2%})")
            
            return needs_rebalancing
            
        except Exception as e:
            logger.error(f"리밸런싱 확인 실패: {e}")
            return False
    
    def generate_rebalancing_orders(self, portfolio_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """리밸런싱 주문 생성"""
        try:
            orders = []
            total_balance = portfolio_state.get('total_balance', 0)
            current_spot_value = portfolio_state.get('spot_balance', 0)
            current_futures_value = portfolio_state.get('futures_balance', 0)
            
            target_spot_value = total_balance * self.spot_allocation
            target_futures_value = total_balance * self.futures_allocation
            
            spot_adjustment = target_spot_value - current_spot_value
            futures_adjustment = target_futures_value - current_futures_value
            
            # 현물 조정
            if abs(spot_adjustment) > total_balance * 0.01:  # 1% 이상 차이
                main_symbol = 'BTC/USDT'  # 메인 심볼로 조정
                current_price = portfolio_state.get('current_prices', {}).get(main_symbol, 0)
                
                if current_price > 0:
                    if spot_adjustment > 0:
                        # 현물 매수 필요
                        orders.append({
                            'strategy': 'rebalancing',
                            'symbol': main_symbol,
                            'exchange_type': 'spot',
                            'action': 'buy',
                            'size': abs(spot_adjustment) / current_price,
                            'confidence': 1.0,
                            'priority': 0  # 최우선
                        })
                    else:
                        # 현물 매도 필요
                        orders.append({
                            'strategy': 'rebalancing',
                            'symbol': main_symbol,
                            'exchange_type': 'spot',
                            'action': 'sell',
                            'size': abs(spot_adjustment) / current_price,
                            'confidence': 1.0,
                            'priority': 0
                        })
            
            # 선물 조정
            if abs(futures_adjustment) > total_balance * 0.01:
                main_symbol = 'BTC/USDT'
                current_price = portfolio_state.get('current_prices', {}).get(main_symbol, 0)
                
                if current_price > 0:
                    if futures_adjustment > 0:
                        # 선물 매수 필요
                        orders.append({
                            'strategy': 'rebalancing',
                            'symbol': main_symbol,
                            'exchange_type': 'futures',
                            'action': 'buy',
                            'size': abs(futures_adjustment) / current_price,
                            'confidence': 1.0,
                            'priority': 0
                        })
                    else:
                        # 선물 매도 필요
                        orders.append({
                            'strategy': 'rebalancing',
                            'symbol': main_symbol,
                            'exchange_type': 'futures',
                            'action': 'sell',
                            'size': abs(futures_adjustment) / current_price,
                            'confidence': 1.0,
                            'priority': 0
                        })
            
            if orders:
                self.last_rebalance = datetime.now()
                logger.info(f"리밸런싱 주문 생성: {len(orders)}개")
            
            return orders
            
        except Exception as e:
            logger.error(f"리밸런싱 주문 생성 실패: {e}")
            return []
    
    def calculate_portfolio_metrics(self, portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
        """포트폴리오 메트릭 계산"""
        try:
            total_balance = portfolio_state.get('total_balance', 0)
            spot_balance = portfolio_state.get('spot_balance', 0)
            futures_balance = portfolio_state.get('futures_balance', 0)
            
            metrics = {
                'total_value': total_balance,
                'spot_value': spot_balance,
                'futures_value': futures_balance,
                'spot_ratio': spot_balance / total_balance if total_balance > 0 else 0,
                'futures_ratio': futures_balance / total_balance if total_balance > 0 else 0,
                'target_spot_ratio': self.spot_allocation,
                'target_futures_ratio': self.futures_allocation,
                'rebalancing_needed': self.check_rebalancing_needed(portfolio_state),
                'last_rebalance': self.last_rebalance.isoformat(),
                'total_positions': len(self.current_positions['spot']) + len(self.current_positions['futures']),
                'spot_positions': len(self.current_positions['spot']),
                'futures_positions': len(self.current_positions['futures'])
            }
            
            # 편차 계산
            metrics['spot_deviation'] = abs(metrics['spot_ratio'] - self.spot_allocation)
            metrics['futures_deviation'] = abs(metrics['futures_ratio'] - self.futures_allocation)
            
            # 리스크 메트릭
            metrics['leverage_ratio'] = futures_balance / spot_balance if spot_balance > 0 else 0
            metrics['risk_level'] = 'low' if metrics['leverage_ratio'] < 1 else 'medium' if metrics['leverage_ratio'] < 2 else 'high'
            
            return metrics
            
        except Exception as e:
            logger.error(f"포트폴리오 메트릭 계산 실패: {e}")
            return {}
    
    def update_positions(self, symbol: str, exchange_type: str, position_data: Dict[str, Any]):
        """포지션 업데이트"""
        try:
            if exchange_type in ['spot', 'futures']:
                self.current_positions[exchange_type][symbol] = position_data
                logger.debug(f"포지션 업데이트: {exchange_type} {symbol}")
        except Exception as e:
            logger.error(f"포지션 업데이트 실패: {e}")
    
    def remove_position(self, symbol: str, exchange_type: str):
        """포지션 제거"""
        try:
            if exchange_type in ['spot', 'futures'] and symbol in self.current_positions[exchange_type]:
                del self.current_positions[exchange_type][symbol]
                logger.debug(f"포지션 제거: {exchange_type} {symbol}")
        except Exception as e:
            logger.error(f"포지션 제거 실패: {e}")
    
    def get_strategy_summary(self) -> Dict[str, Any]:
        """전략 요약 정보 반환"""
        return {
            'strategy_type': 'hybrid_spot_futures',
            'spot_allocation': self.spot_allocation,
            'futures_allocation': self.futures_allocation,
            'arbitrage_threshold': self.arbitrage_threshold,
            'max_leverage': self.max_leverage,
            'current_positions': self.current_positions,
            'last_rebalance': self.last_rebalance.isoformat()
        }