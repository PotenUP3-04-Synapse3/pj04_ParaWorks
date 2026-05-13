import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.db.session import SessionLocal
from backend.app.models import ReviewItem
from sqlalchemy import select

def check_snippets():
    db = SessionLocal()
    try:
        items = db.scalars(select(ReviewItem).where(ReviewItem.status == 'pending_review')).all()
        print(f"Total pending items: {len(items)}")
        for item in items:
            print(f"Item ID: {item.id}, Type: {item.item_type}")
            print(f"  Source links: {len(item.source_links) if item.source_links else 0}")
            print(f"  Source snippets: {len(item.source_snippets) if item.source_snippets else 0}")
            if item.source_snippets:
                print(f"  Sample snippet: {item.source_snippets[0][:50]}...")
            else:
                print("  Sample snippet: NONE")
            print("-" * 30)
    finally:
        db.close()

if __name__ == '__main__':
    check_snippets()
