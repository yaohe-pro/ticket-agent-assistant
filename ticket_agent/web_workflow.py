from ticket_agent.classifier import classify_ticket_content
from ticket_agent.llm import call_deepseek
from ticket_agent.policy import decide_duplicate_policy
from ticket_agent.storage import (
    find_similar_ticket_logs,
    find_ticket_logs_by_id,
    save_ticket_process_log,
)
from ticket_agent.ticket_data import FAKE_TICKET_DATABASE
from ticket_agent.tools import choose_tool_for_ticket, run_registered_tool


def format_history_logs(logs: list) -> str:
    if not logs:
        return ""

    history_texts = []

    for index, log in enumerate(logs, start=1):
        history_text = f"""历史工单 {index}
工单编号：{log.get("ticket_id", "未知")}
工单内容：{log.get("ticket_content", "未知")}
类别：{log.get("category", "未知")}
优先级：{log.get("priority", "未知")}
历史回复：{log.get("draft_reply", "无")}
审核结果：{log.get("review_result", "未知")}
最终状态：{log.get("final_status", "未知")}"""
        history_texts.append(history_text)

    return "\n\n".join(history_texts)


def format_previous_ticket_logs(logs: list) -> str:
    if not logs:
        return ""

    summary_texts = []

    for index, log in enumerate(logs, start=1):
        summary_text = f"""同一工单历史 {index}
处理时间：{log.get("created_at", "未知")}
历史回复：{log.get("draft_reply", "无")}
审核结果：{log.get("review_result", "未知")}
最终状态：{log.get("final_status", "未知")}"""
        summary_texts.append(summary_text)

    return "\n\n".join(summary_texts)


def create_empty_state(ticket_id: str) -> dict:
    return {
        "ticket_id": ticket_id,
        "ticket_content": "",
        "category": "",
        "priority": "",
        "knowledge_context": "",
        "previous_ticket_summary": "",
        "previous_ticket_count": 0,
        "history_context": "",
        "similar_history_count": 0,
        "history_ticket_ids": [],
        "draft_reply": "",
        "tool_name": "",
        "tool_arguments": {},
        "tool_result": "",
        "tool_reason": "",
        "duplicate_review_result": "",
        "review_result": "",
        "final_status": "",
        "logged": False,
        "workflow_status": "created",
        "steps": [],
    }


def build_draft_prompt(state: dict) -> str:
    return f"""
你是一个企业客服工单助手。
请根据工单信息生成一段简洁、礼貌、可直接发给用户的回复草稿。

要求：
1. 不要编造处理结果。
2. 如果是高优先级问题，要体现会优先处理。
3. 回复不要超过 120 个中文字符。
4. 如果提供了知识库资料，必须先提炼资料中的直接答案，再补充处理说明。
5. 如果工单内容是在反馈“知识库没找到答案”，回复里也要先把资料中的答案告诉用户。
6. 不要只说“联系知识管理团队”或“我们会处理”，除非资料中确实没有答案。
7. 如果有历史工单参考，可以借鉴表达方式，但不要照抄，也不要把历史里的错误答案当事实。

【工单编号】
{state["ticket_id"]}

【工单内容】
{state["ticket_content"]}

【工单类别】
{state["category"]}

【优先级】
{state["priority"]}

【知识库资料】
{state["knowledge_context"] or "无"}

【同一工单历史】
{state["previous_ticket_summary"] or "无"}

【相似历史工单】
{state["history_context"] or "无"}

【工具调用结果】
{state["tool_result"] or "无"}

【写作方式】
如果知识库资料不为空，请按这个结构写：
您好，根据已有资料，资料中的直接答案。我们也会继续检查知识库展示情况，感谢您的反馈。

【回复草稿】
"""


def load_and_classify_ticket(ticket_id: str, custom_ticket_content: str = "") -> dict:
    state = create_empty_state(ticket_id)
    state["steps"].append("节点 1：读取工单内容")

    ticket_content = custom_ticket_content.strip() or FAKE_TICKET_DATABASE.get(
        ticket_id,
        "没有找到这个工单。",
    )
    previous_logs = find_ticket_logs_by_id(ticket_id)

    state["ticket_content"] = ticket_content
    state["previous_ticket_summary"] = format_previous_ticket_logs(previous_logs)
    state["previous_ticket_count"] = len(previous_logs)

    state["steps"].append("节点 2：判断工单类别和优先级")
    classification = classify_ticket_content(ticket_content)
    state["category"] = classification["category"]
    state["priority"] = classification["priority"]

    return state


def prepare_ticket_for_review(
    ticket_id: str,
    continue_duplicate: bool = False,
    custom_ticket_content: str = "",
) -> dict:
    state = load_and_classify_ticket(ticket_id, custom_ticket_content)

    state["steps"].append("节点 3：检查是否为重复工单")
    duplicate_policy = decide_duplicate_policy(state["previous_ticket_count"])

    if duplicate_policy["requires_confirmation"] and not continue_duplicate:
        state["duplicate_review_result"] = "waiting_for_duplicate_confirmation"
        state["final_status"] = "检测到重复工单，等待人工确认。"
        state["workflow_status"] = "waiting_duplicate_confirmation"
        return state

    if duplicate_policy["requires_confirmation"] and continue_duplicate:
        state["duplicate_review_result"] = "continued_after_duplicate_warning"
    else:
        state["duplicate_review_result"] = "not_needed"

    state["steps"].append("节点 4：读取相似历史工单")
    similar_logs = find_similar_ticket_logs(
        category=state["category"],
        priority=state["priority"],
        ticket_content=state["ticket_content"],
    )
    state["history_context"] = format_history_logs(similar_logs)
    state["similar_history_count"] = len(similar_logs)
    state["history_ticket_ids"] = [
        log.get("ticket_id", "未知") for log in similar_logs
    ]

    state["steps"].append("节点 5：选择并执行辅助工具")
    tool_call = choose_tool_for_ticket(state)
    state["tool_name"] = tool_call["tool_name"]
    state["tool_arguments"] = tool_call["tool_arguments"]
    state["tool_reason"] = tool_call["reason"]
    state["tool_result"] = run_registered_tool(
        state["tool_name"],
        state["tool_arguments"],
    )

    if state["category"] == "knowledge_question":
        state["steps"].append("节点 6A：检索企业知识库")
        from ticket_agent.rag import retrieve_knowledge

        retrieval_result = retrieve_knowledge(state["ticket_content"])
        state["knowledge_context"] = retrieval_result["context"]
        state["rewritten_query"] = retrieval_result["query"]
    else:
        state["rewritten_query"] = ""

    state["steps"].append("节点 7：让 DeepSeek 生成回复草稿")
    state["draft_reply"] = call_deepseek(build_draft_prompt(state))
    state["workflow_status"] = "waiting_reply_review"
    state["final_status"] = "回复草稿已生成，等待人工审核。"

    return state


def stop_duplicate_ticket(state: dict) -> dict:
    final_state = dict(state)
    final_state["steps"] = list(state.get("steps", [])) + [
        "节点 7B：重复工单停止处理",
        "节点 8：保存处理日志",
    ]
    final_state["duplicate_review_result"] = "stopped_by_duplicate_warning"
    final_state["review_result"] = "rejected"
    final_state["draft_reply"] = ""
    final_state["knowledge_context"] = ""
    final_state["history_context"] = ""
    final_state["similar_history_count"] = 0
    final_state["history_ticket_ids"] = []
    final_state["tool_name"] = ""
    final_state["tool_arguments"] = {}
    final_state["tool_result"] = ""
    final_state["tool_reason"] = ""
    final_state["final_status"] = "检测到重复工单，已停止处理。"
    final_state["workflow_status"] = "finished"
    save_ticket_process_log(final_state)
    final_state["logged"] = True

    return final_state


def finalize_reply_review(state: dict, approved: bool, draft_reply: str) -> dict:
    final_state = dict(state)
    final_state["steps"] = list(state.get("steps", []))
    final_state["draft_reply"] = draft_reply.strip()

    if approved:
        final_state["steps"].append("节点 7A：发送回复")
        final_state["review_result"] = "approved"
        final_state["final_status"] = "已发送回复给用户。"
    else:
        final_state["steps"].append("节点 7B：取消发送")
        final_state["review_result"] = "rejected"
        final_state["final_status"] = "回复草稿未发送，等待人工修改。"

    final_state["steps"].append("节点 8：保存处理日志")
    final_state["workflow_status"] = "finished"
    save_ticket_process_log(final_state)
    final_state["logged"] = True

    return final_state
