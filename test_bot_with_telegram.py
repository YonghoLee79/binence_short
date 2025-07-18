#!/usr/bin/env python3
"""
텔레그램 알림이 통합된 트레이딩 봇 테스트
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_bot_with_telegram():
    """텔레그램 통합 봇 테스트"""
    try:
        from modules import TelegramNotifications
        
        # 텔레그램 알림 초기화
        telegram = TelegramNotifications()
        
        if not telegram.enabled:
            print("❌ 텔레그램 알림이 비활성화되어 있습니다.")
            return False
        
        print("📨 다양한 알림 테스트 중...")
        
        # 1. 거래 알림 테스트
        trade_info = {
            'symbol': 'BTC/USDT',
            'side': 'buy',
            'size': 0.001,
            'price': 65000,
            'exchange_type': 'spot'
        }
        telegram.send_trade_notification(trade_info)
        print("✅ 거래 알림 테스트 완료")
        
        # 2. 포트폴리오 업데이트 테스트
        portfolio_info = {
            'current_balance': 1250.75,
            'total_pnl': 25.50,
            'total_pnl_pct': 2.08,
            'positions_count': 3,
            'total_trades': 45
        }
        telegram.send_portfolio_update(portfolio_info)
        print("✅ 포트폴리오 알림 테스트 완료")
        
        # 3. 리스크 알림 테스트
        alert_info = {
            'type': 'stop_loss',
            'symbol': 'ETH/USDT',
            'severity': 'high',
            'message': '스탑로스 가격에 도달했습니다'
        }
        telegram.send_risk_alert(alert_info)
        print("✅ 리스크 알림 테스트 완료")
        
        # 4. 시스템 상태 테스트
        status_info = {
            'status': 'running',
            'memory_percent': 68.5,
            'cpu_percent': 23.2,
            'network_status': 'connected',
            'uptime_hours': 12.5
        }
        telegram.send_system_status(status_info)
        print("✅ 시스템 상태 알림 테스트 완료")
        
        # 5. 일일 요약 테스트
        summary_info = {
            'date': '2025-07-19',
            'daily_pnl': 45.25,
            'trades_count': 8,
            'win_rate': 75.0,
            'max_profit': 15.80,
            'max_loss': -8.30
        }
        telegram.send_daily_summary(summary_info)
        print("✅ 일일 요약 알림 테스트 완료")
        
        # 6. 종료 알림 테스트
        telegram.send_shutdown_message()
        print("✅ 종료 알림 테스트 완료")
        
        return True
        
    except Exception as e:
        print(f"❌ 텔레그램 통합 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    print("🔧 텔레그램 통합 트레이딩 봇 테스트")
    print("=" * 50)
    
    success = test_bot_with_telegram()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 모든 텔레그램 알림이 정상 작동합니다!")
        print("📱 텔레그램 앱에서 6개의 테스트 메시지를 확인하세요.")
    else:
        print("❌ 텔레그램 알림 통합에 문제가 있습니다.")