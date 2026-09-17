from html import escape

import streamlit as st

from app.db import connect
from app.repository import get_product, list_users


# -----------------------------
# 데이터 불러오기
# -----------------------------
saved = st.session_state.get("fit_result")

if not saved:
    st.info("상품 상세에서 사용자와 사이즈를 선택한 후 분석을 실행해 주세요.")
    st.page_link(
        "views/product_detail.py",
        label="상품 상세로 이동",
        icon="👕"
    )
    st.stop()


with connect() as connection:
    product = get_product(connection, saved["product_id"])
    users = {u["id"]: u["name"] for u in list_users(connection)}

result = saved["result"]

score = result.get("score")
score_text = str(score) if score is not None else "—"


# -----------------------------
# 스타일
# -----------------------------
st.html("""
<style>

/* 전체 화면 폭 */
.block-container {
    max-width: 1180px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}


/* 상단 Hero */
.fit-hero {
    position: relative;
    overflow: hidden;

    padding: 34px 36px;

    border: 1px solid #dce8dd;
    border-radius: 26px;

    background:
        radial-gradient(circle at top right,
            rgba(88, 140, 102, 0.18),
            transparent 35%),
        linear-gradient(
            135deg,
            #f4f8f1 0%,
            #fbfaf7 50%,
            #eef5ed 100%
        );

    box-shadow:
        0 12px 35px rgba(32, 72, 50, 0.06);

    margin-bottom: 22px;
}


.fit-eyebrow {
    display: inline-block;

    font-size: 0.75rem;
    font-weight: 800;

    color: #5d7d68;

    letter-spacing: .16em;

    margin-bottom: 10px;
}


.fit-hero h1 {
    font-size: 2.25rem;
    line-height: 1.25;

    margin: 0 0 12px;

    color: #173d2d;
}


.fit-meta {
    color: #65756a;
    font-size: 0.96rem;

    margin-top: 6px;
}


/* 점수 카드 */
.score-card {
    height: 100%;

    display: flex;
    flex-direction: column;

    align-items: center;
    justify-content: center;

    padding: 28px 18px;

    border-radius: 24px;

    background:
        linear-gradient(
            145deg,
            #194d34,
            #276b49
        );

    box-shadow:
        0 14px 32px rgba(24, 79, 52, 0.18);

    color: white;

    text-align: center;
}


.score-label {
    font-size: 0.78rem;
    font-weight: 700;

    letter-spacing: .12em;

    opacity: .75;

    margin-bottom: 8px;
}


.score-value {
    font-size: 3.5rem;
    line-height: 1;

    font-weight: 900;
}


.score-value span {
    font-size: 1rem;

    margin-left: 4px;

    font-weight: 600;

    opacity: .7;
}


.score-result {
    margin-top: 14px;

    padding: 7px 12px;

    border-radius: 999px;

    background:
        rgba(255,255,255,0.13);

    font-weight: 700;

    font-size: .9rem;
}


/* 섹션 제목 */
.section-title {
    margin-top: 34px;
    margin-bottom: 14px;

    color: #214b35;

    font-size: 1.25rem;
    font-weight: 800;
}


.section-subtitle {
    color: #7a887f;

    font-size: .88rem;

    margin-top: -8px;
    margin-bottom: 16px;
}


/* 카드 */
.info-card {
    padding: 22px;

    border-radius: 20px;

    border: 1px solid #e1e9e1;

    background: white;

    box-shadow:
        0 8px 25px rgba(47, 74, 54, 0.045);

    margin-bottom: 14px;
}


/* -----------------------------
   점수를 구성하는 데이터
----------------------------- */

.metric-row {
    padding: 7px 0 12px;
    border-bottom: 1px solid #edf2ed;
}

.metric-header {
    display: flex;
    align-items: center;
    justify-content: space-between;

    margin-bottom: -2px;
}

.metric-name {
    color: #214936;

    font-size: 1rem;
    font-weight: 750;

    line-height: 1.3;
}

.metric-value {
    color: #08783f;

    font-size: 1.05rem;
    font-weight: 850;

    white-space: nowrap;
}


/* progress 전체 영역 */
div[data-testid="stProgress"] {
    margin-top: -4px !important;
    margin-bottom: -3px !important;
}

/* progress 내부 높이 강제 */
div[data-testid="stProgress"] > div {
    height: 18px !important;
    min-height: 18px !important;
}

/* 실제 progress bar */
div[data-testid="stProgress"] div[role="progressbar"] {
    height: 18px !important;
    min-height: 18px !important;
    border-radius: 999px !important;
}

/* 채워지는 바 */
div[data-testid="stProgress"] div[role="progressbar"] > div {
    height: 18px !important;
    min-height: 18px !important;
    border-radius: 999px !important;
}


/* 표본 + 가중치 */
.metric-meta {
    margin-top: -4px;
    margin-bottom: 2px;

    color: #88958c;

    font-size: 0.76rem;
    font-weight: 500;
}


/* 지표가 들어있는 전체 카드 */
.info-card {
    padding: 22px 24px;

    border-radius: 20px;

    border: 1px solid #e1e9e1;

    background: white;

    box-shadow:
        0 8px 25px rgba(47, 74, 54, 0.045);

    margin-bottom: 14px;
}


/* 분석 근거 */
.reason-card {
    padding: 14px 16px;

    border-radius: 14px;

    background: #f7f9f6;

    border: 1px solid #e7ede6;

    margin-bottom: 8px;

    color: #47564c;
}


/* AI Advisor */
.st-key-fit_advisor {
    border: 1px solid #cfe0ce;

    border-radius: 22px;

    padding: 24px 26px;

    background:
        linear-gradient(
            145deg,
            #f3f8f1,
            #fbfcf8
        );

    box-shadow:
        0 10px 30px rgba(41, 82, 53, 0.06);
}


.st-key-fit_advisor h3 {
    color: #20543a;

    margin-top: 0;
}


/* 하단 안내 */
.request-note {
    margin-top: 22px;

    padding: 11px 14px;

    border-radius: 12px;

    background: #f5f7f5;

    color: #7a857e;

    font-size: .8rem;
}

</style>
""")


# -----------------------------
# HERO
# -----------------------------
hero_left, hero_right = st.columns([3, 1.15], gap="large")

with hero_left:

    username = users.get(saved["user_id"], "사용자")
    preferred_fit = saved.get("preferred_fit", "미선택")
    height = saved.get("height", "-")
    weight = saved.get("weight", "-")

    st.html(
        f"""
        <div class="fit-hero">

            <div class="fit-eyebrow">
                FITWISE · PERSONAL FIT REPORT
            </div>

            <h1>
                {escape(product["name"])}
            </h1>

            <div class="fit-meta">
                👤 {escape(username)}
                &nbsp;&nbsp;·&nbsp;&nbsp;
                📏 {escape(saved["size"])} 사이즈
                &nbsp;&nbsp;·&nbsp;&nbsp;
                👕 {escape(preferred_fit)}
            </div>

            <div class="fit-meta">
                키 {height}cm
                &nbsp;&nbsp;·&nbsp;&nbsp;
                몸무게 {weight}kg
            </div>

        </div>
        """
    )


with hero_right:

    st.html(
        f"""
        <div class="score-card">

            <div class="score-label">
                FITWISE SCORE
            </div>

            <div class="score-value">
                {score_text}
                <span>/ 100</span>
            </div>

            <div class="score-result">
                {escape(result["label"])}
            </div>

        </div>
        """
    )


# -----------------------------
# 핵심 분석
# -----------------------------
st.html(
    """
    <div class="section-title">
        구매 적합도 분석
    </div>

    <div class="section-subtitle">
        개인 구매 이력, 상품 반품 데이터, 체형 유사 사용자와 리뷰를 함께 분석했습니다.
    </div>
    """
)


left, right = st.columns([1, 2], gap="large")


# 왼쪽 결과 요약
with left:

    with st.container(border=True):

        st.caption("분석 결과")

        if score is not None:
            st.metric(
                "종합 구매 적합도",
                f"{score}점",
                help="100점에 가까울수록 선택한 사이즈가 잘 맞을 가능성이 높습니다."
            )
        else:
            st.metric(
                "종합 구매 적합도",
                "데이터 부족"
            )

        st.subheader(result["label"])

        st.caption(
            result["disclaimer"]
        )

        if result["limited_data"]:
            st.warning(
                "일부 지표의 표본이 5건 미만이므로 참고용으로 확인해 주세요."
            )


# -----------------------------
# 오른쪽 세부 지표
# -----------------------------
with right:

    st.markdown("#### 점수를 구성하는 데이터")

    for metric in result["metrics"]:

        value = metric["value"]

        display = (
            f"{value}%"
            if value is not None
            else "데이터 없음"
        )

        # 제목 + 퍼센트
        st.html(
            f"""
            <div class="metric-row">

                <div class="metric-header">

                    <div class="metric-name">
                        {escape(metric["label"])}
                    </div>

                    <div class="metric-value">
                        {display}
                    </div>

                </div>
            """
        )

        # 제목 바로 아래 progress bar
        if value is not None:
            st.progress(
                float(value) / 100
            )

        # progress bar 아래 표본 정보
        st.html(
            f"""
                <div class="metric-meta">
                    표본 {metric["count"]}건
                    &nbsp;·&nbsp;
                    적용 가중치 {metric["effective_weight_pct"]}%
                </div>

            </div>
            """
        )


# -----------------------------
# 분석 근거
# -----------------------------
st.html(
    """
    <div class="section-title">
        왜 이런 점수가 나왔나요?
    </div>

    <div class="section-subtitle">
        구매 적합도 계산에 영향을 준 주요 근거입니다.
    </div>
    """
)


for reason in result["reasons"]:

    st.html(
        f"""
        <div class="reason-card">
            ✓ {escape(str(reason))}
        </div>
        """
    )


# -----------------------------
# AI FIT ADVISOR
# -----------------------------
advisor = result.get("advisor")

if advisor:

    st.html(
        """
        <div class="section-title">
            AI Fit Advisor
        </div>

        <div class="section-subtitle">
            데이터 분석 결과를 바탕으로 구매 전에 확인하면 좋은 내용을 정리했습니다.
        </div>
        """
    )

    with st.container(key="fit_advisor"):

        st.markdown("### 🤖 FitWise AI 추천")

        st.success(
            advisor["recommendation"]
        )

        st.write(
            advisor["explanation"]
        )

        if advisor["risk_signals"]:

            st.markdown("#### ⚠️ 확인이 필요한 신호")

            for item in advisor["risk_signals"]:
                st.write(f"- {item}")

        if advisor["next_actions"]:

            st.markdown("#### ✅ 구매 전 추천 행동")

            for item in advisor["next_actions"]:
                st.write(f"- {item}")


elif result.get("advisor_error"):

    st.warning(
        "AI Fit Advisor를 사용할 수 없어 "
        "규칙 기반 분석 결과만 표시합니다. "
        f"오류 유형: {result['advisor_error']}"
    )


# -----------------------------
# 점수 계산 방식
# -----------------------------
st.html(
    """
    <div class="section-title">
        점수는 어떻게 계산하나요?
    </div>
    """
)


with st.expander("FitWise Score 산정 방식 자세히 보기"):

    st.write(
        "각 지표를 0~100점으로 환산한 뒤 "
        "가중합하여 최종 구매 적합도를 계산합니다."
    )

    st.markdown(
        """
### 1. 개인 선택 사이즈 성공률 · 25%

동일 카테고리에서 사용자가 선택한 사이즈로 구매한 주문의
**미반품 비율**입니다.

`(개인 동일 카테고리·선택 사이즈 주문 수 - 반품 수) / 주문 수 × 100`


### 2. 상품 반품 안정성 · 20%

모든 사용자의 해당 상품 주문 중
**미반품 비율**입니다.

점수가 높을수록 해당 상품의 전반적인 반품 위험이 낮습니다.

`(해당 상품 전체 주문 수 - 전체 반품 수) / 전체 주문 수 × 100`


### 3. 체형 유사 선택 사이즈 성공률 · 30%

해당 상품과 선택 사이즈 주문 중
입력한 키·몸무게와 가까운 구매자에게
더 높은 가중치를 적용합니다.

`Σ(체형 유사도 × 미반품 여부) / Σ(체형 유사도) × 100`


### 4. 체형 유사 리뷰 적합도 · 25%

입력한 체형과 가까운 리뷰 작성자의
긍정 리뷰 비율을 계산합니다.

평점 **4~5점 리뷰를 긍정 리뷰**로 처리합니다.

`Σ(체형 유사도 × 긍정 리뷰 여부) / Σ(체형 유사도) × 100`


### 체형 유사도

키와 몸무게 차이가 작을수록
유사도가 높아집니다.

`max(0.1, 1 - 0.5×min(키 차이, 20)/20 - 0.5×min(몸무게 차이, 20)/20)`


### 최종 점수

`개인 성공률 × 0.25`

`+ 상품 반품 안정성 × 0.20`

`+ 체형 유사 주문 성공률 × 0.30`

`+ 체형 유사 리뷰 적합도 × 0.25`
"""
    )

    st.info(
        "예: 80점, 90점, 70점, 75점이면 "
        "80×0.25 + 90×0.20 + 70×0.30 + 75×0.25 "
        "= 77.75점 → 최종 78점"
    )

    st.caption(
        "데이터가 없는 항목은 100점으로 처리하지 않습니다. "
        "해당 항목을 제외하고 남은 가중치를 다시 100% 기준으로 "
        "재정규화합니다."
    )

    st.caption(
        "표본이 5건 미만인 지표는 참고용 경고를 표시하며, "
        "리뷰의 사이즈·핏 관련 부정 키워드는 점수를 직접 차감하지 않고 "
        "분석 근거와 AI Fit Advisor에 활용합니다."
    )


# -----------------------------
# 실행 정보
# -----------------------------
review_note = (
    "저장된 리뷰 분석 결과를 재사용했습니다."
    if saved.get("review_source") == "cached"
    else "리뷰 분석 결과를 새로 생성해 저장했습니다."
)

st.html(
    f"""
    <div class="request-note">
        실행 ID · {escape(str(saved["request_id"]))}
        &nbsp;&nbsp;|&nbsp;&nbsp;
        {escape(review_note)}
    </div>
    """
)


# -----------------------------
# 하단 이동 버튼
# -----------------------------
st.write("")

a, b = st.columns(2)

a.page_link(
    "views/product_detail.py",
    label="👕 다른 사이즈 확인하기",
    use_container_width=True
)

b.page_link(
    "views/admin_dashboard.py",
    label="📊 Agent 실행 자원 확인하기",
    use_container_width=True
)
