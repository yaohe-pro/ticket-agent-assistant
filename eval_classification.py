import json
from datetime import datetime
from pathlib import Path

from ticket_agent.classifier import classify_ticket_content
from ticket_agent.ticket_data import FAKE_TICKET_DATABASE


PROJECT_ROOT = Path(__file__).resolve().parent
REPORT_FILE = PROJECT_ROOT / "data" / "classification_eval_report.json"


EVAL_CASES = [
    {
        "ticket_id": "T1001",
        "expected_category": "knowledge_question",
        "expected_priority": "medium",
    },
    {
        "ticket_id": "T1002",
        "expected_category": "knowledge_question",
        "expected_priority": "medium",
    },
    {
        "ticket_id": "T1003",
        "expected_category": "system_issue",
        "expected_priority": "high",
    },
    {
        "ticket_id": "T1004",
        "expected_category": "account_issue",
        "expected_priority": "high",
    },
    {
        "ticket_id": "T1005",
        "expected_category": "billing_question",
        "expected_priority": "medium",
    },
    {
        "ticket_id": "T1006",
        "expected_category": "schedule_question",
        "expected_priority": "high",
    },
    {
        "ticket_id": "T1007",
        "expected_category": "complaint",
        "expected_priority": "high",
    },
    {
        "ticket_id": "T1009",
        "expected_category": "billing_question",
        "expected_priority": "high",
    },
    {
        "ticket_id": "T1012",
        "expected_category": "system_issue",
        "expected_priority": "medium",
    },
]


def evaluate_case(eval_case: dict) -> dict:
    ticket_id = eval_case["ticket_id"]
    ticket_content = FAKE_TICKET_DATABASE[ticket_id]

    result = classify_ticket_content(ticket_content)

    category_correct = result["category"] == eval_case["expected_category"]
    priority_correct = result["priority"] == eval_case["expected_priority"]
    is_correct = category_correct and priority_correct

    return {
        "ticket_id": ticket_id,
        "ticket_content": ticket_content,
        "expected_category": eval_case["expected_category"],
        "actual_category": result["category"],
        "expected_priority": eval_case["expected_priority"],
        "actual_priority": result["priority"],
        "is_correct": is_correct,
    }


def run_eval() -> None:
    records = [evaluate_case(eval_case) for eval_case in EVAL_CASES]
    correct_count = sum(1 for record in records if record["is_correct"])
    total_count = len(records)
    accuracy = correct_count / total_count
    report = {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_count": total_count,
        "correct_count": correct_count,
        "accuracy": accuracy,
        "records": records,
    }

    print("工单分类评估")
    print("=" * 30)

    for record in records:
        print("工单编号：", record["ticket_id"])
        print("工单内容：", record["ticket_content"])
        print("期望类别：", record["expected_category"])
        print("实际类别：", record["actual_category"])
        print("期望优先级：", record["expected_priority"])
        print("实际优先级：", record["actual_priority"])
        print("是否正确：", record["is_correct"])
        print("-" * 30)

    print("评估总数：", total_count)
    print("正确数量：", correct_count)
    print("准确率：", accuracy)
    save_report(report)
    print("评估报告：", REPORT_FILE)


def save_report(report: dict) -> None:
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(REPORT_FILE, "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    run_eval()
