"""
system_ruoyi_queries：RuoYi 系统模块常用 DB 查询封装。

依赖: utils.db_client.DBClient（需在 conftest.py 中提前注册 "ry_cloud" 别名）

提供:
    SECOND_LEVEL_DEPT_IDS        二级部门 ID 常量元组 (101, 102)
    fetch_random_third_level_dept_id(second_dept_id)
                                 随机取一条三级子部门 dept_id；无子部门返回 None
    fetch_dept_id_by_dept_name(dept_name, parent_id)
                                 按 deptName（+可选 parentId）精确查 dept_id；未找到返回 None
    fetch_all_eligible_post_ids() 全部状态正常的岗位 post_id 列表（可能为空）
    fetch_all_eligible_role_ids() 全部可绑定的普通角色 role_id 列表（排除超管，可能为空）
    fetch_one_post_id()          随机取一条有效岗位 post_id；无记录返回 None
    fetch_post_id_by_post_code(post_code)
                                 按 postCode 精确查询 post_id；未找到返回 None
    fetch_notice_id_by_notice_title(notice_title)
                                 按 notice_title 精确查询 notice_id（多条取最大 ID）；未找到返回 None
    fetch_one_role_id()          随机取一条有效角色 role_id（排除超级管理员）；无记录返回 None
    fetch_role_id_by_role_key(role_key)
                                 按 roleKey 精确查询 role_id；未找到返回 None
    count_sys_user_post_link(user_id, post_id)
                                 sys_user_post 中 (user_id, post_id) 关联行数
    count_sys_user_role_link(user_id, role_id)
                                 sys_user_role 中 (user_id, role_id) 关联行数
    purge_sys_user_bindings(user_id)
                                 测试收尾：物理删除该用户在 sys_user_role/sys_user_post 的关联行

字段说明（与 sys_dept/sys_post/sys_role DDL 一致）:
    del_flag  逻辑删除标记，'0' 未删除
    status    状态，'0' 正常
"""
from __future__ import annotations

from utils.db_client import DBClient
from utils.logger import logger

# 固定二级部门 ID，与若依系统初始化数据一致
SECOND_LEVEL_DEPT_IDS: tuple[int, ...] = (101, 102)


def fetch_random_third_level_dept_id(second_dept_id: int) -> int | None:
    """
    从 sys_dept 表随机取一条挂在指定二级部门下的三级子部门 ID。

    Args:
        second_dept_id: 二级部门的 dept_id（通常为 101 或 102）。

    Returns:
        三级子部门的 dept_id（int），若该二级下无可用子部门则返回 None。
    """
    db = DBClient.instance("ry_cloud")
    row = db.fetch_one(
        "SELECT dept_id FROM sys_dept "
        "WHERE parent_id = %s AND del_flag = '0' AND status = '0' "
        "ORDER BY RAND() LIMIT 1",
        (second_dept_id,),
    )
    if row is None:
        logger.warning(
            "[system_ruoyi_queries] 二级部门 {} 下无可用三级子部门", second_dept_id
        )
        return None
    dept_id = int(row["dept_id"])
    logger.debug(
        "[system_ruoyi_queries] 随机三级 dept_id={} (parent={})", dept_id, second_dept_id
    )
    return dept_id


def fetch_dept_id_by_dept_name(
    dept_name: str,
    parent_id: int | None = None,
) -> int | None:
    """
    按部门名称精确查询部门 ID（用于新增部门后清理或断言）。

    RuoYi 的 POST /system/dept 成功响应不返回 deptId，需通过此函数从 DB 回查。

    Args:
        dept_name: 部门名称，对应 sys_dept.dept_name（精确匹配）。
        parent_id: 可选，父部门 ID；传入时作为附加过滤条件以避免重名干扰。

    Returns:
        dept_id（int），若未找到则返回 None；多条时取最近插入的一条（dept_id DESC）。
    """
    db = DBClient.instance("ry_cloud")
    if parent_id is not None:
        row = db.fetch_one(
            "SELECT dept_id FROM sys_dept "
            "WHERE dept_name = %s AND parent_id = %s AND del_flag = '0' "
            "ORDER BY dept_id DESC LIMIT 1",
            (dept_name, parent_id),
        )
    else:
        row = db.fetch_one(
            "SELECT dept_id FROM sys_dept "
            "WHERE dept_name = %s AND del_flag = '0' "
            "ORDER BY dept_id DESC LIMIT 1",
            (dept_name,),
        )
    if row is None:
        logger.warning(
            "[system_ruoyi_queries] sys_dept 中未找到 dept_name={} parent_id={}",
            dept_name,
            parent_id,
        )
        return None
    dept_id = int(row["dept_id"])
    logger.debug(
        "[system_ruoyi_queries] dept_name={} parent_id={} → dept_id={}",
        dept_name,
        parent_id,
        dept_id,
    )
    return dept_id


def fetch_all_eligible_post_ids() -> list[int]:
    """
    查询 sys_post 中全部状态为正常的岗位 ID（与 fetch_one_post_id 过滤条件一致）。

    Returns:
        post_id 升序列表；无记录时返回空列表。
    """
    db = DBClient.instance("ry_cloud")
    rows = db.fetch_all(
        "SELECT post_id FROM sys_post WHERE status = '0' ORDER BY post_id ASC"
    )
    ids = [int(r["post_id"]) for r in rows]
    logger.debug("[system_ruoyi_queries] eligible post_ids count={}", len(ids))
    return ids


def fetch_all_eligible_role_ids() -> list[int]:
    """
    查询 sys_role 中全部可分配给普通用户的角色 ID（排除 role_id=1 超级管理员）。

    过滤条件与 fetch_one_role_id 一致：status='0'、del_flag='0'。

    Returns:
        role_id 升序列表；无记录时返回空列表。
    """
    db = DBClient.instance("ry_cloud")
    rows = db.fetch_all(
        "SELECT role_id FROM sys_role "
        "WHERE status = '0' AND del_flag = '0' AND role_id != 1 "
        "ORDER BY role_id ASC"
    )
    ids = [int(r["role_id"]) for r in rows]
    logger.debug("[system_ruoyi_queries] eligible role_ids count={}", len(ids))
    return ids


def fetch_one_post_id() -> int | None:
    """
    从 sys_post 表随机取一条状态正常的岗位 ID。

    Returns:
        post_id（int），若表中无可用记录则返回 None。
    """
    db = DBClient.instance("ry_cloud")
    row = db.fetch_one(
        "SELECT post_id FROM sys_post WHERE status = '0' ORDER BY RAND() LIMIT 1"
    )
    if row is None:
        logger.warning("[system_ruoyi_queries] sys_post 中无可用岗位记录")
        return None
    post_id = int(row["post_id"])
    logger.debug("[system_ruoyi_queries] 随机 post_id={}", post_id)
    return post_id


def fetch_post_id_by_post_code(post_code: str) -> int | None:
    """
    按 postCode 精确查询岗位 ID（用于新增岗位后清理或断言）。

    Args:
        post_code: 岗位编码（唯一标识），对应 sys_post.post_code。

    Returns:
        post_id（int），若未找到则返回 None。
    """
    db = DBClient.instance("ry_cloud")
    row = db.fetch_one(
        "SELECT post_id FROM sys_post WHERE post_code = %s LIMIT 1",
        (post_code,),
    )
    if row is None:
        logger.warning("[system_ruoyi_queries] sys_post 中未找到 post_code={}", post_code)
        return None
    post_id = int(row["post_id"])
    logger.debug("[system_ruoyi_queries] post_code={} → post_id={}", post_code, post_id)
    return post_id


def fetch_notice_id_by_notice_title(notice_title: str) -> int | None:
    """
    按公告标题精确查询 notice_id（用于新增公告后清理或断言）。

    对应表 sys_notice；若存在同名多条记录，取 notice_id 最大的一条。

    Args:
        notice_title: 公告标题（唯一性由用例保证，建议带随机后缀）。

    Returns:
        notice_id（int），若未找到则返回 None。
    """
    db = DBClient.instance("ry_cloud")
    row = db.fetch_one(
        "SELECT notice_id FROM sys_notice WHERE notice_title = %s "
        "ORDER BY notice_id DESC LIMIT 1",
        (notice_title,),
    )
    if row is None:
        logger.warning(
            "[system_ruoyi_queries] sys_notice 中未找到 notice_title={}", notice_title
        )
        return None
    notice_id = int(row["notice_id"])
    logger.debug(
        "[system_ruoyi_queries] notice_title={} → notice_id={}", notice_title, notice_id
    )
    return notice_id


def fetch_one_role_id() -> int | None:
    """
    从 sys_role 表随机取一条状态正常的普通角色 ID（排除 role_id=1 超级管理员）。

    Returns:
        role_id（int），若表中无可用记录则返回 None。
    """
    db = DBClient.instance("ry_cloud")
    row = db.fetch_one(
        "SELECT role_id FROM sys_role "
        "WHERE status = '0' AND del_flag = '0' AND role_id != 1 "
        "ORDER BY RAND() LIMIT 1"
    )
    if row is None:
        logger.warning("[system_ruoyi_queries] sys_role 中无可用普通角色记录")
        return None
    role_id = int(row["role_id"])
    logger.debug("[system_ruoyi_queries] 随机 role_id={}", role_id)
    return role_id


def fetch_role_id_by_role_key(role_key: str) -> int | None:
    """
    按 roleKey 精确查询角色 ID（用于新增角色后验证写入是否成功）。

    Args:
        role_key: 角色权限字符串（唯一标识），对应 sys_role.role_key。

    Returns:
        role_id（int），若未找到则返回 None。
    """
    db = DBClient.instance("ry_cloud")
    row = db.fetch_one(
        "SELECT role_id FROM sys_role "
        "WHERE role_key = %s AND del_flag = '0' LIMIT 1",
        (role_key,),
    )
    if row is None:
        logger.warning("[system_ruoyi_queries] sys_role 中未找到 role_key={}", role_key)
        return None
    role_id = int(row["role_id"])
    logger.debug("[system_ruoyi_queries] role_key={} → role_id={}", role_key, role_id)
    return role_id


def count_sys_user_post_link(user_id: int, post_id: int) -> int:
    """统计 sys_user_post 中指定用户与岗位的关联行数。"""
    db = DBClient.instance("ry_cloud")
    row = db.fetch_one(
        "SELECT COUNT(*) AS cnt FROM sys_user_post "
        "WHERE user_id = %s AND post_id = %s",
        (user_id, post_id),
    )
    return int(row["cnt"]) if row else 0


def count_sys_user_role_link(user_id: int, role_id: int) -> int:
    """统计 sys_user_role 中指定用户与角色的关联行数。"""
    db = DBClient.instance("ry_cloud")
    row = db.fetch_one(
        "SELECT COUNT(*) AS cnt FROM sys_user_role "
        "WHERE user_id = %s AND role_id = %s",
        (user_id, role_id),
    )
    return int(row["cnt"]) if row else 0


def purge_sys_user_bindings(user_id: int) -> None:
    """
    删除指定用户在 sys_user_role / sys_user_post 中的全部关联行。

    用于接口删除用户后仍残留关联、导致「角色已分配不能删」时的测试环境收尾。
    """
    db = DBClient.instance("ry_cloud")
    db.execute("DELETE FROM sys_user_role WHERE user_id = %s", (user_id,))
    db.execute("DELETE FROM sys_user_post WHERE user_id = %s", (user_id,))
    logger.debug("[system_ruoyi_queries] purged role/post bindings for user_id={}", user_id)
