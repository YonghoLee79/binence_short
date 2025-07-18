#!/usr/bin/env python3
"""
텔레그램 알림 모듈
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram_bot import TelegramBot
from utils import logger


class TelegramNotifications:
    """텔레그램 알림 관리 클래스"""
    
    def __init__(self):
        self.telegram = TelegramBot()
        self.enabled = self.telegram.enabled
        
        if self.enabled:
            logger.info("텔레그램 알림 시스템 초기화 완료")
            self.send_startup_message()
        else:
            logger.warning("텔레그램 알림이 비활성화되어 있습니다")
    
    def send_startup_message(self):
        """봇 시작 알림"""
        try:
            message = """
🚀 <b>트레이딩 봇 시작</b>

📅 시작 시간: {}
💰 초기 상태: 시스템 점검 중
🔄 모드: 실시간 거래

<i>봇이 정상적으로 시작되었습니다.</i>
            """.format(
                __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ).strip()
            
            self.telegram.send_message(message)
            logger.info("봇 시작 알림 전송 완료")
        except Exception as e:
            logger.error(f"시작 알림 전송 실패: {e}")
    
    def send_trade_notification(self, trade_info: dict):
        """거래 알림"""
        if not self.enabled:
            return
        
        try:
            side_emoji = "📈" if trade_info.get('side') == 'buy' else "📉"
            
            message = f"""
{side_emoji} <b>거래 실행</b>

🏷️ 심볼: {trade_info.get('symbol', 'N/A')}
📊 방향: {trade_info.get('side', 'N/A').upper()}
🔢 수량: {trade_info.get('size', 0)}
💵 가격: ${trade_info.get('price', 0):,.2f}
💰 총액: ${(trade_info.get('size', 0) * trade_info.get('price', 0)):,.2f}
📍 거래소: {trade_info.get('exchange_type', 'spot').upper()}

<i>거래가 성공적으로 실행되었습니다.</i>
            """.strip()
            
            self.telegram.send_message(message)
            logger.info(f"거래 알림 전송: {trade_info.get('symbol')} {trade_info.get('side')}")
        except Exception as e:
            logger.error(f"거래 알림 전송 실패: {e}")
    
    def send_portfolio_update(self, portfolio_info: dict):
        """포트폴리오 업데이트 알림"""
        if not self.enabled:
            return
        
        try:
            pnl_emoji = "💚" if portfolio_info.get('total_pnl', 0) >= 0 else "❤️"
            
            message = f"""
💼 <b>포트폴리오 업데이트</b>

💰 현재 잔고: ${portfolio_info.get('current_balance', 0):,.2f}
{pnl_emoji} 총 손익: ${portfolio_info.get('total_pnl', 0):+,.2f} ({portfolio_info.get('total_pnl_pct', 0):+.2f}%)
📊 활성 포지션: {portfolio_info.get('positions_count', 0)}개
📈 총 거래: {portfolio_info.get('total_trades', 0)}회

<i>포트폴리오 상태가 업데이트되었습니다.</i>
            """.strip()
            
            self.telegram.send_message(message)
            logger.info("포트폴리오 업데이트 알림 전송 완료")
        except Exception as e:
            logger.error(f"포트폴리오 알림 전송 실패: {e}")
    
    def send_risk_alert(self, alert_info: dict):
        """리스크 알림"""
        if not self.enabled:
            return
        
        try:
            alert_type = alert_info.get('type', 'unknown')
            severity = alert_info.get('severity', 'medium')
            
            emoji_map = {
                'stop_loss': '🛑',
                'take_profit': '🎯',
                'timeout': '⏰',
                'emergency_stop': '🚨',
                'daily_loss': '📉',
                'max_drawdown': '📊'
            }
            
            severity_map = {
                'low': '🟡',
                'medium': '🟠', 
                'high': '🔴',
                'critical': '🚨'
            }
            
            alert_emoji = emoji_map.get(alert_type, '⚠️')
            severity_emoji = severity_map.get(severity, '🟠')
            
            message = f"""
{alert_emoji} <b>리스크 알림</b> {severity_emoji}

🏷️ 유형: {alert_type.replace('_', ' ').title()}
📍 심볼: {alert_info.get('symbol', 'N/A')}
⚠️ 경고도: {severity.upper()}
📝 메시지: {alert_info.get('message', '상세 정보 없음')}

<i>즉시 확인이 필요합니다.</i>
            """.strip()
            
            self.telegram.send_message(message)
            logger.warning(f"리스크 알림 전송: {alert_type} - {alert_info.get('symbol')}")
        except Exception as e:
            logger.error(f"리스크 알림 전송 실패: {e}")
    
    def send_system_status(self, status_info: dict):
        """시스템 상태 알림"""
        if not self.enabled:
            return
        
        try:
            status = status_info.get('status', 'unknown')
            status_emoji = "🟢" if status == 'running' else "🔴" if status == 'error' else "🟡"
            
            message = f"""
🖥️ <b>시스템 상태</b> {status_emoji}

📊 상태: {status.upper()}
💾 메모리: {status_info.get('memory_percent', 0):.1f}%
⚡ CPU: {status_info.get('cpu_percent', 0):.1f}%
🌐 네트워크: {status_info.get('network_status', 'unknown').upper()}
⏱️ 업타임: {status_info.get('uptime_hours', 0):.1f}시간

<i>시스템 상태 점검 완료</i>
            """.strip()
            
            self.telegram.send_message(message)
            logger.info("시스템 상태 알림 전송 완료")
        except Exception as e:
            logger.error(f"시스템 상태 알림 전송 실패: {e}")
    
    def send_daily_summary(self, summary_info: dict):
        """일일 요약 알림"""
        if not self.enabled:
            return
        
        try:
            message = f"""
📊 <b>일일 거래 요약</b>

📅 날짜: {summary_info.get('date', '오늘')}
💰 일일 손익: ${summary_info.get('daily_pnl', 0):+,.2f}
📈 거래 횟수: {summary_info.get('trades_count', 0)}회
🎯 승률: {summary_info.get('win_rate', 0):.1f}%
📊 최고 수익: ${summary_info.get('max_profit', 0):,.2f}
📉 최대 손실: ${summary_info.get('max_loss', 0):,.2f}

<i>오늘의 거래 결과입니다.</i>
            """.strip()
            
            self.telegram.send_message(message)
            logger.info("일일 요약 알림 전송 완료")
        except Exception as e:
            logger.error(f"일일 요약 알림 전송 실패: {e}")
    
    def send_shutdown_message(self):
        """봇 종료 알림"""
        if not self.enabled:
            return
        
        try:
            message = f"""
🔴 <b>트레이딩 봇 종료</b>

📅 종료 시간: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
💡 상태: 정상 종료

<i>봇이 안전하게 종료되었습니다.</i>
            """.strip()
            
            self.telegram.send_message(message)
            logger.info("봇 종료 알림 전송 완료")
        except Exception as e:
            logger.error(f"종료 알림 전송 실패: {e}")