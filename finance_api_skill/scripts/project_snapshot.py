#!/usr/bin/env python3
"""Print a concise snapshot of key files for finance_api_automation."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

KEY_PATHS = [
    "run.py",
    "pytest.ini",
    "requirements.txt",
    "config/settings.py",
    "config/env_test.yaml",
    "api/base_api.py",
    "api/system/base_system_api.py",
    "api/system/login_api.py",
    "api/system/user_api.py",
    "api/system/role_api.py",
    "api/system/post_api.py",
    "api/system/dept_api.py",
    "api/system/notice_api.py",
    "business/system_flows.py",
    "core/request_wrapper.py",
    "core/data_engine.py",
    "core/template_manager.py",
    "core/context.py",
    "tests/conftest.py",
    "tests/test_system/conftest.py",
    "tests/test_system/test_system_business_flows.py",
    "utils/db_client.py",
    "utils/api_logger.py",
    "utils/system_ruoyi_queries.py",
]


def main() -> int:
    print("=== finance_api_automation project snapshot ===")
    print(f"root: {ROOT}")
    print()

    missing: list[str] = []
    for rel_path in KEY_PATHS:
        path = ROOT / rel_path
        status = "OK" if path.exists() else "MISS"
        print(f"[{status:4}] {rel_path}")
        if not path.exists():
            missing.append(rel_path)

    print()
    if missing:
        print("missing key files:")
        for rel_path in missing:
            print(f"- {rel_path}")
        return 1

    print("all key files exist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
