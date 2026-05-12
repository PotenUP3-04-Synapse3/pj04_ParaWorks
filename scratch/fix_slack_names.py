import os
import sys
from sqlalchemy import select, update
from sqlalchemy.orm import Session

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.app.core.config import get_settings
from backend.app.db.session import SessionLocal
from backend.app.connectors.slack import SlackWebApiClient
from backend.app.models.source import Source, DocumentVersion, DocumentChunk
from backend.app.models.review import ReviewItem

def fix_slack_names():
    settings = get_settings()
    if not settings.slack_bot_token:
        print("SLACK_BOT_TOKEN이 설정되어 있지 않습니다.")
        return

    client = SlackWebApiClient(bot_token=settings.slack_bot_token)
    db: Session = SessionLocal()

    try:
        print("[*] Slack 사용자 목록 가져오는 중...")
        members = client.users_list()
        user_map = {}
        for m in members:
            uid = m.get('id')
            name = m.get('real_name') or m.get('profile', {}).get('real_name') or m.get('name')
            if uid and name:
                user_map[uid] = name

        print(f"[*] {len(user_map)}명의 사용자 정보를 확인했습니다.")

        import re
        def replace_mention(match):
            uid = match.group(1) or match.group(2)
            if uid in user_map:
                return f"@{user_map[uid]}"
            return match.group(0)

        mention_pattern = r'<@([A-Z0-9]+)>|(U[A-Z0-9]{8,})'

        # 1. Source 테이블 업데이트
        print("[*] Source 테이블의 작성자 이름 업데이트 중...")
        sources = db.scalars(select(Source).where(Source.source_type == 'slack')).all()
        updated_sources = 0
        for s in sources:
            if s.author in user_map:
                s.author = user_map[s.author]
                updated_sources += 1
        
        # 2. DocumentVersion 본문 업데이트
        print("[*] DocumentVersion 본문 내 멘션 치환 중...")
        versions = db.scalars(select(DocumentVersion)).all()
        updated_versions = 0
        for v in versions:
            new_body = re.sub(mention_pattern, replace_mention, v.body)
            if new_body != v.body:
                v.body = new_body
                updated_versions += 1

        # 3. DocumentChunk 소스 스니펫 업데이트
        print("[*] DocumentChunk 소스 스니펫 내 멘션 치환 중...")
        chunks = db.scalars(select(DocumentChunk)).all()
        updated_chunks = 0
        for c in chunks:
            new_snippet = re.sub(mention_pattern, replace_mention, c.source_snippet)
            if new_snippet != c.source_snippet:
                c.source_snippet = new_snippet
                updated_chunks += 1
        
        # 4. ReviewItem 테이블 업데이트 (payload 내의 assignee 등)
        print("[*] ReviewItem 테이블의 페이로드 업데이트 중...")
        review_items = db.scalars(select(ReviewItem)).all()
        updated_reviews = 0
        for item in review_items:
            payload_data = item.payload or {}
            changed = False
            
            # assignee 치환
            if 'assignee' in payload_data and payload_data['assignee'] in user_map:
                payload_data['assignee'] = user_map[payload_data['assignee']]
                changed = True
            
            if 'title' in payload_data:
                new_title = re.sub(mention_pattern, replace_mention, payload_data['title'])
                if new_title != payload_data['title']:
                    payload_data['title'] = new_title
                    changed = True

            if 'summary' in payload_data:
                new_summary = re.sub(mention_pattern, replace_mention, payload_data['summary'])
                if new_summary != payload_data['summary']:
                    payload_data['summary'] = new_summary
                    changed = True
            
            # source_snippets 리스트 내 멘션 치환
            if item.source_snippets:
                new_snippets = []
                snippet_changed = False
                for snippet in item.source_snippets:
                    new_snippet = re.sub(mention_pattern, replace_mention, snippet)
                    if new_snippet != snippet:
                        snippet_changed = True
                    new_snippets.append(new_snippet)
                if snippet_changed:
                    item.source_snippets = new_snippets
                    changed = True
            
            if changed:
                item.payload = payload_data
                updated_reviews += 1

        db.commit()
        print(f"[+] 완료: Source {updated_sources}개, Version {updated_versions}개, Chunk {updated_chunks}개, ReviewItem {updated_reviews}개 업데이트됨.")

    except Exception as e:
        print(f"[!] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    fix_slack_names()
