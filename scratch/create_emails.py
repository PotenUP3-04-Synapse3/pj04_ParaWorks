import os

base_path = r"c:\potenup3\pj04_ParaWorks\data\demo_data\email"
os.makedirs(base_path, exist_ok=True)

emails = [
    {
        "file": "2026-03-15_Thread1_Msg2.md",
        "content": """---
from: yonghee199702@gmail.com
to: kjw4work@gmail.com
cc: mina@paraworks.com
date: 2026-03-15 14:30:00
subject: RE: [논의] K테크 솔루션즈 파일럿 제안 검토 요청
---
종우님, 확인했습니다.

솔직히 말씀드리면 1개월은 너무 짧습니다. 
우리 제품의 특성상 데이터가 쌓이고 Agent가 학습/검토하는 과정을 제대로 보여주려면 최소 3개월은 필요합니다.
괜히 짧게 했다가 "별거 없네"라는 인상을 줄까 봐 걱정되네요.

성공 지표도 승인율 70% 정도로 잡고, 제대로 3개월 제안하는 게 어떨까요?
"""
    },
    {
        "file": "2026-03-15_Thread1_Msg3.md",
        "content": """---
from: kjw4work@gmail.com
to: yonghee199702@gmail.com
cc: mina@paraworks.com
date: 2026-03-15 16:00:00
subject: RE: RE: [논의] K테크 솔루션즈 파일럿 제안 검토 요청
---
네, 용희님 의견에 동의합니다. 

K테크 담당자에게 3개월의 필요성을 다시 설명하고, 제안서 v2에 해당 내용을 반영해서 업데이트하겠습니다.
미나님과 협의해서 성공 지표 섹션도 강화할게요.
"""
    },
    {
        "file": "2026-05-12_Thread2_Msg1.md",
        "content": """---
from: kjw4work@gmail.com
to: hanvv3@gmail.com
cc: mina@paraworks.com
date: 2026-05-12 11:00:00
subject: [긴급] K테크 파일럿 최종 계약 조건 확정 및 승인 요청
---
승헌님,

K테크 솔루션즈와 파일럿 조건 최종 조율 마쳤습니다.
- 기간: 3개월
- 비용: 월 200만원 (VAT 별도)
- 시작일: 2026년 5월 18일

다음 주 월요일부터 바로 온보딩 들어가는 것으로 합의했습니다. 
최종 승인해주시면 바로 전자계약 진행하겠습니다.
"""
    },
    {
        "file": "2026-05-13_Thread2_Msg2.md",
        "content": """---
from: hanvv3@gmail.com
to: kjw4work@gmail.com
cc: mina@paraworks.com
date: 2026-05-13 09:15:00
subject: RE: [긴급] K테크 파일럿 최종 계약 조건 확정 및 승인 요청
---
종우님, 수고 많으셨습니다.

조건 아주 좋습니다. 승인합니다. 
5월 18일이 우리 서비스 데모 데이이기도 한데, K테크 온보딩도 겹치니 팀원들 리소스 분배 잘 부탁드립니다.
오늘 중으로 계약 완료하고 공지해주세요.
"""
    },
    {
        "file": "2026-05-14_Thread3_Msg1.md",
        "content": """---
from: hanvv3@gmail.com
to: kjw4work@gmail.com, yonghee199702@gmail.com
date: 2026-05-14 15:20:00
subject: [IR] A벤처스 미팅 결과 공유 및 액션 아이템
---
오늘 오후 A벤처스 파트너 미팅 결과 공유합니다.

전체적으로 우리 제품의 '권한 인지형 RAG'와 'Review Queue' 프로세스에 대해 혁신적이라는 평가를 받았습니다.
다만, 2026년 하반기 ARR 프로젝션에 대해 좀 더 디테일한 근거를 요청받았습니다.

종우님, 재무 프로젝션 2026 파일에 해당 부분 보완해서 업데이트 부탁드립니다.
내일 오전 중으로 마무리해서 전달해주시면 좋겠네요. 해당 문서는 기밀로 유지해주세요.
"""
    },
    {
        "file": "2026-05-14_Thread3_Msg2.md",
        "content": """---
from: kjw4work@gmail.com
to: hanvv3@gmail.com
cc: yonghee199702@gmail.com
date: 2026-05-14 17:45:00
subject: RE: [IR] A벤처스 미팅 결과 공유 및 액션 아이템
---
승헌님, 미팅 고생 많으셨습니다.

말씀하신 재무 프로젝션 2026 파일 업데이트 시작했습니다. 
하반기 영업 파이프라인 수치를 좀 더 공격적으로 반영하고 근거를 보강하겠습니다.
내일 오전 10시 전까지 공유드릴게요. restricted 권한으로 업로드하겠습니다.
"""
    },
    {
        "file": "2026-05-16_Thread4_Msg1.md",
        "content": """---
from: hanvv3@gmail.com
to: hanvv3@gmail.com, kjw4work@gmail.com, yonghee199702@gmail.com, mina@paraworks.com, hanvv3@koreacu.ac.kr
date: 2026-05-16 10:00:00
subject: [공지] 5월 18일 데모 데이 및 K테크 온보딩 최종 점검
---
팀 여러분,

드디어 모레가 우리 서비스 정식 데모 데이이자 K테크 솔루션즈 온보딩 날입니다.
지금까지 준비한 모든 데이터와 에이전트 성능을 보여줄 때입니다.

각 파트별로 최종 점검 부탁드립니다.
특히 권한별 검색 결과가 정확히 나오는지, Review Queue에 데이터가 잘 쌓이는지 확인해주세요.
월요일 오전 9시에 최종 스탠드업 미팅 하겠습니다.
"""
    },
    {
        "file": "2026-05-17_Thread4_Msg2.md",
        "content": """---
from: yonghee199702@gmail.com
to: hanvv3@gmail.com
date: 2026-05-17 14:00:00
subject: RE: [공지] 5월 18일 데모 데이 및 K테크 온보딩 최종 점검
---
기술팀 준비 완료되었습니다.

pgvector 인덱싱 상태 최신으로 업데이트했고, 
어제 늦게까지 시연 시나리오대로 테스트해본 결과 RAG 답변 정확도와 citation 모두 문제 없습니다.
내일 뵙겠습니다!
"""
    },
    {
        "file": "2026-05-17_Thread4_Msg3.md",
        "content": """---
from: mina@paraworks.com
to: hanvv3@gmail.com
date: 2026-05-17 16:30:00
subject: RE: RE: [공지] 5월 18일 데모 데이 및 K테크 온보딩 최종 점검
---
미나입니다.

온보딩 가이드 최신본과 데모용 추가 시나리오 문서들 Drive에 최종 업로드했습니다.
Review Queue에 대기 중인 항목들도 실제 시연 시나리오에 맞춰 세팅해두었습니다.
내일 시연 기대되네요! 화이팅입니다.
"""
    }
]

for email in emails:
    with open(os.path.join(base_path, email["file"]), "w", encoding="utf-8") as f:
        f.write(email["content"])
    print(f"Created {email['file']}")
