# -*- coding: utf-8 -*-
"""
随机数据生成工厂模块
用于在 UI 或接口测试中快速生成符合业务逻辑的伪造数据（如中文名、身份证、手机号等）。
"""

import uuid
import random
import string
from datetime import datetime

class DataFactory:
    """
    数据工厂类
    提供静态方法用于生成各种类型的随机测试数据。
    """

    # 预设姓氏与常用名字，用于生成随机姓名
    _SURNAMES = list("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张")
    _FIRST_NAMES = list("伟芳娜敏静丽强磊洋艳勇军杰娟涛超明华雪飞平剛")

    @staticmethod
    def random_chinese_name() -> str:
        """
        随机生成一个 2~3 字的中文姓名
        :return: 姓名字符串
        """
        surname = random.choice(DataFactory._SURNAMES)
        given = "".join(random.choices(DataFactory._FIRST_NAMES, k=random.randint(1, 2)))
        return surname + given

    @staticmethod
    def random_id_card() -> str:
        """
        生成符合长度要求的 18 位随机身份证号 (简易算法)
        注意：仅满足基本的正则校验长度，不保证符合复杂的地区/校验位算法。
        :return: 身份证号码字符串
        """
        area = random.choice(["370102", "110101", "320106", "440305", "510104"])
        year = random.randint(1960, 2005)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        seq = random.randint(100, 999)
        check = random.choice("0123456789X")
        return f"{area}{year}{month:02d}{day:02d}{seq}{check}"

    @staticmethod
    def random_phone() -> str:
        """
        随机生成符合中国手机号段规律的 11 位号码
        :return: 手机号字符串
        """
        prefix = random.choice(["138", "139", "186", "187", "150", "151", "132", "155"])
        tail = "".join(random.choices(string.digits, k=8))
        return prefix + tail

    @staticmethod
    def random_address() -> str:
        """
        生成随机的详细地址
        :return: 地址字符串
        """
        streets = ["银杏路", "清风大道", "阳光街", "民生路", "和平巷", "建设路", "幸福大街"]
        return f"测试{random.choice(streets)}{random.randint(1, 200)}号"

    @staticmethod
    def build_test_data(is_household: str = "是") -> dict:
        """
        自动化构建业务表单所需的全量随机字典数据
        包含户主名、身份证、手机号、申报地址、银行卡、购置金额等。
        
        :param is_household: 是否为本户
        :return: 预填写的表单数据字典
        """
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
            # 补贴申报专用字段
            "energy_type": random.choice(["煤改电", "煤改气", "生物质"]),
            "declaration_type": random.choice(["设备新增", "设备更新"]),
            "device_brand": random.choice(["格力", "美的", "海尔", "大金"]),
            "device_model": f"WS-MOD-{random.randint(100, 999)}",
            "subsidy_amount": str(random.randint(500, 5000)),
        }

    @staticmethod
    def build_device_update_data(is_household: str = "是") -> dict:
        """
        构建设备更新表单所需的补充数据
        设备更新查询后，原档案信息和部分申请人信息已预填，
        此方法生成需要手动填写的空字段数据。
        
        :param is_household: 是否为户主
        :return: 设备更新表单补充数据字典
        """
        data = {
            "is_household": is_household,
            "applicant_phone": DataFactory.random_phone(),
            "heating_area": str(random.randint(30, 300)),
            # 基本信息区块
            "user_number": f"U{random.randint(10000000, 99999999)}",
            "bank_account": "622202" + "".join(random.choices(string.digits, k=13)),
            "account_holder_name": DataFactory.random_chinese_name(),
        }
        # 非户主时，申报人信息不会从原台账自动带入，需要手动填写
        if is_household == "否":
            data["applicant_name"] = DataFactory.random_chinese_name()
            data["applicant_id_card"] = DataFactory.random_id_card()
        return data
