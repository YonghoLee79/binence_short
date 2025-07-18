#!/usr/bin/env python3
"""
트레이딩 봇에서 텔레그램 알림 테스트
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_telegram_from_bot():
    """봇에서 텔레그램 테스트"""
    try:
        from telegram_bot import TelegramBot
        
        # 텔레그램 봇 초기화
        telegram = TelegramBot()
        
        if not telegram.enabled:
            print("❌ 텔레그램 봇이 비활성화되어 있습니다.")
            return False
        
        # 테스트 메시지들
        messages = [
            "🤖 <b>트레이딩 봇 테스트</b>\n\n📊 시스템 상태: 정상\n💰 잔고: 31.74 USDT",
            "🔔 <b>거래 알림 테스트</b>\n\n📈 매수 신호 발생\n🏷️ 심볼: BTC/USDT\n💵 가격: $65,000",
            "⚠️ <b>리스크 알림 테스트</b>\n\n🔻 손실 한도 도달\n📉 현재 손실: -2.5%\n🛑 거래 일시 중단"
        ]
        
        print("📨 텔레그램 알림 테스트 시작...")
        
        for i, message in enumerate(messages, 1):
            print(f"\n{i}. 메시지 전송 중...")
            success = telegram.send_message(message)
            
            if success:
                print(f"✅ 메시지 {i} 전송 성공")
            else:
                print(f"❌ 메시지 {i} 전송 실패")
                return False
        
        print(f"\n🎉 모든 테스트 메시지가 성공적으로 전송되었습니다!")
        return True
        
    except ImportError as e:
        print(f"❌ 모듈 import 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 텔레그램 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    print("🔧 트레이딩 봇 텔레그램 알림 테스트")
    print("=" * 45)
    
    success = test_telegram_from_bot()
    
    print("\n" + "=" * 45)
    if success:
        print("✅ 텔레그램 알림이 정상 작동합니다!")
        print("📱 텔레그램 앱에서 메시지를 확인하세요.")
    else:
        print("❌ 텔레그램 알림에 문제가 있습니다.")
        print("💡 .env 파일의 설정을 확인하세요.")