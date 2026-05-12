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
    print(" [ParaWorks] 슬랙 최근 일주일(7일) 동기화 통합 테스트 ".center(70, "="))
    print("="*70 + "\n")

    # 사용자 토큰을 우선 확인 (개인 DM 테스트용), 없으면 봇 토큰 사용
    user_token = os.environ.get("SLACK_USER_TOKEN")
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    
    token_to_use = user_token if user_token else bot_token
    token_type = "사용자(User)" if user_token else "봇(Bot)"

    if not token_to_use:
        print(" [!] 에러: .env 파일에 토큰이 없습니다.")
        return

    print(f"[*] 사용 중인 토큰 타입: {token_type}")
    client = SlackWebApiClient(bot_token=token_to_use)
    
    total_candidates = [] # 모든 채널의 후보를 모으기 위한 리스트

    try:
        # 사용자 이름 매핑 정보 수집 (채널 공통)
        print("[*] 워크스페이스 사용자 정보 수집 중...")
        users = client.users_list()
        user_map = {u.get('id'): u.get('real_name') or u.get('name') for u in users}

        # 1. 참여 중인 모든 채널 및 DM 목록 조회
        print("[*] 봇/사용자가 참여 중인 모든 채널 및 DM 목록 조회 중...")
        all_channels = client.conversations_list()
        # 일반 채널은 is_member, DM은 is_im/is_mpim으로 필터링
        joined_channels = [
            c for c in all_channels 
            if c.get('is_member') or c.get('is_im') or c.get('is_mpim')
        ]

        if not joined_channels:
            print(" [!] 참여 중인 채널이나 DM이 없습니다.")
            return

        def get_channel_display_name(c):
            if c.get('is_im'):
                user_id = c.get('user')
                user_name = user_map.get(user_id, user_id) if user_id else '알수없음'
                return f"개인DM(@{user_name})"
            elif c.get('is_mpim'):
                return f"그룹DM({c.get('name', 'unknown')})"
            else:
                return f"#{c.get('name', 'unknown')}"

        print(f"[*] 총 {len(joined_channels)}개의 참여 채널/DM을 발견했습니다:")
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
            print(f" [채널 분석 시작: {channel_name} ({channel_id})] ".center(70, "-"))
            print(f"{'-'*70}\n")
            
            print(f"[*] {today_start.strftime('%Y-%m-%d')} 이후의 최근 7일간 대화 기록 수집 중...")
            history = client.conversation_history(channel_id, oldest=oldest_ts)
            
            if not history:
                print(f" [!] {channel_name} 채널에 최근 7일간 발생한 메시지가 없습니다. 건너뜀.")
                continue

            # 각 메시지에 사용자 이름 주입
            for msg in history:
                user_id = msg.get('user')
                msg['user_name'] = user_map.get(user_id, user_id)

            print(f"[*] 총 {len(history)}건의 메시지를 수집했습니다.")
            print("[*] 동기화 기반 에이전트 분석 시작...\n")
            
            # 에이전트 실행
            result = process_daily_slack_sync(channel_id, history)
            
            candidates = result.get('candidates', [])
            if candidates:
                total_candidates.extend(candidates)
            
            print("\n [채널 분석 요약] ")
            print(f" - 업무 관련성 존재: {result.get('is_work_related')}")
            
            if result.get('summary'):
                print(f" - 요약: {result.get('summary')[:100]}...")
            
            if candidates:
                print(f" - 발견된 지식 후보: {len(candidates)}건")
            
            run_cost = result.get('run_cost')
            if run_cost:
                print(f" - 소모 비용: ${run_cost.estimated_cost_usd:.5f} (총 토큰: {run_cost.token_usage.total_tokens})")

        # === 최종 요약 섹션 ===
        print("\n" + "="*70)
        print(" [ ParaWorks 최종 분석 결과 요약 ] ".center(70, "="))
        print("="*70)

        # 1. 오늘의 할 일 (Todo)
        todos = [c for c in total_candidates if (c.item_type if hasattr(c, 'item_type') else c.get('item_type')) == 'Todo']
        print(f"\n [오늘의 할 일 (Action Items)] - {len(todos)}건")
        if todos:
            for idx, todo in enumerate(todos, 1):
                title = todo.title if hasattr(todo, 'title') else todo.get('title')
                payload = todo.payload_fields if hasattr(todo, 'payload_fields') else todo.get('payload_fields', {})
                assignee = payload.get('assignee', '미지정')
                due_date = payload.get('due_date', '기한없음')
                category = payload.get('category', 'N/A')
                print(f"   {idx}. [{category}] {title}")
                print(f"      - 담당자: {assignee} | 기한: {due_date}")
        else:
            print("   (검출된 할 일이 없습니다.)")

        # 2. 승인이 필요한 검토 항목 (Decision, Record)
        approvals = [c for c in total_candidates if (c.item_type if hasattr(c, 'item_type') else c.get('item_type')) != 'Todo']
        print(f"\n [승인이 필요한 검토 항목 (Review Needed)] - {len(approvals)}건")
        if approvals:
            for idx, item in enumerate(approvals, 1):
                title = item.title if hasattr(item, 'title') else item.get('title')
                payload = item.payload_fields if hasattr(item, 'payload_fields') else item.get('payload_fields', {})
                item_type = item.item_type if hasattr(item, 'item_type') else item.get('item_type', 'N/A')
                category = payload.get('category', 'N/A')
                topic = payload.get('topic_tag', 'N/A')
                print(f"   {idx}. [{category} | {item_type}] {title}")
                print(f"      - 토픽: {topic}")
        else:
            print("   (승인이 필요한 항목이 없습니다.)")

        print("\n" + "="*70)
        print(" [모든 테스트 완료] ".center(70, "="))
        print("="*70)

    except Exception as e:
        print(f"\n [!] 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_real_slack_batch_test()
    print("\n" + "="*70)
