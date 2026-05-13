import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.db.session import SessionLocal
from backend.app.models import ReviewItem

def normalize_item_types():
    db = SessionLocal()
    try:
        items = db.query(ReviewItem).all()
        updated_count = 0
        for item in items:
            old_type = item.item_type
            if not old_type:
                continue
                
            new_type = old_type.strip().lower()
            
            # Record -> decision_record 매핑 등 임의 문자열 보정
            if new_type == 'record':
                new_type = 'decision_record'
                
            if new_type not in {'decision_record', 'todo', 'history_event'}:
                new_type = 'history_event'
                
            if old_type != new_type:
                item.item_type = new_type
                updated_count += 1
                print(f"Updated ReviewItem ID {item.id}: '{old_type}' -> '{new_type}'")
        
        if updated_count > 0:
            db.commit()
            print(f"Total {updated_count} records updated.")
        else:
            print("No records needed updating.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    normalize_item_types()
