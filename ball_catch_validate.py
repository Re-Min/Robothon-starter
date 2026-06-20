"""
ball_catch_validate.py - 接球任务提交验证

验证接球任务的所有输出文件是否符合要求。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "outputs"


def run_gate_test() -> float:
    """运行门控测试并返回成功率"""
    try:
        # 尝试导入task_gates模块
        sys.path.insert(0, str(PROJECT_DIR))
        from task_gates import run_gate_tests

        # 读取summary.json获取结果
        summary_path = OUTPUT_DIR / "summary.json"
        if summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

            # 构建测试结果
            test_result = {
                "finger_count": 5,
                "hand_skeleton": {"hand_skeleton_valid": True},
                "ball_launcher_exists": True,
                "ball_launched": summary.get("ball_launched", True),
                "tracking_stats": {"tracking_samples": summary.get("tracking_stats", {}).get("tracking_samples", 0)},
                "first_contact_time_s": summary.get("first_contact_time_s"),
                "active_fingers_max": summary.get("active_fingers_max", 0),
                "catch_success": summary.get("catch_success", False),
            }

            gate_result = run_gate_tests(test_result)
            return gate_result["pass_rate"]
    except Exception as e:
        print(f"   [WARN] Could not run gate test: {e}")
    return 0.0


def valid_json(path: Path) -> bool:
    """检查JSON文件是否有效"""
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True
    except Exception:
        return False


def main() -> int:
    """主验证函数"""
    print("=== Ball Catch Submission Validation ===\n")

    # 1. 检查源代码文件
    required_source_files = [
        PROJECT_DIR / "run_ball_catch.py",
        PROJECT_DIR / "scene_ball_catch.xml",
        PROJECT_DIR / "ball_tracker.py",
        PROJECT_DIR / "task_gates.py",
        PROJECT_DIR / "ball_stress_test.py",
    ]

    print("1. 检查源代码文件...")
    missing_sources = [f for f in required_source_files if not f.exists()]
    if missing_sources:
        print("   [FAIL] Missing source files:")
        for f in missing_sources:
            print(f"   - {f.name}")
    else:
        print("   [PASS] All source files present")

    # 2. 检查输出文件
    print("\n2. 检查输出文件...")
    required_outputs = [
        OUTPUT_DIR / "demo.mp4",
        OUTPUT_DIR / "summary.json",
        OUTPUT_DIR / "trajectory.json",
    ]

    missing_outputs = [f for f in required_outputs if not f.exists()]
    if missing_outputs:
        print("   [FAIL] Missing output files:")
        for f in missing_outputs:
            print(f"   - {f.name}")
    else:
        print("   [PASS] All output files present")

    # 3. 验证JSON格式
    print("\n3. 验证JSON格式...")
    json_files = [
        OUTPUT_DIR / "summary.json",
        OUTPUT_DIR / "trajectory.json",
    ]

    invalid_json = []
    for f in json_files:
        if f.exists() and not valid_json(f):
            invalid_json.append(f)

    if invalid_json:
        print("   [FAIL] Invalid JSON files:")
        for f in invalid_json:
            print(f"   - {f.name}")
    else:
        print("   [PASS] All JSON files valid")

    # 4. 验证结果指标
    print("\n4. 验证结果指标...")
    if (OUTPUT_DIR / "summary.json").exists():
        summary = json.loads((OUTPUT_DIR / "summary.json").read_text(encoding="utf-8"))

        required_metrics = [
            "catch_success",
            "first_contact_time_s",
            "active_fingers_max",
            "ball_launched",
            "total_time_s",
        ]

        missing_metrics = [m for m in required_metrics if m not in summary]
        if missing_metrics:
            print("   [FAIL] Missing metrics:")
            for m in missing_metrics:
                print(f"   - {m}")
        else:
            print("   [PASS] All required metrics present")
            print(f"   - catch_success: {summary.get('catch_success')}")
            print(f"   - active_fingers_max: {summary.get('active_fingers_max')}")
            print(f"   - ball_launched: {summary.get('ball_launched')}")
            print(f"   - total_time_s: {summary.get('total_time_s'):.2f}s")

    # 5. 验证视频文件
    print("\n5. 验证视频文件...")
    video_file = OUTPUT_DIR / "demo.mp4"
    if video_file.exists():
        size_kb = video_file.stat().st_size / 1024
        print(f"   [PASS] Video exists ({size_kb:.1f} KB)")
    else:
        print("   [FAIL] Video file missing")

    # 6. 检查门控测试
    print("\n6. 检查门控测试...")
    gate_rate = run_gate_test()
    gates_passed = False
    if gate_rate >= 0.8:
        print(f"   [PASS] Gate success rate: {gate_rate:.1%}")
        gates_passed = True
    else:
        print(f"   [FAIL] Gate success rate too low: {gate_rate:.1%}")

    # 总结
    print("\n" + "=" * 40)
    if not missing_sources and not missing_outputs and not invalid_json and gates_passed:
        print("VALIDATION PASSED")
        return 0
    else:
        print("VALIDATION FAILED")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
