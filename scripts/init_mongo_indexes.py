"""
MongoDB 索引初始化脚本。

用途:
    首次部署或重建集合时执行，创建必要的查询索引与可选 TTL 索引。
    幂等执行：索引已存在时自动跳过，不会报错。

使用方式:
    # 使用默认配置（mongodb://localhost:27018）
    python scripts/init_mongo_indexes.py

    # 覆盖连接参数
    MONGO_URI=mongodb://host:27017 \
    MONGO_DB=finance_auto_logs \
    MONGO_COLLECTION=api_logs \
    python scripts/init_mongo_indexes.py

    # 同时启用 TTL 索引（保留 30 天）
    MONGO_TTL_DAYS=30 python scripts/init_mongo_indexes.py

索引清单:
    必建索引（查询与链路追踪）:
        1. trace_id          - 单字段唯一索引，链路追踪核心
        2. created_at        - 时间范围查询
        3. pytest_nodeid + created_at  - 按用例查询请求历史
        4. module + api_name + created_at  - 按接口统计分析
        5. result + created_at  - 按结果过滤（success/fail/error）

    可选索引（由 MONGO_TTL_DAYS > 0 控制）:
        6. created_at TTL    - 自动过期删除旧日志
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 允许直接在项目根目录运行
sys.path.insert(0, str(Path(__file__).parent.parent))


def _get_config() -> dict:
    """从环境变量读取连接配置，优先于 YAML（让脚本可独立运行）。"""
    try:
        from config.settings import cfg
        mongo_cfg: dict = cfg.logging.get("mongo", {})
        uri = mongo_cfg.get("uri", "mongodb://localhost:27018")
        db_name = mongo_cfg.get("db_name", "finance_auto_logs")
        collection_name = mongo_cfg.get("collection_name", "api_logs")
        ttl_days = cfg.logging.get("ttl_days", 0)
    except Exception:
        uri = "mongodb://localhost:27018"
        db_name = "finance_auto_logs"
        collection_name = "api_logs"
        ttl_days = 0

    return {
        "uri": os.environ.get("MONGO_URI", uri),
        "db_name": os.environ.get("MONGO_DB", db_name),
        "collection_name": os.environ.get("MONGO_COLLECTION", collection_name),
        "ttl_days": int(os.environ.get("MONGO_TTL_DAYS", ttl_days)),
    }


def create_indexes(
    uri: str,
    db_name: str,
    collection_name: str,
    ttl_days: int = 0,
) -> None:
    try:
        from pymongo import MongoClient, ASCENDING  # type: ignore[import]
    except ImportError:
        print("[ERROR] pymongo 未安装，请先执行: pip install pymongo")
        sys.exit(1)

    print(f"[INFO] 连接 MongoDB: {uri}")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)

    try:
        client.server_info()
    except Exception as exc:
        print(f"[ERROR] 连接失败: {exc}")
        sys.exit(1)

    col = client[db_name][collection_name]
    print(f"[INFO] 目标集合: {db_name}.{collection_name}")

    # ------------------------------------------------------------------
    # 必建索引
    # ------------------------------------------------------------------
    indexes = [
        {
            "keys": [("trace_id", ASCENDING)],
            "name": "idx_trace_id",
            "unique": True,
            "background": True,
        },
        {
            "keys": [("created_at", ASCENDING)],
            "name": "idx_created_at",
            "background": True,
        },
        {
            "keys": [("pytest_nodeid", ASCENDING), ("created_at", ASCENDING)],
            "name": "idx_nodeid_created_at",
            "background": True,
        },
        {
            "keys": [("module", ASCENDING), ("api_name", ASCENDING), ("created_at", ASCENDING)],
            "name": "idx_module_api_created_at",
            "background": True,
        },
        {
            "keys": [("result", ASCENDING), ("created_at", ASCENDING)],
            "name": "idx_result_created_at",
            "background": True,
        },
    ]

    for idx_def in indexes:
        keys = idx_def.pop("keys")
        name = idx_def["name"]
        try:
            col.create_index(keys, **idx_def)
            print(f"[OK]   索引创建/确认: {name}")
        except Exception as exc:
            print(f"[WARN] 索引 {name} 创建失败（可能已存在且配置不同）: {exc}")

    # ------------------------------------------------------------------
    # 可选 TTL 索引
    # ------------------------------------------------------------------
    if ttl_days > 0:
        ttl_seconds = ttl_days * 24 * 3600
        try:
            col.create_index(
                [("created_at", ASCENDING)],
                name="idx_ttl_created_at",
                expireAfterSeconds=ttl_seconds,
                background=True,
            )
            print(f"[OK]   TTL 索引创建/确认: 保留 {ttl_days} 天（expireAfterSeconds={ttl_seconds}）")
        except Exception as exc:
            print(f"[WARN] TTL 索引创建失败: {exc}")
    else:
        print("[SKIP] TTL 索引未启用（ttl_days=0），如需启用请设置 MONGO_TTL_DAYS > 0")

    # ------------------------------------------------------------------
    # 打印当前集合所有索引
    # ------------------------------------------------------------------
    print("\n[INFO] 当前集合索引列表:")
    for idx in col.list_indexes():
        print(f"       {idx['name']:40s}  key={dict(idx['key'])}")

    client.close()
    print("\n[DONE] 索引初始化完成。")


def main() -> None:
    config = _get_config()
    print("=" * 60)
    print("  MongoDB 索引初始化")
    print(f"  URI        : {config['uri']}")
    print(f"  DB         : {config['db_name']}")
    print(f"  Collection : {config['collection_name']}")
    print(f"  TTL Days   : {config['ttl_days']} (0=不启用)")
    print("=" * 60)
    create_indexes(**config)


if __name__ == "__main__":
    main()
