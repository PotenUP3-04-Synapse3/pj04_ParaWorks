import requests
import json
import time

API_BASE = "http://127.0.0.1:8000/api/v1"
DEMO_USER = "hanvv-employee"

def test_slack_sync_and_dashboard():
    print("\n" + "="*70)
    print(" [ParaWorks] 백엔드 API 연동 통합 테스트 (Sync + Agent + DB) ".center(70, "="))
    print("="*70 + "\n")

    headers = {
        "X-Demo-User": DEMO_USER,
        "Content-Type": "application/json"
    }

    # 1. 슬랙 동기화 트리거
    print("[*] 1. 슬랙 동기화 요청 중 (POST /integrations/slack/sync)...")
    try:
        sync_response = requests.post(f"{API_BASE}/integrations/slack/sync", headers=headers, timeout=60)
        if sync_response.status_code != 200:
            print(f" [!] 에러: 동기화 실패 ({sync_response.status_code})")
            print(sync_response.text)
            return

        sync_data = sync_response.json()
        print(f"[*] 동기화 작업 시작됨: Job ID = {sync_data.get('job_id')}")
        print(f"[*] 상태: {sync_data.get('status')}")
        print(f"[*] 수집된 이벤트: {sync_data.get('fetched_events')}건")
        print(f"[*] 생성된 리뷰 항목: {sync_data.get('created_review_items')}건 (에이전트 분석 결과 포함)")

        # 2. 잠시 대기 (DB 반영 시간)
        print("\n[*] 2. 데이터 처리 중... (3초 대기)")
        time.sleep(3)

        # 3. 대시보드 데이터 확인
        print("\n[*] 3. 대시보드 데이터 조회 중 (GET /dashboard)...")
        dash_response = requests.get(f"{API_BASE}/dashboard", headers=headers)
        if dash_response.status_code == 200:
            dash_data = dash_response.json()
            
            print(f"\n [ 대시보드 요약 ]")
            print(f" - 전체 검토 대기 항목: {dash_data.get('pending_review_count')}건")
            
            print(f"\n [ 오늘의 할 일 (Today's Todos) ]")
            todos = dash_data.get('today_todos', [])
            if todos:
                for idx, todo in enumerate(todos, 1):
                    print(f"   {idx}. [{todo['category']}] {todo['title']} (담당: {todo['assignee']}, 기한: {todo['due_date']})")
            else:
                print("   (추출된 할 일이 없습니다.)")

            print(f"\n [ 최근 검토 항목 (Pending Review) ]")
            items = dash_data.get('pending_items', [])
            if items:
                for idx, item in enumerate(items, 1):
                    print(f"   {idx}. [{item['category']} | {item['item_type']}] {item['title']} (신뢰도: {int(item['confidence_score']*100)}%)")
            else:
                print("   (검토 대기 항목이 없습니다.)")
        else:
            print(f" [!] 에러: 대시보드 조회 실패 ({dash_response.status_code})")

        print("\n" + "="*70)
        print(" [ 테스트 완료: 이제 대시보드 화면(http://localhost:3000)에서 확인하세요! ] ".center(70, "="))
        print("="*70)

    except Exception as e:
        print(f"\n [!] 테스트 중 오류 발생: {e}")

if __name__ == "__main__":
    test_slack_sync_and_dashboard()
