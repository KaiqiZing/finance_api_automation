"""
IdentityFactory：金融"三要素"（姓名、证件号、手机号）联动生成器。

金融系统通常对三要素进行关联校验（如姓名与证件号必须绑定同一人），
本工厂通过构造一致性数据来绕过后端合规拦截。
"""
from __future__ import annotations

import random
import string
from dataclasses import dataclass

from faker import Faker

_fake = Faker("zh_CN")


@dataclass(frozen=True)
class Identity:
    """一套完整的测试身份信息。"""
    name: str
    id_type: str        # 01=身份证, 02=护照
    id_no: str
    mobile: str
    gender: str         # M/F
    nationality: str    # CN


class IdentityFactory:
    """生成符合金融合规校验规则的测试三要素。"""

    @classmethod
    def gen_id_card_identity(cls) -> Identity:
        """生成居民身份证三要素。"""
        gender = random.choice(["M", "F"])
        name = _fake.name_male() if gender == "M" else _fake.name_female()
        id_no = cls._gen_id_card(gender)
        mobile = cls._gen_mobile()
        return Identity(
            name=name,
            id_type="01",
            id_no=id_no,
            mobile=mobile,
            gender=gender,
            nationality="CN",
        )

    @classmethod
    def gen_passport_identity(cls) -> Identity:
        """生成护照三要素。"""
        name = _fake.name()
        id_no = "E" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        mobile = cls._gen_mobile()
        return Identity(
            name=name,
            id_type="02",
            id_no=id_no,
            mobile=mobile,
            gender=random.choice(["M", "F"]),
            nationality="CN",
        )

    @staticmethod
    def _gen_mobile() -> str:
        prefixes = ["130", "131", "135", "137", "138", "139",
                    "150", "151", "158", "159", "180", "181",
                    "185", "186", "187", "188", "189"]
        return random.choice(prefixes) + "".join(random.choices(string.digits, k=8))

    @staticmethod
    def _gen_id_card(gender: str = "M") -> str:
        """生成通过 Luhn 加权校验的 18 位身份证号。"""
        area_codes = ["110101", "310101", "440301", "330101", "610101", "500101"]
        area = random.choice(area_codes)
        year = random.randint(1975, 1998)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        seq_odd = random.choice([1, 3, 5, 7, 9])    # 奇数=男
        seq_even = random.choice([2, 4, 6, 8, 0])   # 偶数=女
        seq_digit = seq_odd if gender == "M" else seq_even
        seq = f"{random.randint(10, 99)}{seq_digit}"
        body = f"{area}{year:04d}{month:02d}{day:02d}{seq}"
        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        check_map = "10X98765432"
        total = sum(int(d) * w for d, w in zip(body, weights))
        return body + check_map[total % 11]

    @staticmethod
    def gen_bank_account_no() -> str:
        """生成测试用银行账号。"""
        prefixes = ["622202", "622848", "621226", "621483"]
        return random.choice(prefixes) + "".join(random.choices(string.digits, k=13))

    @staticmethod
    def gen_amount(min_val: float = 1000.0, max_val: float = 100000.0) -> float:
        """生成合规交易金额（保留2位小数）。"""
        return round(random.uniform(min_val, max_val), 2)
