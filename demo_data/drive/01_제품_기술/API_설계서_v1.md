# ParaWorks API 설계서 v1

본 문서는 ParaWorks 플랫폼 내부 및 외부 연동을 위한 RESTful API 규격을 정의합니다.

## 1. 기본 정보
- **Base URL**: `http://localhost:8000/api/v1`
- **인증 방식**: HTTP Bearer Authentication (JWT)
- **Content-Type**: `application/json`
- **Rate Limit**: 분당 최대 100건 요청 (IP 및 사용자 기준)

## 2. 주요 엔드포인트

### [인증 및 사용자]
| Method | Endpoint | 설명 |
| :--- | :--- | :--- |
| `POST` | `/auth/login` | 사용자 로그인 및 토큰 발급 |
| `GET` | `/users/me` | 현재 로그인된 사용자 정보 확인 |

### [연동 관리]
| Method | Endpoint | 설명 |
| :--- | :--- | :--- |
| `GET` | `/integrations` | 연동된 서비스 목록(Slack, Gmail 등) 및 상태 조회 |
| `POST` | `/integrations/{type}/sync` | 특정 서비스의 데이터 동기화 강제 실행 |

### [문서 및 리뷰]
| Method | Endpoint | 설명 |
| :--- | :--- | :--- |
| `GET` | `/documents` | 동기화된 문서 목록 조회 (필터링 지원) |
| `GET` | `/review` | 검토 대기 중인 결정사항 후보 목록 조회 |
| `POST` | `/review/{id}/approve` | 특정 후보를 공식 지식으로 승인 |
| `POST` | `/review/{id}/reject` | 특정 후보를 반려 |

### [지식 검색 및 Q&A]
| Method | Endpoint | 설명 |
| :--- | :--- | :--- |
| `GET` | `/search` | 벡터 기반 지식 검색 (Query string: `q`) |
| `POST` | `/ask` | RAG 기반 AI 질문 답변 생성 (Chat-style) |

## 3. 에러 코드 정의
- `400 Bad Request`: 요청 파라미터가 올바르지 않음
- `401 Unauthorized`: 인증 토큰이 유효하지 않거나 누락됨
- `403 Forbidden`: 해당 리소스에 대한 접근 권한이 없음 (권한 인지형 정책)
- `429 Too Many Requests`: 요청 제한 횟수 초과
- `500 Internal Server Error`: 서버 내부 오류

## 4. 인증 흐름
1. 클라이언트는 `/auth/login`을 통해 자격 증명을 전송합니다.
2. 서버는 유효성 검사 후 `access_token`을 반환합니다.
3. 이후 모든 요청의 `Authorization` 헤더에 `Bearer {token}`을 포함해야 합니다.

---
*작성일: 2025년 11월 15일*
*작성자: 김용희 CTO*
