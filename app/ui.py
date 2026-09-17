"""공통 표시 컴포넌트. HTML에는 신뢰하지 않는 문자열을 escape합니다."""
from base64 import b64encode
from functools import lru_cache
from html import escape
from pathlib import Path

import streamlit as st

from app.config import ROOT

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
CATEGORY_KEYWORDS = {"상의": "shirt", "아우터": "jacket", "하의": "pants"}


def garment(product):
    image = product_image_path(product["id"])
    if image.exists():
        st.image(image, width="stretch")
        return

    background, color = COLORS.get(product["color"], COLORS["sage"])
    rating = product.get("rating")
    badge = f'<span class="garment-badge">★ {rating:.1f}</span>' if rating else ""
    local_path = ROOT / "static" / "images" / f"product_{product['id']}.png"
    if local_path.exists():
        image_url = f"app/static/images/product_{product['id']}.png"
    else:
        # 실사 이미지가 아직 없는 상품은 카테고리 키워드 기반 플레이스홀더로 채웁니다.
        keyword = CATEGORY_KEYWORDS.get(product["category"], "fashion")
        image_url = f"https://loremflickr.com/400/500/{keyword}?lock={product['id']}"
    st.html(f'''<div class="garment" style="background:{background};color:{color}">
    <span class="garment-tag">{escape(product['subcategory'])}</span>{badge}
    <img src="{image_url}" alt="{escape(product['name'])}" loading="lazy">
    <span>FITWISE</span></div>''')


def show_review(result):
    mode_label = f"AI 에이전트 분석 · {result['mode']}" if result["mode"].startswith("api-") else f"규칙 기반 분석 · {result['mode']}"
    st.caption(mode_label)
    metrics = (("긍정", "positive_pct"), ("중립", "neutral_pct"), ("부정", "negative_pct"), ("사이즈 불만", "size_complaint_pct"))
    for row_start in (0, 2):
        cols = st.columns(2)
        for col, (label, key) in zip(cols, metrics[row_start:row_start + 2]):
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
    advisor = result.get("advisor")
    if advisor:
        st.markdown("**AI Review Advisor 조언**")
        st.info(advisor["recommendation"])
        st.write(advisor["explanation"])
        st.caption(f"판단 신뢰도: {advisor['confidence']}")
        if advisor["risk_signals"]:
            st.write("주의 신호: " + " · ".join(advisor["risk_signals"]))
        if advisor["next_actions"]:
            st.write("다음 행동: " + " · ".join(advisor["next_actions"]))
    elif result.get("advisor_error"):
        st.warning(
            "AI Review Advisor를 사용할 수 없어 분석 결과만 표시합니다. "
            f"오류 유형: {result['advisor_error']}"
        )
