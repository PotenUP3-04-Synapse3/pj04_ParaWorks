import sys
import os

# Add backend to sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.db.session import SessionLocal
from backend.app.models import Source, Document, DocumentVersion, DocumentParserRun, DocumentChunk, IntegrationConnection, SyncJob, VectorIndexState
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError

def delete_slack_data():
    db: Session = SessionLocal()
    
    try:
        # 1. Find all sources with source_type == 'slack'
        slack_sources = db.scalars(sa.select(Source.id).where(Source.source_type == 'slack')).all()
        
        print(f"Found {len(slack_sources)} Slack sources.")
        if slack_sources:
            # Document chunks
            chunk_ids = db.scalars(sa.select(DocumentChunk.id).where(DocumentChunk.source_id.in_(slack_sources))).all()
            if chunk_ids:
                print(f"Deleting {len(chunk_ids)} DocumentChunks...")
                chunk_doc_ids = [f'chunk:{cid}' for cid in chunk_ids]
                
                # Delete vector index states
                db.execute(sa.delete(VectorIndexState).where(VectorIndexState.document_id.in_(chunk_doc_ids)))
                
                # Delete from rag_vector_documents
                try:
                    db.execute(sa.text("DELETE FROM rag_vector_documents WHERE document_id = ANY(:doc_ids)"), {"doc_ids": chunk_doc_ids})
                except ProgrammingError as e:
                    # Table might not exist if pgvector isn't set up yet
                    print(f"Skipping rag_vector_documents deletion: {e}")
                
                db.execute(sa.delete(DocumentChunk).where(DocumentChunk.source_id.in_(slack_sources)))
            
            # Document parser runs
            parser_runs_count = db.execute(sa.delete(DocumentParserRun).where(DocumentParserRun.source_id.in_(slack_sources))).rowcount
            print(f"Deleted {parser_runs_count} DocumentParserRuns.")
            
            # Document versions
            doc_ids = db.scalars(sa.select(Document.id).where(Document.source_id.in_(slack_sources))).all()
            if doc_ids:
                versions_count = db.execute(sa.delete(DocumentVersion).where(DocumentVersion.document_id.in_(doc_ids))).rowcount
                print(f"Deleted {versions_count} DocumentVersions.")
            
            # Documents
            docs_count = db.execute(sa.delete(Document).where(Document.source_id.in_(slack_sources))).rowcount
            print(f"Deleted {docs_count} Documents.")
            
            # Sources
            sources_count = db.execute(sa.delete(Source).where(Source.id.in_(slack_sources))).rowcount
            print(f"Deleted {sources_count} Sources.")
        
        # Integration Connections
        conns_count = db.execute(sa.delete(IntegrationConnection).where(IntegrationConnection.connector_type == 'slack')).rowcount
        print(f"Deleted {conns_count} IntegrationConnections.")
        
        # SyncJobs
        jobs_count = db.execute(sa.delete(SyncJob).where(SyncJob.connector_type == 'slack')).rowcount
        print(f"Deleted {jobs_count} SyncJobs.")
        
        db.commit()
        print("Deletion transaction committed.")
    except Exception as e:
        db.rollback()
        print(f"Error during deletion: {e}")
        raise
    finally:
        db.close()

if __name__ == '__main__':
    delete_slack_data()
