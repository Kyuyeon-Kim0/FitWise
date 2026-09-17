import random

import pandas as pd
import streamlit as st

from app.config import get_settings
from app.db import connect
from app.llm import LLMError
from app.repository import list_products, list_users
from app.services import browse_detail, run_fit, run_review
from app.ui import garment, product_thumbnail, review_image_path, show_review

st.caption("COLLECTION / PRODUCT DETAIL")
with connect() as connection:
    catalog = list_products(connection)
    users = list_users(connection)
if not catalog:
    st.info("등록된 상품이 없습니다.")
    st.stop()
names = {p["id"]: p["name"] for p in catalog}
ids = list(names)
query_product = st.query_params.get("product")
try:
    query_product = int(query_product) if query_product is not None else None
except (TypeError, ValueError):
    query_product = None
selected = query_product if query_product in ids else st.session_state.get("selected_product", ids[0])
product_id = selected if selected in ids else ids[0]
st.session_state.selected_product = product_id
product, reviews = browse_detail(product_id)

thumbnail_column, image_column, right = st.columns([0.22, 0.9, 1.2], gap="medium")
with thumbnail_column:
    with st.container(height=560, border=False, key="product_thumbnail_rail"):
        for item in catalog:
            thumbnail_key = "thumb_selected" if item["id"] == product_id else f"thumb_{item['id']}"
            with st.container(key=thumbnail_key):
                product_thumbnail(item)
with image_column:
    with st.container(height=560, border=False, key="product_image_panel"):
        garment(product)
with right:
    with st.container(height=560, border=False, key="product_detail_panel"):
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
                preferred_fit = st.radio(
                    "평소 선호하는 핏", ["슬림핏", "레귤러핏", "루즈핏"], horizontal=True
                )
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
else:
    st.caption("착용 사진과 후기를 좌우로 넘겨 확인해 보세요.")
    review_ids = [review["id"] for review in reviews]
    photo_key = f"review_photo_ids_{product_id}"
    saved_photo_ids = st.session_state.get(photo_key, [])
    if len(saved_photo_ids) != min(2, len(review_ids)) or not set(saved_photo_ids).issubset(review_ids):
        saved_photo_ids = random.sample(review_ids, min(2, len(review_ids)))
        st.session_state[photo_key] = saved_photo_ids
    photo_variants = {review_id: variant for review_id, variant in zip(saved_photo_ids, ("a", "b"))}

    with st.container(horizontal=True, gap="medium", key="review_scroller"):
        for review in reviews:
            with st.container(border=True, width=300):
                variant = photo_variants.get(review["id"])
                if variant:
                    image = review_image_path(product_id, variant)
                    if image.exists():
                        st.image(image, width="stretch")
                    else:
                        st.html('<div class="review-image-placeholder">착용 사진 없음</div>')
                else:
                    st.html('<div class="review-image-placeholder">착용 사진 없음</div>')
                st.write(f"**{review['user_name']}**")
                st.write(f"{'★' * review['rating']}{'☆' * (5-review['rating'])}")
                st.write(review["content"])
                st.caption(f"{review['size']} 사이즈 · {review['created_at']}")
