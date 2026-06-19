def classify_ticket_content(content: str) -> dict:
    if "打不开" in content or "影响" in content:
        category = "system_issue"
        priority = "high"
    elif "产品" in content or "人群" in content:
        category = "knowledge_question"
        priority = "medium"
    else:
        category = "unknown"
        priority = "low"

    return {
        "category": category,
        "priority": priority,
    }
