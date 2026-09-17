"""공통 표시 컴포넌트. HTML에는 신뢰하지 않는 문자열을 escape합니다."""
from html import escape

import streamlit as st

COLORS = {"sage": ("#e2eadd", "#809a78"), "sand": ("#efe9de", "#b4a181"),
          "blue": ("#e2e8ef", "#637f9e"), "rose": ("#f0e3e2", "#b99390"),
          "stone": ("#e8e7e0", "#929488"), "ink": ("#e3e5e8", "#515d69")}


def garment(product):
    background, color = COLORS.get(product["color"], COLORS["sage"])
    rating = product.get("rating")
    badge = f'<span class="garment-badge">★ {rating:.1f}</span>' if rating else ""
    image_url = f"app/static/images/product_{product['id']}.png"
    st.html(f'''<div class="garment" style="background:{background};color:{color}">
    <span class="garment-tag">{escape(product['subcategory'])}</span>{badge}
    <img src="{image_url}" alt="{escape(product['name'])}" loading="lazy">
    <span>FITWISE</span></div>''')


def show_review(result):
    st.caption("규칙 기반 리뷰 분석 · 평점 및 키워드 사전")
    cols = st.columns(4)
    for col, label, key in zip(cols, ("긍정", "중립", "부정", "사이즈 불만"),
                               ("positive_pct", "neutral_pct", "negative_pct", "size_complaint_pct")):
        value = result[key]
        col.metric(label, f"{value}%" if value is not None else "—")
    st.write(result["summary"])
    left, right = st.columns(2)
    for col, label, key in ((left, "주요 긍정 키워드", "positive_keywords"),
                            (right, "주요 주의 키워드", "negative_keywords")):
        with col:
            st.markdown(f"**{label}**")
            if result[key]:
                st.write(" · ".join(f"{item['keyword']} ({item['count']})" for item in result[key]))
            else:
                st.caption("검출된 키워드가 없습니다.")
    with st.expander("사이즈 · 핏 의견 원문"):
        st.write("사이즈 의견")
        for comment in result["size_comments"]:
            st.write(f"• {comment}")
        st.write("핏 의견")
        for comment in result["fit_comments"]:
            st.write(f"• {comment}")
    st.caption("긍정 4~5점 · 중립 3점 · 부정 1~2점. 키워드 분석은 문맥과 부정 표현을 오해할 수 있습니다.")
