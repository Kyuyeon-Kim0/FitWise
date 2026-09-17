import streamlit as st

from app.db import connect
from app.repository import get_product, list_users

st.caption("YOUR FIT REPORT")
st.title("나의 구매적합도")
saved = st.session_state.get("fit_result")
if not saved:
    st.info("상품 상세에서 사용자와 사이즈를 선택한 후 분석을 실행해 주세요.")
    st.page_link("views/product_detail.py", label="상품 상세로 이동", icon="👕")
    st.stop()
with connect() as connection:
    product = get_product(connection, saved["product_id"])
    users = {u["id"]: u["name"] for u in list_users(connection)}
result = saved["result"]
st.write(f"**{users.get(saved['user_id'], '사용자')}** · {product['name']} · **{saved['size']}** 사이즈")
st.caption(f"이번 분석의 선택 선호 핏: {saved.get('preferred_fit', '미선택')}")
left, right = st.columns([1, 2], gap="large")
with left, st.container(border=True):
    st.metric("FITWISE SCORE", f"{result['score']} / 100" if result["score"] is not None else "데이터 부족")
    st.subheader(result["label"])
    st.caption(result["disclaimer"])
    if result["limited_data"]:
        st.warning("일부 항목의 표본이 5건 미만입니다.")
with right, st.container(border=True):
    st.subheader("점수를 구성하는 데이터")
    for metric in result["metrics"]:
        value = metric["value"]
        display = f"{value}%" if value is not None else "데이터 없음"
        st.write(f"**{metric['label']}** · {display}")
        st.progress(float(value or 0) / 100)
        st.caption(f"표본 {metric['count']}건 · 적용 가중치 {metric['effective_weight_pct']}%")

st.subheader("분석 근거")
for reason in result["reasons"]:
    st.write(f"• {reason}")
advisor = result.get("advisor")
if advisor:
    st.subheader("AI Fit Advisor 권고")
    st.info(advisor["recommendation"])
    st.write(advisor["explanation"])
    if advisor["risk_signals"]:
        st.write("주의 신호: " + " · ".join(advisor["risk_signals"]))
    if advisor["next_actions"]:
        st.write("다음 행동: " + " · ".join(advisor["next_actions"]))
elif result.get("advisor_error"):
    st.warning(
        "AI Fit Advisor를 사용할 수 없어 규칙 기반 분석 결과만 표시합니다. "
        f"오류 유형: {result['advisor_error']}"
    )
with st.expander("점수 산정 방식"):
    st.write("각 지표를 0~100점으로 환산한 뒤 가중합하여 최종 구매적합도를 계산합니다.")
    st.markdown("""
**1. 개인 선택 사이즈 성공률 · 30%**
동일 카테고리에서 사용자가 선택한 사이즈로 구매한 주문의 미반품 비율입니다.

`(개인 동일 카테고리·선택 사이즈 주문 수 - 반품 수) / 주문 수 × 100`

**2. 상품 반품 안정성 · 20%**
모든 사용자의 해당 상품 주문 중 미반품 비율입니다. 점수가 높을수록 전반적인 반품 위험이 낮습니다.

`(해당 상품 전체 주문 수 - 전체 반품 수) / 전체 주문 수 × 100`

**3. 선택 사이즈 반품 안정성 · 25%**
모든 사용자의 해당 상품·선택 사이즈 주문 중 미반품 비율입니다.

`(해당 상품·선택 사이즈 주문 수 - 반품 수) / 주문 수 × 100`

**4. 리뷰 적합도 · 25%**
해당 상품의 전체 리뷰 중 평점 4~5점인 긍정 리뷰의 비율입니다.

`긍정 리뷰 수 / 전체 리뷰 수 × 100`

**최종 점수**
`개인 선택 사이즈 성공률 × 0.30 + 상품 반품 안정성 × 0.20 + 선택 사이즈 반품 안정성 × 0.25 + 리뷰 적합도 × 0.25`
""")
    st.caption("예: 80점, 90점, 70점, 75점이면 80×0.30 + 90×0.20 + 70×0.25 + 75×0.25 = 78.25점이며, 최종 표시는 78점입니다.")
    st.write("데이터가 없는 항목은 100점으로 처리하지 않고 제외한 뒤, 남은 가중치를 합계 100%가 되도록 재정규화합니다. 모든 항목에 데이터가 없으면 점수를 산출하지 않습니다.")
    st.write("각 항목의 표본이 5건 미만이면 참고용 경고를 표시합니다. 리뷰의 사이즈·핏 부정 키워드는 점수를 직접 차감하지 않고 분석 근거와 AI 권고에 반영합니다.")
review_note = "저장된 리뷰 분석 결과를 재사용했습니다." if saved.get("review_source") == "cached" else "리뷰 분석 결과를 새로 생성해 저장했습니다."
st.caption(f"실행 ID: {saved['request_id']} · {review_note}")
a, b = st.columns(2)
a.page_link("views/product_detail.py", label="다른 사이즈 확인하기", icon="👕")
b.page_link("views/admin_dashboard.py", label="실행 자원 확인하기", icon="📊")
