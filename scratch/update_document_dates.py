import os
import re

root_path = r"c:\potenup3\pj04_ParaWorks\data\demo_data\drive"

def update_date_in_file(file_path, new_date_str):
    if not os.path.exists(file_path):
        return
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Replace date patterns like YYYY년 MM월 DD일 or YYYY-MM-DD
    content = re.sub(r"\d{4}년 \d{1,2}월 \d{1,2}일", new_date_str, content)
    content = re.sub(r"\d{4}-\d{2}-\d{2}", new_date_str.replace("년 ", "-").replace("월 ", "-").replace("일", ""), content)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

# Define file to date mapping
updates = {
    "00_회사규정/온보딩_가이드.md": "2026년 3월 10일",
    "00_회사규정/보안_정책_v1.0.txt": "2026년 3월 12일",
    "00_회사규정/정보보호_서약서_템플릿.txt": "2026년 3월 12일",
    "01_제품_기술/ParaWorks_기술_개요.md": "2026년 4월 05일",
    "01_제품_기술/API_설계서_v1.md": "2026년 4월 15일",
    "01_제품_기술/배포_런북.md": "2026년 4월 20일",
    "02_파일럿_프로젝트/K테크_파일럿_제안서_v1.txt": "2026년 5월 02일",
    "02_파일럿_프로젝트/K테크_파일럿_제안서_v2.txt": "2026년 5월 11일",
    "02_파일럿_프로젝트/파일럿_성공지표_정의서.md": "2026년 5월 12일",
    "02_파일럿_프로젝트/고객_온보딩_체크리스트.md": "2026년 5월 15일",
    "03_IR_투자/ParaWorks_IR_데크_v1.txt": "2026년 4월 20일",
    "03_IR_투자/ParaWorks_IR_데크_v2.txt": "2026년 5월 05일",
    "03_IR_투자/재무_프로젝션_2026.txt": "2026년 5월 12일",
}

for rel_path, date_str in updates.items():
    update_date_in_file(os.path.join(root_path, rel_path), date_str)
