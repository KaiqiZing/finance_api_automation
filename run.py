"""
项目命令行启动入口。

用法:
    python run.py                        # 运行全部测试
    python run.py --env test             # 指定环境
    python run.py --mark smoke           # 运行冒烟测试
    python run.py --mark account -n 4    # 账户模块并行执行
    python run.py --report               # 运行后自动打开 Allure 报告
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Finance API Automation Test Runner")
    parser.add_argument("--env", choices=["dev", "test"], default="test", help="运行环境 (默认: test)")
    parser.add_argument("--mark", default=None, help="Pytest mark 过滤标签 (如: smoke, account)")
    parser.add_argument("-n", "--workers", type=int, default=1, help="并行工作进程数 (默认: 1)")
    parser.add_argument("--report", action="store_true", help="测试完成后自动打开 Allure 报告")
    parser.add_argument("--failfast", action="store_true", help="遇到第一个失败立即停止")
    return parser.parse_args()


def build_pytest_cmd(args: argparse.Namespace) -> list[str]:
    cmd = [sys.executable, "-m", "pytest"]
    if args.mark:
        cmd += ["-m", args.mark]
    if args.workers > 1:
        cmd += ["-n", str(args.workers)]
    if args.failfast:
        cmd.append("-x")
    return cmd


def main() -> None:
    args = parse_args()
    os.environ["TEST_ENV"] = args.env

    (BASE_DIR / "outputs" / "logs").mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "outputs" / "allure_results").mkdir(parents=True, exist_ok=True)

    cmd = build_pytest_cmd(args)
    print(f"[Runner] 环境: {args.env} | 命令: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=BASE_DIR)

    if args.report:
        report_dir = BASE_DIR / "report"
        allure_results = BASE_DIR / "outputs" / "allure_results"
        subprocess.run(["allure", "generate", str(allure_results), "-o", str(report_dir), "--clean"])
        subprocess.run(["allure", "open", str(report_dir)])

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
