import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.db.session import SessionLocal
from backend.app.models import ReviewItem
from sqlalchemy import select

def check_payloads():
    db = SessionLocal()
    try:
        items = db.scalars(select(ReviewItem).where(ReviewItem.id.in_([99, 100, 101, 102, 103, 104, 105, 106, 107]))).all()
        for item in items:
            print(f"Item ID: {item.id}, Type: {item.item_type}")
            print(f"Payload: {json.dumps(item.payload, ensure_ascii=False)}")
            print("-" * 30)
    finally:
        db.close()

if __name__ == '__main__':
    check_payloads()
