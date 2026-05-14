import requests
import json
import time

API_BASE = "http://127.0.0.1:8000/api/v1"
DEMO_USER = "hanvv-employee"

def test_slack_sync_and_dashboard():
    print("\n" + "="*70)
    print(" [ParaWorks] Backend API Integration Test (Sync + Agent + DB) ".center(70, "="))
    print("="*70 + "\n")

    headers = {
        "X-Demo-User": DEMO_USER,
        "Content-Type": "application/json"
    }

    # 1. 슬랙 동기화 트리거
    print("[*] 1. Requesting Slack sync (POST /integrations/slack/sync)...")
    try:
        sync_response = requests.post(f"{API_BASE}/integrations/slack/sync", headers=headers, timeout=60)
        if sync_response.status_code != 200:
            print(f" [!] Error: Sync failed ({sync_response.status_code})")
            print(sync_response.text)
            return

        sync_data = sync_response.json()
        print(f"[*] Sync job started: Job ID = {sync_data.get('job_id')}")
        print(f"[*] Status: {sync_data.get('status')}")
        print(f"[*] Fetched events: {sync_data.get('fetched_events')} items")
        print(f"[*] Created review items: {sync_data.get('created_review_items')} items (including agent analysis)")

        # 2. 잠시 대기 (DB 반영 시간)
        print("\n[*] 2. Processing data... (Waiting 3 seconds)")
        time.sleep(3)

        # 3. 대시보드 데이터 확인
        print("\n[*] 3. Fetching dashboard data (GET /dashboard)...")
        dash_response = requests.get(f"{API_BASE}/dashboard", headers=headers)
        if dash_response.status_code == 200:
            dash_data = dash_response.json()
            
            print(f"\n [ Dashboard Summary ]")
            print(f" - Total Pending Review Items: {dash_data.get('pending_review_count')} items")
            
            print(f"\n [ 오늘의 할 일 (Today's Todos) ]")
            todos = dash_data.get('today_todos', [])
            if todos:
                for idx, todo in enumerate(todos, 1):
                    print(f"   {idx}. [{todo['category']}] {todo['title']} (Assignee: {todo['assignee']}, Due Date: {todo['due_date']})")
            else:
                print("   (No todos extracted.)")

            print(f"\n [ Recent Items (Pending Review) ]")
            items = dash_data.get('pending_items', [])
            if items:
                for idx, item in enumerate(items, 1):
                    print(f"   {idx}. [{item['category']} | {item['item_type']}] {item['title']} (Confidence: {int(item['confidence_score']*100)}%)")
            else:
                print("   (No items pending review.)")
        else:
            print(f" [!] Error: Dashboard fetch failed ({dash_response.status_code})")

        print("\n" + "="*70)
        print(" [ Test Completed: Check the dashboard at http://localhost:3000! ] ".center(70, "="))
        print("="*70)

    except Exception as e:
        print(f"\n [!] Error during test: {e}")

if __name__ == "__main__":
    test_slack_sync_and_dashboard()
