# ParaWorks 개발자 협업 가이드 (Slack Agent 파트)

본 문서는 **개발자 A(김용희)**가 담당하는 Slack Agent 시스템의 구조를 설명하고, **개발자 B(김종우)** 및 **개발자 C(한승헌)**와의 원활한 협업을 위해 작성되었습니다.

---

## 1. 팀 역할 정의
- **개발자 A (김용희)**: Slack Agent 설계 및 커뮤니케이션 인텔리전스 구현 (이벤트 기반 추출, PII 마스킹, 요약 로직).
- **개발자 B (김종우)**: 문서 파이싱 및 지식 파이프라인 구축 (Google Drive 연동, 벡터 DB 인덱싱).
- **개발자 C (한승헌)**: 오케스트레이션 및 리뷰 제품 관리 (LangGraph 메인 워크플로우, 리뷰 큐 UI, 권한 관리).

---

## 2. Slack Agent 작동 원리 (Batch/Sync-Driven)

우리 시스템은 실시간 폴링이나 이벤트 감시 방식에서 벗어나, **일괄 동기화(Batch/Sync)** 방식으로 작동합니다. (버튼 클릭 또는 스케줄러에 의해 트리거됨)

1.  **동기화 수신**: 사용자가 '동기화' 버튼을 누르거나 설정된 시간이 되면 하루 동안(또는 특정 기간)의 채널 대화 목록을 수집합니다.
2.  **전처리 (Middleware)**: 수집된 전체 메시지에 대해 로깅 및 개인정보(PII) 마스킹이 수행됩니다.
3.  **데이터 필터링 및 요약**: 대화 중 업무와 관련된 메시지만 선별하여 하나의 거대한 문맥으로 연결하고, 전체 흐름을 요약합니다.
4.  **다중 지식 추출**: 요약본을 바탕으로 여러 개의 정제된 `ReviewCandidate` 객체(결정사항, 할 일 등)를 생성하여 **개발자 C(한승헌)**의 리뷰 큐 시스템으로 전달합니다.

---

## 3. 개발자 간 협업 지점

### 3.1 개발자 C (한승헌)님께: 리뷰 큐 연동
- **전달 데이터**: Slack Agent는 `ReviewCandidate` 목록과 토큰 소모량이 계산된 `AgentRunCost`를 함께 전달합니다.
- **포함 필수값 (Evidence-First)**: 
    - `source_links`: 슬랙 원본 메시지로 바로 갈 수 있는 타임스탬프(`ts`) 기반 딥링크.
    - `source_snippets`: 사용자가 판단할 수 있는 마스킹 처리된 원문 텍스트.
    - `confidence_score`: 추출 결과에 대한 AI의 신뢰도.

### 3.2 개발자 B (김종우)님께: 지식 파이프라인 연동
- **확정 데이터 활용**: 리뷰 큐에서 승인된 슬랙 지식은 `DecisionRecord` 또는 `TimelineEvent` 테이블에 저장됩니다.
- **RAG 활용**: 승인된 데이터는 김종우님이 관리하시는 벡터 DB 인덱싱 대상에 포함되므로, 데이터 형식(JSON)에 대한 정렬이 필요할 때 언제든 협의 가능합니다.

### 3.3 데이터 인터페이스 정의 (JSON Payload Example)
Slack Agent의 분석 결과는 아래와 같은 구조화된 데이터로 반환됩니다. 모든 데이터 필드는 `backend/app/agent_runtime/contracts.py`에 정의된 규격을 준수합니다.

```json
{
  "candidates": [
    {
      "item_type": "decision_record",
      "title": "벡터 DB 도입 결정",
      "summary": "금일 회의를 통해 벡터 DB는 pgvector를 사용하기로 확정함.",
      "source_links": [
        "https://workspace.slack.com/archives/C123/p1715000001"
      ],
      "source_snippets": [
        "[10:05] 김용희: 벡터 DB는 pgvector로 가는 게 좋겠네요."
      ],
      "confidence_score": 0.85,
      "permission_level": "internal",
      "uncertainty_reason": null
    }
  ],
  "run_cost": {
    "model_name": "gpt-4o-mini",
    "token_usage": {
      "input_tokens": 1200,
      "output_tokens": 350,
      "total_tokens": 1550
    },
    "estimated_cost_usd": 0.00039,
    "cache_hit": false
  }
}
```

---

## 4. 공통 준수 사항
- **비용 및 예산 통제 (Cost Guard)**: 일괄 동기화 시 데이터가 30,000자를 초과하면 안전하게 자르거나(Truncation) 묶음 처리하여 토큰 폭발을 방지합니다. 또한 실행 결과에 항상 비용 정보를 반환합니다.
- **에러 처리 (Fallback)**: 슬랙 API 장애나 모델 호출 실패 시 **Fallback 미들웨어**가 작동하여 `gemini-3.1-pro` 모델 등으로 자동 전환되도록 설계되어 있습니다.
- **보안 (PII Masking)**: 모든 대화 데이터는 LLM으로 전달되기 전 김용희 담당 파트에서 개인정보 마스킹을 완료한 후 전달합니다.

---
**최종 수정일**: 2026-05-12
**작성자**: 개발자 A 김용희 (백엔드 API 및 에이전트 분석 연동 완료)
