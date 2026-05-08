# ParaWorks 포트폴리오: 슬랙 에이전트 및 커뮤니케이션 인텔리전스
**개발자:** 김용희 (Developer A)
**역할:** Communication Intelligence Agent 소유자

---

## 1. 프로젝트 개요 (Project Summary)
ParaWorks는 기업 내 흩어진 슬랙 메시지, 메일, 문서를 '조직의 기억'으로 변환하는 멀티 에이전트 플랫폼입니다. 저는 이 중 **슬랙 에이전트(Slack Agent)**의 전체 생명주기를 설계하고 구현했습니다.

## 2. 해결하려는 문제 (Problem Statement)
- **휘발되는 의사결정:** 슬랙의 방대한 메시지 속에서 중요한 의사결정과 할 일(Todo)이 기록되지 않고 잊혀짐.
- **맥락의 부재:** AI가 생성한 요약본이 실제 어떤 메시지에 근거했는지 알 수 없어 신뢰도가 떨어짐.
- **토큰 비용 부담:** 모든 채널의 메시지를 LLM에 보내는 것은 비효율적이며 비용 통제가 어려움.

## 3. 주요 기여 및 해결책 (Key Contributions & Solutions)

### 3.1 증거 중심의 슬랙 커넥터 (Evidence-First Slack Connector)
- **어댑터 패턴(Adapter Pattern) 적용:** `SlackApiClient` 프로토콜을 정의하여 외부 SDK에 의존하지 않는 독립적인 커넥터 구현.
- **맥락 보존 증거 추출:** 스레드 답글(Reply) 동기화 시 부모 메시지의 맥락을 메타데이터와 함께 보존하여 에이전트의 이해도 향상.
- **증분 동기화:** 증분 커서(Incremental Cursor) 로직을 적용하여 중복 데이터 수집을 방지하고 비용 절감.

### 3.2 멀티 LLM 기반 슬랙 에이전트 (Multi-LLM Slack Agent)
- **하이브리드 모델 구조:** OpenAI(Primary)와 Gemini(Fallback)를 결합한 어댑터 구조를 설계하여 API 가용성 확보.
- **랭킹 기반 증거 선택 (Ranked Evidence Selection):** 전체 메시지를 보내는 대신, 중요도에 따라 랭킹화하고 중복을 제거(Dedupe)한 뒤 예산(Budget Cap) 내에서 최적의 맥락만 추출하여 전송.

### 3.3 검토 큐(Review Queue) 통합 및 지식 승격
- **AI-Human 루프 구현:** 에이전트가 추출한 후보(의사결정, 할 일, 타임라인)를 즉시 지식으로 저장하지 않고, `pending_review` 상태로 검토 큐에 전송.
- **증거 기반 검토 UX:** 검토자가 AI 답변의 근거가 된 슬랙 메시지 원문(Snippet)과 링크(URL)를 즉시 확인할 수 있도록 `Source Evidence Drawer` 연동.

## 4. 기술적 강점 (Technical Highlights)

- **비용 가시성 (Cost Observability):** 모든 에이전트 실행을 `AgentRun`으로 기록하고, 사용된 토큰과 예상 비용을 UI에 노출하여 운영 가시성 확보.
- **보안 및 권한 보존:** 슬랙의 소스 권한(Permission)을 지식 승격 과정까지 유지하여 권한 인지형 RAG의 기반 마련.
- **테스트 주도 개발 (TDD):** 60개 이상의 백엔드 테스트 케이스를 통해 슬랙 페이로드 매핑, 에이전트 런타임, 지식 승격 로직의 안정성 검증.

## 5. 성과 지표 (Metrics)
- **비용 최적화:** 증분 동기화 및 랭킹 기반 맥락 선택을 통해 불필요한 LLM API 호출 30% 이상 감소 예상.
- **신뢰도:** 모든 AI 생성물에 100% 출처(Source Evidence)를 첨부하여 지식의 신뢰성 확보.
- **안정성:** 백엔드 테스트 Suite 100% 통과 및 Playwright 기반의 E2E 스모크 테스트 완료.

---

## 6. 핵심 문구 (Portfolio Talking Points)
> "단순히 슬랙 메시지를 요약하는 에이전트가 아니라, 기업이 AI의 결과물을 신뢰하고 실제 업무 지식으로 활용할 수 있도록 **증거(Evidence)와 검토(Review)** 프로세스를 아키텍처 레벨에서 통합했습니다. 특히 멀티 LLM 구조와 비용 통제 전략을 통해 비즈니스 지속 가능성을 고려한 설계를 지향했습니다."
