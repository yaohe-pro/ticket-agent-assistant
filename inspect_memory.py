from ticket_agent.classifier import classify_ticket_content
from ticket_agent.storage import describe_similar_ticket_logs
from ticket_agent.ticket_data import FAKE_TICKET_DATABASE


def inspect_memory(ticket_id: str) -> None:
    ticket_content = FAKE_TICKET_DATABASE.get(ticket_id)

    if ticket_content is None:
        print("没有找到这个工单。")
        return

    classification = classify_ticket_content(ticket_content)

    memory_records = describe_similar_ticket_logs(
        category=classification["category"],
        priority=classification["priority"],
        ticket_content=ticket_content,
    )

    print("当前工单记忆检查")
    print("=" * 30)
    print("工单编号：", ticket_id)
    print("工单内容：", ticket_content)
    print("工单类别：", classification["category"])
    print("优先级：", classification["priority"])
    print("匹配到的历史数量：", len(memory_records))

    if not memory_records:
        print("暂时没有可参考的历史工单。")
        return

    for index, record in enumerate(memory_records, start=1):
        log = record["log"]
        print("=" * 30)
        print("历史记录：", index)
        print("相似分数：", record["score"])
        print("匹配关键词：", record["matching_keywords"] or "无")
        print("历史工单编号：", log.get("ticket_id"))
        print("历史创建时间：", log.get("created_at", "未知"))
        print("历史工单内容：", log.get("ticket_content"))
        print("历史回复草稿：", log.get("draft_reply"))
        print("历史审核结果：", log.get("review_result"))
        print("历史最终状态：", log.get("final_status"))


if __name__ == "__main__":
    user_ticket_id = input("请输入工单编号，例如 T1001：").strip()
    inspect_memory(user_ticket_id)
