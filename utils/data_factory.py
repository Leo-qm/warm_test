# -*- coding: utf-8 -*-
import uuid
import random
import string
from datetime import datetime

class DataFactory:
    """生成测试所需的随机数据"""

    _SURNAMES = list("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张")
    _FIRST_NAMES = list("伟芳娜敏静丽强磊洋艳勇军杰娟涛超明华雪飞平剛")

    @staticmethod
    def random_chinese_name() -> str:
        surname = random.choice(DataFactory._SURNAMES)
        given = "".join(random.choices(DataFactory._FIRST_NAMES, k=random.randint(1, 2)))
        return surname + given

    @staticmethod
    def random_id_card() -> str:
        """生成 18 位随机身份证号（简易版）"""
        area = random.choice(["370102", "110101", "320106", "440305", "510104"])
        year = random.randint(1960, 2005)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        seq = random.randint(100, 999)
        check = random.choice("0123456789X")
        return f"{area}{year}{month:02d}{day:02d}{seq}{check}"

    @staticmethod
    def random_phone() -> str:
        prefix = random.choice(["138", "139", "186", "187", "150", "151", "132", "155"])
        tail = "".join(random.choices(string.digits, k=8))
        return prefix + tail

    @staticmethod
    def random_address() -> str:
        streets = ["银杏路", "清风大道", "阳光街", "民生路", "和平巷", "建设路", "幸福大街"]
        return f"测试{random.choice(streets)}{random.randint(1, 200)}号"

    @staticmethod
    def build_test_data(is_household: str = "是") -> dict:
        """构建表单所需全量随机数据"""
        sn = uuid.uuid4().hex[:6]
        return {
            "is_household": is_household,
            "household_name": f"自动化测试_{sn}",
            "id_card": DataFactory.random_id_card(),
            "phone": DataFactory.random_phone(),
            "address": DataFactory.random_address(),
            "door_number": f"{random.randint(1, 30)}栋{random.randint(101, 2505)}室",
            "customer_id": f"KH{datetime.now().strftime('%Y%m%d')}{random.randint(1000, 9999)}",
            "applicant_name": DataFactory.random_chinese_name(),
            "applicant_id_card": DataFactory.random_id_card(),
            "applicant_phone": DataFactory.random_phone(),
            "heating_area": str(random.randint(30, 300)),
            "user_number": f"U{random.randint(10000000, 99999999)}",
            "bank_account": "622202" + "".join(random.choices(string.digits, k=13)),
            "account_holder_name": DataFactory.random_chinese_name(),
            "purchase_amount": str(random.randint(2000, 15000)),
            "invoice_number": f"INV{datetime.now().strftime('%Y%m%d')}{random.randint(100, 999)}",
            "installer_name": DataFactory.random_chinese_name() + "师傅",
            "installer_phone": DataFactory.random_phone(),
        }
