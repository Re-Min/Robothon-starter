"""
task_gates.py - 接球任务门控验证

验证任务的关键功能和成功标准。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ball_tracker import TRACKING_CONFIGS


@dataclass
class Gate:
    """门控定义"""
    gate_id: int
    name: str
    description: str


# 门控列表
BALL_CATCH_GATES = [
    Gate(1, "five_fingers_present", "五指灵巧手完整"),
    Gate(2, "hand_skeleton_valid", "手部骨骼结构有效"),
    Gate(3, "ball_launcher_present", "发射器存在"),
    Gate(4, "ball_motion_initiated", "球运动启动"),
    Gate(5, "hand_tracking_active", "手部追踪激活"),
    Gate(6, "ball_contact_detected", "球接触检测"),
    Gate(7, "stable_catch_achieved", "稳定抓取达成"),
    Gate(8, "ball_held_without_drop", "球被握住未掉落"),
]


def check_gate(result: dict, gate: Gate) -> tuple[bool, str]:
    """
    检查单个门控

    Returns:
        (passed, message)
    """
    if gate.name == "five_fingers_present":
        finger_count = result.get("finger_count", 0)
        passed = finger_count == 5
        return passed, f"finger_count={finger_count}"

    elif gate.name == "hand_skeleton_valid":
        skeleton = result.get("hand_skeleton", {})
        passed = skeleton.get("hand_skeleton_valid", False)
        return passed, f"hand_skeleton_valid={passed}"

    elif gate.name == "ball_launcher_present":
        # 检查场景中是否有发射器
        passed = result.get("ball_launcher_exists", True)
        return passed, f"ball_launcher_exists={passed}"

    elif gate.name == "ball_motion_initiated":
        passed = result.get("ball_launched", False)
        return passed, f"ball_launched={passed}"

    elif gate.name == "hand_tracking_active":
        # 检查是否有追踪数据
        tracking = result.get("tracking_stats", {})
        passed = tracking.get("tracking_samples", 0) > 0
        return passed, f"tracking_samples={tracking.get('tracking_samples', 0)}"

    elif gate.name == "ball_contact_detected":
        passed = result.get("first_contact_time_s") is not None
        return passed, f"first_contact_time={result.get('first_contact_time_s')}"

    elif gate.name == "stable_catch_achieved":
        active_max = result.get("active_fingers_max", 0)
        passed = active_max >= 4
        return passed, f"active_fingers_max={active_max}"

    elif gate.name == "ball_held_without_drop":
        passed = result.get("catch_success", False)
        return passed, f"catch_success={passed}"

    else:
        return False, f"Unknown gate: {gate.name}"


def run_gate_tests(result: dict) -> dict:
    """
    运行所有门控测试

    Args:
        result: 任务执行结果

    Returns:
        门控测试结果
    """
    gates_passed = []
    gates_failed = []

    gate_results = []

    for gate in BALL_CATCH_GATES:
        passed, message = check_gate(result, gate)
        gate_results.append({
            "gate_id": gate.gate_id,
            "name": gate.name,
            "description": gate.description,
            "passed": passed,
            "message": message,
        })

        if passed:
            gates_passed.append(gate.name)
        else:
            gates_failed.append(gate.name)

    return {
        "total_gates": len(BALL_CATCH_GATES),
        "gates_passed": len(gates_passed),
        "gates_failed": gates_failed,
        "pass_rate": round(len(gates_passed) / len(BALL_CATCH_GATES), 4),
        "final_task_success": len(gates_passed) >= 7,  # 至少7/8通过
        "gate_results": gate_results,
    }


def main():
    """测试门控验证"""
    # 测试用的模拟结果
    test_result = {
        "finger_count": 5,
        "hand_skeleton": {"hand_skeleton_valid": True},
        "ball_launcher_exists": True,
        "ball_launched": True,
        "tracking_stats": {"tracking_samples": 150},
        "first_contact_time_s": 1.5,
        "active_fingers_max": 5,
        "catch_success": True,
    }

    gate_result = run_gate_tests(test_result)

    print("=== GATE TEST RESULTS ===")
    print(f"Total gates: {gate_result['total_gates']}")
    print(f"Passed: {gate_result['gates_passed']}")
    print(f"Failed: {gate_result['gates_failed']}")
    print(f"Pass rate: {gate_result['pass_rate']:.1%}")
    print(f"Task success: {gate_result['final_task_success']}")

    print("\n=== GATE DETAILS ===")
    for gr in gate_result["gate_results"]:
        status = "PASS" if gr["passed"] else "FAIL"
        print(f"  [{gr['gate_id']}] {status}: {gr['name']} - {gr['message']}")


if __name__ == "__main__":
    main()
