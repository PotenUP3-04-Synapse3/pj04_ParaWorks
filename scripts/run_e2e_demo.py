import asyncio
import os
from sqlalchemy.orm import Session
from backend.app.db.session import SessionLocal
from backend.app.db.init_db import init_db
from backend.app.core.config import get_settings
from backend.app.models.integrations import IntegrationConnection
from backend.app.ingestion.sync import sync_connector_events
from backend.app.connectors.google import GoogleConnectorConfig
from backend.app.connectors.slack import SlackConnectorConfig
from backend.app.api.v1.search import search_knowledge
from backend.app.schemas.search import SearchRequest
from backend.app.core.demo_auth import DemoUser
from backend.app.db.base import Base
from backend.app.db.session import engine

def main():
    os.environ["PARAWORKS_DEMO_MODE"] = "true"
    settings = get_settings()
    
    # Initialize DB
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    init_db(db)
    
    # Add Google integration if not exists
    conn = db.query(IntegrationConnection).filter_by(connector_type="google").first()
    if not conn:
        conn = IntegrationConnection(
            connector_type="google",
            workspace_id="demo-workspace",
            workspace_name="Demo Workspace",
            status="active",
            masked_bot_token="mock-token",
            scopes=["drive.readonly", "gmail.readonly"]
        )
        db.add(conn)
        db.commit()

    # Create dummy user
    user = DemoUser(
        id="demo-1", 
        email="demo@example.com", 
        role="employee", 
        permission_levels=["public", "team", "confidential"],
        name="Demo",
        title="Demo",
        department="Demo"
    )

    print("--- Running connector sync ---")
    result = sync_connector_events(db=db, connector_type="google")
    print(f"Sync Result: {result}")
    
    print("\n--- Getting Documents ---")
    from backend.app.api.v1.documents import list_documents
    docs = list_documents(db=db)
    for doc in docs:
        print(f"Doc: {doc['title']}, Status: {doc['parser_status']}, URL: {doc.get('source_url')}")
    
    print("\n--- Running Search ---")
    search_req = SearchRequest(query="Golden")
    search_res = search_knowledge(request=search_req, db=db, user=user, settings=settings)
    for res in search_res["results"]:
        print(f"Result: {res['text'][:30]}... | Status: {res.get('parser_status')} | Permissions: {res.get('permission_level')}")

if __name__ == "__main__":
    main()
