from collections import Counter

import streamlit as st

from ticket_agent.storage import LOG_FILE, load_logs
from ticket_agent.ticket_data import FAKE_TICKET_DATABASE
from ticket_agent.web_workflow import (
    finalize_reply_review,
    prepare_ticket_for_review,
    stop_duplicate_ticket,
)


st.set_page_config(
    page_title="企业工单处理 Agent",
    page_icon="",
    layout="wide",
)


CUSTOM_CSS = """
<style>
  .block-container {
    padding-top: 2.2rem;
    max-width: 1320px;
  }
  .main-title {
    font-size: 2.4rem;
    line-height: 1.2;
    font-weight: 750;
    margin: 0 0 0.4rem 0;
  }
  .subtle {
    color: #667085;
    font-size: 0.96rem;
  }
  .status-strip {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.75rem;
    margin: 1rem 0 1.2rem 0;
  }
  .metric-tile {
    border: 1px solid #d9dee7;
    border-radius: 8px;
    padding: 0.8rem 0.9rem;
    background: #ffffff;
  }
  .metric-label {
    color: #667085;
    font-size: 0.82rem;
    margin-bottom: 0.25rem;
  }
  .metric-value {
    color: #1f2937;
    font-size: 1.25rem;
    font-weight: 700;
  }
  .step-line {
    border-left: 3px solid #2f80ed;
    padding: 0.2rem 0 0.2rem 0.75rem;
    margin: 0.35rem 0;
    color: #344054;
  }
  .ticket-card {
    border: 1px solid #d9dee7;
    background: #ffffff;
    border-radius: 8px;
    padding: 0.9rem 1rem;
    margin-bottom: 0.75rem;
  }
  .warning-box {
    border: 1px solid #f0b429;
    background: #fff8e6;
    color: #5f4700;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    margin: 0.75rem 0;
  }
  .ok-box {
    border: 1px solid #7bc47f;
    background: #edf8ef;
    color: #205c28;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    margin: 0.75rem 0;
  }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def init_state() -> None:
    if "ticket_state" not in st.session_state:
        st.session_state["ticket_state"] = None
    if "selected_ticket_id" not in st.session_state:
        st.session_state["selected_ticket_id"] = "T1001"


def count_by(logs: list, field: str) -> Counter:
    return Counter(log.get(field, "未知") for log in logs)


def render_metric(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="metric-tile">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_step_list(steps: list) -> None:
    if not steps:
        st.caption("还没有执行流程。")
        return

    for step in steps:
        st.markdown(f'<div class="step-line">{step}</div>', unsafe_allow_html=True)


def render_log_summary(logs: list) -> None:
    review_counter = count_by(logs, "review_result")
    category_counter = count_by(logs, "category")
    duplicate_counter = count_by(logs, "duplicate_review_result")

    st.markdown("### 日志统计")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric("处理总数", str(len(logs)))
    with col2:
        render_metric("已发送", str(review_counter.get("approved", 0)))
    with col3:
        render_metric("未发送/停止", str(review_counter.get("rejected", 0)))
    with col4:
        render_metric("重复停止", str(duplicate_counter.get("stopped_by_duplicate_warning", 0)))

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**工单类别**")
        st.json(dict(category_counter))
    with col_b:
        st.markdown("**重复工单处理**")
        st.json(dict(duplicate_counter))


def render_current_ticket(state: dict) -> None:
    if not state:
        st.info("请先在左侧选择工单，然后点击“生成处理草稿”。")
        return

    st.markdown("### 当前工单")
    st.markdown(
        f"""
        <div class="ticket-card">
          <strong>{state["ticket_id"]}</strong><br>
          {state["ticket_content"]}
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric("类别", state.get("category") or "未知")
    with col2:
        render_metric("优先级", state.get("priority") or "未知")
    with col3:
        render_metric("同一工单历史", str(state.get("previous_ticket_count", 0)))
    with col4:
        render_metric("相似历史", str(state.get("similar_history_count", 0)))

    st.markdown("### 处理流程")
    render_step_list(state.get("steps", []))

    if state.get("workflow_status") == "waiting_duplicate_confirmation":
        st.markdown(
            """
            <div class="warning-box">
            系统检测到这个工单之前已经处理过。这里暂停，是为了避免重复发送回复或重复处理同一个问题。
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("查看同一工单历史", expanded=True):
            st.text(state.get("previous_ticket_summary") or "暂无同一工单历史。")

        col_continue, col_stop = st.columns(2)
        with col_continue:
            if st.button("继续处理这个重复工单", type="primary", use_container_width=True):
                with st.spinner("正在读取历史、检索知识库并生成草稿..."):
                    st.session_state["ticket_state"] = prepare_ticket_for_review(
                        state["ticket_id"],
                        continue_duplicate=True,
                    )
                st.rerun()

        with col_stop:
            if st.button("停止处理并记录日志", use_container_width=True):
                st.session_state["ticket_state"] = stop_duplicate_ticket(state)
                st.rerun()

        return

    if state.get("workflow_status") == "waiting_reply_review":
        st.markdown("### 回复草稿审核")
        draft_key = f"draft_reply_{state['ticket_id']}_{state.get('previous_ticket_count', 0)}"
        draft_reply = st.text_area(
            "回复草稿",
            value=state.get("draft_reply", ""),
            height=140,
            key=draft_key,
        )

        col_approve, col_reject = st.columns(2)
        with col_approve:
            if st.button("审核通过并发送", type="primary", use_container_width=True):
                st.session_state["ticket_state"] = finalize_reply_review(
                    state,
                    approved=True,
                    draft_reply=draft_reply,
                )
                st.rerun()

        with col_reject:
            if st.button("不发送，等待人工修改", use_container_width=True):
                st.session_state["ticket_state"] = finalize_reply_review(
                    state,
                    approved=False,
                    draft_reply=draft_reply,
                )
                st.rerun()

    if state.get("workflow_status") == "finished":
        st.markdown(
            f"""
            <div class="ok-box">
            当前流程已结束：{state.get("final_status", "无最终状态")}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("查看查询改写和知识库资料", expanded=False):
        st.markdown("**改写后的检索问题**")
        st.write(state.get("rewritten_query") or "本工单未触发知识库检索。")
        st.markdown("**知识库资料**")
        st.text(state.get("knowledge_context") or "无")

    with st.expander("查看历史记忆", expanded=False):
        st.markdown("**同一工单历史**")
        st.text(state.get("previous_ticket_summary") or "无")
        st.markdown("**相似历史工单**")
        st.text(state.get("history_context") or "无")


def render_recent_logs(logs: list) -> None:
    st.markdown("### 最近处理记录")

    if not logs:
        st.info("还没有处理日志。")
        return

    for index, log in enumerate(reversed(logs[-6:]), start=1):
        title = (
            f"{index}. {log.get('ticket_id', '未知工单')} | "
            f"{log.get('review_result', '未知审核')} | "
            f"{log.get('created_at', '未知时间')}"
        )
        with st.expander(title, expanded=index == 1):
            st.write("工单内容：", log.get("ticket_content", ""))
            st.write("类别/优先级：", log.get("category", ""), "/", log.get("priority", ""))
            st.write("是否使用知识库：", bool(log.get("used_knowledge_context")))
            st.write("同一工单历史次数：", log.get("previous_ticket_count", 0))
            st.write("重复工单确认：", log.get("duplicate_review_result") or "无")
            st.write("参考历史工单：", log.get("history_ticket_ids") or "无")
            st.write("回复草稿：", log.get("draft_reply", ""))
            st.write("最终状态：", log.get("final_status", ""))


init_state()
logs = load_logs()

with st.sidebar:
    st.markdown("## 工单设置")
    ticket_options = list(FAKE_TICKET_DATABASE.keys())
    selected_ticket_id = st.selectbox(
        "选择工单",
        ticket_options,
        index=ticket_options.index(st.session_state["selected_ticket_id"]),
    )
    st.session_state["selected_ticket_id"] = selected_ticket_id

    st.markdown("### 工单内容")
    st.caption(FAKE_TICKET_DATABASE[selected_ticket_id])

    if st.button("生成处理草稿", type="primary", use_container_width=True):
        with st.spinner("正在读取工单、检查历史并生成草稿..."):
            st.session_state["ticket_state"] = prepare_ticket_for_review(
                selected_ticket_id,
                continue_duplicate=False,
            )
        st.rerun()

    if st.button("清空当前页面状态", use_container_width=True):
        st.session_state["ticket_state"] = None
        st.rerun()

    st.divider()
    st.markdown("### 项目信息")
    st.write("处理日志：")
    st.code(str(LOG_FILE), language="text")
    st.write("当前能力：")
    st.write("- 工单分类")
    st.write("- 重复工单确认")
    st.write("- 历史记忆")
    st.write("- RAG 检索")
    st.write("- 人工审核")
    st.write("- 日志持久化")

st.markdown('<div class="main-title">企业工单处理 Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtle">把命令行工单 Agent 产品化：选择工单、生成草稿、查看记忆、人工审核、保存日志。</div>',
    unsafe_allow_html=True,
)

tab_process, tab_logs = st.tabs(["处理工单", "日志与观测"])

with tab_process:
    render_current_ticket(st.session_state["ticket_state"])

with tab_logs:
    render_log_summary(logs)
    render_recent_logs(logs)
