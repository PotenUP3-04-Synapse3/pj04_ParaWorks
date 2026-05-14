import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.session import SessionLocal
from backend.app.models import ReviewItem, TimelineEvent

db = SessionLocal()

print(f"Total ReviewItems: {db.query(ReviewItem).count()}")
print(f"Approved ReviewItems: {db.query(ReviewItem).filter(ReviewItem.status == 'approved').count()}")

events = db.query(TimelineEvent).all()
print(f"Total TimelineEvents: {len(events)}")
for e in events:
    print(f"- ID: {e.id}, ProjectKey: {e.project_key}, Title: {e.title}")
