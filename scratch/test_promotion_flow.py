import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.session import SessionLocal
from backend.app.models import ReviewItem, TimelineEvent
from backend.app.knowledge.promotion import promote_review_item

db = SessionLocal()

# 1. Update payload for all items to include a project_key if missing
pending_items = db.query(ReviewItem).filter(ReviewItem.status == 'pending_review').all()
for item in pending_items:
    if not item.payload.get('project_key'):
        new_payload = dict(item.payload)
        new_payload['project_key'] = 'k-tech-pilot'
        item.payload = new_payload
        db.add(item)

db.commit()

# 2. Approve one item to test promotion
item_to_approve = db.query(ReviewItem).filter(ReviewItem.status == 'pending_review').first()
if item_to_approve:
    print(f"Approving item {item_to_approve.id}...")
    promote_review_item(db, item_to_approve)
    db.commit()
    print("Promoted successfully.")

# 3. Check TimelineEvents
events = db.query(TimelineEvent).order_by(TimelineEvent.id.desc()).limit(3).all()
for e in events:
    print(f"- ID: {e.id}, ProjectKey: {e.project_key}, Title: {e.title}")
