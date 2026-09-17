"""공통 표시 컴포넌트. HTML에는 신뢰하지 않는 문자열을 escape합니다."""
from base64 import b64encode
from functools import lru_cache
from html import escape
from pathlib import Path

import streamlit as st

COLORS = {"sage": ("#e2eadd", "#809a78"), "sand": ("#efe9de", "#b4a181"),
          "blue": ("#e2e8ef", "#637f9e"), "rose": ("#f0e3e2", "#b99390"),
          "stone": ("#e8e7e0", "#929488"), "ink": ("#e3e5e8", "#515d69")}
IMAGE_ROOT = Path(__file__).resolve().parents[1] / "images"


def product_image_path(product_id):
    """샘플 상품 ID에 대응하는 로컬 카탈로그 이미지 경로를 반환합니다."""
    return IMAGE_ROOT / f"product-{product_id}.png"


@lru_cache(maxsize=16)
def _image_data_uri(path):
    image = Path(path)
    mime = "image/webp" if image.suffix.lower() == ".webp" else "image/png"
    return f"data:{mime};base64,{b64encode(image.read_bytes()).decode('ascii')}"


def product_thumbnail(product):
    """현재 탭에서 상품을 전환하는 클릭 가능한 소형 썸네일입니다."""
    thumbnail = IMAGE_ROOT / "thumbnails" / f"product-{product['id']}.webp"
    if not thumbnail.exists():
        thumbnail = product_image_path(product["id"])
    if not thumbnail.exists():
        return
    st.html(
        f'<a class="product-thumb-link" href="?product={product["id"]}" target="_self" '
        f'aria-label="{escape(product["name"])} 상품 보기">'
        f'<img src="{_image_data_uri(str(thumbnail))}" alt="{escape(product["name"])}"></a>'
    )


def review_image_path(product_id, variant):
    """상품별로 준비된 착용 사진 경로를 반환합니다."""
    return IMAGE_ROOT / f"review-{product_id}-{variant}.png"


def garment(product):
    image = product_image_path(product["id"])
    if image.exists():
        st.image(image, width="stretch")
        return

    background, color = COLORS.get(product["color"], COLORS["sage"])
    pants = product["category"] == "하의"
    shape = ("M99 45H201L215 251 157 255 150 130 141 255 84 251Z" if pants else
             "M119 58 86 69 47 141 80 162 101 123 99 242Q149 251 201 242L199 123 221 162 253 141 214 69 181 58Q150 76 119 58Z")
    seam = ("M99 60H200M149 48V115M105 65Q104 92 124 93M194 65Q193 92 176 93" if pants else
            "M120 58Q150 100 181 58M101 124L106 85M199 124L194 85M101 231Q151 239 200 231")
    st.html(f'''<div class="garment" style="background:{background};color:{color}">
    <svg viewBox="0 0 300 300" role="img" aria-label="{escape(product['name'])} 일러스트">
    <ellipse cx="150" cy="268" rx="78" ry="10" fill="currentColor" opacity=".09"/>
    <path d="{shape}" fill="currentColor"/>
    <path d="{seam}" fill="none" stroke="white" stroke-opacity=".5" stroke-width="2"/>
    </svg><span>FITWISE / {escape(product['subcategory'])}</span></div>''')


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
