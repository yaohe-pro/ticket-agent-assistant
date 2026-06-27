import json
from datetime import datetime
from pathlib import Path

from ticket_agent.storage import find_similar_ticket_logs


PROJECT_ROOT = Path(__file__).resolve().parent
REPORT_FILE = PROJECT_ROOT / "data" / "memory_retrieval_eval_report.json"


EVAL_CASES = [
    {
        "name": "产品类知识工单历史记忆",
        "category": "knowledge_question",
        "priority": "medium",
        "ticket_content": "用户反馈：知识库问答没有找到产品介绍，希望尽快处理。",
        "min_expected_count": 1,
        "expected_keyword": "产品",
    },
    {
        "name": "高优先级系统问题历史记忆",
        "category": "system_issue",
        "priority": "high",
        "ticket_content": "用户反馈：系统页面打不开，影响今天的培训课程。",
        "min_expected_count": 1,
        "expected_keyword": "打不开",
    },
    {
        "name": "支付权限类历史记忆",
        "category": "billing_question",
        "priority": "high",
        "ticket_content": "用户反馈：支付成功后没有开通课程权限。",
        "min_expected_count": 1,
        "expected_keyword": "支付",
    },
]


def evaluate_case(eval_case: dict) -> dict:
    similar_logs = find_similar_ticket_logs(
        category=eval_case["category"],
        priority=eval_case["priority"],
        ticket_content=eval_case["ticket_content"],
    )

    category_correct = all(
        log.get("category") == eval_case["category"] for log in similar_logs
    )
    priority_correct = all(
        log.get("priority") == eval_case["priority"] for log in similar_logs
    )
    count_correct = len(similar_logs) >= eval_case["min_expected_count"]
    keyword_correct = any(
        eval_case["expected_keyword"] in log.get("ticket_content", "")
        or eval_case["expected_keyword"] in log.get("draft_reply", "")
        for log in similar_logs
    )
    is_correct = category_correct and priority_correct and count_correct and keyword_correct

    return {
        "name": eval_case["name"],
        "category": eval_case["category"],
        "priority": eval_case["priority"],
        "ticket_content": eval_case["ticket_content"],
        "min_expected_count": eval_case["min_expected_count"],
        "expected_keyword": eval_case["expected_keyword"],
        "actual_count": len(similar_logs),
        "retrieved_ticket_ids": [log.get("ticket_id") for log in similar_logs],
        "category_correct": category_correct,
        "priority_correct": priority_correct,
        "count_correct": count_correct,
        "keyword_correct": keyword_correct,
        "is_correct": is_correct,
    }


def save_report(report: dict) -> None:
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(REPORT_FILE, "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)


def run_eval() -> None:
    records = [evaluate_case(eval_case) for eval_case in EVAL_CASES]
    correct_count = sum(1 for record in records if record["is_correct"])
    total_count = len(records)
    accuracy = correct_count / total_count if total_count else 0

    report = {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_count": total_count,
        "correct_count": correct_count,
        "accuracy": accuracy,
        "records": records,
    }

    print("历史记忆检索评估")
    print("=" * 30)

    for record in records:
        print("测试项：", record["name"])
        print("当前工单内容：", record["ticket_content"])
        print("目标类别：", record["category"])
        print("目标优先级：", record["priority"])
        print("期望关键词：", record["expected_keyword"])
        print("期望最少命中数量：", record["min_expected_count"])
        print("实际命中数量：", record["actual_count"])
        print("命中的工单编号：", record["retrieved_ticket_ids"])
        print("是否正确：", record["is_correct"])
        print("-" * 30)

    print("评估总数：", total_count)
    print("正确数量：", correct_count)
    print("准确率：", accuracy)
    save_report(report)
    print("评估报告：", REPORT_FILE)


if __name__ == "__main__":
    run_eval()
