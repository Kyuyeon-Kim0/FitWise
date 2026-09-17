import streamlit as st

from app.services import browse_products
from app.ui import garment

st.html('''<section class="hero"><p class="eyebrow">A BETTER FIT STARTS WITH DATA</p>
<h1>취향에 맞게.<br>사이즈는 더 정확하게.</h1>
<p>리뷰와 나의 구매 기록으로 찾는 더 나은 선택.<br>FitWise와 함께 나에게 맞는 옷을 알아보세요.</p></section>''')
st.subheader("당신의 다음 데일리웨어")
category = st.radio("카테고리", ["전체", "상의", "아우터", "하의"], horizontal=True, key="category")
products = browse_products(category)
st.caption(f"{len(products)}개의 상품 · 가상 데모 컬렉션")

if not products:
    st.info("등록된 상품이 없습니다.")
for start in range(0, len(products), 4):
    columns = st.columns(4)
    for column, product in zip(columns, products[start:start + 4]):
        with column, st.container(border=True, key=f"card_{product['id']}"):
            garment(product)
            st.markdown(f"**{product['name']}**")
            st.write(f"₩{product['price']:,}")
            rating = f"{product['rating']:.1f}" if product["rating"] else "—"
            st.caption(f"★ {rating} ({product['review_count']})")
            if st.button("나의 핏 확인 →", key=f"product_{product['id']}", width="stretch"):
                st.session_state.selected_product = product["id"]
                st.switch_page("views/product_detail.py")

st.info("가상 상품·리뷰·구매 데이터를 사용하는 개발용 데모입니다. 분석 점수는 실제 반품 확률이 아닙니다.")
