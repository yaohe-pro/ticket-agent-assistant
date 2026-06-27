from ticket_agent.ticket_data import TICKET_STATUS_DATABASE


def search_ticket_status(ticket_id: str) -> str:
    return TICKET_STATUS_DATABASE.get(ticket_id, f"没有找到工单 {ticket_id}。")


def estimate_processing_cost(ticket_count: int, price_per_ticket: float = 0.002) -> str:
    total_cost = ticket_count * price_per_ticket
    return f"预计处理 {ticket_count} 个工单的模型调用成本约为 {total_cost:.2f} 元。"


def suggest_owner_team(category: str, priority: str) -> str:
    owner_map = {
        "knowledge_question": "知识库运营团队",
        "system_issue": "技术支持团队",
        "account_issue": "账号支持团队",
        "billing_question": "商务/财务团队",
        "schedule_question": "教务运营团队",
        "complaint": "客服主管或人工升级队列",
    }
    owner_team = owner_map.get(category, "人工客服团队")

    if priority == "high":
        return f"建议转交：{owner_team}。该工单为高优先级，需要优先跟进。"

    return f"建议转交：{owner_team}。"


TOOL_REGISTRY = {
    "search_ticket_status": {
        "description": "查询模拟工单的当前处理状态。",
        "function": search_ticket_status,
    },
    "estimate_processing_cost": {
        "description": "根据工单数量估算模型调用成本。",
        "function": estimate_processing_cost,
    },
    "suggest_owner_team": {
        "description": "根据工单类别和优先级建议负责团队。",
        "function": suggest_owner_team,
    },
}


def choose_tool_for_ticket(state: dict) -> dict:
    if state.get("priority") == "high":
        return {
            "tool_name": "suggest_owner_team",
            "tool_arguments": {
                "category": state.get("category", "unknown"),
                "priority": state.get("priority", "low"),
            },
            "reason": "高优先级工单需要先建议负责团队。",
        }

    if state.get("category") in {"billing_question", "account_issue", "schedule_question"}:
        return {
            "tool_name": "suggest_owner_team",
            "tool_arguments": {
                "category": state.get("category", "unknown"),
                "priority": state.get("priority", "low"),
            },
            "reason": "该类别适合先分派到明确业务团队。",
        }

    return {
        "tool_name": "search_ticket_status",
        "tool_arguments": {
            "ticket_id": state.get("ticket_id", ""),
        },
        "reason": "普通工单先查询当前处理状态。",
    }


def run_registered_tool(tool_name: str, tool_arguments: dict) -> str:
    tool = TOOL_REGISTRY.get(tool_name)

    if not tool:
        return "没有找到可执行工具。"

    return tool["function"](**tool_arguments)
