import requests
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class TelegramBot:
    """텔레그램 봇 알림 클래스"""
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        # 로깅 설정
        self.logger = logging.getLogger(__name__)
        
        if not self.bot_token or not self.chat_id:
            self.logger.warning("텔레그램 봇 토큰 또는 채팅 ID가 설정되지 않았습니다.")
            self.enabled = False
        else:
            self.enabled = True
            self.logger.info("텔레그램 봇 초기화 완료")
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """메시지 전송"""
        if not self.enabled:
            self.logger.debug(f"텔레그램 비활성화 - 메시지: {message}")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                self.logger.debug("텔레그램 메시지 전송 성공")
                return True
            else:
                self.logger.error(f"텔레그램 메시지 전송 실패: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"텔레그램 메시지 전송 중 오류: {e}")
            return False
    
    def send_trade_notification(self, trade_data: Dict[str, Any]) -> bool:
        """거래 알림 전송"""
        try:
            symbol = trade_data.get('symbol', 'Unknown')
            side = trade_data.get('side', 'Unknown')
            amount = trade_data.get('amount', 0)
            price = trade_data.get('price', 0)
            trade_type = trade_data.get('type', 'spot')
            pnl = trade_data.get('pnl', 0)
            
            # 이모지 설정
            if side.lower() == 'buy':
                emoji = "🟢"
            elif side.lower() == 'sell':
                emoji = "🔴"
            else:
                emoji = "🔵"
            
            if trade_type.lower() == 'futures':
                type_emoji = "🚀"
            else:
                type_emoji = "📊"
            
            # 메시지 구성
            message = f"""
{emoji} <b>거래 실행 알림</b> {type_emoji}

🪙 <b>심볼:</b> {symbol}
📈 <b>타입:</b> {trade_type.upper()}
🎯 <b>주문:</b> {side.upper()}
💰 <b>수량:</b> {amount:.6f}
💵 <b>가격:</b> ${price:,.2f}
📊 <b>총액:</b> ${amount * price:,.2f}

{f"💹 <b>손익:</b> {pnl:+,.2f} USDT" if pnl != 0 else ""}

⏰ <b>시간:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            return self.send_message(message.strip())
            
        except Exception as e:
            self.logger.error(f"거래 알림 전송 중 오류: {e}")
            return False
    
    def send_balance_update(self, balance_data: Dict[str, Any]) -> bool:
        """잔고 업데이트 알림"""
        try:
            current_balance = balance_data.get('current_balance', 0)
            initial_balance = balance_data.get('initial_balance', 0)
            pnl = current_balance - initial_balance
            pnl_pct = (pnl / initial_balance * 100) if initial_balance > 0 else 0
            
            spot_balance = balance_data.get('spot_balance', 0)
            futures_balance = balance_data.get('futures_balance', 0)
            
            # 수익률에 따른 이모지
            if pnl > 0:
                pnl_emoji = "📈"
            elif pnl < 0:
                pnl_emoji = "📉"
            else:
                pnl_emoji = "➡️"
            
            message = f"""
💰 <b>잔고 업데이트</b>

🏦 <b>총 잔고:</b> ${current_balance:,.2f}
📊 <b>현물:</b> ${spot_balance:,.2f}
🚀 <b>선물:</b> ${futures_balance:,.2f}

{pnl_emoji} <b>손익:</b> {pnl:+,.2f} USDT ({pnl_pct:+.2f}%)

⏰ <b>시간:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            return self.send_message(message.strip())
            
        except Exception as e:
            self.logger.error(f"잔고 업데이트 알림 전송 중 오류: {e}")
            return False
    
    def send_error_alert(self, error_message: str, error_type: str = "ERROR") -> bool:
        """에러 알림 전송"""
        try:
            message = f"""
🚨 <b>에러 알림</b>

⚠️ <b>타입:</b> {error_type}
💬 <b>메시지:</b> {error_message}

⏰ <b>시간:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            return self.send_message(message.strip())
            
        except Exception as e:
            self.logger.error(f"에러 알림 전송 중 오류: {e}")
            return False
    
    def send_system_status(self, status_data: Dict[str, Any]) -> bool:
        """시스템 상태 알림"""
        try:
            bot_status = status_data.get('status', 'Unknown')
            active_positions = status_data.get('active_positions', 0)
            total_trades = status_data.get('total_trades', 0)
            win_rate = status_data.get('win_rate', 0)
            
            if bot_status.lower() == 'running':
                status_emoji = "🟢"
            elif bot_status.lower() == 'stopped':
                status_emoji = "🔴"
            else:
                status_emoji = "🟡"
            
            message = f"""
🤖 <b>시스템 상태</b>

{status_emoji} <b>상태:</b> {bot_status.upper()}
🎯 <b>활성 포지션:</b> {active_positions}개
📊 <b>총 거래:</b> {total_trades}회
🏆 <b>승률:</b> {win_rate:.1f}%

⏰ <b>시간:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            return self.send_message(message.strip())
            
        except Exception as e:
            self.logger.error(f"시스템 상태 알림 전송 중 오류: {e}")
            return False
    
    def send_market_analysis(self, analysis_data: Dict[str, Any]) -> bool:
        """시장 분석 알림"""
        try:
            symbol = analysis_data.get('symbol', 'Unknown')
            trend = analysis_data.get('trend', 'neutral')
            rsi = analysis_data.get('rsi', 0)
            price = analysis_data.get('price', 0)
            
            # 트렌드에 따른 이모지
            if trend.lower() == 'bullish':
                trend_emoji = "🟢📈"
            elif trend.lower() == 'bearish':
                trend_emoji = "🔴📉"
            else:
                trend_emoji = "🟡➡️"
            
            # RSI 분석
            if rsi > 70:
                rsi_status = "과매수"
                rsi_emoji = "🔴"
            elif rsi < 30:
                rsi_status = "과매도"
                rsi_emoji = "🟢"
            else:
                rsi_status = "중성"
                rsi_emoji = "🟡"
            
            message = f"""
📊 <b>시장 분석</b>

🪙 <b>심볼:</b> {symbol}
💵 <b>현재가:</b> ${price:,.2f}
{trend_emoji} <b>트렌드:</b> {trend.upper()}
{rsi_emoji} <b>RSI:</b> {rsi:.1f} ({rsi_status})

⏰ <b>시간:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            return self.send_message(message.strip())
            
        except Exception as e:
            self.logger.error(f"시장 분석 알림 전송 중 오류: {e}")
            return False
    
    def send_startup_message(self) -> bool:
        """봇 시작 메시지"""
        message = f"""
🚀 <b>하이브리드 트레이딩 봇 시작</b>

🤖 봇이 성공적으로 시작되었습니다!
📊 현물 + 선물 하이브리드 전략 활성화
🔄 자동 거래 및 리스크 관리 시스템 온라인

⏰ <b>시작 시간:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💡 주요 기능:
• 실시간 시장 분석
• 자동 포지션 관리
• 리스크 기반 거래 실행
• 24/7 모니터링

📈 성공적인 거래를 시작합니다!
"""
        
        return self.send_message(message.strip())
    
    def send_shutdown_message(self) -> bool:
        """봇 종료 메시지"""
        message = f"""
🔴 <b>하이브리드 트레이딩 봇 종료</b>

🤖 봇이 안전하게 종료되었습니다.
📊 모든 포지션 및 거래 내역이 저장되었습니다.

⏰ <b>종료 시간:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💼 다음 실행 시 자동으로 상태가 복원됩니다.
🔒 보안을 위해 API 연결이 안전하게 해제되었습니다.

👋 거래 세션을 마칩니다!
"""
        
        return self.send_message(message.strip())
    
    def test_connection(self) -> bool:
        """연결 테스트"""
        if not self.enabled:
            return False
        
        test_message = f"""
🧪 <b>텔레그램 봇 연결 테스트</b>

✅ 연결이 정상적으로 작동합니다!
🤖 알림 시스템이 준비되었습니다.

⏰ <b>테스트 시간:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return self.send_message(test_message.strip())

# 테스트 실행
if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)
    
    # 텔레그램 봇 초기화
    bot = TelegramBot()
    
    if bot.enabled:
        print("텔레그램 봇 연결 테스트 중...")
        
        # 연결 테스트
        if bot.test_connection():
            print("✅ 텔레그램 봇 연결 성공!")
            
            # 예시 알림들
            bot.send_trade_notification({
                'symbol': 'BTC/USDT',
                'side': 'buy',
                'amount': 0.001,
                'price': 45000,
                'type': 'spot',
                'pnl': 0
            })
            
            bot.send_balance_update({
                'current_balance': 1150,
                'initial_balance': 1000,
                'spot_balance': 690,
                'futures_balance': 460
            })
            
        else:
            print("❌ 텔레그램 봇 연결 실패")
    else:
        print("⚠️ 텔레그램 봇이 비활성화되어 있습니다.")
        print("TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID를 .env 파일에 설정하세요.")