#!/usr/bin/env python3
"""
현물 + 선물 하이브리드 트레이딩 봇 v2
고급 포트폴리오 전략 적용
"""

import asyncio
import time
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import config
from utils import logger
from modules import (
    TechnicalAnalyzer,
    ExchangeInterface,
    StrategyEngine,
    RiskManager,
    PortfolioManager,
    TelegramNotifications
)
from modules.hybrid_portfolio_strategy import HybridPortfolioStrategy
from modules.database_manager import get_database_manager


class HybridTradingBotV2:
    """현물 + 선물 하이브리드 트레이딩 봇 v2"""
    
    def __init__(self):
        self.config = config
        self.logger = logger
        self.running = False
        self.cycle_count = 0
        self.start_time = datetime.now()
        
        # 컴포넌트 초기화
        self._initialize_components()
        
        # 하이브리드 전략 초기화
        hybrid_config = {
            'spot_allocation': self.config.SPOT_ALLOCATION,
            'futures_allocation': self.config.FUTURES_ALLOCATION,
            'arbitrage_threshold': 0.003,  # 0.3% 프리미엄
            'rebalance_threshold': 0.08,   # 8% 편차시 리밸런싱
            'max_leverage': 3,
            'max_position_size': 0.15,     # 단일 포지션 최대 15%
            'correlation_limit': 0.75
        }
        self.hybrid_strategy = HybridPortfolioStrategy(hybrid_config)
        
        # 상태 추적
        self.last_portfolio_update = datetime.now()
        self.last_telegram_summary = datetime.now()
        self.performance_metrics = {
            'total_trades': 0,
            'successful_trades': 0,
            'total_pnl': 0.0,
            'daily_pnl': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0
        }
        
        self.logger.info("하이브리드 트레이딩 봇 v2 초기화 완료")
        
        # 시작 알림 전송
        self._send_startup_notification()
    
    def _initialize_components(self):
        """컴포넌트 초기화"""
        try:
            # 거래소 인터페이스
            exchange_config = {
                'api_key': self.config.BINANCE_API_KEY,
                'secret_key': self.config.BINANCE_SECRET_KEY,
                'use_testnet': self.config.USE_TESTNET
            }
            self.exchange = ExchangeInterface(exchange_config)
            
            # 리스크 관리자
            risk_config = self.config.get_risk_config()
            self.risk_manager = RiskManager(risk_config)
            
            # 기술적 분석기
            technical_config = self.config.get_technical_config()
            self.technical_analyzer = TechnicalAnalyzer(technical_config)
            
            # 전략 엔진
            strategy_config = self.config.get_strategy_config()
            strategy_config.update(technical_config)
            self.strategy_engine = StrategyEngine(strategy_config, self.exchange)
            
            # 포트폴리오 관리자
            portfolio_config = {
                'initial_balance': self.config.INITIAL_BALANCE,
                'spot_allocation': self.config.SPOT_ALLOCATION,
                'futures_allocation': self.config.FUTURES_ALLOCATION,
                'rebalance_threshold': self.config.REBALANCE_THRESHOLD,
                'trading_symbols': self.config.TRADING_SYMBOLS,
                'fees': self.config.FEES
            }
            portfolio_config.update(risk_config)
            self.portfolio_manager = PortfolioManager(
                portfolio_config, self.exchange, self.risk_manager
            )
            
            # 텔레그램 알림
            self.telegram = TelegramNotifications()
            
            # 데이터베이스
            self.db = get_database_manager()
            
            self.logger.info("모든 컴포넌트 초기화 완료")
            
        except Exception as e:
            self.logger.error(f"컴포넌트 초기화 실패: {e}")
            raise
    
    def _send_startup_notification(self):
        """시작 알림 전송"""
        try:
            startup_info = {
                'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'strategy': 'Hybrid Spot + Futures',
                'spot_allocation': f"{self.config.SPOT_ALLOCATION:.0%}",
                'futures_allocation': f"{self.config.FUTURES_ALLOCATION:.0%}",
                'trading_symbols': ', '.join(self.config.TRADING_SYMBOLS[:3]) + f" (+{len(self.config.TRADING_SYMBOLS)-3} more)",
                'mode': 'TESTNET' if self.config.USE_TESTNET else 'LIVE TRADING'
            }
            
            message = f"""
🚀 <b>하이브리드 트레이딩 봇 v2 시작</b>

📅 시작 시간: {startup_info['start_time']}
🎯 전략: {startup_info['strategy']}
💰 현물 할당: {startup_info['spot_allocation']}
⚡ 선물 할당: {startup_info['futures_allocation']}
📊 거래 심볼: {startup_info['trading_symbols']}
🔧 모드: <b>{startup_info['mode']}</b>

🔄 <b>전략 특징:</b>
• 아비트라지 기회 포착
• 트렌드 추종 + 헤징
• 자동 리밸런싱
• 다층 리스크 관리

<i>하이브리드 포트폴리오 전략으로 시작합니다!</i>
            """.strip()
            
            self.telegram.telegram.send_message(message)
            
        except Exception as e:
            self.logger.error(f"시작 알림 전송 실패: {e}")
    
    async def collect_market_data(self) -> Dict[str, Any]:
        """시장 데이터 수집"""
        try:
            market_data = {}
            
            # 병렬로 모든 심볼의 데이터 수집
            tasks = []
            for symbol in self.config.TRADING_SYMBOLS:
                tasks.append(self._fetch_symbol_data(symbol))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.warning(f"데이터 수집 실패 ({self.config.TRADING_SYMBOLS[i]}): {result}")
                    continue
                
                if result:
                    symbol = self.config.TRADING_SYMBOLS[i]
                    market_data[symbol] = result
            
            self.logger.info(f"시장 데이터 수집 완료: {len(market_data)}개 심볼")
            return market_data
            
        except Exception as e:
            self.logger.error(f"시장 데이터 수집 실패: {e}")
            return {}
    
    async def _fetch_symbol_data(self, symbol: str) -> Dict[str, Any]:
        """개별 심볼 데이터 수집"""
        try:
            # 현물 및 선물 티커
            spot_ticker = self.exchange.get_ticker(symbol, 'spot')
            futures_ticker = self.exchange.get_ticker(symbol, 'future')
            
            # OHLCV 데이터
            spot_ohlcv = self.exchange.get_ohlcv(symbol, '1h', 100, 'spot')
            futures_ohlcv = self.exchange.get_ohlcv(symbol, '1h', 100, 'future')
            
            if spot_ohlcv is None or futures_ohlcv is None or spot_ohlcv.empty or futures_ohlcv.empty:
                return None
            
            # 기술적 분석
            spot_indicators = self.technical_analyzer.get_all_indicators(spot_ohlcv)
            futures_indicators = self.technical_analyzer.get_all_indicators(futures_ohlcv)
            
            # 신호 생성
            spot_signals = self.technical_analyzer.generate_signals(spot_indicators)
            futures_signals = self.technical_analyzer.generate_signals(futures_indicators)
            
            return {
                'symbol': symbol,
                'spot_ticker': spot_ticker,
                'futures_ticker': futures_ticker,
                'spot_ohlcv': spot_ohlcv,
                'futures_ohlcv': futures_ohlcv,
                'spot_indicators': spot_indicators,
                'futures_indicators': futures_indicators,
                'spot_signals': spot_signals,
                'futures_signals': futures_signals,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"심볼 데이터 수집 실패 ({symbol}): {e}")
            return None
    
    def analyze_and_execute_strategy(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """전략 분석 및 실행"""
        try:
            # 포트폴리오 상태 업데이트
            portfolio_state = self.portfolio_manager.get_portfolio_summary()
            
            # 하이브리드 전략 기회 분석
            opportunities = self.hybrid_strategy.analyze_market_opportunity(market_data)
            
            self.logger.info(f"전략 기회 발견: "
                           f"아비트라지 {len(opportunities['arbitrage'])}개, "
                           f"트렌드 {len(opportunities['trend_following'])}개, "
                           f"헤징 {len(opportunities['hedging'])}개, "
                           f"모멘텀 {len(opportunities['momentum'])}개")
            
            # 리밸런싱 확인
            executed_trades = []
            if self.hybrid_strategy.check_rebalancing_needed(portfolio_state):
                rebalancing_orders = self.hybrid_strategy.generate_rebalancing_orders(portfolio_state)
                for order in rebalancing_orders:
                    trade_result = self._execute_trade(order)
                    if trade_result and trade_result.get('success'):
                        executed_trades.append(trade_result)
                        self._send_trade_notification(trade_result, order)
            
            # 전략 신호 생성
            signals = self.hybrid_strategy.generate_portfolio_signals(opportunities, portfolio_state)
            
            # 신호 실행
            for signal in signals[:5]:  # 최대 5개까지만
                # 리스크 검증
                risk_check = self.risk_manager.validate_trade(
                    symbol=signal['symbol'],
                    side=signal['action'],
                    size=signal['size'],
                    price=market_data.get(signal['symbol'], {}).get(f"{signal['exchange_type']}_ticker", {}).get('last', 0),
                    current_balance=portfolio_state['current_balance'],
                    exchange_type=signal['exchange_type']
                )
                
                if risk_check['is_valid']:
                    # 거래 실행
                    trade_result = self._execute_trade(signal)
                    if trade_result and trade_result.get('success'):
                        executed_trades.append(trade_result)
                        self._send_trade_notification(trade_result, signal)
                        
                        # 포지션 업데이트
                        self.hybrid_strategy.update_positions(
                            signal['symbol'], 
                            signal['exchange_type'], 
                            trade_result
                        )
                else:
                    self.logger.warning(f"리스크 검증 실패: {signal['symbol']} - {risk_check['errors']}")
            
            return executed_trades
            
        except Exception as e:
            self.logger.error(f"전략 분석 및 실행 실패: {e}")
            return []
    
    def _execute_trade(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """거래 실행"""
        try:
            result = self.portfolio_manager.execute_trade(
                symbol=signal['symbol'],
                side=signal['action'],
                size=signal['size'],
                price=None,  # 시장가
                exchange_type=signal['exchange_type'],
                order_type='market'
            )
            
            if result and result.get('success'):
                # 데이터베이스에 기록
                trade_data = {
                    'symbol': signal['symbol'],
                    'side': signal['action'],
                    'size': signal['size'],
                    'price': result.get('price', 0),
                    'exchange_type': signal['exchange_type'],
                    'order_type': 'market',
                    'fees': result.get('fees', 0),
                    'strategy': signal['strategy']
                }
                self.db.insert_trade(trade_data)
                
                # 성과 업데이트
                self.performance_metrics['total_trades'] += 1
                if result.get('pnl', 0) > 0:
                    self.performance_metrics['successful_trades'] += 1
                
                self.performance_metrics['win_rate'] = (
                    self.performance_metrics['successful_trades'] / 
                    self.performance_metrics['total_trades'] * 100
                )
                
                self.logger.info(f"거래 실행 성공: {signal['strategy']} - {signal['symbol']} {signal['action']}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"거래 실행 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    def _send_trade_notification(self, trade_result: Dict[str, Any], signal: Dict[str, Any]):
        """거래 알림 전송"""
        try:
            trade_info = {
                'symbol': signal['symbol'],
                'side': signal['action'],
                'size': signal['size'],
                'price': trade_result.get('price', 0),
                'exchange_type': signal['exchange_type'],
                'strategy': signal['strategy'],
                'confidence': signal.get('confidence', 0)
            }
            
            # 전략별 이모지
            strategy_emoji = {
                'arbitrage': '⚖️',
                'trend_following': '📈',
                'hedging': '🛡️',
                'momentum': '🚀',
                'rebalancing': '⚖️'
            }
            
            emoji = strategy_emoji.get(signal['strategy'], '📊')
            side_emoji = "📈" if signal['action'] == 'buy' else "📉"
            
            message = f"""
{emoji} <b>{signal['strategy'].title()} 거래 실행</b> {side_emoji}

🏷️ 심볼: {signal['symbol']}
📊 방향: {signal['action'].upper()}
🔢 수량: {signal['size']:.6f}
💵 가격: ${trade_result.get('price', 0):,.2f}
💰 총액: ${signal['size'] * trade_result.get('price', 0):,.2f}
📍 거래소: {signal['exchange_type'].upper()}
🎯 신뢰도: {signal.get('confidence', 0):.1%}

<i>{signal['strategy']} 전략으로 거래 완료</i>
            """.strip()
            
            self.telegram.telegram.send_message(message)
            
        except Exception as e:
            self.logger.error(f"거래 알림 전송 실패: {e}")
    
    def _send_portfolio_update(self):
        """포트폴리오 업데이트 알림"""
        try:
            portfolio_state = self.portfolio_manager.get_portfolio_summary()
            metrics = self.hybrid_strategy.calculate_portfolio_metrics(portfolio_state)
            
            message = f"""
💼 <b>하이브리드 포트폴리오 현황</b>

💰 총 자산: ${metrics.get('total_value', 0):,.2f}
💎 현물: ${metrics.get('spot_value', 0):,.2f} ({metrics.get('spot_ratio', 0):.1%})
⚡ 선물: ${metrics.get('futures_value', 0):,.2f} ({metrics.get('futures_ratio', 0):.1%})

🎯 <b>목표 비율:</b>
• 현물: {metrics.get('target_spot_ratio', 0):.0%} (편차: {metrics.get('spot_deviation', 0):.1%})
• 선물: {metrics.get('target_futures_ratio', 0):.0%} (편차: {metrics.get('futures_deviation', 0):.1%})

📊 포지션: {metrics.get('total_positions', 0)}개 (현물 {metrics.get('spot_positions', 0)}, 선물 {metrics.get('futures_positions', 0)})
📈 총 거래: {self.performance_metrics['total_trades']}회
🎯 승률: {self.performance_metrics['win_rate']:.1f}%
⚖️ 레버리지: {metrics.get('leverage_ratio', 0):.1f}x

{'🟢 균형 상태' if not metrics.get('rebalancing_needed') else '🟡 리밸런싱 필요'}
            """.strip()
            
            self.telegram.telegram.send_message(message)
            self.last_portfolio_update = datetime.now()
            
        except Exception as e:
            self.logger.error(f"포트폴리오 업데이트 알림 실패: {e}")
    
    def _send_daily_summary(self):
        """일일 요약 전송"""
        try:
            stats = self.db.get_trading_statistics(days=1)
            
            summary_info = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'daily_pnl': stats.get('total_pnl', 0),
                'trades_count': stats.get('total_trades', 0),
                'win_rate': stats.get('win_rate', 0),
                'max_profit': stats.get('max_profit', 0),
                'max_loss': stats.get('max_loss', 0)
            }
            
            self.telegram.send_daily_summary(summary_info)
            self.last_telegram_summary = datetime.now()
            
        except Exception as e:
            self.logger.error(f"일일 요약 전송 실패: {e}")
    
    async def run_trading_cycle(self):
        """거래 사이클 실행"""
        try:
            cycle_start = time.time()
            self.cycle_count += 1
            
            self.logger.info(f"=== 하이브리드 거래 사이클 #{self.cycle_count} 시작 ===")
            
            # 1. 시장 데이터 수집
            market_data = await self.collect_market_data()
            
            if not market_data:
                self.logger.warning("시장 데이터가 없어 사이클을 건너뜁니다")
                return
            
            # 2. 전략 분석 및 실행
            executed_trades = self.analyze_and_execute_strategy(market_data)
            
            # 3. 포트폴리오 상태 업데이트
            self.portfolio_manager.update_portfolio_state()
            
            # 4. 리스크 모니터링
            alerts = self.risk_manager.get_risk_alerts()
            for alert in alerts:
                self.telegram.send_risk_alert(alert)
            
            # 5. 주기적 알림
            time_since_portfolio_update = datetime.now() - self.last_portfolio_update
            if time_since_portfolio_update > timedelta(hours=2):  # 2시간마다
                self._send_portfolio_update()
            
            time_since_daily_summary = datetime.now() - self.last_telegram_summary
            if time_since_daily_summary > timedelta(hours=24):  # 24시간마다
                self._send_daily_summary()
            
            cycle_duration = time.time() - cycle_start
            self.logger.info(f"사이클 #{self.cycle_count} 완료: {cycle_duration:.2f}초, "
                           f"거래 {len(executed_trades)}개 실행")
            
        except Exception as e:
            self.logger.error(f"거래 사이클 실행 실패: {e}")
            
            # 오류 알림
            error_alert = {
                'type': 'system_error',
                'symbol': 'SYSTEM',
                'severity': 'high',
                'message': f'거래 사이클 오류: {str(e)[:100]}'
            }
            self.telegram.send_risk_alert(error_alert)
    
    async def start(self):
        """봇 시작"""
        try:
            self.running = True
            self.logger.info("🚀 하이브리드 트레이딩 봇 v2 시작")
            
            while self.running:
                await self.run_trading_cycle()
                
                # 1분 대기
                await asyncio.sleep(60)
                
        except KeyboardInterrupt:
            self.logger.info("사용자에 의한 중단")
        except Exception as e:
            self.logger.error(f"봇 실행 실패: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """봇 중지"""
        self.running = False
        self.telegram.send_shutdown_message()
        self.logger.info("하이브리드 트레이딩 봇 v2 종료")


async def main():
    """메인 함수"""
    bot = HybridTradingBotV2()
    await bot.start()


if __name__ == "__main__":
    print("🚀 하이브리드 트레이딩 봇 v2 (현물 + 선물)")
    print("=" * 50)
    
    # 비동기 실행
    asyncio.run(main())