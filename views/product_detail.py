import pandas as pd
import streamlit as st

from app.config import get_settings
from app.db import connect
from app.llm import LLMError
from app.repository import list_products, list_users
from app.services import browse_detail, run_fit, run_review
from app.ui import garment, show_review

REVIEW_PAGE_SIZE = 5

st.caption("COLLECTION / PRODUCT DETAIL")
with connect() as connection:
    catalog = list_products(connection)
    users = list_users(connection)
if not catalog:
    st.info("등록된 상품이 없습니다.")
    st.stop()
names = {p["id"]: p["name"] for p in catalog}
selected = st.session_state.get("selected_product", catalog[0]["id"])
ids = list(names)
product_id = st.selectbox("상품", ids, index=ids.index(selected) if selected in ids else 0,
                          format_func=names.get, key="detail_product")
st.session_state.selected_product = product_id
product, reviews = browse_detail(product_id)
left, right = st.columns([1, 1.2], gap="large")
with left:
    garment(product)
with right:
    st.caption(f"{product['category']} / {product['subcategory']}")
    st.title(product["name"])
    st.subheader(f"₩{product['price']:,}")
    st.write(product["description"])
    st.caption(f"리뷰 {len(reviews)}건 · 샘플 상품")
    if not users:
        st.warning("분석할 사용자가 없습니다.")
    else:
        user_names = {u["id"]: u["name"] for u in users}
        with st.form(f"fit_form_{product_id}"):
            user_id = st.selectbox("데모 사용자", list(user_names), format_func=user_names.get)
            size = st.radio("사이즈 선택", product["sizes"], horizontal=True)
            preferred_fit = st.radio("평소 선호하는 핏", ["슬림핏", "레귤러핏", "루즈핏"],
                                     horizontal=True)
            submitted = st.form_submit_button("구매적합도 분석하기 ✦", type="primary", width="stretch")
        if submitted:
            try:
                with st.spinner("구매·반품 기록과 저장된 리뷰 분석 결과를 확인하고 있습니다..."):
                    st.session_state.fit_result = run_fit(product_id, user_id, size, preferred_fit)
                st.switch_page("views/fit_result.py")
            except ValueError as exc:
                st.error(str(exc))
        st.caption("가중치 기반 적합도 점수 · AI Fit Advisor · 내부 참고 지표")

st.subheader("사이즈 가이드")
st.caption("단면 기준 · cm · 가상 실측 데이터")
st.dataframe(pd.DataFrame(product["measurements"]).T.rename_axis("사이즈"), width="stretch")
st.divider()
st.subheader("리뷰 분석 · AI 에이전트 사용 비교")
settings = get_settings()
baseline_col, api_col = st.columns(2)
for col, mode, label, enabled, hint in (
    (baseline_col, "baseline", "규칙 기반 분석 (baseline)", True, ""),
    (api_col, "api", f"AI 에이전트 분석 ({settings.model or 'OpenAI'})", bool(settings.api_key),
     "실행하려면 .env에 OPENAI_API_KEY를 설정하세요."),
):
    with col:
        if st.button(f"{label} 실행", key=f"run_review_{mode}", type="primary", disabled=not enabled, width="stretch"):
            try:
                with st.spinner("리뷰를 분석하고 있습니다..."):
                    st.session_state[f"review_{product_id}_{mode}"] = run_review(product_id, mode=mode)
            except (ValueError, LLMError) as exc:
                st.error(str(exc))
        if not enabled:
            st.caption(hint)
        saved_review = st.session_state.get(f"review_{product_id}_{mode}")
        if saved_review:
            with st.container(border=True):
                show_review(saved_review["result"])
                caption = ("저장된 분석 결과를 재사용했습니다." if saved_review["review_source"] == "cached"
                           else f"실행 ID: {saved_review['request_id']} · 분석 결과를 저장했습니다.")
                st.caption(caption)

st.subheader(f"고객 리뷰 ({len(reviews)})")
if not reviews:
    st.info("아직 리뷰가 없습니다.")
review_key = f"reviews_revealed_{product_id}"
if st.session_state.get(f"{review_key}_for") != product_id:
    st.session_state[review_key] = REVIEW_PAGE_SIZE
    st.session_state[f"{review_key}_for"] = product_id
revealed_reviews = st.session_state[review_key]
for review in reviews[:revealed_reviews]:
    with st.container(border=True):
        st.write(f"**{review['user_name']}** · {'★' * review['rating']}{'☆' * (5-review['rating'])}")
        st.write(review["content"])
        st.caption(f"{review['size']} 사이즈 · {review['created_at']}")
if len(reviews) > revealed_reviews:
    if st.button("리뷰 더 보기 ↓", key="load_more_reviews", width="stretch"):
        st.session_state[review_key] = revealed_reviews + REVIEW_PAGE_SIZE
        st.rerun()
