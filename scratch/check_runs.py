import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.db.session import SessionLocal
from backend.app.models import AgentRun
from sqlalchemy import select

def check_agent_runs():
    db = SessionLocal()
    try:
        runs = db.scalars(select(AgentRun).where(AgentRun.id.in_([34, 35]))).all()
        for run in runs:
            print(f"Run ID: {run.id}, Agent: {run.agent_name}, Model: {run.model_name}")
            print(f"Metadata: {run.metadata_}")
            print("-" * 30)
    finally:
        db.close()

if __name__ == '__main__':
    check_agent_runs()
