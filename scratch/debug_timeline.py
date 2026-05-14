import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.session import SessionLocal
from backend.app.models import ReviewItem, TimelineEvent

db = SessionLocal()

print("--- RECENT APPROVED REVIEW ITEMS ---")
approved_items = db.query(ReviewItem).filter(ReviewItem.status == 'approved').order_by(ReviewItem.id.desc()).limit(5).all()
for item in approved_items:
    payload = item.payload or {}
    print(f"ID: {item.id}, Type: {item.item_type}, ProjectKey: {payload.get('project_key')}, Title: {payload.get('title')}")

print("\n--- RECENT TIMELINE EVENTS ---")
events = db.query(TimelineEvent).order_by(TimelineEvent.id.desc()).limit(5).all()
for e in events:
    print(f"ID: {e.id}, ProjectKey: {e.project_key}, Title: {e.title}, Status: {e.review_status}")

print("\n--- ALL UNIQUE TIMELINE PROJECT KEYS ---")
keys = db.query(TimelineEvent.project_key).distinct().all()
print([k[0] for k in keys])
