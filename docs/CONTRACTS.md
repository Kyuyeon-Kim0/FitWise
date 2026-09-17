# 공통 규격 v1

## 실행 경계

`views/` → `app/services.py` → `repository + agents + monitoring` → SQLite.
분석 모듈은 Streamlit을 import하지 않습니다. UI에서 SQL 또는 psutil을 직접 호출하지 않습니다.
모든 서비스는 마지막 인자 `database=None`에 테스트용 DB 경로를 주입할 수 있습니다.
SQLite 연결은 `with connect(...)`로 열고 닫습니다. 연결 객체를 전역 또는 Streamlit 캐시에 넣지 않습니다.

## 서비스

| 함수 | 입력 | 반환 |
|---|---|---|
| `browse_products(category, database)` | 전체/상의/아우터/하의 | 상품 dict 목록 |
| `browse_detail(product_id, database)` | 상품 ID | (상품 dict, 리뷰 dict 목록) |
| `run_review(product_id, database)` | 상품 ID | `{result, request_id}` |
| `run_fit(product_id, user_id, size, preferred_fit, height, database)` | 상품/사용자 ID, 유효한 사이즈·선호 핏·키(140~200cm, 1cm 단위) | `{result, request_id, product_id, user_id, size, preferred_fit, height}` |

잘못된 카테고리/상품/사용자/사이즈는 ValueError입니다. 검증 실패는 Agent 실행으로 세지 않습니다.
실제 분석 중 발생한 예외는 재발생시키고 `error` 로그를 남깁니다.
UI 결과는 session_state에 저장하고 단순 rerun에서 Agent를 재실행하지 않습니다.
DB에는 분석 결과 JSON이 보존되며, 현재 UI는 세션의 최신 결과만 표시합니다.

## Review 반환값

`mode`, `count`, `positive_pct`, `neutral_pct`, `negative_pct`, `size_complaint_pct`,
`positive_keywords`, `negative_keywords`, `size_comments`, `fit_comments`, `summary`.

- 비율: 0~100 float 또는 표본 없음일 때 None.
- 긍정 평점 4~5 / 중립 3 / 부정 1~2. 분모는 전체 리뷰 수.
- 사이즈 불만: 크다·작다·긴 소매/기장·타이트 키워드가 있는 리뷰 수 / 전체 리뷰 수.
- 키워드: `[{keyword: str, count: int}, ...]`, 리뷰당 같은 키워드는 한 번만 셈.
- 원문 의견: 문자열 목록. 현재 각각 최대 4건, 키워드 최대 5개.
- 문맥/부정어 처리는 아직 단순 규칙으로, 실제 AI 모델이 아님.

## Fit 반환값 및 수식

`mode`, `score`, `size`, `metrics`, `reasons`, `limited_data`, `label`, `disclaimer`.

`score = round(Σ(가용 지표 성공률 × 기본 가중치) / Σ(가용 지표 기본 가중치))`.

| 지표 | 표시 | 계산 | 기본 가중치 |
|---|---|---|---|
| 개인 동일 카테고리 구매 | 성공률 | 미반품 주문 / 전체 주문 | 20% |
| 개인 동일 카테고리·선택 사이즈 | 성공률 | 미반품 주문 / 전체 주문 | 30% |
| 상품 전체 | 반품률 | 계산에는 100 − 반품률 | 15% |
| 상품 선택 사이즈 | 반품률 | 계산에는 100 − 반품률 | 20% |
| 리뷰 | 긍정 평점 비율 | Review positive_pct | 15% |

metrics: label, count, success_pct, value, weight, effective_weight_pct, is_return_rate.
주문 지표에는 returned도 포함합니다. 없음은 0%가 아닌 None입니다.
한 항목이라도 표본이 5 미만이면 limited_data=True입니다. 가용 지표가 없으면 score=None입니다.
사용자 선호 핏은 표시만 하며 현재 공식에는 미포함입니다.
이 수식은 내부 프로젝트 지표로 실제 반품 확률을 추정하거나 검증한 모델이 아닙니다.

## DB

현재 기본 경로는 `data/demo/fashion_shop.db`입니다. 별도 스키마의 `data/fashion_shop.db`를 보존하기 위해 분리했습니다.
기존 테이블의 필수 컬럼이 다르면 초기화가 오류 안내 후 중단됩니다. 무단 스키마 변환은 하지 않습니다.

`app/schema.sql`을 기준으로 합니다. 버전 변경 시 기존 DB를 자동 삭제하지 말고 마이그레이션을 추가합니다.
상품 sizes/measurements, Agent result_json은 JSON 문자열입니다. 상품 조회 함수에서 앞의 둘을 역직렬화합니다.
orders 한 행은 상품 1개 구매입니다. returns.order_id는 UNIQUE이며 모든 관계에 외래키가 적용됩니다.
주문 날짜와 리뷰 날짜는 ISO 날짜, 실행 로그는 UTC ISO datetime입니다.
샘플 주문은 모두 반품 기간이 종료된 것으로 가정합니다. 실서비스에서는 관측 기간 정의가 필요합니다.

## 측정

- operation: browse/review/fit. status: success/error.
- CPU: `time.process_time` 증가량 / `time.perf_counter` 증가량 × 100, 1코어 기준.
- RSS: `psutil.Process().memory_info().rss / 1024**2` (엄밀하게 MiB, UI에서는 MB로 표시).
- processing_ms: 분석 함수 실행. browse는 조회 구간.
- response_ms: 서비스 측정 구간 전체. Agent 로그 저장 포함, resource_logs INSERT 제외.
- 브라우저 렌더링/네트워크 전송/전체 Streamlit rerun 시간은 포함하지 않습니다.
- Fit 1회 → agent_logs Review 1 + Fit 1, resource_logs fit 1. request_id는 동일.
- Fit 처리시간은 Review를 포함하므로 Review 시간을 더하지 않습니다.
- 매우 짧은 작업은 CPU가 0으로 측정될 수 있습니다. 프로세스 내 동시 세션과 서버 작업이 측정에 섞일 수 있습니다.
- Dashboard 평균은 성공 작업 전체 기준이며, 표본을 초기화하거나 삭제하지 않습니다.

## 미래 API 연결

`OPENAI_API_KEY`와 `OPENAI_MODEL`만 공통 설정에서 읽습니다. 실제 API 호출은 아직 구현하지 않았습니다.
모델은 팀이 선택한 값을 사용하고 API 키 원문·전체 입력을 로그에 저장하지 않습니다.
API 결과에도 현재 계약을 적용하고 `mode`로 baseline/API 여부를 명시하세요.
선택한 SDK와 모델에 대한 구현은 [공식 OpenAI 문서](https://developers.openai.com/api/docs/quickstart)를 확인합니다.

Streamlit 화면 구조는 [공식 multipage 문서](https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation),
메모리 측정은 [psutil 문서](https://psutil.readthedocs.io/stable/)를 참고했습니다.
