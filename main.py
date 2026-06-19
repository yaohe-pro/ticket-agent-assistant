from ticket_agent.agent import process_ticket
from ticket_agent.storage import LOG_FILE


if __name__ == "__main__":
    ticket_id = input("请输入工单编号，例如 T1001：")
    result = process_ticket(ticket_id)

    print("\n最终工单状态：")
    print("工单编号：", result["ticket_id"])
    print("工单内容：", result["ticket_content"])
    print("工单类别：", result["category"])
    print("优先级：", result["priority"])
    print("是否使用知识库资料：", bool(result["knowledge_context"]))
    print("同一工单历史次数：", result["previous_ticket_count"])
    print("重复工单确认结果：", result["duplicate_review_result"] or "无")
    print("相似历史工单数量：", result["similar_history_count"])
    print("参考历史工单：", result["history_ticket_ids"] or "无")
    print("回复草稿：", result["draft_reply"])
    print("人工审核：", result["review_result"])
    print("最终状态：", result["final_status"])
    print("是否已保存日志：", result["logged"])
    print("日志文件：", LOG_FILE)
