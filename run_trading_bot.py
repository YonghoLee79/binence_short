#!/usr/bin/env python3
"""
트레이딩 봇 실행 스크립트
"""

import sys
import os
import asyncio
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """메인 실행 함수"""
    print("🚀 암호화폐 트레이딩 봇")
    print("=" * 50)
    
    print("\n실행 옵션을 선택하세요:")
    print("1. 기본 트레이딩 봇 (모듈화 버전)")
    print("2. 비동기 최적화 트레이딩 봇")
    print("3. 모니터링 대시보드만 실행")
    print("4. 단위 테스트 실행")
    print("5. 데이터베이스 테스트")
    
    choice = input("\n선택 (1-5): ").strip()
    
    if choice == "1":
        run_basic_bot()
    elif choice == "2":
        run_async_bot()
    elif choice == "3":
        run_dashboard()
    elif choice == "4":
        run_tests()
    elif choice == "5":
        run_database_test()
    else:
        print("잘못된 선택입니다.")

def run_basic_bot():
    """기본 트레이딩 봇 실행"""
    print("\n🤖 기본 트레이딩 봇 실행 중...")
    try:
        # run_modular.py가 없으면 기본 run.py 사용
        if os.path.exists("run_modular.py"):
            from run_modular import main as modular_main
            modular_main()
        elif os.path.exists("run.py"):
            import subprocess
            subprocess.run([sys.executable, "run.py"])
        else:
            print("❌ 실행할 메인 파일을 찾을 수 없습니다.")
    except Exception as e:
        print(f"❌ 기본 봇 실행 실패: {e}")

def run_async_bot():
    """비동기 트레이딩 봇 실행"""
    print("\n⚡ 비동기 최적화 트레이딩 봇 실행 중...")
    try:
        from modules.async_trading_bot import main as async_main
        asyncio.run(async_main())
    except Exception as e:
        print(f"❌ 비동기 봇 실행 실패: {e}")

def run_dashboard():
    """모니터링 대시보드 실행"""
    print("\n📊 모니터링 대시보드 실행 중...")
    print("웹 대시보드: http://localhost:8080")
    try:
        from modules.monitoring_dashboard import MonitoringDashboard, WebDashboardServer
        
        dashboard = MonitoringDashboard()
        web_server = WebDashboardServer(dashboard)
        
        async def start_dashboard():
            await web_server.start_server()
            await dashboard.start_monitoring()
        
        asyncio.run(start_dashboard())
    except KeyboardInterrupt:
        print("\n📊 대시보드 종료")
    except Exception as e:
        print(f"❌ 대시보드 실행 실패: {e}")

def run_tests():
    """단위 테스트 실행"""
    print("\n🧪 단위 테스트 실행 중...")
    try:
        import subprocess
        
        print("기술적 분석 테스트...")
        result1 = subprocess.run([sys.executable, "-m", "tests.test_technical_analysis"], 
                               capture_output=True, text=True)
        
        print("리스크 관리 테스트...")
        result2 = subprocess.run([sys.executable, "-m", "tests.test_risk_manager"], 
                               capture_output=True, text=True)
        
        if result1.returncode == 0 and result2.returncode == 0:
            print("✅ 모든 테스트 통과!")
        else:
            print("❌ 일부 테스트 실패")
            if result1.returncode != 0:
                print(f"기술적 분석 테스트 오류:\n{result1.stderr}")
            if result2.returncode != 0:
                print(f"리스크 관리 테스트 오류:\n{result2.stderr}")
                
    except Exception as e:
        print(f"❌ 테스트 실행 실패: {e}")

def run_database_test():
    """데이터베이스 테스트 실행"""
    print("\n🗄️ 데이터베이스 테스트 실행 중...")
    try:
        from modules.database_manager import DatabaseManager
        
        with DatabaseManager("test_trading_bot.db") as db:
            # 테스트 데이터 삽입
            trade_data = {
                'symbol': 'BTC/USDT',
                'side': 'buy',
                'size': 0.001,
                'price': 50000,
                'exchange_type': 'spot',
                'order_type': 'market',
                'fees': 0.5,
                'pnl': 10.0,
                'strategy': 'test_strategy',
                'status': 'filled'
            }
            
            trade_id = db.insert_trade(trade_data)
            print(f"✅ 거래 기록 삽입 성공: ID {trade_id}")
            
            trades = db.get_trades(limit=5)
            print(f"✅ 거래 기록 조회 성공: {len(trades)}개")
            
            stats = db.get_trading_statistics(days=1)
            print(f"✅ 거래 통계 조회 성공")
            
            print("✅ 데이터베이스 테스트 완료")
            
    except Exception as e:
        print(f"❌ 데이터베이스 테스트 실패: {e}")

if __name__ == "__main__":
    main()