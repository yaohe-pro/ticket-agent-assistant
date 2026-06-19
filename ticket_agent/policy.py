def decide_duplicate_policy(previous_ticket_count: int) -> dict:
    if previous_ticket_count <= 0:
        return {
            "requires_confirmation": False,
            "reason": "没有同一工单历史，可以继续正常处理。",
        }

    return {
        "requires_confirmation": True,
        "reason": "检测到同一工单历史，需要人工确认是否继续处理。",
    }
