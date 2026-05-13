import sys
import os
from datetime import datetime, timedelta, UTC

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.db.session import SessionLocal
from backend.app.models import SyncJob, AgentRun, ReviewItem, Source
from sqlalchemy import select, func

def check_db():
    db = SessionLocal()
    try:
        # Check recent SyncJobs
        print("--- Recent Sync Jobs ---")
        jobs = db.scalars(select(SyncJob).order_by(SyncJob.created_at.desc()).limit(5)).all()
        for j in jobs:
            print(f"ID: {j.job_id}, Type: {j.connector_type}, Status: {j.status}, Msg: {j.message}, Time: {j.created_at}")
            
        print("\n--- Recent Agent Runs ---")
        runs = db.scalars(select(AgentRun).order_by(AgentRun.started_at.desc()).limit(5)).all()
        for r in runs:
            print(f"Agent: {r.agent_name}, Status: {r.status}, Tokens: {r.total_tokens}, Time: {r.started_at}")
            print(f"  Metadata: {r.metadata_}")
            
        print("\n--- Counts ---")
        sources_cnt = db.scalar(select(func.count(Source.id)))
        runs_cnt = db.scalar(select(func.count(AgentRun.id)))
        review_cnt = db.scalar(select(func.count(ReviewItem.id)))
        pending_review_cnt = db.scalar(select(func.count(ReviewItem.id)).where(ReviewItem.status == 'pending_review'))
        print(f"Total Sources: {sources_cnt}")
        print(f"Total Agent Runs: {runs_cnt}")
        print(f"Total Review Items: {review_cnt}")
        print(f"Pending Review Items: {pending_review_cnt}")
        
    finally:
        db.close()

if __name__ == '__main__':
    check_db()
