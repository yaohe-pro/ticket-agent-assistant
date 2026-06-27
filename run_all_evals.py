import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
SUMMARY_FILE = DATA_DIR / "evaluation_summary.json"


EVAL_SCRIPTS = [
    {
        "name": "classification",
        "title": "工单分类和优先级评估",
        "script": PROJECT_ROOT / "eval_classification.py",
        "report": DATA_DIR / "classification_eval_report.json",
    },
    {
        "name": "duplicate_policy",
        "title": "重复工单策略评估",
        "script": PROJECT_ROOT / "eval_duplicate_policy.py",
        "report": DATA_DIR / "duplicate_policy_eval_report.json",
    },
    {
        "name": "memory_retrieval",
        "title": "历史记忆检索评估",
        "script": PROJECT_ROOT / "eval_memory_retrieval.py",
        "report": DATA_DIR / "memory_retrieval_eval_report.json",
    },
    {
        "name": "tool_routing",
        "title": "工具路由评估",
        "script": PROJECT_ROOT / "eval_tool_routing.py",
        "report": DATA_DIR / "tool_routing_eval_report.json",
    },
]


def run_eval_script(eval_script: dict) -> None:
    print("=" * 40)
    print("开始运行：", eval_script["title"])
    print("=" * 40)
    sys.stdout.flush()

    subprocess.run(
        [sys.executable, str(eval_script["script"])],
        cwd=PROJECT_ROOT,
        check=True,
    )


def load_report(report_path: Path) -> dict:
    with open(report_path, "r", encoding="utf-8") as file:
        return json.load(file)


def build_summary() -> dict:
    reports = []

    for eval_script in EVAL_SCRIPTS:
        report = load_report(eval_script["report"])
        reports.append(
            {
                "name": eval_script["name"],
                "title": eval_script["title"],
                "report_file": str(eval_script["report"]),
                "total_count": report["total_count"],
                "correct_count": report["correct_count"],
                "accuracy": report["accuracy"],
            }
        )

    all_passed = all(report["accuracy"] == 1.0 for report in reports)

    return {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "all_passed": all_passed,
        "report_count": len(reports),
        "reports": reports,
    }


def save_summary(summary: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(SUMMARY_FILE, "w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)


def print_summary(summary: dict) -> None:
    print("=" * 40)
    print("评估总览")
    print("=" * 40)
    print("是否全部通过：", summary["all_passed"])

    for report in summary["reports"]:
        print("-" * 40)
        print("评估项：", report["title"])
        print("测试数量：", report["total_count"])
        print("正确数量：", report["correct_count"])
        print("准确率：", report["accuracy"])

    print("-" * 40)
    print("总览报告：", SUMMARY_FILE)


def main() -> None:
    for eval_script in EVAL_SCRIPTS:
        run_eval_script(eval_script)

    summary = build_summary()
    save_summary(summary)
    print_summary(summary)


if __name__ == "__main__":
    main()
