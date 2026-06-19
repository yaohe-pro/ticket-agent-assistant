from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from ticket_agent.classifier import classify_ticket_content
from ticket_agent.llm import call_deepseek
from ticket_agent.policy import decide_duplicate_policy
from ticket_agent.rag import retrieve_knowledge
from ticket_agent.storage import (
    find_similar_ticket_logs,
    find_ticket_logs_by_id,
    save_ticket_process_log,
)
from ticket_agent.ticket_data import FAKE_TICKET_DATABASE


class TicketState(TypedDict):
    ticket_id: str
    ticket_content: str
    category: str
    priority: str
    knowledge_context: str
    previous_ticket_summary: str
    previous_ticket_count: int
    history_context: str
    similar_history_count: int
    history_ticket_ids: list
    draft_reply: str
    duplicate_review_result: str
    review_result: str
    final_status: str
    logged: bool


def load_ticket_node(state: TicketState) -> TicketState:
    print("节点 1：读取工单内容")

    ticket_id = state["ticket_id"]
    ticket_content = FAKE_TICKET_DATABASE.get(ticket_id, "没有找到这个工单。")
    previous_logs = find_ticket_logs_by_id(ticket_id)
    previous_ticket_summary = format_previous_ticket_logs(previous_logs)

    print("同一工单历史次数：", len(previous_logs))

    return {
        "ticket_id": ticket_id,
        "ticket_content": ticket_content,
        "category": "",
        "priority": "",
        "knowledge_context": "",
        "previous_ticket_summary": previous_ticket_summary,
        "previous_ticket_count": len(previous_logs),
        "history_context": "",
        "similar_history_count": 0,
        "history_ticket_ids": [],
        "draft_reply": "",
        "duplicate_review_result": "",
        "review_result": "",
        "final_status": "",
        "logged": False,
    }


def classify_ticket_node(state: TicketState) -> TicketState:
    print("节点 2：判断工单类别和优先级")

    content = state["ticket_content"]
    classification = classify_ticket_content(content)

    return {
        "ticket_id": state["ticket_id"],
        "ticket_content": content,
        "category": classification["category"],
        "priority": classification["priority"],
        "knowledge_context": "",
        "previous_ticket_summary": state["previous_ticket_summary"],
        "previous_ticket_count": state["previous_ticket_count"],
        "history_context": "",
        "similar_history_count": 0,
        "history_ticket_ids": [],
        "draft_reply": "",
        "duplicate_review_result": "",
        "review_result": "",
        "final_status": "",
        "logged": False,
    }


def route_after_classification(state: TicketState) -> Literal[
    "knowledge_question",
    "other",
]:
    if state["category"] == "knowledge_question":
        return "knowledge_question"

    return "other"


def duplicate_check_node(state: TicketState) -> TicketState:
    print("节点 3：检查是否为重复工单")

    duplicate_policy = decide_duplicate_policy(state["previous_ticket_count"])

    if not duplicate_policy["requires_confirmation"]:
        print(duplicate_policy["reason"])
        duplicate_review_result = "not_needed"
        review_result = ""
        final_status = ""
    else:
        print("\n注意：这个工单之前已经处理过。")
        print("处理策略：", duplicate_policy["reason"])
        print("同一工单历史次数：", state["previous_ticket_count"])
        print("最近处理记录：")
        print(state["previous_ticket_summary"])

        continue_input = input(
            "是否仍然继续处理这个重复工单？请输入 yes 或 no："
        ).strip().lower()

        if continue_input == "yes":
            duplicate_review_result = "continued_after_duplicate_warning"
            review_result = ""
            final_status = ""
        else:
            duplicate_review_result = "stopped_by_duplicate_warning"
            review_result = "rejected"
            final_status = "检测到重复工单，已停止处理。"

    return {
        "ticket_id": state["ticket_id"],
        "ticket_content": state["ticket_content"],
        "category": state["category"],
        "priority": state["priority"],
        "knowledge_context": state["knowledge_context"],
        "previous_ticket_summary": state["previous_ticket_summary"],
        "previous_ticket_count": state["previous_ticket_count"],
        "history_context": state["history_context"],
        "similar_history_count": state["similar_history_count"],
        "history_ticket_ids": state["history_ticket_ids"],
        "draft_reply": state["draft_reply"],
        "duplicate_review_result": duplicate_review_result,
        "review_result": review_result,
        "final_status": final_status,
        "logged": False,
    }


def route_after_duplicate_check(state: TicketState) -> Literal["continue", "stop"]:
    if state["duplicate_review_result"] == "stopped_by_duplicate_warning":
        return "stop"

    return "continue"


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


def retrieve_history_node(state: TicketState) -> TicketState:
    print("节点 4：读取相似历史工单")

    similar_logs = find_similar_ticket_logs(
        category=state["category"],
        priority=state["priority"],
        ticket_content=state["ticket_content"],
    )
    history_context = format_history_logs(similar_logs)
    history_ticket_ids = [log.get("ticket_id", "未知") for log in similar_logs]

    print("找到历史工单数量：", len(similar_logs))
    print("参考历史工单：", history_ticket_ids if history_ticket_ids else "无")

    return {
        "ticket_id": state["ticket_id"],
        "ticket_content": state["ticket_content"],
        "category": state["category"],
        "priority": state["priority"],
        "knowledge_context": "",
        "previous_ticket_summary": state["previous_ticket_summary"],
        "previous_ticket_count": state["previous_ticket_count"],
        "history_context": history_context,
        "similar_history_count": len(similar_logs),
        "history_ticket_ids": history_ticket_ids,
        "draft_reply": "",
        "duplicate_review_result": state["duplicate_review_result"],
        "review_result": "",
        "final_status": "",
        "logged": False,
    }


def retrieve_knowledge_node(state: TicketState) -> TicketState:
    print("节点 5A：检索企业知识库")

    retrieval_result = retrieve_knowledge(state["ticket_content"])
    print("改写后的检索问题：", retrieval_result["query"])

    return {
        "ticket_id": state["ticket_id"],
        "ticket_content": state["ticket_content"],
        "category": state["category"],
        "priority": state["priority"],
        "knowledge_context": retrieval_result["context"],
        "previous_ticket_summary": state["previous_ticket_summary"],
        "previous_ticket_count": state["previous_ticket_count"],
        "history_context": state["history_context"],
        "similar_history_count": state["similar_history_count"],
        "history_ticket_ids": state["history_ticket_ids"],
        "draft_reply": "",
        "duplicate_review_result": state["duplicate_review_result"],
        "review_result": "",
        "final_status": "",
        "logged": False,
    }


def draft_reply_with_llm_node(state: TicketState) -> TicketState:
    print("节点 6：让 DeepSeek 生成回复草稿")

    prompt = f"""
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

【写作方式】
如果知识库资料不为空，请按这个结构写：
您好，根据已有资料，资料中的直接答案。我们也会继续检查知识库展示情况，感谢您的反馈。

【回复草稿】
"""

    draft_reply = call_deepseek(prompt)

    return {
        "ticket_id": state["ticket_id"],
        "ticket_content": state["ticket_content"],
        "category": state["category"],
        "priority": state["priority"],
        "knowledge_context": state["knowledge_context"],
        "previous_ticket_summary": state["previous_ticket_summary"],
        "previous_ticket_count": state["previous_ticket_count"],
        "history_context": state["history_context"],
        "similar_history_count": state["similar_history_count"],
        "history_ticket_ids": state["history_ticket_ids"],
        "draft_reply": draft_reply,
        "duplicate_review_result": state["duplicate_review_result"],
        "review_result": "",
        "final_status": "",
        "logged": False,
    }


def human_review_node(state: TicketState) -> TicketState:
    print("节点 7：人工确认回复草稿")

    print("\n请审核下面的回复草稿：")
    print(state["draft_reply"])

    user_input = input("是否发送给用户？请输入 yes 或 no：").strip().lower()

    if user_input == "yes":
        review_result = "approved"
    else:
        review_result = "rejected"

    return {
        "ticket_id": state["ticket_id"],
        "ticket_content": state["ticket_content"],
        "category": state["category"],
        "priority": state["priority"],
        "knowledge_context": state["knowledge_context"],
        "previous_ticket_summary": state["previous_ticket_summary"],
        "previous_ticket_count": state["previous_ticket_count"],
        "history_context": state["history_context"],
        "similar_history_count": state["similar_history_count"],
        "history_ticket_ids": state["history_ticket_ids"],
        "draft_reply": state["draft_reply"],
        "duplicate_review_result": state["duplicate_review_result"],
        "review_result": review_result,
        "final_status": "",
        "logged": False,
    }


def route_after_review(state: TicketState) -> Literal["approved", "rejected"]:
    return state["review_result"]


def send_reply_node(state: TicketState) -> TicketState:
    print("节点 8A：发送回复")

    return {
        "ticket_id": state["ticket_id"],
        "ticket_content": state["ticket_content"],
        "category": state["category"],
        "priority": state["priority"],
        "knowledge_context": state["knowledge_context"],
        "previous_ticket_summary": state["previous_ticket_summary"],
        "previous_ticket_count": state["previous_ticket_count"],
        "history_context": state["history_context"],
        "similar_history_count": state["similar_history_count"],
        "history_ticket_ids": state["history_ticket_ids"],
        "draft_reply": state["draft_reply"],
        "duplicate_review_result": state["duplicate_review_result"],
        "review_result": state["review_result"],
        "final_status": "已发送回复给用户。",
        "logged": False,
    }


def stop_reply_node(state: TicketState) -> TicketState:
    print("节点 8B：取消发送")

    return {
        "ticket_id": state["ticket_id"],
        "ticket_content": state["ticket_content"],
        "category": state["category"],
        "priority": state["priority"],
        "knowledge_context": state["knowledge_context"],
        "previous_ticket_summary": state["previous_ticket_summary"],
        "previous_ticket_count": state["previous_ticket_count"],
        "history_context": state["history_context"],
        "similar_history_count": state["similar_history_count"],
        "history_ticket_ids": state["history_ticket_ids"],
        "draft_reply": state["draft_reply"],
        "duplicate_review_result": state["duplicate_review_result"],
        "review_result": state["review_result"],
        "final_status": state["final_status"] or "回复草稿未发送，等待人工修改。",
        "logged": False,
    }


def save_process_log_node(state: TicketState) -> TicketState:
    print("节点 9：保存处理日志")

    save_ticket_process_log(dict(state))

    return {
        "ticket_id": state["ticket_id"],
        "ticket_content": state["ticket_content"],
        "category": state["category"],
        "priority": state["priority"],
        "knowledge_context": state["knowledge_context"],
        "previous_ticket_summary": state["previous_ticket_summary"],
        "previous_ticket_count": state["previous_ticket_count"],
        "history_context": state["history_context"],
        "similar_history_count": state["similar_history_count"],
        "history_ticket_ids": state["history_ticket_ids"],
        "draft_reply": state["draft_reply"],
        "duplicate_review_result": state["duplicate_review_result"],
        "review_result": state["review_result"],
        "final_status": state["final_status"],
        "logged": True,
    }


def build_graph():
    graph_builder = StateGraph(TicketState)

    graph_builder.add_node("load_ticket", load_ticket_node)
    graph_builder.add_node("classify_ticket", classify_ticket_node)
    graph_builder.add_node("duplicate_check", duplicate_check_node)
    graph_builder.add_node("retrieve_history", retrieve_history_node)
    graph_builder.add_node("retrieve_knowledge", retrieve_knowledge_node)
    graph_builder.add_node("draft_reply_with_llm", draft_reply_with_llm_node)
    graph_builder.add_node("human_review", human_review_node)
    graph_builder.add_node("send_reply", send_reply_node)
    graph_builder.add_node("stop_reply", stop_reply_node)
    graph_builder.add_node("save_process_log", save_process_log_node)

    graph_builder.add_edge(START, "load_ticket")
    graph_builder.add_edge("load_ticket", "classify_ticket")
    graph_builder.add_edge("classify_ticket", "duplicate_check")
    graph_builder.add_conditional_edges(
        "duplicate_check",
        route_after_duplicate_check,
        {
            "continue": "retrieve_history",
            "stop": "save_process_log",
        },
    )
    graph_builder.add_conditional_edges(
        "retrieve_history",
        route_after_classification,
        {
            "knowledge_question": "retrieve_knowledge",
            "other": "draft_reply_with_llm",
        },
    )
    graph_builder.add_edge("retrieve_knowledge", "draft_reply_with_llm")
    graph_builder.add_edge("draft_reply_with_llm", "human_review")
    graph_builder.add_conditional_edges(
        "human_review",
        route_after_review,
        {
            "approved": "send_reply",
            "rejected": "stop_reply",
        },
    )
    graph_builder.add_edge("send_reply", "save_process_log")
    graph_builder.add_edge("stop_reply", "save_process_log")
    graph_builder.add_edge("save_process_log", END)

    return graph_builder.compile()


def process_ticket(ticket_id: str) -> TicketState:
    graph = build_graph()

    return graph.invoke(
        {
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
            "duplicate_review_result": "",
            "review_result": "",
            "final_status": "",
            "logged": False,
        }
    )
