import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.db.session import SessionLocal
from backend.app.models import ReviewItem
from sqlalchemy import select, delete

def delete_hardcoded_items():
    db = SessionLocal()
    try:
        # Delete items with title 'Use Redis for queues and job progress', 'Project Beta advanced diff UI moved out of MVP', 'Verify evidence inspection before launch'
        titles = [
            'Use Redis for queues and job progress',
            'Project Beta advanced diff UI moved out of MVP',
            'Verify evidence inspection before launch'
        ]
        
        # Also let's check current items
        items = db.scalars(select(ReviewItem).where(ReviewItem.status == 'pending_review')).all()
        to_delete = []
        for item in items:
            title = item.payload.get('title')
            if title in titles:
                to_delete.append(item.id)
                
        if to_delete:
            print(f"Deleting hardcoded review items: {to_delete}")
            db.execute(delete(ReviewItem).where(ReviewItem.id.in_(to_delete)))
            db.commit()
            print("Deletion complete.")
        else:
            print("No hardcoded items found.")
            
    finally:
        db.close()

if __name__ == '__main__':
    delete_hardcoded_items()
