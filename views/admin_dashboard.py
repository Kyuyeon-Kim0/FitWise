import pandas as pd
import streamlit as st

from app.db import connect
from app.monitoring import dashboard_data


def as_kst_frame(rows):
    """UTC로 저장한 DB 시각을 관리자 화면에서만 한국 표준시로 표시합니다."""
    frame = pd.DataFrame(rows)
    if not frame.empty and "created_at" in frame:
        frame["created_at"] = (pd.to_datetime(frame["created_at"], utc=True)
                               .dt.tz_convert("Asia/Seoul")
                               .dt.strftime("%Y-%m-%d %H:%M:%S KST"))
    return frame


st.caption("SYSTEM OBSERVABILITY")
st.title("Resource Dashboard")
st.write("일반 조회와 Agent 실행에 사용된 로컬 프로세스 자원을 비교합니다.")
st.caption("로컬 개발용 · 인증 미구현 · 수치는 실제 실행 시 측정")
st.button("최신 기록 새로고침", key="refresh_dashboard")
with connect() as connection:
    data = dashboard_data(connection)

cols = st.columns(3)
cols[0].metric("Agent 실행 횟수", data["counts"]["total"])
cols[1].metric("실패한 Agent 실행", data["counts"]["errors"])
cols[2].metric("성공한 측정 작업", sum(row["count"] for row in data["summary"]))
st.subheader("기능별 자원 사용량")
st.caption("전체 성공 작업 평균 · Fit 요청에는 Review 실행 포함")
labels = {"browse": "일반 조회", "review": "Review Agent", "fit": "Fit + Review"}
if data["summary"]:
    summary = pd.DataFrame(data["summary"])
    summary["operation"] = summary.operation.map(labels)
    summary = summary.set_index("operation")
    charts = st.columns(3)
    for col, field, title in zip(charts, ["cpu_percent", "memory_mb", "processing_ms"],
                                  ["CPU · 1코어 기준 %", "RSS Memory · MB", "처리시간 · ms"]):
        with col:
            st.caption(title)
            st.bar_chart(summary[[field]], color="#387859")
    st.dataframe(summary.rename(columns={"count": "작업 수", "cpu_percent": "CPU %",
                 "memory_mb": "RSS MB", "memory_delta_mb": "RSS 변화 MB",
                 "processing_ms": "처리 ms", "response_ms": "서비스 응답 ms"}).round(3), width="stretch")
else:
    st.info("기록이 없습니다. 상품을 조회하거나 Agent를 실행해 보세요.")

st.subheader("Agent 실행 로그")
st.caption("최근 30건 · 완료된 Agent 실행 · KST 시각 · 동일 request_id로 Review와 Fit 연결")
if data["agents"]:
    st.dataframe(as_kst_frame(data["agents"]), hide_index=True, width="stretch")
else:
    st.info("아직 Agent 실행 기록이 없습니다.")
with st.expander("작업별 자원 로그 · 최근 50건"):
    if data["resources"]:
        st.dataframe(as_kst_frame(data["resources"]), hide_index=True, width="stretch")
    else:
        st.caption("기록 없음")
with st.expander("측정 기준과 한계", expanded=True):
    st.markdown("""
    - CPU: 프로세스 CPU 시간 증가량 / 작업 경과시간 × 100. 1코어 기준이며 100%를 넘을 수 있습니다. 짧은 작업은 0%로 측정될 수 있습니다.
    - Memory: psutil로 측정한 작업 전·후 프로세스 RSS. 최대 메모리 또는 Agent 전용 메모리가 아닙니다.
    - 처리시간: 분석 함수 실행 구간. 일반 조회는 DB 조회 구간입니다.
    - 서비스 응답시간: 서비스 작업과 Agent 로그 저장을 포함합니다. 자원 로그 저장·Streamlit 화면 렌더링·네트워크 전송은 제외합니다.
    - 분석 버튼을 누르면 resource_logs에 requested 이벤트가, 작업이 끝나면 completed 이벤트가 생성됩니다.
    - Agent도 started와 success/error 이벤트를 각각 남깁니다. Dashboard 집계는 완료 이벤트만 사용합니다.
    - 상품 화면의 위젯 변경으로 rerun되면 조회 로그가 추가됩니다. 분석은 버튼을 눌러야 실행됩니다. Dashboard 조회는 측정에서 제외합니다.
    - 같은 프로세스의 다른 세션과 백그라운드 작업이 수치에 영향을 줍니다. 한 사용자·한 탭에서 같은 조건으로 반복 비교하세요.
    - 향후 외부 API 연결 시 이 수치는 로컬 클라이언트 자원이며, 원격 AI 서버의 CPU·GPU 사용량을 의미하지 않습니다.
    """)
