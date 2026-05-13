import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.db.session import SessionLocal
from backend.app.models import ReviewItem
from sqlalchemy import select, delete

def delete_bad_items():
    db = SessionLocal()
    try:
        # source_snippets 가 없거나 0인 항목들 찾기
        items = db.scalars(select(ReviewItem).where(ReviewItem.status == 'pending_review')).all()
        to_delete = []
        for item in items:
            if not item.source_snippets or len(item.source_snippets) == 0:
                to_delete.append(item.id)
                
        if to_delete:
            print(f"Deleting bad review items: {to_delete}")
            db.execute(delete(ReviewItem).where(ReviewItem.id.in_(to_delete)))
            db.commit()
            print("Deletion complete.")
        else:
            print("No bad review items found.")
    finally:
        db.close()

if __name__ == '__main__':
    delete_bad_items()
