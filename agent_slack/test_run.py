import os
import sys
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# .env 파일 로드 (없으면 .env.example 참고)
load_dotenv()
if not os.environ.get("SLACK_BOT_TOKEN") and not os.environ.get("SLACK_USER_TOKEN"):
    load_dotenv('.env.example')

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# 윈도우 한글 출력 깨짐 방지
import io
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

from agent_slack import process_daily_slack_sync
from backend.app.connectors.slack import SlackWebApiClient

def run_real_slack_batch_test():
    print("\n" + "="*70)
    print(" [ParaWorks] Slack Recent 7-Day Sync Integration Test ".center(70, "="))
    print("="*70 + "\n")

    # 사용자 토큰을 우선 확인 (개인 DM 테스트용), 없으면 봇 토큰 사용
    user_token = os.environ.get("SLACK_USER_TOKEN")
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    
    token_to_use = user_token if user_token else bot_token
    token_type = "User" if user_token else "Bot"

    if not token_to_use:
        print(" [!] Error: No token found in .env file.")
        return

    print(f"[*] Token type in use: {token_type}")
    client = SlackWebApiClient(bot_token=token_to_use)
    
    total_candidates = [] # 모든 채널의 후보를 모으기 위한 리스트

    try:
        # 사용자 이름 매핑 정보 수집 (채널 공통)
        print("[*] Collecting workspace user information...")
        users = client.users_list()
        user_map = {u.get('id'): u.get('real_name') or u.get('name') for u in users}

        # 1. 참여 중인 모든 채널 및 DM 목록 조회
        print("[*] Fetching all joined channels and DM lists...")
        all_channels = client.conversations_list()
        # 일반 채널은 is_member, DM은 is_im/is_mpim으로 필터링
        joined_channels = [
            c for c in all_channels 
            if c.get('is_member') or c.get('is_im') or c.get('is_mpim')
        ]

        if not joined_channels:
            print(" [!] No joined channels or DMs found.")
            return

        def get_channel_display_name(c):
            if c.get('is_im'):
                user_id = c.get('user')
                user_name = user_map.get(user_id, user_id) if user_id else 'Unknown'
                return f"PrivateDM(@{user_name})"
            elif c.get('is_mpim'):
                return f"GroupDM({c.get('name', 'unknown')})"
            else:
                return f"#{c.get('name', 'unknown')}"

        print(f"[*] Found {len(joined_channels)} joined channels/DMs:")
        for c in joined_channels:
            print(f"    - {get_channel_display_name(c)} (ID: {c.get('id')})")

        # 최근 7일 전의 타임스탬프 계산
        now = datetime.now()
        start_date = now - timedelta(days=7)
        # 시간 단위를 00:00:00으로 설정하여 일주일 전 전체 데이터를 포함
        today_start = datetime(start_date.year, start_date.month, start_date.day)
        oldest_ts = str(today_start.timestamp())
        
        # 각 채널별로 데이터 수집 및 분석 진행
        for channel in joined_channels:
            channel_id = channel['id']
            channel_name = get_channel_display_name(channel)
            
            print(f"\n{'-'*70}")
            print(f" [Channel Analysis Start: {channel_name} ({channel_id})] ".center(70, "-"))
            print(f"{'-'*70}\n")
            
            print(f"[*] Fetching conversation history for the last 7 days since {today_start.strftime('%Y-%m-%d')}...")
            history = client.conversation_history(channel_id, oldest=oldest_ts)
            
            if not history:
                print(f" [!] No messages found in {channel_name} in the last 7 days. Skipping.")
                continue

            # 각 메시지에 사용자 이름 주입
            for msg in history:
                user_id = msg.get('user')
                msg['user_name'] = user_map.get(user_id, user_id)

            print(f"[*] Collected {len(history)} messages.")
            print("[*] Starting agent analysis based on sync...\n")
            
            # 에이전트 실행
            result = process_daily_slack_sync(channel_id, history)
            
            candidates = result.get('candidates', [])
            if candidates:
                total_candidates.extend(candidates)
            
            print("\n [채널 분석 요약] ")
            print(f" - Work Related: {result.get('is_work_related')}")
            
            if result.get('summary'):
                print(f" - Summary: {result.get('summary')[:100]}...")
            
            if candidates:
                print(f" - Knowledge Candidates Found: {len(candidates)} items")
            
            run_cost = result.get('run_cost')
            if run_cost:
                print(f" - Estimated Cost: ${run_cost.estimated_cost_usd:.5f} (Total Tokens: {run_cost.token_usage.total_tokens})")

        # === 최종 요약 섹션 ===
        print("\n" + "="*70)
        print(" [ ParaWorks Final Analysis Result Summary ] ".center(70, "="))
        print("="*70)

        # 1. 오늘의 할 일 (Todo)
        todos = [c for c in total_candidates if (c.item_type if hasattr(c, 'item_type') else c.get('item_type')) == 'Todo']
        print(f"\n [Today's Action Items (Todos)] - {len(todos)} items")
        if todos:
            for idx, todo in enumerate(todos, 1):
                title = todo.title if hasattr(todo, 'title') else todo.get('title')
                payload = todo.payload_fields if hasattr(todo, 'payload_fields') else todo.get('payload_fields', {})
                assignee = payload.get('assignee', 'Unassigned')
                due_date = payload.get('due_date', 'No Due Date')
                category = payload.get('category', 'N/A')
                print(f"   {idx}. [{category}] {title}")
                print(f"      - Assignee: {assignee} | Due Date: {due_date}")
        else:
            print("   (No todos detected.)")

        # 2. 승인이 필요한 검토 항목 (Decision, Record)
        approvals = [c for c in total_candidates if (c.item_type if hasattr(c, 'item_type') else c.get('item_type')) != 'Todo']
        print(f"\n [Review Needed Items (Pending)] - {len(approvals)} items")
        if approvals:
            for idx, item in enumerate(approvals, 1):
                title = item.title if hasattr(item, 'title') else item.get('title')
                payload = item.payload_fields if hasattr(item, 'payload_fields') else item.get('payload_fields', {})
                item_type = item.item_type if hasattr(item, 'item_type') else item.get('item_type', 'N/A')
                category = payload.get('category', 'N/A')
                topic = payload.get('topic_tag', 'N/A')
                print(f"   {idx}. [{category} | {item_type}] {title}")
                print(f"      - Topic: {topic}")
        else:
            print("   (No items needing approval.)")

        print("\n" + "="*70)
        print(" [All Tests Completed] ".center(70, "="))
        print("="*70)

    except Exception as e:
        print(f"\n [!] Error during test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_real_slack_batch_test()
    print("\n" + "="*70)
