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
with st.expander("점수 산정 방식"):
    st.write("개인 선택 사이즈 성공률 30% + 상품 반품 안정성 20% + 선택 사이즈 반품 안정성 25% + 리뷰 적합도 25%의 가중합입니다.")
    st.write("개인 이력은 동일 카테고리만 사용합니다. 데이터가 없는 항목은 제외하고 남은 가중치를 정규화합니다. 전부 없으면 점수를 산출하지 않습니다.")
    st.write("반품 기간이 종료된 주문으로 가정합니다. 선호 핏·신체 치수는 점수에 반영하지 않으며, 브랜드별 실측 차이는 추후 개선 항목입니다.")
review_note = "저장된 리뷰 분석 결과를 재사용했습니다." if saved.get("review_source") == "cached" else "리뷰 분석 결과를 새로 생성해 저장했습니다."
st.caption(f"실행 ID: {saved['request_id']} · {review_note}")
a, b = st.columns(2)
a.page_link("views/product_detail.py", label="다른 사이즈 확인하기", icon="👕")
b.page_link("views/admin_dashboard.py", label="실행 자원 확인하기", icon="📊")
