import random

import pandas as pd
import streamlit as st

from app.config import get_settings
from app.db import connect
from app.llm import LLMError
from app.repository import list_products, list_users
from app.services import ask_review_agent, browse_detail, run_fit, run_review
from app.ui import garment, product_thumbnail, review_image_path, show_review

REVIEW_PAGE_SIZE = 5
EXAMPLE_QUESTIONS = {
    "사이즈 · 핏": [
        "허리 사이즈 어때?", "이거 크게 나왔나요?", "평소 M 입는데 이것도 M 사면 돼?",
        "사이즈가 좀 작게 나온 편이야?", "정사이즈인가요?", "한 사이즈 업해야 하나요?",
        "오버핏 느낌인가요?", "몸에 붙는 스타일이에요?", "넉넉하게 입을 수 있나요?",
        "허벅지가 좀 굵은데 괜찮을까요?", "배가 좀 나온 사람도 입기 괜찮아요?",
        "어깨가 넓은 편인데 작지 않을까요?", "팔이 긴 편인데 소매 괜찮을까요?",
        "마른 사람이 입으면 너무 커 보이나요?", "통이 넓은 편인가요?",
    ],
    "기장 · 실측": [
        "기장 많이 길어요?", "바지 길이가 어느 정도예요?", "총장 몇 cm예요?",
        "소매 길이 알려줘", "허리 단면 얼마예요?", "M 사이즈 총장 알려줘",
        "L 사이즈랑 M 사이즈 차이 얼마나 나?", "사이즈별 허리 치수 비교해줘",
        "가장 작은 사이즈 실측이 어떻게 돼?", "리뷰에서 기장이 길다는 말 많아요?",
    ],
    "체형 관련": [
        "170에 65인데 M 괜찮을까요?", "175/70이면 무슨 사이즈가 좋아?",
        "키 작은 사람이 입기 괜찮나요?", "160인데 기장 너무 길까요?",
        "180인데 소매 짧지 않을까요?", "상체가 큰 편인데 괜찮을까요?",
        "허리는 얇고 허벅지가 굵은데 잘 맞을까요?", "어깨가 좁은 사람이 입으면 이상할까요?",
    ],
    "소재 · 착용감": [
        "소재 괜찮아요?", "재질이 부드러운가요?", "까슬거리나요?",
        "피부에 닿았을 때 불편하다는 리뷰 있어?", "생각보다 얇나요?", "비침 있나요?",
        "두꺼운 편이에요?", "신축성 있어요?", "활동하기 편해요?",
        "입었을 때 답답하다는 사람 있어?", "무거운 편인가요?", "촉감 관련 리뷰 찾아줘.",
    ],
    "계절 · 상황": [
        "여름에 입기 괜찮아요?", "한여름에는 더울까요?", "겨울에도 입을 수 있나요?",
        "봄가을용인가요?", "출근할 때 입기 괜찮을까요?", "데일리로 입기 좋아요?",
        "오래 앉아 있어도 편할까요?", "여행할 때 입기 괜찮아?",
        "운동할 때 입는 건 무리겠죠?", "비 오는 날 입어도 괜찮을까요?",
    ],
    "단점 · 품질": [
        "단점이 뭐예요?", "사람들이 가장 많이 불만 가지는 게 뭐야?", "마감 안 좋다는 리뷰 있어?",
        "실밥 얘기 있나요?", "세탁하고 줄었다는 사람 있어?", "보풀 생긴다는 리뷰 있나요?",
        "색 빠진다는 얘기는?", "지퍼 문제 있다는 사람 있어?", "오래 입으면 늘어난다는 리뷰 있어?",
        "반품하고 싶었다는 리뷰 있어?", "별로라는 사람들은 왜 별로래?", "낮은 평점 리뷰에서는 뭐라고 해?",
    ],
    "장점": [
        "사람들이 가장 좋아하는 부분은 뭐야?", "착용감 좋다는 리뷰 많아요?", "디자인 칭찬 많나요?",
        "재구매한다는 사람 있어?", "만족한다는 의견이 많아요?", "사진보다 실물이 낫다는 리뷰 있어?",
        "가격 대비 괜찮다는 의견 있나요?", "가장 칭찬 많이 받는 부분 알려줘.",
    ],
    "구매 결정": [
        "그래서 살 만해?", "사이즈 때문에 고민인데 사도 될까요?", "출근용으로 사려고 하는데 괜찮을까?",
        "편하게 입을 바지 찾는데 이거 괜찮아?", "너무 타이트한 옷 싫어하는데 괜찮을까요?",
        "긴 옷 싫어하는데 이 상품은 어때?", "피부가 예민한 사람이 입기 괜찮을까?",
        "리뷰 기준으로 어떤 사람이 사면 만족할 것 같아?", "반대로 어떤 사람한테는 안 맞을 것 같아?",
    ],
    "짧고 애매한 질문": [
        "이거 어때?", "많이 커?", "길어?", "얇음?", "허리 괜춘?", "사이즈 어떰",
        "재질 별로임?", "팔 긴가요", "핏이 어떤 느낌임?", "빡빡해?",
        "생각보다 크다는 말 있어?", "사이즈 미스 많음?", "사도 됨?", "리뷰 좀 봐줘",
        "별로라는 사람들은 왜 그런 거임?",
    ],
    "복합 질문 (도구 여러 번 호출)": [
        "허리랑 기장 둘 다 어떤지 알려줘.", "사이즈랑 소재에 대한 불만 찾아줘.",
        "M 사이즈 실측 알려주고 리뷰에서 크게 나왔다는 말도 찾아줘.", "소매 길이랑 착용감 같이 알려줘.",
        "제품 설명이랑 실제 리뷰가 비슷한지 봐줘.", "상품은 여유로운 핏이라고 하는데 리뷰도 그래?",
        "실측은 큰데 리뷰에서는 작다고 하는 사람 있나요?", "소재가 부드럽다고 설명되어 있는데 실제 리뷰도 그런가요?",
        "사이즈, 기장, 소재 중에서 리뷰에서 가장 문제되는 게 뭐야?",
    ],
    "답하기 어려운 질문 (범위 밖)": [
        "내일 이 옷 입고 나가도 돼?", "나한테 어울릴까?", "이 옷 입으면 날씬해 보여?",
        "여자친구가 좋아할까요?", "무조건 사야 돼?", "이 브랜드 믿을 만해?",
        "다른 쇼핑몰보다 싸?", "세탁기에 돌려도 돼?", "모델 키가 몇이야?", "배송 언제 와요?",
    ],
}

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
    st.caption(f"{product['category']} / {product['subcategory']}")
    st.title(product["name"])
    st.subheader(f"₩{product['price']:,}")
    st.write(product["description"])
    st.caption(f"리뷰 {len(reviews)}건 · 샘플 상품")
    size = height = weight = preferred_fit = None
    if not users:
        st.warning("분석할 사용자가 없습니다.")
    else:
        user_names = {u["id"]: u["name"] for u in users}
        with st.form(f"fit_form_{product_id}"):
            user_id = st.selectbox("데모 사용자", list(user_names), format_func=user_names.get)
            size = st.radio("사이즈 선택", product["sizes"], horizontal=True)
            preferred_fit = st.radio("평소 선호하는 핏", ["슬림핏", "레귤러핏", "루즈핏"],
                                     horizontal=True)
            height = st.select_slider("키 (cm)", options=list(range(145, 196)), value=165)
            weight = st.select_slider("몸무게 (kg)", options=list(range(40, 121)), value=60)
            submitted = st.form_submit_button("구매적합도 분석하기 ✦", type="primary", width="stretch")
        if submitted:
            try:
                with st.spinner("구매·반품 기록과 저장된 리뷰 분석 결과를 확인하고 있습니다..."):
                    st.session_state.fit_result = run_fit(product_id, user_id, size, preferred_fit, height, weight)
                st.switch_page("views/fit_result.py")
            except ValueError as exc:
                st.error(str(exc))
        st.caption("가중치 기반 적합도 점수 · AI Fit Advisor · 내부 참고 지표")

st.subheader("사이즈 가이드")
st.caption("단면 기준 · cm · 가상 실측 데이터")
st.dataframe(pd.DataFrame(product["measurements"]).T.rename_axis("사이즈"), width="stretch")
st.divider()
settings = get_settings()

st.subheader("리뷰 분석")
st.caption("정해진 규칙으로 빠르고 저렴하게 전체 리뷰의 긍정/부정 비율과 키워드를 요약합니다.")
if st.button("리뷰 분석하기 🔍", key="run_review_baseline", type="primary", width="stretch"):
    try:
        with st.spinner("리뷰를 분석하고 있습니다..."):
            st.session_state[f"review_{product_id}"] = run_review(product_id)
    except ValueError as exc:
        st.error(str(exc))
saved_review = st.session_state.get(f"review_{product_id}")
if saved_review:
    with st.container(border=True):
        show_review(saved_review["result"])
        caption = ("저장된 분석 결과를 재사용했습니다." if saved_review["review_source"] == "cached"
                   else f"실행 ID: {saved_review['request_id']} · 분석 결과를 저장했습니다.")
        st.caption(caption)

st.divider()
st.subheader("AI Review Agent")
st.caption("궁금한 걸 직접 물어보면, 관련 리뷰와 상품 정보를 스스로 찾아서 근거를 들어 답합니다.")
if not settings.api_key:
    st.info("실행하려면 .env에 OPENAI_API_KEY를 설정하세요.")
else:
    quick_questions = ["허리 사이즈 어때?", "기장 많이 길어요?", "단점이 뭐예요?", "그래서 살 만해?"]
    quick_cols = st.columns(len(quick_questions))
    qa_input_key = f"qa_input_{product_id}"
    for col, example in zip(quick_cols, quick_questions):
        if col.button(example, key=f"quick_{product_id}_{example}", width="stretch"):
            st.session_state[qa_input_key] = example
    with st.expander("💬 질문 예시 더 보기 (카테고리별)"):
        category = st.selectbox("질문 유형", list(EXAMPLE_QUESTIONS), key=f"qa_category_{product_id}")
        for example in EXAMPLE_QUESTIONS[category]:
            if st.button(example, key=f"example_{product_id}_{category}_{example}", width="stretch"):
                st.session_state[qa_input_key] = example
    question = st.text_input("무엇이 궁금하세요?", key=qa_input_key,
                             placeholder="예: 키 175인데 기장 괜찮을까?")
    if size:
        st.caption(f"위 구매적합도 입력값을 함께 참고합니다: {size} 사이즈 · 키 {height}cm · 몸무게 {weight}kg · {preferred_fit}")
    if st.button("AI에게 물어보기 →", key="ask_review_agent", type="primary", width="stretch"):
        try:
            with st.spinner("리뷰를 찾아보고 답변을 준비하고 있습니다..."):
                st.session_state[f"qa_result_{product_id}"] = ask_review_agent(
                    product_id, question, size=size, height=height, weight=weight, preferred_fit=preferred_fit)
        except (ValueError, LLMError) as exc:
            st.error(str(exc))
    qa_result = st.session_state.get(f"qa_result_{product_id}")
    if qa_result:
        payload = qa_result["result"]
        stance_labels = {"positive": "🟢 대체로 긍정적", "mixed": "🟡 의견이 갈림",
                         "negative": "🔴 대체로 부정적", "insufficient_data": "⚪ 판단할 데이터 부족"}
        fit_labels = {"good_fit": "✅ 잘 맞을 것 같아요", "risky": "⚠️ 애매할 수 있어요",
                     "poor_fit": "❌ 잘 안 맞을 수 있어요", "unknown": "판단하기 어려워요 (정보 부족)"}
        with st.container(border=True):
            st.write(payload["answer"])
            st.caption(f"리뷰 전반 스탠스: {stance_labels.get(payload['overall_stance'], payload['overall_stance'])}"
                      f" — {payload['stance_reason']}")
            st.write(f"**{fit_labels.get(payload['fit_assessment'], payload['fit_assessment'])}**")
            tools = payload.get("tools_used")
            if tools:
                st.caption("사용한 도구: " + " → ".join(tools))
            st.caption(f"실행 ID: {qa_result['request_id']}")

        if payload.get("recommend_alternatives") and payload.get("recommended_product_ids"):
            st.markdown("**대신 이런 상품은 어때요?**")
            by_id = {p["id"]: p for p in catalog}
            recommended = [by_id[pid] for pid in payload["recommended_product_ids"][:3] if pid in by_id]
            if recommended:
                alt_cols = st.columns(len(recommended))
                for col, alt in zip(alt_cols, recommended):
                    with col, st.container(border=True):
                        garment(alt)
                        st.write(f"**{alt['name']}**")
                        st.write(f"₩{alt['price']:,}")
                        if st.button("이 상품 보기 →", key=f"alt_{product_id}_{alt['id']}", width="stretch"):
                            st.session_state.selected_product = alt["id"]
                            st.rerun()

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
review_key = f"reviews_revealed_{product_id}"
if st.session_state.get(f"{review_key}_for") != product_id:
    st.session_state[review_key] = REVIEW_PAGE_SIZE
    st.session_state[f"{review_key}_for"] = product_id
revealed_reviews = st.session_state[review_key]
for review in reviews[:revealed_reviews]:
    with st.container(border=True):
        st.write(f"**{review['user_name']}** ({review['user_height']}cm · {review['user_weight']}kg) · {'★' * review['rating']}{'☆' * (5-review['rating'])}")
        st.write(review["content"])
        st.caption(f"{review['size']} 사이즈 · {review['created_at']}")
if len(reviews) > revealed_reviews:
    if st.button("리뷰 더 보기 ↓", key="load_more_reviews", width="stretch"):
        st.session_state[review_key] = revealed_reviews + REVIEW_PAGE_SIZE
        st.rerun()

same_category_ids = [p["id"] for p in catalog if p["category"] == product["category"] and p["id"] != product_id]
if same_category_ids:
    st.divider()
    st.subheader(f"{product['category']}의 다른 상품도 살펴보세요")
    similar_key = f"similar_products_{product_id}"
    saved_similar_ids = st.session_state.get(similar_key, [])
    if (len(saved_similar_ids) != min(4, len(same_category_ids))
            or not set(saved_similar_ids).issubset(same_category_ids)):
        saved_similar_ids = random.sample(same_category_ids, min(4, len(same_category_ids)))
        st.session_state[similar_key] = saved_similar_ids
    by_id = {p["id"]: p for p in catalog}
    similar_products = [by_id[i] for i in saved_similar_ids if i in by_id]
    similar_cols = st.columns(len(similar_products))
    for col, item in zip(similar_cols, similar_products):
        with col, st.container(border=True):
            garment(item)
            st.write(f"**{item['name']}**")
            st.write(f"₩{item['price']:,}")
            if st.button("보러 가기 →", key=f"similar_{product_id}_{item['id']}", width="stretch"):
                st.session_state.selected_product = item["id"]
                st.rerun()
