# ParaWorks 기술 개요 (Technical Overview)

ParaWorks는 기업 내 산재된 다양한 커뮤니케이션 채널과 문서 저장소의 데이터를 통합 분석하여, 조직의 기억을 하나로 모으고 지식의 소실을 방지하는 **"회사 기억 플랫폼"**입니다.

## 1. 제품 개요
많은 스타트업과 기업들이 Slack에서의 휘발성 대화, Gmail에 묻힌 히스토리, Google Drive의 방대한 문서들 사이에서 "누가, 언제, 왜 이 결정을 내렸는가?"를 찾는 데 많은 시간을 허비합니다. ParaWorks는 이러한 문제를 AI 에이전트를 통해 자동화하고 구조화합니다.

## 2. 핵심 기능
- **통합 동기화 (Multi-Source Sync)**: Slack, Gmail, Google Drive 데이터를 실시간 또는 주기적으로 동기화합니다.
- **AI 기반 결정사항/타임라인 추출**: 방대한 대화 맥락 속에서 중요한 의사결정, 할 일(Todo), 프로젝트 타임라인 후보를 LLM이 자동으로 추출합니다.
- **Review Queue (신뢰 지식화)**: AI가 추출한 후보를 담당자가 검토하고 승인함으로써, 오답(Hallucination)을 배제한 신뢰할 수 있는 공식 지식을 구축합니다.
- **권한 인지형 RAG (Permission-Aware RAG)**: 사용자의 접근 권한(Public/Internal/Restricted)을 실시간으로 확인하여, 권한이 있는 정보만 검색 결과 및 AI 답변에 포함합니다.

## 3. 기술 스택
ParaWorks는 현대적이고 확장 가능한 기술 스택을 기반으로 구축되었습니다.

- **Backend**: Python 3.11+, FastAPI, LangChain, LangGraph
- **Database**: PostgreSQL (Relational Data), pgvector (Vector Store)
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS
- **Infra/Task**: Docker, Redis, Celery (Async Jobs)
- **AI/LLM**: OpenAI GPT-4o, Claude 3.5 Sonnet (Agentic Workflows)

## 4. 데이터 흐름 (Data Flow)
1. **Ingestion**: Connector를 통해 외부 데이터(Slack, Gmail 등)를 수집합니다.
2. **Preprocessing**: 텍스트 추출, 메타데이터 정제 및 권한 수준을 분류합니다.
3. **Agent Analysis**: LangGraph 기반의 에이전트들이 맥락을 분석하고 결정사항 후보를 생성합니다.
4. **Human-in-the-loop**: Review Queue를 통해 사람이 최종 승인합니다.
5. **RAG Serving**: 승인된 지식과 원본 증거(Evidence)를 벡터화하여 사용자 질문에 답변합니다.

## 5. 핵심 차별점
- **Evidence-First 설계**: 모든 AI 답변은 반드시 근거가 되는 원본 메시지 링크나 문서 스니펫을 포함합니다.
- **강력한 보안**: 데이터의 원본 권한 체계를 그대로 유지하며, Restricted 데이터에 대한 엄격한 필터링을 제공합니다.

---
*작성일: 2025년 12월 26일*
*작성자: 김용희 CTO*
