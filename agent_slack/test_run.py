import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# .env.example 파일 로드
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
    print(" [ParaWorks] 슬랙 하루 치 동기화(Batch/Sync) 통합 테스트 ".center(70, "="))
    print("="*70 + "\n")

    bot_token = os.environ.get("SLACK_BOT_TOKEN")

    if not bot_token:
        print(" [!] 에러: .env.example 파일에 SLACK_BOT_TOKEN이 없습니다.")
        return

    client = SlackWebApiClient(bot_token=bot_token)
    try:
        # 1. 봇이 참여 중인 모든 채널 목록 조회
        print("[*] 봇이 참여 중인 모든 채널 목록 조회 중...")
        all_channels = client.conversations_list()
        # 봇이 멤버인 채널만 필터링
        joined_channels = [c for c in all_channels if c.get('is_member')]

        if not joined_channels:
            print(" [!] 봇이 참여 중인 채널이 없습니다. 채널에 봇을 초대해 주세요.")
            return

        print(f"[*] 총 {len(joined_channels)}개의 참여 채널을 발견했습니다: " + 
              ", ".join([f"#{c.get('name')}" for c in joined_channels]))

        # 사용자 이름 매핑 정보 수집 (채널 공통)
        print("[*] 워크스페이스 사용자 정보 수집 중...")
        users = client.users_list()
        user_map = {u.get('id'): u.get('real_name') or u.get('name') for u in users}

        # 오늘 00:00:00 의 타임스탬프 계산
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        oldest_ts = str(today_start.timestamp())
        
        # 각 채널별로 데이터 수집 및 분석 진행
        for channel in joined_channels:
            channel_id = channel['id']
            channel_name = channel['name']
            
            print(f"\n{'-'*70}")
            print(f" [채널 분석 시작: #{channel_name} ({channel_id})] ".center(70, "-"))
            print(f"{'-'*70}\n")
            
            print(f"[*] {today_start.strftime('%Y-%m-%d')} 00:00:00 이후의 대화 기록 수집 중...")
            history = client.conversation_history(channel_id, oldest=oldest_ts)
            
            if not history:
                print(f" [!] #{channel_name} 채널에 오늘 발생한 메시지가 없습니다. 건너뜜.")
                continue

            # 각 메시지에 사용자 이름 주입
            for msg in history:
                user_id = msg.get('user')
                msg['user_name'] = user_map.get(user_id, user_id)

            print(f"[*] 총 {len(history)}건의 메시지를 수집했습니다.")
            print("[*] 동기화 기반 에이전트 분석 시작...\n")
            
            # 에이전트 실행
            result = process_daily_slack_sync(channel_id, history)
            
            print("\n [분석 결과 요약] ")
            print(f" - 업무 관련성 존재: {result.get('is_work_related')}")
            
            if result.get('summary'):
                print(f" - 요약: {result.get('summary')[:100]}...")
            
            candidates = result.get('candidates')
            if candidates and len(candidates) > 0:
                print(f" - 추출된 지식 후보: {len(candidates)}건")
                for idx, candidate in enumerate(candidates, 1):
                    title = candidate.title if hasattr(candidate, 'title') else candidate.get('title')
                    print(f"   {idx}. {title}")
            
            run_cost = result.get('run_cost')
            if run_cost:
                print(f" - 소모 비용: ${run_cost.estimated_cost_usd:.5f} (총 토큰: {run_cost.token_usage.total_tokens})")

        print("\n" + "="*70)
        print(" [모든 채널 분석 완료] ".center(70, "="))
        print("="*70)

    except Exception as e:
        print(f"\n [!] 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_real_slack_batch_test()
    print("\n" + "="*70)
