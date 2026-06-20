"""
ball_summary_report.py - 接球任务汇总统计分析报告

汇总所有难度级别的测试结果，生成综合分析报告。
"""
from __future__ import annotations

import json
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class DifficultyStats:
    """难度级别统计"""
    difficulty: str
    total_trials: int = 0
    successful_catches: int = 0
    partial_contacts: int = 0
    missed_catches: int = 0
    catch_rate: float = 0.0
    contact_rate: float = 0.0


def load_stress_test(path: Path) -> Optional[dict]:
    """加载压力测试结果"""
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def generate_summary_report(output_dir: Path) -> dict:
    """生成汇总报告"""
    difficulties = ["easy", "medium", "hard"]
    stats = {}

    for diff in difficulties:
        stress_path = output_dir / f"stress_test_{diff}.json"
        data = load_stress_test(stress_path)

        if data:
            # Get from top-level first, then from summary as fallback
            top_level = data.get("total_trials", 0)
            summary = data.get("summary", {})
            stats[diff] = DifficultyStats(
                difficulty=diff,
                total_trials=summary.get("total_trials", top_level),
                successful_catches=summary.get("successful_catches", 0),
                partial_contacts=summary.get("partial_contacts", 0),
                missed_catches=summary.get("missed_catches", 0),
                catch_rate=summary.get("catch_rate", 0.0),
                contact_rate=summary.get("contact_rate", 0.0),
            )
        else:
            stats[diff] = DifficultyStats(difficulty=diff)

    # 计算总计
    total_trials = sum(s.total_trials for s in stats.values())
    total_success = sum(s.successful_catches for s in stats.values())
    total_contact = sum(s.successful_catches + s.partial_contacts for s in stats.values())

    # 构建报告
    report = {
        "title": "Ball Catch - Comprehensive Test Report",
        "overview": {
            "total_trials": total_trials,
            "total_successful": total_success,
            "total_failed": total_trials - total_success,
            "overall_catch_rate": round(total_success / total_trials, 4) if total_trials > 0 else 0.0,
            "overall_contact_rate": round(total_contact / total_trials, 4) if total_trials > 0 else 0.0,
        },
        "by_difficulty": {
            diff: {
                "trials": s.total_trials,
                "successful": s.successful_catches,
                "partial": s.partial_contacts,
                "missed": s.missed_catches,
                "catch_rate": s.catch_rate,
                "contact_rate": s.contact_rate,
            }
            for diff, s in stats.items()
        },
    }

    return report


def print_report(report: dict):
    """打印报告"""
    print("\n" + "=" * 70)
    print("  BALL CATCH - COMPREHENSIVE TEST REPORT")
    print("=" * 70)

    overview = report["overview"]
    print(f"\n[TOTAL OVERVIEW]")
    print(f"  Total Trials:     {overview['total_trials']}")
    print(f"  Successful:      {overview['total_successful']}")
    print(f"  Failed:          {overview['total_failed']}")
    print(f"  Catch Rate:      {overview['overall_catch_rate']*100:.1f}%")
    print(f"  Contact Rate:    {overview['overall_contact_rate']*100:.1f}%")

    print(f"\n[SUCCESS RATE BY DIFFICULTY]")
    print("-" * 70)
    print(f"{'Difficulty':<12} {'Trials':<8} {'Success':<10} {'Partial':<10} {'Missed':<10} {'Rate':<10}")
    print("-" * 70)

    by_diff = report["by_difficulty"]
    for diff in ["easy", "medium", "hard"]:
        if diff in by_diff:
            d = by_diff[diff]
            rate_str = f"{d['catch_rate']*100:.1f}%"
            bar = "█" * int(d['catch_rate'] * 20) + "░" * (20 - int(d['catch_rate'] * 20))
            print(f"{diff.capitalize():<12} {d['trials']:<8} {d['successful']:<10} {d['partial']:<10} {d['missed']:<10} {bar} {rate_str}")

    print("-" * 70)

    # 成功率可视化柱状图
    print(f"\n[SUCCESS RATE VISUALIZATION]")
    print()
    max_rate = max(by_diff.get(d, {}).get('catch_rate', 0) for d in ["easy", "medium", "hard"])
    if max_rate > 0:
        bar_width = 40
        for diff in ["easy", "medium", "hard"]:
            if diff in by_diff:
                rate = by_diff[diff]['catch_rate']
                bar_len = int(rate / max_rate * bar_width) if max_rate > 0 else 0
                bar = "█" * bar_len + "░" * (bar_width - bar_len)
                label = diff.upper()
                print(f"  {label:>8}: [{bar}] {rate*100:.1f}%")

    print()

    # 性能评价
    overall_rate = overview['overall_catch_rate']
    if overall_rate >= 0.95:
        grade = "S - EXCELLENT"
    elif overall_rate >= 0.85:
        grade = "A - GREAT"
    elif overall_rate >= 0.75:
        grade = "B - GOOD"
    elif overall_rate >= 0.60:
        grade = "C - FAIR"
    else:
        grade = "D - NEEDS IMPROVEMENT"

    print(f"[OVERALL GRADE]: {grade}")
    print()
    print("=" * 70)


def save_report(report: dict, output_path: Path):
    """保存报告为JSON"""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved to: {output_path}")


def generate_ascii_chart(report: dict) -> str:
    """生成ASCII柱状图"""
    lines = []
    lines.append("\n  SUCCESS RATE COMPARISON")
    lines.append("  " + "─" * 50)

    by_diff = report.get("by_difficulty", {})
    max_rate = max(by_diff.get(d, {}).get('catch_rate', 0) for d in ["easy", "medium", "hard"])

    for diff in ["easy", "medium", "hard"]:
        if diff in by_diff:
            rate = by_diff[diff]['catch_rate']
            trials = by_diff[diff]['trials']
            if max_rate > 0:
                bar_len = int(rate / max_rate * 25)
            else:
                bar_len = 0
            bar = "▓" * bar_len + "░" * (25 - bar_len)
            lines.append(f"  {diff.upper():<8} [{bar}] {rate*100:5.1f}% ({trials} trials)")

    lines.append("  " + "─" * 50)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Ball Catch Summary Report")
    parser.add_argument("--output", type=str, default="outputs_ball_catch",
                       help="Output directory")
    parser.add_argument("--save", action="store_true",
                       help="Save report to JSON")

    args = parser.parse_args()
    output_dir = Path(args.output)

    if not output_dir.exists():
        print(f"Error: Directory not found: {output_dir}")
        return 1

    report = generate_summary_report(output_dir)
    print_report(report)

    if args.save:
        save_path = output_dir / "summary_report.json"
        save_report(report, save_path)

    # 生成ASCII图表
    print(generate_ascii_chart(report))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
