"""FitWise Agent 운영 및 리소스 모니터링 Dashboard."""
import pandas as pd
import streamlit as st

from app.db import connect
from app.monitoring import dashboard_data


OPERATION_LABELS = {"browse": "상품 조회", "review": "리뷰 분석", "fit": "구매 적합도"}
AGENT_LABELS = {"browse": "General", "review": "Review", "fit": "Fit"}


def average(frame, column):
    if frame.empty or column not in frame:
        return None
    value = frame[column].mean()
    return None if pd.isna(value) else float(value)


def number(value, digits=1, suffix=""):
    return "—" if value is None else f"{value:,.{digits}f}{suffix}"


def reset_filters():
    defaults = {
        "dashboard_period": "전체 기간",
        "dashboard_mode": "전체",
        "dashboard_agent": "전체 유형",
        "dashboard_operation": "전체 작업",
    }
    for key, value in defaults.items():
        st.session_state[key] = value


st.html("""
<style>
.st-key-dashboard_header {
    border: 1px solid #dce5d6; border-radius: 18px; padding: 22px 24px;
    background: linear-gradient(135deg, #eef3e9 0%, #fafaf6 72%); margin-bottom: 8px;
}
.st-key-dashboard_header h1 { color:#173d2d; margin-bottom:.2rem; }
.st-key-dashboard_filters {
    border: 1px solid #dce5d6; border-radius: 14px; background: #f8f9f5; padding: 12px 14px 4px;
}
.dashboard-section-title {
    margin: 18px 0 10px; display:flex; align-items:flex-end; justify-content:space-between; gap:16px;
}
.dashboard-section-title h3 { margin:0; color:#234936; }
.dashboard-section-title span { color:#7a897e; font-size:.78rem; }
.st-key-dashboard_phase_before,
.st-key-dashboard_phase_running,
.st-key-dashboard_phase_after { min-height: 170px; border-radius: 14px; padding: 4px; }
.st-key-dashboard_phase_running { background:#f0f6ef; box-shadow:inset 0 0 0 1px #8eb49a; }
.dashboard-phase-label {
    display:inline-flex; padding:4px 9px; border-radius:999px; background:#e8eee5;
    color:#4e6a58; font-size:.68rem; font-weight:700; letter-spacing:.08em;
}
.dashboard-note {
    padding:12px 14px; border:1px solid #ead9ad; border-radius:10px;
    background:#fff9e9; color:#76643a; font-size:.79rem;
}
.st-key-dashboard_logs [data-testid="stDataFrame"] { border-radius:12px; overflow:hidden; }
@media(max-width:700px) {
    .st-key-dashboard_header { padding:18px; }
    .dashboard-section-title { display:block; }
    .dashboard-section-title span { display:block; margin-top:4px; }
}
</style>
""")

with connect() as connection:
    data = dashboard_data(connection)

resources = pd.DataFrame(data["resources"])
agents = pd.DataFrame(data["agents"])

if not resources.empty:
    resources["created_at"] = pd.to_datetime(resources["created_at"], utc=True, errors="coerce")
    for column in ("cpu_percent", "memory_before_mb", "memory_after_mb", "memory_delta_mb",
                   "processing_ms", "response_ms"):
        resources[column] = pd.to_numeric(resources[column], errors="coerce")
    resources["mode"] = resources["operation"].map(
        lambda value: "Agent 미사용" if value == "browse" else "Agent 사용"
    )
    resources["agent_type"] = resources["operation"].map(AGENT_LABELS)
    resources["operation_label"] = resources["operation"].map(OPERATION_LABELS)

last_log = resources["created_at"].max() if not resources.empty else None
last_log_text = (
    last_log.strftime("%Y.%m.%d %H:%M UTC")
    if last_log is not None and not pd.isna(last_log)
    else "기록 없음"
)

with st.container(key="dashboard_header"):
    title_column, status_column = st.columns([3, 1])
    with title_column:
        st.caption("SYSTEM OBSERVABILITY / AGENT OPS")
        st.title("Agent 운영 Dashboard")
        st.write("Agent 실행 여부에 따른 리소스 영향과 응답 성능을 비교합니다.")
    with status_column:
        st.caption("마지막 수집 로그")
        st.markdown(f"**{last_log_text}**")
        st.button("최신 기록 새로고침", key="refresh_dashboard", width="stretch")

with st.container(key="dashboard_filters"):
    period_column, mode_column, agent_column, operation_column, reset_column = st.columns([1, 1, 1, 1, .65])
    with period_column:
        period = st.selectbox(
            "기간", ["전체 기간", "최근 24시간", "최근 3일", "최근 7일"], key="dashboard_period"
        )
    with mode_column:
        mode = st.selectbox("실행 모드", ["전체", "Agent 사용", "Agent 미사용"], key="dashboard_mode")
    with agent_column:
        agent_type = st.selectbox(
            "Agent 유형", ["전체 유형", "Fit", "Review", "General"], key="dashboard_agent"
        )
    with operation_column:
        operation = st.selectbox(
            "작업", ["전체 작업", "상품 조회", "리뷰 분석", "구매 적합도"], key="dashboard_operation"
        )
    with reset_column:
        st.write("")
        st.button("초기화", key="dashboard_reset", on_click=reset_filters, width="stretch")

filtered = resources.copy()
if not filtered.empty:
    period_hours = {"최근 24시간": 24, "최근 3일": 72, "최근 7일": 168}.get(period)
    if period_hours and last_log is not None and not pd.isna(last_log):
        filtered = filtered[filtered["created_at"] >= last_log - pd.Timedelta(hours=period_hours)]
    if mode != "전체":
        filtered = filtered[filtered["mode"] == mode]
    if agent_type != "전체 유형":
        filtered = filtered[filtered["agent_type"] == agent_type]
    if operation != "전체 작업":
        filtered = filtered[filtered["operation_label"] == operation]

successful = filtered[filtered["status"] == "success"] if not filtered.empty else filtered
agent_runs = successful[successful["operation"] != "browse"] if not successful.empty else successful
baseline = successful[successful["operation"] == "browse"] if not successful.empty else successful

cpu_on = average(agent_runs, "cpu_percent")
cpu_off = average(baseline, "cpu_percent")
memory_on = average(agent_runs, "memory_after_mb")
memory_off = average(baseline, "memory_after_mb")
response_on = average(agent_runs, "response_ms")
cpu_delta = cpu_on - cpu_off if cpu_on is not None and cpu_off is not None else None
memory_delta = memory_on - memory_off if memory_on is not None and memory_off is not None else None
error_count = int((filtered["status"] == "error").sum()) if not filtered.empty else 0

st.html('<div class="dashboard-section-title"><h3>핵심 운영 지표</h3><span>선택된 로그 기준</span></div>')
kpis = st.columns(4)
kpis[0].metric("Agent 실행", f"{len(agent_runs):,}건", delta=f"실패 {error_count}건", delta_color="inverse")
kpis[1].metric(
    "CPU 오버헤드", number(cpu_delta, 1, "%p"),
    delta=f"ON {number(cpu_on, 1, '%')} · OFF {number(cpu_off, 1, '%')}", delta_color="off",
)
kpis[2].metric(
    "Memory 오버헤드", number(memory_delta, 1, " MB"),
    delta=f"ON {number(memory_on, 1, ' MB')}", delta_color="off",
)
kpis[3].metric(
    "Agent 응답시간", number(response_on / 1000 if response_on is not None else None, 3, "초"),
    delta="평균 서비스 응답", delta_color="off",
)

st.html('<div class="dashboard-section-title"><h3>리소스 영향 비교</h3><span>Agent 미사용 대비 실행 구간</span></div>')
cpu_column, memory_column = st.columns(2)
with cpu_column, st.container(border=True):
    st.subheader("평균 CPU 사용량")
    st.caption("1코어 기준 · 로그 행별 평균")
    cpu_compare = pd.DataFrame(
        {"CPU %": [cpu_off, cpu_on]}, index=["Agent 미사용", "Agent 사용"]
    ).dropna()
    if cpu_compare.empty:
        st.info("비교할 CPU 로그가 없습니다.")
    else:
        st.bar_chart(cpu_compare, color="#21634B", horizontal=True, height=220)
with memory_column, st.container(border=True):
    st.subheader("평균 Memory 사용량")
    st.caption("프로세스 RSS · 로그 행별 평균")
    memory_compare = pd.DataFrame(
        {"Memory MB": [memory_off, memory_on]}, index=["Agent 미사용", "Agent 사용"]
    ).dropna()
    if memory_compare.empty:
        st.info("비교할 Memory 로그가 없습니다.")
    else:
        st.bar_chart(memory_compare, color="#718A67", horizontal=True, height=220)

st.html('<div class="dashboard-section-title"><h3>작업 단계별 리소스 프로파일</h3><span>BEFORE · RUNNING · AFTER</span></div>')
before_column, running_column, after_column = st.columns(3)
before_memory = average(agent_runs, "memory_before_mb")
after_memory = average(agent_runs, "memory_after_mb")
processing_time = average(agent_runs, "processing_ms")
with before_column, st.container(border=True, key="dashboard_phase_before"):
    st.html('<span class="dashboard-phase-label">01 · BEFORE</span>')
    st.subheader("작업 시작")
    st.metric("Memory", number(before_memory, 1, " MB"))
    st.caption("작업 직전 프로세스 RSS")
with running_column, st.container(border=True, key="dashboard_phase_running"):
    st.html('<span class="dashboard-phase-label">02 · RUNNING</span>')
    st.subheader("Agent 실행")
    running_metrics = st.columns(2)
    running_metrics[0].metric("CPU", number(cpu_on, 1, "%"))
    running_metrics[1].metric("처리시간", number(processing_time, 1, " ms"))
with after_column, st.container(border=True, key="dashboard_phase_after"):
    st.html('<span class="dashboard-phase-label">03 · AFTER</span>')
    st.subheader("작업 종료")
    st.metric(
        "Memory", number(after_memory, 1, " MB"),
        delta=number(memory_delta, 1, " MB"), delta_color="inverse",
    )
    st.caption("응답 완료 직후 프로세스 RSS")

st.html(
    '<div class="dashboard-note">현재 CPU는 작업 구간 전체의 프로세스 사용률입니다. '
    '더 정밀한 전·중·후 비교에는 단계별 CPU 샘플과 회복시간 수집이 필요합니다.</div>'
)

st.html('<div class="dashboard-section-title"><h3>응답 성능</h3><span>Agent 유형별 추이와 평균</span></div>')
trend_column, agent_column = st.columns([1.35, 1])
with trend_column, st.container(border=True):
    st.subheader("Agent 응답시간 추이")
    trend = (
        agent_runs.dropna(subset=["created_at"]).sort_values("created_at")
        if not agent_runs.empty else agent_runs
    )
    if trend.empty:
        st.info("표시할 Agent 실행 로그가 없습니다.")
    else:
        trend = trend.assign(response_seconds=trend["response_ms"] / 1000)
        st.line_chart(
            trend, x="created_at", y="response_seconds", color="#21634B", height=260,
            x_label="실행 시각", y_label="응답시간 (초)",
        )
with agent_column, st.container(border=True):
    st.subheader("Agent 유형별 응답시간")
    if agent_runs.empty:
        st.info("표시할 Agent 실행 로그가 없습니다.")
    else:
        agent_average = (
            agent_runs.groupby("agent_type", as_index=True)["response_ms"].mean() / 1000
        ).to_frame("평균 초")
        st.bar_chart(agent_average, color="#6F8F76", height=260)

st.html('<div class="dashboard-section-title"><h3>최근 실행 로그</h3><span>선택된 조건의 최신 작업</span></div>')
with st.container(key="dashboard_logs"):
    if filtered.empty:
        st.info("조건에 맞는 실행 로그가 없습니다.")
    else:
        logs = filtered.sort_values("created_at", ascending=False).head(30).copy()
        logs["실행 시각"] = logs["created_at"].dt.strftime("%m.%d %H:%M")
        logs["CPU"] = logs["cpu_percent"].map(lambda value: number(value, 1, "%"))
        logs["Memory"] = logs["memory_after_mb"].map(lambda value: number(value, 1, " MB"))
        logs["응답시간"] = logs["response_ms"].map(lambda value: number(value / 1000, 3, "초"))
        st.dataframe(
            logs[["실행 시각", "mode", "agent_type", "operation_label", "CPU", "Memory", "응답시간", "status"]]
            .rename(columns={
                "mode": "모드", "agent_type": "Agent 유형", "operation_label": "작업", "status": "상태",
            }),
            hide_index=True, width="stretch", height=360,
        )

with st.expander("Agent 실행 상세 · 최근 30건"):
    if agents.empty:
        st.caption("Agent 실행 기록이 없습니다.")
    else:
        st.dataframe(agents, hide_index=True, width="stretch")

with st.expander("측정 기준과 한계"):
    st.markdown("""
    - **CPU**: 프로세스 CPU 시간 증가량을 작업 경과시간으로 나눈 1코어 기준 값입니다.
    - **Memory**: `psutil`로 측정한 작업 전·후 프로세스 RSS이며 Agent 전용 메모리나 최대 사용량은 아닙니다.
    - **처리시간**: 분석 함수 실행 구간이며, 서비스 응답시간은 Agent 로그 저장까지 포함합니다.
    - **Fit 작업**은 내부 Review 실행을 포함하므로 Agent 로그 수와 리소스 작업 수가 다를 수 있습니다.
    - 같은 프로세스의 다른 세션과 백그라운드 작업이 측정값에 영향을 줄 수 있습니다.
    - 외부 API 연결 이후에도 이 값은 로컬 프로세스 기준이며 원격 AI 서버의 CPU·GPU 사용량은 아닙니다.
    """)
