import os
import shutil

root_path = r"c:\potenup3\pj04_ParaWorks\data\demo_data\drive"
minutes_path = os.path.join(root_path, "04_회의록")

# Old files list (approximate matching since names might be garbled in shell)
# Actually it's safer to just empty the directory and create new ones.
if os.path.exists(minutes_path):
    shutil.rmtree(minutes_path)
os.makedirs(minutes_path, exist_ok=True)

minutes = [
    {
        "file": "2026-03-15_파일럿전략_회의.md",
        "content": """# 2026-03-15 파일럿 전략 회의록

## 1. 회의 개요
- **일시**: 2026년 3월 15일 (일) 10:00 ~ 11:00
- **참석자**: 한승헌(CEO), 김종우(COO), 김용희(CTO)

## 2. 안건: K테크 솔루션즈 파일럿 전략 검토
- **논의**: 1개월 파일럿 제안에 대한 타당성 검토.
- **결정**: 1개월은 짧으므로 3개월로 제안하기로 확정. 성공 지표는 승인율 70% 목표.
"""
    },
    {
        "file": "2026-04-05_IR전략_킥오프.md",
        "content": """# 2026-04-05 IR 전략 킥오프 회의록

## 1. 회의 개요
- **일시**: 2026년 4월 5일 (일) 14:00 ~ 15:30
- **참석자**: 한승헌(CEO), 김종우(COO), 김용희(CTO)

## 2. 안건: 시드 라운드 투자 유치 계획
- **목표**: 투자금 15억, Pre-money valuation 70억 기준.
- **결정**: 재무 프로젝션 문서는 restricted로 관리하고, 공개 IR 데크와 분리함.
"""
    },
    {
        "file": "2026-05-11_K테크_최종조율.md",
        "content": """# 2026-05-11 K테크 최종 조율 회의록

## 1. 회의 개요
- **일시**: 2026년 5월 11일 (월) 11:00 ~ 12:00
- **참석자**: 김종우(COO), 김미나(PM)

## 2. 안건: 온보딩 일정 및 최종 계약 조건 확인
- **내용**: 월 200만원, 3개월 파일럿 최종 합의. 5월 18일부터 온보딩 시작.
- **결정**: 온보딩 전까지 NDA 체결 및 보안 교육 자료 준비 완료하기로 함.
"""
    },
    {
        "file": "2026-05-13_VC미팅_메모_A벤처스.md",
        "content": """# 2026-05-13 A벤처스 투자 미팅 메모 (Restricted)

## 1. 미팅 개요
- **일시**: 2026년 5월 13일 (수) 14:00 ~ 15:00
- **참석자**: 한승헌(CEO), 김종우(COO), A벤처스 파트너

## 2. 주요 질의응답
- **질문**: 권한 인지형 RAG의 보안 수준은?
- **답변**: pgvector 필터링과 애플리케이션 레벨의 RBAC을 결합하여 완벽하게 격리함.
- **결정**: 하반기 매출 근거 보강하여 재공유하기로 함.
"""
    },
    {
        "file": "2026-05-15_온보딩_준비회의.md",
        "content": """# 2026-05-15 데모 및 온보딩 준비 회의록

## 1. 회의 개요
- **일시**: 2026년 5월 15일 (금) 16:00 ~ 17:30
- **참석자**: 전 사원

## 2. 안건: 5/18 데모 데이 및 K테크 온보딩 리소스 배분
- **결정**: CTO는 기술 시연, COO는 계약 마무리, PM은 온보딩 가이드 배포 담당.
"""
    },
    {
        "file": "2026-05-18_데모_및_온보딩_킥오프.md",
        "content": """# 2026-05-18 데모 데이 및 온보딩 킥오프

## 1. 개요
- **일시**: 2026년 5월 18일 (월) 09:00 ~ 10:00
- **참석자**: 전 사원

## 2. 아침 스탠드업
- 드디어 오늘입니다. 모든 시스템 정상 확인 완료. 
- 오전 K테크 온보딩 시작, 오후 VC 대상 서비스 데모 진행.
"""
    }
]

for item in minutes:
    with open(os.path.join(minutes_path, item["file"]), "w", encoding="utf-8") as f:
        f.write(item["content"])

# Add rich documents
extra_docs = [
    {
        "path": "00_회사규정/보안_정책_v2.0_K테크_반영본.md",
        "content": "# 보안 정책 v2.0 (K테크 파일럿 전용)\n\n- 외부 파트너 접속 시 MFA 의무화\n- 민감 데이터 접근 로그 주 단위 리뷰\n- 업데이트 날짜: 2026-05-13"
    },
    {
        "path": "03_IR_투자/시장_분석_보고서_2026_Q2_업데이트.md",
        "content": "# 2026년 Q2 시장 분석 보고서\n\n- AI Agent 시장 연평균 성장률 35% 예상\n- ParaWorks 점유율 목표치 상향\n- 작성일: 2026-05-14"
    },
    {
        "path": "02_파일럿_프로젝트/K테크_사용자_교육_자료.md",
        "content": "# K테크 솔루션즈 사용자 교육 가이드\n\n- ParaWorks 사용법 요약\n- Review Queue 승인 프로세스 안내\n- 작성일: 2026-05-18"
    }
]

for doc in extra_docs:
    full_path = os.path.join(root_path, doc["path"])
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(doc["content"])
