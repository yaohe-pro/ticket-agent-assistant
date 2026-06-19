import json
from datetime import datetime
from pathlib import Path

from ticket_agent.policy import decide_duplicate_policy


PROJECT_ROOT = Path(__file__).resolve().parent
REPORT_FILE = PROJECT_ROOT / "data" / "duplicate_policy_eval_report.json"


EVAL_CASES = [
    {
        "name": "没有同一工单历史",
        "previous_ticket_count": 0,
        "expected_requires_confirmation": False,
    },
    {
        "name": "有 1 次同一工单历史",
        "previous_ticket_count": 1,
        "expected_requires_confirmation": True,
    },
    {
        "name": "有多次同一工单历史",
        "previous_ticket_count": 3,
        "expected_requires_confirmation": True,
    },
]


def evaluate_case(eval_case: dict) -> dict:
    policy = decide_duplicate_policy(eval_case["previous_ticket_count"])
    is_correct = (
        policy["requires_confirmation"]
        == eval_case["expected_requires_confirmation"]
    )

    return {
        "name": eval_case["name"],
        "previous_ticket_count": eval_case["previous_ticket_count"],
        "expected_requires_confirmation": eval_case[
            "expected_requires_confirmation"
        ],
        "actual_requires_confirmation": policy["requires_confirmation"],
        "reason": policy["reason"],
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

    print("重复工单策略评估")
    print("=" * 30)

    for record in records:
        print("测试项：", record["name"])
        print("同一工单历史次数：", record["previous_ticket_count"])
        print("期望需要确认：", record["expected_requires_confirmation"])
        print("实际需要确认：", record["actual_requires_confirmation"])
        print("策略原因：", record["reason"])
        print("是否正确：", record["is_correct"])
        print("-" * 30)

    print("评估总数：", total_count)
    print("正确数量：", correct_count)
    print("准确率：", accuracy)
    save_report(report)
    print("评估报告：", REPORT_FILE)


if __name__ == "__main__":
    run_eval()
