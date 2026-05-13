import os
import sys
import logging
from sqlalchemy.orm import Session

# 프로젝트 루트를 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.app.db.session import SessionLocal
from backend.app.agents.slack_agent.sync_service import trigger_slack_agent_analysis
from backend.app.connectors.factory import get_sync_connector
from backend.app.core.config import get_settings
from backend.app.ingestion.sync import sync_connector_events

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sync_slack_script")

def main():
    db = SessionLocal()
    settings = get_settings()
    
    try:
        print("\n" + "="*70)
        print(" [ParaWorks] 슬랙 동기화 및 에이전트 분석 시작 ".center(70, "="))
        print("="*70 + "\n")

        # 1. 슬랙 이벤트 동기화 (Slack API -> Source 테이블)
        print("[*] 1. 슬랙 데이터 수집 중...")
        connector = get_sync_connector("slack", settings, db=db)
        sync_result = sync_connector_events(db=db, connector=connector)
        print(f"[*] 수집 완료: {sync_result.fetched_events}건의 이벤트 발견")

        # 2. 에이전트 분석 (Source 테이블 -> ReviewItem 테이블)
        print("\n[*] 2. 에이전트 분석 및 지식 추출 중 (최근 7일)...")
        trigger_slack_agent_analysis(db=db, days=7)
        print("[*] 분석 완료: 지식 후보가 데이터베이스에 저장되었습니다.")

        print("\n" + "="*70)
        print(" [동기화 성공] ".center(70, "="))
        print("="*70 + "\n")

    except Exception as e:
        print(f"\n [!] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
