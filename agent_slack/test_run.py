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
    channel_ids = os.environ.get("SLACK_CHANNEL_IDS")

    if not bot_token or not channel_ids:
        print(" [!] 에러: .env.example 파일에 토큰 또는 채널 ID가 없습니다.")
        return

    target_channel = channel_ids.split(',')[0].strip()
    print(f"[*] 대상 채널: {target_channel}")
    
    client = SlackWebApiClient(bot_token=bot_token)
    try:
        # 오늘 00:00:00 의 타임스탬프 계산 (정확히 오늘 대화만 가져오기 위함)
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        oldest_ts = str(today_start.timestamp())
        
        print(f"[*] {today_start.strftime('%Y-%m-%d')} 00:00:00 이후의 대화 기록 일괄 수집 중...")
        
        # 오늘 데이터만 수집하도록 oldest 인자 추가
        history = client.conversation_history(target_channel, oldest=oldest_ts)
        
        if not history:
            print(" [!] 오늘(00:00 이후) 발생한 메시지가 채널에 존재하지 않습니다.")
            return

        # 사용자 이름 매핑 정보 수집 (가독성 향상)
        print("[*] 워크스페이스 사용자 정보 수집 중...")
        users = client.users_list()
        user_map = {u.get('id'): u.get('real_name') or u.get('name') for u in users}
        
        # 각 메시지에 사용자 이름 주입
        for msg in history:
            user_id = msg.get('user')
            msg['user_name'] = user_map.get(user_id, user_id)

        print(f"[*] 총 {len(history)}건의 메시지를 수집했습니다.\n")
        print("[*] 동기화 기반 에이전트 분석 시작 (아래에 미들웨어 작동 로그가 표시됩니다)\n")
        
        # 에이전트 실행 (단일 메시지가 아닌 메시지 리스트 전체 전달)
        result = process_daily_slack_sync(target_channel, history)
        
        print("\n" + "-" * 50)
        print(" [최종 분석 결과] ")
        print(f" - 업무 관련성 존재 여부: {result.get('is_work_related')}")
        
        if result.get('summary'):
            print(f"\n [오늘의 요약본]\n{result.get('summary')}\n")
        
        candidates = result.get('candidates')
        if candidates and len(candidates) > 0:
            print(f" [추출된 지식 후보 총 {len(candidates)}건]")
            for idx, candidate in enumerate(candidates, 1):
                title = candidate.title if hasattr(candidate, 'title') else candidate.get('title')
                summary = candidate.summary if hasattr(candidate, 'summary') else candidate.get('summary')
                item_type = candidate.item_type if hasattr(candidate, 'item_type') else candidate.get('item_type')
                links = candidate.source_links if hasattr(candidate, 'source_links') else candidate.get('source_links', [])
                snippets = candidate.source_snippets if hasattr(candidate, 'source_snippets') else candidate.get('source_snippets', [])
                
                print(f"   {idx}. [{item_type}] {title}")
                print(f"      - 내용: {summary[:50]}...")
                if snippets:
                    print(f"      - 원문 증거: {snippets[0][:80]}...")
                if links:
                    print(f"      - 링크: {links[0]}")
        else:
            print(" - 추출된 지식 후보가 없습니다.")
        
        if result.get('error'):
            print(f"\n [!] 에러 발생: {result.get('error')}")
            
        print(f"\n - 사용된 모델: {result.get('model_name')}")
        
        run_cost = result.get('run_cost')
        if run_cost:
            print(f" - 소모 비용: ${run_cost.estimated_cost_usd:.5f} (총 토큰: {run_cost.token_usage.total_tokens})")

    except Exception as e:
        print(f"\n [!] 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_real_slack_batch_test()
    print("\n" + "="*70)
