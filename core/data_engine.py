"""
DataEngine：动态标签解析引擎。

支持的内置标签:
    ${rand_str(chn, 4)}       - 随机中文字符串，长度 4
    ${rand_str(en, 8)}        - 随机英文字母串，长度 8
    ${rand_str(num, 6)}       - 随机数字串，长度 6
    ${rand_str(mix, 10)}      - 随机混合字符串，长度 10
    ${get_mobile}             - 随机手机号
    ${get_id_card}            - 随机身份证号
    ${get_bank_card}          - 随机银行卡号
    ${get_name}               - 随机中文姓名
    ${choice(['01','02'])}    - 从列表随机取一项
    ${gen_id_by_type(01)}     - 按证件类型生成证件号
    $CONTEXT{apply_no}        - 从 GlobalContext 读取变量
    ${timestamp}              - 当前 Unix 时间戳
    ${uuid}                   - UUID4 字符串
"""
from __future__ import annotations

import ast
import random
import re
import string
import time
import uuid
from typing import Any

from core.context import GlobalContext

_CTX_PATTERN = re.compile(r"\$CONTEXT\{(\w+)\}")
_TAG_PATTERN = re.compile(r"\$\{([^}]+)\}")


class DataEngine:
    """将 YAML 模板中的动态标签替换为真实数据。"""

    def render(self, data: Any, overrides: dict[str, Any] | None = None) -> Any:
        """
        对模板数据执行两阶段渲染:
        1. 应用 overrides（用例层覆盖值）。
        2. 解析剩余动态标签。

        Args:
            data:      从 TemplateManager 获取的模板深拷贝。
            overrides: 用例层传入的字段覆盖字典，支持点分路径如 {"payload.id_type": "02"}。

        Returns:
            渲染后的数据对象。
        """
        if overrides:
            data = self._apply_overrides(data, overrides)
        return self._resolve(data)

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------

    def _apply_overrides(self, data: dict, overrides: dict[str, Any]) -> dict:
        for dotted_key, value in overrides.items():
            keys = dotted_key.split(".")
            obj = data
            for k in keys[:-1]:
                obj = obj.setdefault(k, {})
            obj[keys[-1]] = value
        return data

    def _resolve(self, node: Any) -> Any:
        if isinstance(node, dict):
            return {k: self._resolve(v) for k, v in node.items()}
        if isinstance(node, list):
            return [self._resolve(item) for item in node]
        if isinstance(node, str):
            return self._render_string(node)
        return node

    def _render_string(self, value: str) -> Any:
        # 先处理 $CONTEXT{key} 引用
        value = _CTX_PATTERN.sub(self._ctx_replacer, value)

        # 若整个字符串就是一个 ${tag}，直接返回解析结果（保持原始类型）
        full_match = re.fullmatch(r"\$\{([^}]+)\}", value)
        if full_match:
            return self._dispatch(full_match.group(1))

        # 否则做字符串内插
        return _TAG_PATTERN.sub(lambda m: str(self._dispatch(m.group(1))), value)

    def _ctx_replacer(self, m: re.Match) -> str:
        return str(GlobalContext.instance().get_required(m.group(1)))

    def _dispatch(self, tag: str) -> Any:
        tag = tag.strip()

        if tag == "timestamp":
            return int(time.time())
        if tag == "uuid":
            return str(uuid.uuid4())
        if tag == "get_mobile":
            return self._gen_mobile()
        if tag == "get_id_card":
            return self._gen_id_card()
        if tag == "get_bank_card":
            return self._gen_bank_card()
        if tag == "get_name":
            return self._gen_name()

        # rand_str(type, length)
        m = re.fullmatch(r"rand_str\((\w+),\s*(\d+)\)", tag)
        if m:
            return self._rand_str(m.group(1), int(m.group(2)))

        # choice([...])
        m = re.fullmatch(r"choice\((\[.*?\])\)", tag)
        if m:
            options = ast.literal_eval(m.group(1))
            return random.choice(options)

        # gen_id_by_type(type_code)
        m = re.fullmatch(r"gen_id_by_type\((\w+)\)", tag)
        if m:
            return self._gen_id_by_type(m.group(1))

        raise ValueError(f"[DataEngine] 未知标签: ${{{tag}}}")

    # ------------------------------------------------------------------
    # 数据生成方法
    # ------------------------------------------------------------------

    @staticmethod
    def _rand_str(kind: str, length: int) -> str:
        if kind == "chn":
            pool = "".join(chr(c) for c in range(0x4E00, 0x9FA5 + 1))
        elif kind == "en":
            pool = string.ascii_letters
        elif kind == "num":
            pool = string.digits
        else:
            pool = string.ascii_letters + string.digits
        return "".join(random.choices(pool, k=length))

    @staticmethod
    def _gen_mobile() -> str:
        prefixes = ["130", "131", "132", "133", "135", "137", "138", "139",
                    "150", "151", "152", "155", "158", "159",
                    "170", "176", "177", "178", "180", "181", "182",
                    "183", "185", "186", "187", "188", "189"]
        return random.choice(prefixes) + "".join(random.choices(string.digits, k=8))

    @staticmethod
    def _gen_id_card() -> str:
        """生成符合 Luhn 校验的 18 位身份证号（仅用于测试）。"""
        area_codes = ["110101", "310101", "440301", "330101", "610101"]
        area = random.choice(area_codes)
        year = random.randint(1970, 2000)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        seq = random.randint(100, 999)
        body = f"{area}{year:04d}{month:02d}{day:02d}{seq:03d}"
        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        check_map = "10X98765432"
        total = sum(int(d) * w for d, w in zip(body, weights))
        return body + check_map[total % 11]

    @staticmethod
    def _gen_bank_card() -> str:
        prefixes = ["622202", "622848", "621226", "621483", "622588"]
        prefix = random.choice(prefixes)
        return prefix + "".join(random.choices(string.digits, k=13))

    @staticmethod
    def _gen_name() -> str:
        surnames = "赵钱孙李周吴郑王冯陈楚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
        given_pool = "伟芳娜秀英敏静冰华玲雪燕珍梅兰凤艳洁丽萍"
        length = random.choice([1, 2])
        return random.choice(surnames) + "".join(random.choices(given_pool, k=length))

    def _gen_id_by_type(self, type_code: str) -> str:
        if type_code == "01":
            return self._gen_id_card()
        if type_code == "02":
            letters = string.ascii_uppercase
            return "E" + "".join(random.choices(letters + string.digits, k=8))
        return self._rand_str("mix", 12)
