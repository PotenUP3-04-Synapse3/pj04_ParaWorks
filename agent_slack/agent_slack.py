import os
import json
import re
import logging
from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END

from backend.app.agent_runtime.contracts import ReviewCandidate, TokenUsage, AgentRunCost
from backend.app.connectors.slack import SlackWebApiClient

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SlackAgent")

# 환경 변수 기반 예산 설정 (저비용 필터링 도입으로 제한 상향)
MAX_INPUT_CHARS = int(os.environ.get("AGENT_LLM_MAX_INPUT_CHARS", 30000))
COST_PER_1M_INPUT = float(os.environ.get("AGENT_LLM_INPUT_COST_PER_1M_TOKENS", 0.15))
COST_PER_1M_OUTPUT = float(os.environ.get("AGENT_LLM_OUTPUT_COST_PER_1M_TOKENS", 0.60))

# 1. 미들웨어: 개인정보 마스킹 (PII Detection)
def mask_pii(text: str) -> str:
    text = re.sub(r'\d{6}-\d{7}', '[RESIDENT_ID_MASKED]', text)
    text = re.sub(r'010-\d{3,4}-\d{4}', '[PHONE_MASKED]', text)
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL_MASKED]', text)
    return text

# 2. 다중 추출을 위한 Pydantic 래퍼 클래스
class CandidateItem(BaseModel):
    title: str = Field(description="지식의 명확한 제목")
    summary: str = Field(description="상세 내용 요약")
    
    # 차원 1: 업무 성격 (분류)
    category: str = Field(
        description="업무 분류: 'Project'(프로젝트), 'Operations'(운영/유지보수), 'Administration'(공통/지원), 'Ad-hoc'(단발성 이슈) 중 하나"
    )
    
    # 차원 2: 지식 유형
    item_type: str = Field(
        description="지식 유형: 반드시 'decision_record'(결정사항), 'todo'(할 일), 'history_event'(기록/공유) 셋 중 하나만 사용하세요."
    )
    
    # 차원 3: 구체적 토픽/프로젝트명
    topic_tag: str = Field(description="구체적인 프로젝트명이나 서비스명 (예: '홈페이지 리뉴얼', '인사정책')")
    
    # 대시보드 할 일 관리를 위한 추가 정보
    assignee: Optional[str] = Field(description="할 일(todo)인 경우 담당자 이름 (없으면 null)")
    due_date: Optional[str] = Field(description="마감 기한이 언급된 경우 (예: '2026-05-15', 없으면 null)")
    
    source_ts_list: List[str] = Field(description="이 지식의 증거가 되는 원본 메시지의 TS 값 목록 (예: '1715000.001')")
    source_snippets: List[str] = Field(description="증거가 되는 원문 일부. 핵심 발언이나 문장을 1~2개 이상 배열에 문자열로 담으세요.")

class CandidateList(BaseModel):
    candidate_items: List[CandidateItem] = Field(description="추출된 지식 후보들의 목록")

# 3. 워크플로우 상태 정의
class SlackAgentState(BaseModel):
    channel_id: str = ""
    messages: List[dict] = Field(default_factory=list)
    processed_text: str = ""
    is_work_related: bool = False
    summary: Optional[str] = None
    candidates: List[ReviewCandidate] = Field(default_factory=list)
    model_name: str = "gpt-4o-mini"
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    error: Optional[str] = None
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

def calculate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return (prompt_tokens / 1_000_000 * COST_PER_1M_INPUT) + (completion_tokens / 1_000_000 * COST_PER_1M_OUTPUT)

# 4. 노드 구현: 전처리 & 증거 매핑 (PII Masking & Evidence Mapping Middleware)
def preprocess_node(state: SlackAgentState):
    logger.info(f"[Middleware: PII Masking & Evidence] 채널({state.channel_id}) 전처리 시작.")
    
    combined_text = ""
    for msg in sorted(state.messages, key=lambda x: float(x.get("ts", 0))):
        # user_name에 '[3기/AI] 김종우'와 같은 전체 이름이 들어있으므로 이를 우선 사용
        user_display = msg.get("user_name") or msg.get("user", "Unknown")
        text = msg.get("text", "")
        ts_val = msg.get("ts", "0")
        
        # 가독성을 위한 시간 변환 (HH:MM:SS)
        readable_time = datetime.fromtimestamp(float(ts_val)).strftime('%H:%M:%S')
        
        # [시간] 이름: 메시지 [TS: ...] 포맷으로 가독성 극대화
        combined_text += f"[{readable_time}] {user_display}: {text} [TS: {ts_val}]\n"

    # Cost Guard Middleware: 길이 초과 시 Truncation 적용
    if len(combined_text) > MAX_INPUT_CHARS:
        logger.warning(f"[Middleware: Cost Guard] 텍스트 길이({len(combined_text)}자)가 제한({MAX_INPUT_CHARS}자)을 초과하여 자릅니다.")
        combined_text = combined_text[:MAX_INPUT_CHARS] + "\n...[COST_GUARD_TRUNCATED]..."

    masked_text = mask_pii(combined_text)
    return {"processed_text": masked_text, "model_name": "gpt-4o-mini"}

# 5. 노드 구현: 업무 필터링 (Tool: Work Filter / Middleware: Context Compression)
def classify_work_node(state: SlackAgentState):
    logger.info("[Tool: Work Filter] 저비용 모델로 업무 관련 메시지 선별 중...")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=state.openai_api_key)
    
    # 메시지 리스트에서 인덱스와 본문만 추출하여 프롬프트 구성
    simple_list = ""
    for i, msg in enumerate(state.messages):
        simple_list += f"[{i}] {msg.get('text', '')[:50]}\n"
        
    prompt = (
        "다음 슬랙 대화 목록 중 기업 지식으로 남길 가치가 있는 업무 관련 메시지의 번호(index)만 콤마로 구분해서 답하세요. "
        "만약 업무 관련 내용이 전혀 없다면 'NONE'이라고 답하세요.\n\n"
        f"{simple_list}"
    )
    
    response = llm.invoke(prompt)
    usage = response.usage_metadata
    
    # 리스트 형태의 content 안전하게 문자열로 변환
    raw_content = response.content
    if isinstance(raw_content, list):
        res_text = "".join([c if isinstance(c, str) else str(c) for c in raw_content]).strip().upper()
    else:
        res_text = raw_content.strip().upper()
    
    pt = usage.get('prompt_tokens', 0) if usage else 0
    ct = usage.get('completion_tokens', 0) if usage else 0
    # 정적 분석기를 위한 명시적 타입 확정
    if not isinstance(pt, int): pt = 0
    if not isinstance(ct, int): ct = 0
    
    if "NONE" in res_text:
        return {
            "is_work_related": False, 
            "total_prompt_tokens": state.total_prompt_tokens + pt,
            "total_completion_tokens": state.total_completion_tokens + ct
        }
    
    # 필터링된 인덱스 추출 및 문맥 재구성 (Context Compression)
    try:
        indices = [int(idx.strip()) for idx in res_text.split(',') if idx.strip().isdigit()]
        compressed_messages = [state.messages[i] for i in indices if i < len(state.messages)]
        
        # 압축된 텍스트 생성
        compressed_text = ""
        for msg in sorted(compressed_messages, key=lambda x: float(x.get("ts", 0))):
            user_display = msg.get("user_name", msg.get("user", "Unknown"))
            text = msg.get("text", "")
            ts_val = msg.get("ts", "0")
            
            # 가독성을 위한 시간 변환 (HH:MM:SS)
            readable_time = datetime.fromtimestamp(float(ts_val)).strftime('%H:%M:%S')
            
            compressed_text += f"[{readable_time}] {user_display}: {text} [TS: {ts_val}]\n"
            
        logger.info(f"[Middleware: Context Compression] 원본 {len(state.messages)}건 -> 필터링 {len(compressed_messages)}건으로 압축 완료.")
        
        return {
            "is_work_related": True,
            "processed_text": compressed_text,
            "total_prompt_tokens": state.total_prompt_tokens + pt,
            "total_completion_tokens": state.total_completion_tokens + ct
        }
    except Exception as e:
        logger.warning(f"필터링 파싱 실패, 전체 내용으로 진행: {e}")
        return {
            "is_work_related": True,
            "total_prompt_tokens": state.total_prompt_tokens + pt,
            "total_completion_tokens": state.total_completion_tokens + ct
        }

# 6. 노드 구현: 요약 및 모델 스위칭 (Summarizer Tool + Model Switching Middleware)
def summarize_node(state: SlackAgentState):
    # 이미 필터링을 거쳤으므로 텍스트가 짧아져서 4o-mini로도 충분할 가능성이 높아짐
    model = "gpt-4o-mini"
    if len(state.processed_text) > 2000: # 필터링 후에도 길다면 고성능 모델 사용
        model = "gpt-4o"
        logger.info(f"[Middleware: Model Switching] 압축 후에도 내용이 방대하여 고성능 모델({model})을 사용합니다.")

    logger.info(f"[Tool: Summarizer] 필터링된 핵심 맥락 요약 중... (사용 모델: {model})")
    llm = ChatOpenAI(model=model, temperature=0, api_key=state.openai_api_key)
    
    # 이름 보존을 위한 강력한 지침 추가
    prompt = (
        "다음 필터링된 업무 대화록을 주요 안건 위주로 요약하세요.\n"
        "**중요 원칙**: 대화록에 등장하는 사용자 이름(예: [3기/AI] 김종우)은 절대 줄이거나 변경하지 말고 전체 형식을 그대로 유지하세요.\n"
        "핵심 결정이나 발언이 있다면 '누가(전체 이름)' 말했는지 명시하고, [TS: ...] 정보는 지우지 말고 꼭 유지하세요:\n\n"
        f"{state.processed_text}"
    )
    
    response = llm.invoke(prompt)
    
    # 리스트 형태의 content 안전하게 문자열로 변환
    raw_content = response.content
    if isinstance(raw_content, list):
        summary_text = "".join([c if isinstance(c, str) else str(c) for c in raw_content])
    else:
        summary_text = raw_content
    
    usage = response.usage_metadata
    pt = usage.get('prompt_tokens', 0) if usage else 0
    ct = usage.get('completion_tokens', 0) if usage else 0
    if not isinstance(pt, int): pt = 0
    if not isinstance(ct, int): ct = 0
    
    return {"summary": summary_text, "model_name": model, "total_prompt_tokens": state.total_prompt_tokens + pt, "total_completion_tokens": state.total_completion_tokens + ct}

# 7. 노드 구현: 다중 지식 추출 및 폴백 (Agent + Fallback Middleware)
def extract_candidate_node(state: SlackAgentState):
    current_model = state.model_name
    logger.info(f"[Agent: Knowledge Extractor] 다중 지식 후보 추출 시작. (모델: {current_model})")
    try:
        llm = ChatOpenAI(model=current_model, temperature=0, api_key=state.openai_api_key)
        structured_llm = llm.with_structured_output(CandidateList)
        
        # 프롬프트에 이름 보존 및 스니펫 형식 지침 강화
        prompt = f"""
다음 요약본을 바탕으로 보존할 가치가 있는 기업 지식들을 추출하세요. 

**필수 준수 사항**:
1. 사용자 이름(예: [3기/AI] 김종우)은 절대로 변경하거나 성만 떼지 말고, 대화록에 있는 전체 이름 그대로 사용하세요.
2. source_snippets 배열에는 지식을 뒷받침하는 핵심 발언 원문을 그대로 채워 넣으세요. (이름을 붙이지 마세요)
3. source_ts_list 배열에는 해당 지식의 근거가 되는 메시지의 [TS: ...] 숫자값을 반드시 1개 이상 포함하세요. (매우 중요)
4. 지식 유형(item_type)은 반드시 'decision_record', 'todo', 'history_event' 중 하나만 사용하세요.

카테고리 분류 기준:
- Project (프로젝트): 명확한 기한과 목표가 있는 신규 기획/개발 건
- Operations (운영/유지보수): 상시 발생하는 서비스 운영 및 관리
- Administration (공통/지원): HR, 재무, 사내 IT 정책 등 지원 업무
- Ad-hoc (단발성 이슈): 특정 카테고리에 묶기 힘든 일회성 문제

특히 'todo' 유형은 대화 맥락에서 파악 가능한 '담당자(assignee)'와 '마감 기한(due_date)'을 반드시 포함하세요. 
마감 기한은 YYYY-MM-DD 형식으로 변환하되, 연도가 없으면 현재 연도(2026년)를 기준으로 합니다.

분석 대상 요약본:
{state.summary}
"""
        parsed_result = structured_llm.invoke(prompt)
        
        if not parsed_result or not hasattr(parsed_result, 'candidate_items'):
            logger.warning("[Agent] 추출된 결과가 없거나 형식이 올바르지 않습니다.")
            return {"candidates": [], "total_prompt_tokens": state.total_prompt_tokens + 100, "total_completion_tokens": state.total_completion_tokens + 100}

        # 기본 토큰 근사치 가산 (with_structured_output 한계 보완)
        approx_pt = len(prompt) // 4
        approx_ct = 500
        
        final_candidates = []
        # 중앙 설정 시스템에서 워크스페이스 URL 로드
        from backend.app.core.config import get_settings
        from backend.app.connectors.slack import build_slack_permalink
        settings = get_settings()
        base_url = settings.slack_workspace_url.rstrip('/')
        
        for item in parsed_result.candidate_items:
            # TS 값을 이용해 딥링크 생성
            links = []
            for ts in item.source_ts_list:
                # 표준화된 퍼머링크 생성 함수 사용 (16자리 포맷 보장)
                links.append(build_slack_permalink(base_url, state.channel_id, ts))

            # item_type 안전 처리
            safe_type = item.item_type.strip().lower()
            if safe_type not in {'decision_record', 'todo', 'history_event'}:
                safe_type = 'history_event'
                
            # snippets 안전 처리
            snippets = item.source_snippets if item.source_snippets else ["근거 발언을 추출하지 못했습니다."]
                
            final_candidates.append(ReviewCandidate(
                title=item.title,
                summary=item.summary,
                item_type=safe_type,
                source_links=links,
                source_snippets=snippets,
                confidence_score=0.85,
                permission_level="internal",
                payload_fields={
                    "category": item.category,
                    "topic_tag": item.topic_tag,
                    "original_item_type": item.item_type,
                    "assignee": item.assignee or "미지정",
                    "due_date": item.due_date or "기한없음"
                }
            ))
            
        return {"candidates": final_candidates, "total_prompt_tokens": state.total_prompt_tokens + approx_pt, "total_completion_tokens": state.total_completion_tokens + approx_ct}
        
    except Exception as e:
        logger.error(f"[Middleware: Fallback] 기본 모델 실패. Gemini 모델로 폴백합니다. Error: {e}")
        gemini_llm = ChatGoogleGenerativeAI(model="gemini-3.1-pro", temperature=0, google_api_key=state.gemini_api_key)
        
        response = gemini_llm.invoke(f"다음 텍스트에서 주요 결정 사항과 할 일을 추출해 JSON 리스트 형식으로만 답해줘. 사용자 이름은 전체 형식을 유지해줘: {state.summary}")
        
        # 리스트 형태의 content 안전하게 문자열로 변환
        raw_content = response.content
        if isinstance(raw_content, list):
            res_text = "".join([c if isinstance(c, str) else str(c) for c in raw_content])
        else:
            res_text = raw_content

        return {
            "candidates": [ReviewCandidate(
                title="Fallback Extracted Multi-Item",
                summary="제미나이 폴백 작동: " + res_text[:100],
                item_type="history_event",
                source_links=[],
                source_snippets=[state.processed_text[:100]],
                confidence_score=0.5,
                permission_level="internal"
            )],
            "total_prompt_tokens": state.total_prompt_tokens + 100,
            "total_completion_tokens": state.total_completion_tokens + 100
        }

# 8. LangGraph 그래프 구축
def build_slack_agent_graph():
    workflow = StateGraph(SlackAgentState)
    workflow.add_node("preprocess", preprocess_node)
    workflow.add_node("classify", classify_work_node)
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("extract", extract_candidate_node)
    
    workflow.add_edge(START, "preprocess")
    workflow.add_edge("preprocess", "classify")
    workflow.add_conditional_edges("classify", lambda state: "summarize" if state.is_work_related else END)
    workflow.add_edge("summarize", "extract")
    workflow.add_edge("extract", END)
    return workflow.compile()

# 9. 실행 엔트리포인트
def process_daily_slack_sync(channel_id: str, messages: List[dict], openai_api_key: Optional[str] = None, gemini_api_key: Optional[str] = None):
    app = build_slack_agent_graph()
    initial_state = SlackAgentState(
        channel_id=channel_id, 
        messages=messages,
        openai_api_key=openai_api_key,
        gemini_api_key=gemini_api_key
    )
    
    final_state = app.invoke(initial_state)
    
    # Token Tracker 미들웨어: 최종 비용 정산 로직
    cost_usd = calculate_cost(final_state["total_prompt_tokens"], final_state["total_completion_tokens"])
    
    agent_run_cost = AgentRunCost(
        model_name=final_state["model_name"],
        token_usage=TokenUsage(
            input_tokens=final_state["total_prompt_tokens"],
            output_tokens=final_state["total_completion_tokens"]
        ),
        estimated_cost_usd=cost_usd,
        cache_hit=False # 배치는 현재 캐시 미적용
    )
    
    logger.info(f"[MW: Token Tracker] 비용 정산 완료: ${cost_usd:.5f} (총 토큰: {agent_run_cost.token_usage.total_tokens})")
    
    # 결과 반환 시 비용 객체 추가
    final_state["run_cost"] = agent_run_cost
    return final_state
