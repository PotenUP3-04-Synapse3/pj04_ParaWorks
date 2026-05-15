import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.session import SessionLocal
from backend.app.projects.service import build_project_memory

db = SessionLocal()
projects = build_project_memory(db)
print(f"Count: {len(projects)}")
for p in projects:
    print(f"Key: {p.project_key}, Name: {p.name}")
    print(f"  Evidence: {len(p.evidence)}")
    print(f"  Timeline: {len(p.timeline_items)}")
