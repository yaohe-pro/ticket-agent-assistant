import json
from datetime import datetime
from pathlib import Path

from ticket_agent.classifier import classify_ticket_content
from ticket_agent.tools import choose_tool_for_ticket
from ticket_agent.ticket_data import FAKE_TICKET_DATABASE


PROJECT_ROOT = Path(__file__).resolve().parent
REPORT_FILE = PROJECT_ROOT / "data" / "tool_routing_eval_report.json"


EVAL_CASES = [
    {
        "ticket_id": "T1003",
        "expected_tool": "suggest_owner_team",
    },
    {
        "ticket_id": "T1005",
        "expected_tool": "suggest_owner_team",
    },
    {
        "ticket_id": "T1001",
        "expected_tool": "search_ticket_status",
    },
]


def evaluate_case(eval_case: dict) -> dict:
    ticket_id = eval_case["ticket_id"]
    ticket_content = FAKE_TICKET_DATABASE[ticket_id]
    classification = classify_ticket_content(ticket_content)
    state = {
        "ticket_id": ticket_id,
        "ticket_content": ticket_content,
        "category": classification["category"],
        "priority": classification["priority"],
    }
    tool_call = choose_tool_for_ticket(state)
    actual_tool = tool_call["tool_name"]

    return {
        "ticket_id": ticket_id,
        "ticket_content": ticket_content,
        "category": classification["category"],
        "priority": classification["priority"],
        "expected_tool": eval_case["expected_tool"],
        "actual_tool": actual_tool,
        "is_correct": actual_tool == eval_case["expected_tool"],
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

    print("工具路由评估")
    print("=" * 30)

    for record in records:
        print("工单编号：", record["ticket_id"])
        print("工单内容：", record["ticket_content"])
        print("类别：", record["category"])
        print("优先级：", record["priority"])
        print("期望工具：", record["expected_tool"])
        print("实际工具：", record["actual_tool"])
        print("是否正确：", record["is_correct"])
        print("-" * 30)

    print("评估总数：", total_count)
    print("正确数量：", correct_count)
    print("准确率：", accuracy)
    save_report(report)
    print("评估报告：", REPORT_FILE)


if __name__ == "__main__":
    run_eval()
