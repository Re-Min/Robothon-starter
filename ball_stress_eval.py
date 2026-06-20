"""
ball_stress_eval.py - 接球任务压力测试

使用真实的run_episode进行完整模拟，评估各种扰动下的成功率。
"""
from __future__ import annotations

import argparse
import json
import sys
import numpy as np
from pathlib import Path

try:
    import mujoco
except ImportError:
    raise SystemExit(
        "Missing dependency. Install from the repository root with:\n"
        "  python -m pip install -r requirements.txt"
    )

from run_ball_catch import run_episode


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Ball Catch Stress Evaluation")
    parser.add_argument("--seeds", type=int, default=16, help="测试次数")
    parser.add_argument(
        "--difficulty",
        type=str,
        choices=["easy", "medium", "hard"],
        default="easy",
        help="难度级别",
    )
    parser.add_argument("--scene", type=str, default="scene_ball_catch.xml", help="场景XML路径")
    parser.add_argument("--output", type=str, default="outputs_ball_catch", help="输出目录")
    parser.add_argument("--no-video", action="store_true", help="禁用视频渲染")

    args = parser.parse_args()

    scene_path = Path(args.scene)
    if not scene_path.exists():
        print(f"Error: Scene file not found: {scene_path}")
        sys.exit(1)

    output_dir = Path(args.output) if args.output else None

    print(f"Loading scene: {scene_path}")
    model = mujoco.MjModel.from_xml_path(str(scene_path))

    results = {
        "project": "Ball Catch",
        "evaluation": f"stress_test_{args.difficulty}",
        "total_trials": args.seeds,
        "difficulty": args.difficulty,
        "trials": [],
        "summary": {
            "successful_catches": 0,
            "partial_contacts": 0,
            "missed_catches": 0,
            "catch_rate": 0.0,
            "contact_rate": 0.0,
        },
    }

    successful_catches = 0
    partial_contacts = 0
    missed_catches = 0

    for seed in range(args.seeds):
        print(f"Running trial {seed + 1}/{args.seeds}...", end=" ")

        # 运行完整episode
        result = run_episode(
            model=model,
            scene_path=scene_path,
            seed=seed,
            difficulty=args.difficulty,
            render_video=False,  # 压力测试不生成视频
            output_dir=None,
            debug=False,
        )

        catch_success = result.get("catch_success", False)
        first_contact = result.get("first_contact_time_s") is not None
        active_fingers = result.get("active_fingers_max", 0)

        # 记录结果
        trial_result = {
            "seed": seed,
            "catch_success": catch_success,
            "first_contact": first_contact,
            "active_fingers_max": active_fingers,
            "total_time_s": result.get("total_time_s", 0),
        }
        results["trials"].append(trial_result)

        # 统计
        if catch_success:
            successful_catches += 1
            print("SUCCESS")
        elif first_contact:
            partial_contacts += 1
            print("PARTIAL")
        else:
            missed_catches += 1
            print("MISSED")

    # 计算统计
    n = args.seeds
    results["summary"]["successful_catches"] = successful_catches
    results["summary"]["partial_contacts"] = partial_contacts
    results["summary"]["missed_catches"] = missed_catches
    results["summary"]["catch_rate"] = round(successful_catches / n, 4)
    results["summary"]["contact_rate"] = round((successful_catches + partial_contacts) / n, 4)

    # 打印结果
    print(f"\n=== STRESS TEST RESULTS ===")
    print(f"Total trials: {n}")
    print(f"Successful catches: {successful_catches} ({results['summary']['catch_rate']:.1%})")
    print(f"Partial contacts: {partial_contacts} ({partial_contacts/n:.1%})")
    print(f"Missed catches: {missed_catches} ({missed_catches/n:.1%})")
    print(f"Contact rate: {results['summary']['contact_rate']:.1%}")

    # 保存结果
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"stress_test_{args.difficulty}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to: {output_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
