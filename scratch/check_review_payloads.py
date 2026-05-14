import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.session import SessionLocal
from backend.app.models import ReviewItem

db = SessionLocal()

items = db.query(ReviewItem).all()
for item in items:
    print(f"ID: {item.id}, Status: {item.status}, Type: {item.item_type}")
    print(f"  Project Key: {item.payload.get('project_key')}")
