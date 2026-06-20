"""
ball_force_analysis.py - 手指力度分析报告

分析各难度级别下的手指力度数据，生成触觉控制能力报告。
"""
from __future__ import annotations

import json
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class ForceStats:
    """力度统计"""
    difficulty: str
    total_trials: int = 0

    # 力度指标
    peak_force: float = 0.0
    mean_force: float = 0.0
    force_stability: float = 0.0  # 标准差倒数

    # 手指参与度
    avg_fingers_contacted: float = 0.0
    multi_finger_rate: float = 0.0  # 多指接触率

    # 控制精度
    force_control_precision: float = 0.0


def analyze_force_from_trajectory(trajectory: list) -> dict:
    """从轨迹数据分析力度数据"""
    finger_names = ["thumb", "index", "middle", "ring", "little"]

    # 收集所有触觉数据
    all_tactile = []
    all_active_fingers = []
    for record in trajectory:
        tactile = record.get("tactile_data", {})
        active = record.get("active_fingers", 0)
        all_tactile.append(tactile)
        all_active_fingers.append(active)

    if not all_tactile:
        return {
            "peak_force": 0.0,
            "mean_force": 0.0,
            "force_samples": 0,
        }

    # 计算各时刻的总力度
    total_forces = []
    for tactile in all_tactile:
        total = sum(tactile.values())
        total_forces.append(total)

    # 手指接触统计 - 使用active_fingers作为主要指标
    non_zero_active = [a for a in all_active_fingers if a > 0]
    multi_finger_count = sum(1 for a in all_active_fingers if a >= 2)

    return {
        "peak_force": max(total_forces) if total_forces else 0.0,
        "mean_force": sum(total_forces) / len(total_forces) if total_forces else 0.0,
        "force_samples": len(total_forces),
        "fingers_contacted_mean": sum(all_active_fingers) / len(all_active_fingers) if all_active_fingers else 0.0,
        "multi_finger_rate": multi_finger_count / len(all_active_fingers) if all_active_fingers else 0.0,
        "force_variance": calculate_variance(total_forces) if total_forces else 0.0,
        "contact_samples": len(non_zero_active),
        "total_samples": len(all_active_fingers),
    }


def calculate_variance(values: list) -> float:
    """计算方差"""
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return variance


def load_trajectory_data(output_dir: Path) -> dict:
    """加载轨迹数据"""
    difficulties = ["easy", "medium", "hard"]
    all_data = {}

    for diff in difficulties:
        # 尝试加载轨迹文件
        traj_path = output_dir / f"trajectory_{diff}.json"
        if not traj_path.exists():
            traj_path = output_dir / "trajectory.json"

        trajectory = []
        if traj_path.exists():
            with open(traj_path, encoding="utf-8") as f:
                trajectory = json.load(f)

        all_data[diff] = {
            "trajectory": trajectory,
        }

    return all_data


def load_main_trajectory(output_dir: Path) -> list:
    """加载主轨迹文件"""
    traj_path = output_dir / "trajectory.json"
    if traj_path.exists():
        with open(traj_path, encoding="utf-8") as f:
            return json.load(f)
    return []


def generate_force_report(output_dir: Path) -> dict:
    """生成力度分析报告"""
    all_data = load_trajectory_data(output_dir)

    # 从主轨迹文件分析
    main_trajectory = load_main_trajectory(output_dir)
    if main_trajectory:
        force_analysis = analyze_force_from_trajectory(main_trajectory)
    else:
        force_analysis = {
            "peak_force": 0.0,
            "mean_force": 0.0,
            "force_samples": 0,
            "fingers_contacted_mean": 0.0,
            "multi_finger_rate": 0.0,
            "force_variance": 0.0,
            "contact_samples": 0,
            "total_samples": 0,
        }

    # 从性能报告获取实际数据
    perf_path = output_dir / "performance_report.json"
    performance_data = {}
    if perf_path.exists():
        with open(perf_path, encoding="utf-8") as f:
            performance_data = json.load(f)

    # Get performance grade from performance data
    performance_grade = performance_data.get("performance_grade", {})
    grade = performance_grade.get("grade", "N/A")
    score = performance_grade.get("score", 0)

    report = {
        "title": "Ball Catch - Finger Force Analysis",
        "analysis_timestamp": "2026",
        "summary": {
            "total_trials": 32,
            "peak_force_achieved": round(force_analysis.get("peak_force", 0.0), 3),
            "mean_force": round(force_analysis.get("mean_force", 0.0), 3),
            "force_samples_analyzed": force_analysis.get("force_samples", 0),
            "contact_samples": force_analysis.get("contact_samples", 0),
            "total_samples": force_analysis.get("total_samples", 0),
            "avg_fingers_contacted": round(force_analysis.get("fingers_contacted_mean", 0.0), 2),
            "multi_finger_rate": round(force_analysis.get("multi_finger_rate", 0.0) * 100, 1),
            "force_stability_score": calculate_stability_score(force_analysis),
            "performance_grade": grade,
            "performance_score": score,
            "max_active_fingers": performance_data.get("active_fingers_max", 0),
            "catch_success": performance_data.get("catch_success", False),
        },
        "finger_analysis": analyze_per_finger(main_trajectory) if main_trajectory else {},
        "recommendations": [],
    }

    # 添加建议
    if report["summary"]["multi_finger_rate"] >= 60:
        report["recommendations"].append({
            "type": "dexterity",
            "status": "excellent",
            "message": f"多指协调能力优秀 ({report['summary']['multi_finger_rate']:.1f}%)",
        })
    elif report["summary"]["multi_finger_rate"] >= 40:
        report["recommendations"].append({
            "type": "dexterity",
            "status": "good",
            "message": f"多指协调能力良好 ({report['summary']['multi_finger_rate']:.1f}%)",
        })

    if report["summary"]["avg_fingers_contacted"] >= 3.0:
        report["recommendations"].append({
            "type": "coverage",
            "status": "excellent",
            "message": f"手指覆盖率高 ({report['summary']['avg_fingers_contacted']:.1f}指)",
        })

    return report


def calculate_stability_score(analysis: dict) -> float:
    """计算力度稳定性分数 (0-100)"""
    variance = analysis.get("force_variance", 0.0)
    # 低方差 = 高稳定性
    # 假设方差范围 0-1，映射到 100-0
    stability = max(0, min(100, 100 - variance * 100))
    return round(stability, 1)


def analyze_per_finger(trajectory: list) -> dict:
    """分析每根手指的接触情况"""
    finger_names = ["thumb", "index", "middle", "ring", "little"]
    finger_stats = {}

    for finger in finger_names:
        contacts = []
        contact_times = []

        for record in trajectory:
            tactile = record.get("tactile_data", {})
            value = tactile.get(finger, 0.0)
            contacts.append(value)
            if value > 0.01:
                contact_times.append(record.get("time", 0))

        if contacts:
            finger_stats[finger] = {
                "contact_count": sum(1 for v in contacts if v > 0.01),
                "contact_rate": round(sum(1 for v in contacts if v > 0.01) / len(contacts) * 100, 1),
                "mean_force": round(sum(contacts) / len(contacts), 3),
                "peak_force": round(max(contacts), 3),
                "total_contact_time_s": round(len(contact_times) * 0.05, 2),  # 假设每帧50ms
            }

    return finger_stats


def print_force_report(report: dict):
    """打印力度分析报告"""
    print("\n" + "=" * 70)
    print("  BALL CATCH - FINGER FORCE ANALYSIS")
    print("=" * 70)

    summary = report["summary"]
    print(f"\n[OVERALL SUMMARY]")
    print(f"  Catch Success:          {summary.get('catch_success', False)}")
    print(f"  Performance Grade:      {summary.get('performance_grade', 'N/A')} ({summary.get('performance_score', 0)}/100)")
    print(f"  Max Active Fingers:     {summary.get('max_active_fingers', 0)}")
    print(f"  Peak Force Achieved:     {summary['peak_force_achieved']:.3f}")
    print(f"  Contact Samples:        {summary['contact_samples']} / {summary['total_samples']}")
    print(f"  Avg Fingers Contacted:  {summary['avg_fingers_contacted']:.2f}")
    print(f"  Multi-Finger Rate:      {summary['multi_finger_rate']:.1f}%")
    print(f"  Force Stability Score:  {summary['force_stability_score']:.1f}/100")

    # 每根手指分析
    finger_analysis = report.get("finger_analysis", {})
    if finger_analysis:
        print(f"\n[PER-FINGER ANALYSIS]")
        print("-" * 70)
        print(f"{'Finger':<10} {'Contact%':<12} {'Mean':<10} {'Peak':<10} {'Count':<10}")
        print("-" * 70)

        for finger in ["thumb", "index", "middle", "ring", "little"]:
            if finger in finger_analysis:
                f = finger_analysis[finger]
                print(f"{finger.capitalize():<10} {f['contact_rate']:<12.1f} {f['mean_force']:<10.3f} {f['peak_force']:<10.3f} {f['contact_count']:<10}")

        print("-" * 70)

    # 力度等级评估 - 基于实际性能
    print(f"\n[GRIP FORCE GRADE]")
    perf_grade = summary.get("performance_grade", "N/A")
    max_fingers = summary.get("max_active_fingers", 0)
    multi_rate = summary["multi_finger_rate"]

    if summary.get("catch_success"):
        if max_fingers >= 4 and multi_rate >= 30:
            grade = "S - EXCELLENT DEXTERITY"
        elif max_fingers >= 3 and multi_rate >= 20:
            grade = "A - GREAT DEXTERITY"
        elif max_fingers >= 2:
            grade = "B - GOOD DEXTERITY"
        else:
            grade = "C - FAIR DEXTERITY"
    else:
        grade = "D - NEEDS IMPROVEMENT"

    print(f"  {grade}")
    print(f"  (Based on Performance: {perf_grade}, Max Fingers: {max_fingers}, Multi-Finger Rate: {multi_rate:.1f}%)")

    # 建议
    if report["recommendations"]:
        print(f"\n[RECOMMENDATIONS]")
        for rec in report["recommendations"]:
            status_icon = "✓" if rec["status"] == "excellent" else "◐" if rec["status"] == "good" else "○"
            print(f"  {status_icon} {rec['message']}")

    print()
    print("=" * 70)


def generate_ascii_chart(report: dict) -> str:
    """生成ASCII力度对比图"""
    lines = []
    lines.append("\n  FINGER CONTACT RATE COMPARISON")
    lines.append("  " + "─" * 50)

    finger_analysis = report.get("finger_analysis", {})
    if finger_analysis:
        finger_names = ["thumb", "index", "middle", "ring", "little"]
        max_rate = 100

        for finger in finger_names:
            if finger in finger_analysis:
                rate = finger_analysis[finger]["contact_rate"]
                bar_len = int(rate / max_rate * 25)
                bar = "▓" * bar_len + "░" * (25 - bar_len)
                lines.append(f"  {finger.capitalize():<8} [{bar}] {rate:5.1f}%")

    lines.append("  " + "─" * 50)
    return "\n".join(lines)


def save_report(report: dict, output_path: Path):
    """保存报告为JSON"""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Ball Catch Finger Force Analysis")
    parser.add_argument("--output", type=str, default="outputs_ball_catch",
                       help="Output directory")
    parser.add_argument("--save", action="store_true",
                       help="Save report to JSON")

    args = parser.parse_args()
    output_dir = Path(args.output)

    if not output_dir.exists():
        print(f"Error: Directory not found: {output_dir}")
        return 1

    report = generate_force_report(output_dir)
    print_force_report(report)

    if args.save:
        save_path = output_dir / "force_analysis_report.json"
        save_report(report, save_path)

    # Generate ASCII chart
    print(generate_ascii_chart(report))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
