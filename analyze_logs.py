from collections import Counter

from ticket_agent.storage import LOG_FILE, load_logs


def print_counter(title: str, counter: Counter) -> None:
    print(title)

    if not counter:
        print("- 暂无数据")
        return

    for key, count in counter.items():
        print(f"- {key}: {count}")


def analyze_logs(logs: list) -> None:
    total_count = len(logs)
    review_counter = Counter(log["review_result"] for log in logs)
    category_counter = Counter(log["category"] for log in logs)
    priority_counter = Counter(log["priority"] for log in logs)
    knowledge_counter = Counter(
        "used_rag" if log.get("used_knowledge_context") else "no_rag"
        for log in logs
    )
    history_counter = Counter(
        "used_history" if log.get("used_history_context") else "no_history"
        for log in logs
    )
    previous_ticket_counter = Counter(
        "has_previous_ticket_history"
        if log.get("previous_ticket_count", 0) > 0
        else "no_previous_ticket_history"
        for log in logs
    )
    duplicate_review_counter = Counter(
        log.get("duplicate_review_result") or "no_duplicate_review"
        for log in logs
    )
    referenced_history_counter = Counter(
        history_ticket_id
        for log in logs
        for history_ticket_id in log.get("history_ticket_ids", [])
    )
    status_counter = Counter(log["final_status"] for log in logs)

    print("工单处理日志分析")
    print("=" * 30)
    print("日志文件：", LOG_FILE)
    print("处理总数：", total_count)
    print()

    print_counter("人工审核统计：", review_counter)
    print()
    print_counter("工单类别统计：", category_counter)
    print()
    print_counter("优先级统计：", priority_counter)
    print()
    print_counter("知识库使用统计：", knowledge_counter)
    print()
    print_counter("历史记忆使用统计：", history_counter)
    print()
    print_counter("同一工单历史统计：", previous_ticket_counter)
    print()
    print_counter("重复工单确认统计：", duplicate_review_counter)
    print()
    print_counter("被参考的历史工单统计：", referenced_history_counter)
    print()
    print_counter("最终状态统计：", status_counter)


if __name__ == "__main__":
    logs = load_logs()

    if not logs:
        print("还没有工单处理日志，请先运行 python main.py。")
    else:
        analyze_logs(logs)
