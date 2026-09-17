"""실행: python -m streamlit run streamlit_app.py"""
import streamlit as st

from app.config import ROOT, get_settings
from app.db import initialize

st.set_page_config(page_title="FitWise · 나에게 맞는 선택", page_icon="👕", layout="wide")


@st.cache_resource
def prepare_database(path):
    # DB 연결 자체를 캐시하지 않습니다. 세션/스레드마다 독립 연결을 엽니다.
    initialize(path)


settings = get_settings()
try:
    prepare_database(str(settings.database))
except ValueError as exc:
    st.error(str(exc))
    st.stop()
st.html(f"<style>{(ROOT / 'static' / 'css' / 'style.css').read_text(encoding='utf-8')}</style>")

with st.sidebar:
    st.title("FitWise 👕")
    st.caption("Better Fit. Smarter Purchase.\nFewer Returns.")
    st.divider()

page = st.navigation([
    st.Page("views/products.py", title="상품 목록", icon="🛍️", default=True),
    st.Page("views/product_detail.py", title="상품 상세 · 리뷰", icon="👕"),
    st.Page("views/fit_result.py", title="구매적합도", icon="🎯"),
    st.Page("views/admin_dashboard.py", title="관리자 Dashboard", icon="📊"),
])

with st.sidebar:
    st.divider()
    st.caption("LOCAL DEMO · 가상 샘플 데이터")
    st.caption("분석: 규칙 기반 baseline")
    st.caption("API 키: 설정됨 (연결 전)" if settings.api_key else "API 키: 미설정 · 기본 기능 실행 가능")
    st.caption("관리자 인증은 후속 개발 항목입니다.")

if settings.analysis_mode != "baseline":
    st.warning("현재 구현은 baseline만 지원합니다. .env의 FITWISE_ANALYSIS_MODE를 baseline으로 설정하세요.")

page.run()
