import json
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_FILE = DATA_DIR / "ticket_process_log.json"

MEMORY_KEYWORDS = [
    "产品",
    "介绍",
    "人群",
    "用户",
    "适合",
    "使用",
    "知识库",
    "打不开",
    "系统",
    "页面",
    "培训",
    "影响",
]


def load_logs() -> list:
    if not LOG_FILE.exists():
        return []

    with open(LOG_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_logs(logs: list) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(LOG_FILE, "w", encoding="utf-8") as file:
        json.dump(logs, file, ensure_ascii=False, indent=2)


def save_ticket_process_log(state: dict) -> None:
    logs = load_logs()

    log_record = {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ticket_id": state["ticket_id"],
        "ticket_content": state["ticket_content"],
        "category": state["category"],
        "priority": state["priority"],
        "used_knowledge_context": bool(state.get("knowledge_context")),
        "previous_ticket_count": state.get("previous_ticket_count", 0),
        "duplicate_review_result": state.get("duplicate_review_result", ""),
        "similar_history_count": state.get("similar_history_count", 0),
        "history_ticket_ids": state.get("history_ticket_ids", []),
        "used_history_context": bool(state.get("history_context")),
        "draft_reply": state["draft_reply"],
        "review_result": state["review_result"],
        "final_status": state["final_status"],
    }

    logs.append(log_record)
    save_logs(logs)


def find_ticket_logs_by_id(ticket_id: str, limit: int = 3) -> list:
    logs = load_logs()
    matched_logs = [
        log for log in reversed(logs) if log.get("ticket_id") == ticket_id
    ]

    return matched_logs[:limit]


def get_matching_keywords(ticket_content: str, log: dict) -> list:
    history_text = log.get("ticket_content", "") + log.get("draft_reply", "")
    matching_keywords = []

    for keyword in MEMORY_KEYWORDS:
        if keyword in ticket_content and keyword in history_text:
            matching_keywords.append(keyword)

    return matching_keywords


def score_log_similarity(ticket_content: str, log: dict) -> int:
    return len(get_matching_keywords(ticket_content, log))


def describe_similar_ticket_logs(
    category: str,
    priority: str,
    ticket_content: str = "",
    limit: int = 2,
) -> list:
    logs = load_logs()
    memory_records = []

    for log in reversed(logs):
        if log.get("category") != category:
            continue

        if priority == "high" and log.get("priority") != "high":
            continue

        matching_keywords = get_matching_keywords(ticket_content, log)
        memory_records.append(
            {
                "score": len(matching_keywords),
                "matching_keywords": matching_keywords,
                "log": log,
            }
        )

    memory_records.sort(key=lambda item: item["score"], reverse=True)

    positive_records = [record for record in memory_records if record["score"] > 0]

    if positive_records:
        return positive_records[:limit]

    return memory_records[:limit]


def find_similar_ticket_logs(
    category: str,
    priority: str,
    ticket_content: str = "",
    limit: int = 2,
) -> list:
    memory_records = describe_similar_ticket_logs(
        category=category,
        priority=priority,
        ticket_content=ticket_content,
        limit=limit,
    )

    return [record["log"] for record in memory_records]
