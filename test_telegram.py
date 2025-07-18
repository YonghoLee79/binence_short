#!/usr/bin/env python3
"""
텔레그램 알림 테스트 스크립트
"""

import os
import sys
import requests
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def test_telegram_connection():
    """텔레그램 연결 테스트"""
    
    # 환경변수 확인
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    print("🔍 텔레그램 설정 확인")
    print(f"BOT_TOKEN: {bot_token[:20]}..." if bot_token else "❌ BOT_TOKEN 없음")
    print(f"CHAT_ID: {chat_id}" if chat_id else "❌ CHAT_ID 없음")
    
    if not bot_token or not chat_id:
        print("❌ 텔레그램 설정이 누락되었습니다.")
        return False
    
    # 봇 정보 확인
    print("\n📡 봇 정보 확인 중...")
    try:
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe", timeout=10)
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info['ok']:
                print(f"✅ 봇 연결 성공: {bot_info['result']['username']}")
            else:
                print(f"❌ 봇 응답 오류: {bot_info}")
                return False
        else:
            print(f"❌ HTTP 오류: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 봇 정보 확인 실패: {e}")
        return False
    
    # 테스트 메시지 전송
    print("\n📨 테스트 메시지 전송 중...")
    try:
        message = "🧪 텔레그램 알림 테스트\n\n이 메시지가 도착했다면 텔레그램 설정이 정상입니다!"
        
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['ok']:
                print("✅ 테스트 메시지 전송 성공!")
                return True
            else:
                print(f"❌ 메시지 전송 실패: {result}")
                
                # 일반적인 오류 해결 방법 제시
                if 'chat not found' in str(result).lower():
                    print("\n💡 해결 방법:")
                    print("1. 텔레그램에서 봇과 대화를 시작하세요 (/start 명령)")
                    print("2. Chat ID가 올바른지 확인하세요")
                elif 'unauthorized' in str(result).lower():
                    print("\n💡 해결 방법:")
                    print("1. 봇 토큰이 올바른지 확인하세요")
                    print("2. 봇이 비활성화되지 않았는지 확인하세요")
                
                return False
        else:
            print(f"❌ HTTP 오류: {response.status_code}")
            print(f"응답: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 메시지 전송 실패: {e}")
        return False

def get_chat_id_instructions():
    """Chat ID 확인 방법 안내"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    print("\n📋 Chat ID 확인 방법:")
    print("1. 텔레그램에서 봇과 대화 시작 (/start)")
    print("2. 아무 메시지나 전송")
    print(f"3. 다음 URL 접속: https://api.telegram.org/bot{bot_token}/getUpdates")
    print("4. 'chat' 섹션에서 'id' 값 확인")
    print("\n또는 @userinfobot 에게 /start 보내서 Chat ID 확인")

if __name__ == "__main__":
    print("🔧 텔레그램 알림 진단 도구")
    print("=" * 40)
    
    success = test_telegram_connection()
    
    if not success:
        get_chat_id_instructions()
        
    print("\n" + "=" * 40)
    if success:
        print("🎉 텔레그램 설정이 정상입니다!")
    else:
        print("❌ 텔레그램 설정에 문제가 있습니다.")