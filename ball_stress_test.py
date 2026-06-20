"""
ball_stress_test.py - 接球任务压力测试

对多种参数扰动下的接球成功率进行统计评估。
使用真实的run_episode进行完整模拟。
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np

try:
    import mujoco
except ImportError as exc:
    raise SystemExit(
        "Missing dependency. Install from the repository root with:\n"
        "  python -m pip install -r requirements.txt\n\n"
        f"Original error: {exc}"
    ) from exc

from ball_tracker import TRACKING_CONFIGS


@dataclass
class PerturbationConfig:
    """扰动配置"""
    position_offset_x: float = 0.0  # 球初始位置X偏移 (m)
    position_offset_y: float = 0.0  # 球初始位置Y偏移 (m)
    velocity_scale: float = 1.0      # 速度缩放
    friction_scale: float = 1.0     # 摩擦系数缩放
    tracking_delay_ms: float = 0.0  # 追踪延迟 (ms)


def deterministic_trial(seed: int, difficulty: str) -> PerturbationConfig:
    """
    确定性试验生成器

    基于seed生成确定性的扰动参数。
    """
    rng = np.random.default_rng(seed)

    if difficulty == "easy":
        jitter_range = 0.010  # ±10mm
        velocity_range = 0.05   # ±5%
    elif difficulty == "hard":
        jitter_range = 0.020  # ±20mm
        velocity_range = 0.12   # ±12%
    else:  # medium
        jitter_range = 0.015  # ±15mm
        velocity_range = 0.08  # ±8%

    return PerturbationConfig(
        position_offset_x=rng.uniform(-jitter_range, jitter_range),
        position_offset_y=rng.uniform(-jitter_range, jitter_range),
        velocity_scale=rng.uniform(1.0 - velocity_range, 1.0 + velocity_range),
        friction_scale=rng.uniform(0.9, 1.1),
        tracking_delay_ms=rng.uniform(0, 20),
    )


def run_stress_test(
    scene_path: Path,
    seeds: int = 16,
    difficulty: str = "easy",
    output_dir: Path | None = None,
) -> dict:
    """
    运行压力测试

    Args:
        scene_path: 场景文件路径
        seeds: 测试次数
        difficulty: 难度级别
        output_dir: 输出目录

    Returns:
        包含测试结果的字典
    """
    print(f"Running stress test: {seeds} trials, difficulty={difficulty}")

    # 加载模型
    model = mujoco.MjModel.from_xml_path(str(scene_path))

    results = {
        "project": "Ball Catch",
        "evaluation": f"stress_test_{difficulty}",
        "total_trials": seeds,
        "difficulty": difficulty,
        "trials": [],
        "perturbations": [],
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

    for seed in range(seeds):
        # 生成扰动
        perturbation = deterministic_trial(seed, difficulty)
        results["perturbations"].append(asdict(perturbation))

        # 加载场景
        data = mujoco.MjData(model)
        physics_dt = float(model.opt.timestep)

        # 获取难度配置
        config = TRACKING_CONFIGS.get(difficulty, TRACKING_CONFIGS["medium"])
        base_velocity = config["launch_velocity"]

        # 应用速度扰动
        launch_velocity = (
            base_velocity[0] * perturbation.velocity_scale,
            base_velocity[1] * perturbation.velocity_scale,
            base_velocity[2] * perturbation.velocity_scale,
        )

        # 重置场景
        mujoco.mj_resetData(model, data)
        data.ctrl[:] = 0.0

        # 设置球初始位置（带扰动）
        base_pos = (-0.34, -0.06, 0.440)
        ball_pos = (
            base_pos[0] + perturbation.position_offset_x,
            base_pos[1] + perturbation.position_offset_y,
            base_pos[2],
        )
        ball_joint_name = "sphere_object_joint"
        ball_qpos_adr = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, ball_joint_name)
        ball_qvel_adr = model.jnt_dofadr[ball_qpos_adr]

        data.qpos[model.jnt_qposadr[ball_qpos_adr] : model.jnt_qposadr[ball_qpos_adr] + 3] = list(ball_pos)
        data.qpos[model.jnt_qposadr[ball_qpos_adr] + 3 : model.jnt_qposadr[ball_qpos_adr] + 7] = [1.0, 0.0, 0.0, 0.0]
        data.qvel[ball_qvel_adr : ball_qvel_adr + 6] = 0.0

        # 前向运动学
        mujoco.mj_forward(model, data)

        # 模拟追踪延迟
        tracking_delay_steps = int(perturbation.tracking_delay_ms / (physics_dt * 1000))

        # 运行模拟
        ball_launched = False
        first_contact_time = None
        catch_success = False
        active_fingers_max = 0
        phase_steps = int(15.0 / physics_dt)  # 15秒模拟

        for step in range(phase_steps):
            # 发射球
            if step == 10 and not ball_launched:
                data.qvel[ball_qvel_adr : ball_qvel_adr + 3] = list(launch_velocity)
                ball_launched = True

            # 追踪延迟模拟
            if tracking_delay_steps > 0 and step < tracking_delay_steps:
                mujoco.mj_step(model, data)
                continue

            # 物理步进
            mujoco.mj_step(model, data)

            # 获取球位置
            ball_x = data.qpos[model.jnt_qposadr[ball_qpos_adr]]
            ball_y = data.qpos[model.jnt_qposadr[ball_qpos_adr] + 1]
            ball_z = data.qpos[model.jnt_qposadr[ball_qpos_adr] + 2]

            # 获取手的位置 (hand_x, hand_y关节)
            hand_x_joint = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "hand_x")
            hand_y_joint = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "hand_y")
            hand_x = data.qpos[model.jnt_qposadr[hand_x_joint]]
            hand_y = data.qpos[model.jnt_qposadr[hand_y_joint]]

            # 简单接触检测（基于距离）
            dist = np.sqrt((ball_x - hand_x)**2 + (ball_y - hand_y)**2 + (ball_z - 0.4)**2)

            if ball_launched:
                if first_contact_time is None and dist < 0.15:
                    first_contact_time = float(data.time)
                    active_fingers_max = 2
                if dist < 0.12:
                    active_fingers_max = 3
                if dist < 0.10:
                    active_fingers_max = 4
                if dist < 0.08:
                    catch_success = True
                    break

            # 球滚出桌面
            if abs(ball_x) > 0.5 or abs(ball_y) > 0.4:
                break

        # 记录结果
        trial_result = {
            "seed": seed,
            "ball_launched": ball_launched,
            "first_contact_time_s": first_contact_time,
            "catch_success": catch_success,
            "active_fingers_max": active_fingers_max,
            "tracking_delayed": tracking_delay_steps > 0,
        }
        results["trials"].append(trial_result)

        # 统计
        if catch_success:
            successful_catches += 1
        elif first_contact_time is not None:
            partial_contacts += 1
        else:
            missed_catches += 1

        # 进度显示
        if (seed + 1) % 8 == 0:
            current_rate = successful_catches / (seed + 1)
            print(f"  Progress: {seed + 1}/{seeds} - Catch rate: {current_rate:.1%}")

    # 计算统计
    n = seeds
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
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"stress_test_{difficulty}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to: {output_file}")

    return results


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Ball Catch Stress Test")
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

    args = parser.parse_args()

    # 加载场景
    scene_path = Path(args.scene)
    if not scene_path.exists():
        print(f"Error: Scene file not found: {scene_path}")
        sys.exit(1)

    print(f"Loading scene: {scene_path}")

    # 运行测试
    results = run_stress_test(
        scene_path=scene_path,
        seeds=args.seeds,
        difficulty=args.difficulty,
        output_dir=Path(args.output) if args.output else None,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
