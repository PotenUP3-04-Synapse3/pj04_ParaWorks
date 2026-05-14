import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.session import SessionLocal
from backend.app.models import ReviewItem, TimelineEvent
from backend.app.agents.slack_agent.service import _determine_project_from_tag

db = SessionLocal()

# 1. Update payload for all items where project_key is None
items = db.query(ReviewItem).all()
for item in items:
    if not item.payload.get('project_key'):
        topic_tag = item.payload.get('topic_tag', 'N/A')
        summary = item.payload.get('summary', '')
        pk, _ = _determine_project_from_tag(topic_tag, summary)
        
        new_payload = dict(item.payload)
        new_payload['project_key'] = pk
        item.payload = new_payload
        db.add(item)

# 2. Update TimelineEvent project keys
events = db.query(TimelineEvent).filter(TimelineEvent.project_key == None).all()
for e in events:
    # Just setting to ad-hoc if missing, or we can look up matching ReviewItem.
    # Since it's demo data, just set to ad-hoc.
    e.project_key = 'ad-hoc'
    db.add(e)

db.commit()
print("Migration completed. project_key=None resolved.")
