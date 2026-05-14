import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.session import SessionLocal
from backend.app.agents.slack_agent.sync_service import trigger_slack_agent_analysis

db = SessionLocal()
count = trigger_slack_agent_analysis(db, days=14)
print(f"Triggered analysis and created {count} candidates.")
