#!/usr/bin/env python3
"""
让邺城燃烧 — Bio-Logic Debugger 命令行界面

交互式育种验证控制台。运行方式：
  python -m bio_logic_debugger.cli
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Optional

from bio_logic_debugger.core.domain import (
    BreedingGoal,
    ConstraintSeverity,
    EvidenceLevel,
    Trait,
    TraitTarget,
)
from bio_logic_debugger.core.engine import BioLogicEngine
from bio_logic_debugger.knowledge.rice_knowledge import (
    ANTI_PATTERNS,
    CONSTRAINTS,
    CORRELATIONS,
    TRAITS,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class BioLogicCLI:
    """交互式育种验证控制台"""

    def __init__(self):
        self.engine = BioLogicEngine()
        self._load_default_knowledge()

    def _load_default_knowledge(self) -> None:
        """加载内置知识库"""
        self.engine.register_traits(TRAITS)
        self.engine.register_correlations(CORRELATIONS)
        self.engine.register_constraints(CONSTRAINTS)
        self.engine.register_anti_patterns(ANTI_PATTERNS)
        logger.info(f"已加载 {len(TRAITS)} 个性状, {len(CORRELATIONS)} 条关联, "
                    f"{len(CONSTRAINTS)} 条约束, {len(ANTI_PATTERNS)} 个反模式")

    # ---- 展示 ----

    def list_traits(self, category: str = "") -> None:
        """列出所有性状"""
        traits = self.engine._traits.values()
        if category:
            traits = [t for t in traits if t.category == category]

        cats = {}
        for t in traits:
            cats.setdefault(t.category, []).append(t)

        for cat, ts in cats.items():
            print(f"\n[{cat}]")
            for t in sorted(ts, key=lambda x: x.id):
                ranges = f" [{t.typical_range[0]}~{t.typical_range[1]}{t.unit}]" if t.typical_range[0] else ""
                print(f"  {t.id:40s} {t.name}{ranges}")

    def list_anti_patterns(self) -> None:
        """列出所有反模式"""
        for ap in self.engine._anti_patterns._patterns.values():
            severity_tag = {
                ConstraintSeverity.FATAL: "🔴",
                ConstraintSeverity.SEVERE: "🟠",
                ConstraintSeverity.WARNING: "🟡",
                ConstraintSeverity.INFO: "🔵",
            }.get(ap.severity, "⚪")
            print(f"\n{severity_tag} {ap.name}")
            print(f"  触发性状: {', '.join(ap.trigger_traits)}")
            print(f"  描述: {ap.description[:120]}...")

    def show_trait_detail(self, trait_id: str) -> None:
        """显示单个性状的详细信息"""
        trait = self.engine._traits.get(trait_id)
        if not trait:
            print(f"未找到性状: {trait_id}")
            return

        print(f"\n{'='*50}")
        print(f"性状: {trait.name} ({trait.id})")
        print(f"{'='*50}")
        print(f"  分类: {trait.category}")
        print(f"  单位: {trait.unit}")
        print(f"  范围: {trait.typical_range}")
        print(f"  描述: {trait.description}")
        if trait.tags:
            print(f"  标签: {', '.join(trait.tags)}")

        # 显示相关关联
        print(f"\n  相关关联:")
        for corr in self.engine._correlations:
            if trait.id in (corr.trait_a, corr.trait_b):
                other = corr.trait_b if corr.trait_a == trait.id else corr.trait_a
                other_name = self.engine._trait_name(other)
                tag = "🔴拮抗" if corr.is_antagonistic() else "🟡权衡" if corr.corr_type.name == "TRADE_OFF" else "🔵相关"
                print(f"    {tag} {other_name} ({corr.corr_type.name}, r={corr.strength})")

    # ---- 验证 ----

    def run_validation(self, goal: BreedingGoal) -> None:
        """执行验证并打印报告"""
        print(f"\n{'='*60}")
        print(f"  育种目标: {goal.name}")
        print(f"  物种: {goal.species}")
        print(f"{'='*60}")

        for t in goal.targets:
            trait = self.engine._traits.get(t.trait_id)
            tname = trait.name if trait else t.trait_id
            val = t.desired_value or f"[{t.range_min}~{t.range_max}]"
            dir_symbol = {">=": "≥", "<=": "≤", "==": "=", "range": "∈"}.get(t.direction, t.direction)
            print(f"  {tname:20s} {dir_symbol} {val}  (优先级: {t.priority})")

        print()
        report = self.engine.validate(goal)
        print(report.narrative())

        return report

    # ---- 交互模式 ----

    def interactive(self) -> None:
        """进入交互式控制台"""
        print("=" * 50)
        print("  让邺城燃烧 — Bio-Logic Debugger")
        print("  交互式育种逻辑验证控制台")
        print("=" * 50)
        print("\n可用命令:")
        print("  traits [分类]    — 列出性状")
        print("  trait <id>       — 查看性状详情")
        print("  patterns          — 列出反模式")
        print("  validate          — 交互式输入育种目标并验证")
        print("  quick <trait> <dir> <val> — 快速验证：如 quick rice_yield_per_plant >= 50")
        print("  multi            — 多目标验证（逐步输入）")
        print("  help             — 帮助")
        print("  exit             — 退出")

        while True:
            try:
                cmd = input("\n>> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n再见。")
                break

            if not cmd:
                continue

            parts = cmd.split()
            action = parts[0].lower()

            if action in ("exit", "quit", "q"):
                print("种地去吧，育种家没有休息日。")
                break

            elif action == "traits":
                category = " ".join(parts[1:]) if len(parts) > 1 else ""
                self.list_traits(category)

            elif action == "trait" and len(parts) > 1:
                self.show_trait_detail(parts[1])

            elif action == "patterns":
                self.list_anti_patterns()

            elif action == "validate":
                goal = self._interactive_goal_input()
                if goal:
                    self.run_validation(goal)

            elif action == "quick" and len(parts) >= 4:
                goal = BreedingGoal(name="快速验证", species="水稻")
                trait_id = parts[1]
                direction = parts[2]
                try:
                    value = float(parts[3])
                except ValueError:
                    print(f"无效数值: {parts[3]}")
                    continue
                goal.add_target(TraitTarget(trait_id, desired_value=value, direction=direction))
                self.run_validation(goal)

            elif action == "multi":
                goal = self._interactive_goal_input()
                if goal:
                    self.run_validation(goal)

            elif action == "help":
                print("可用命令:")
                print("  traits [分类]      — 列出性状，可选按分类筛选")
                print("  trait <id>         — 查看性状详情")
                print("  patterns           — 列出所有反模式")
                print("  validate           — 交互式输入育种目标")
                print("  quick <id> <dir> <val> — 单性状快速验证")
                print("  exit               — 退出")

            else:
                print(f"未知命令: {action}，输入 help 查看帮助")

    def _interactive_goal_input(self) -> Optional[BreedingGoal]:
        """交互式输入育种目标"""
        name = input("育种目标名称: ").strip() or "未命名目标"
        species = input("物种（默认水稻）: ").strip() or "水稻"

        goal = BreedingGoal(name=name, species=species)
        print("\n输入目标性状（每行一个，留空结束）：")
        print("格式: 性状ID 方向(>=/<=/=) 数值 [优先级1-10]")
        print("示例: rice_yield_per_plant >= 50 8")
        print("      rice_grain_length >= 7.0 6")
        print("")

        while True:
            line = input("  > ").strip()
            if not line:
                break

            parts = line.split()
            if len(parts) < 3:
                print("格式错误，需要至少 性状ID 方向 数值")
                continue

            trait_id = parts[0]
            direction = parts[1]
            try:
                value = float(parts[2])
            except ValueError:
                print(f"无效数值: {parts[2]}")
                continue

            priority = int(parts[3]) if len(parts) > 3 else 5

            if trait_id not in self.engine._traits:
                print(f"⚠ 性状 '{trait_id}' 不在知识库中，仍将添加")
                tname = trait_id
            else:
                tname = self.engine._trait_name(trait_id)

            goal.add_target(TraitTarget(trait_id, desired_value=value, direction=direction, priority=priority))
            print(f"  已添加: {tname} {direction} {value} (优先级: {priority})")

        if not goal.targets:
            print("未添加任何目标")
            return None

        context = input("\n育种背景描述（可选，留空跳过）: ").strip()
        if context:
            goal.context = context

        return goal


def main():
    parser = argparse.ArgumentParser(description="Bio-Logic Debugger — 育种逻辑验证系统")
    parser.add_argument("--trait", "-t", help="查看性状详情")
    parser.add_argument("--list-traits", "-l", action="store_true", help="列出所有性状")
    parser.add_argument("--list-patterns", "-p", action="store_true", help="列出所有反模式")
    parser.add_argument("--validate", "-v", nargs=3, metavar=("TRAIT", "DIR", "VAL"), help="快速验证单个目标")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")

    args = parser.parse_args()
    cli = BioLogicCLI()

    if args.interactive or len(sys.argv) == 1:
        cli.interactive()
        return

    if args.list_traits:
        cli.list_traits()
    elif args.trait:
        cli.show_trait_detail(args.trait)
    elif args.list_patterns:
        cli.list_anti_patterns()
    elif args.validate:
        trait_id, direction, value_str = args.validate
        try:
            value = float(value_str)
        except ValueError:
            print(f"无效数值: {value_str}")
            sys.exit(1)
        goal = BreedingGoal(name="命令行验证", species="水稻")
        goal.add_target(TraitTarget(trait_id, desired_value=value, direction=direction))
        report = cli.run_validation(goal)

        if args.json:
            print(report.to_json())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
