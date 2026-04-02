# -*- coding: utf-8 -*-
"""
冒烟测试：设备更新流程验证
使用固定身份证号直接验证设备更新的创建流程（跳过前置设备新增）：
  村级用户登录 → 点击添加 → 选设备更新 → 输入身份证号查询 → 填写表单 → 保存
"""
import pytest
import allure
from pages.login_page import LoginPage
from pages.home_page import HomePage
from pages.declaration_page import DeclarationPage
from utils.config import Config
from utils.data_factory import DataFactory
from utils.logger import log


# 硬编码已审核通过的设备新增记录的身份证号
FIXED_ID_CARD = "320106199302014433"


@pytest.mark.smoke
@allure.feature("设备更新")
@allure.story("冒烟测试：设备更新申报创建")
class TestSmokeDeviceUpdate:
    """冒烟测试：直接用固定身份证号验证设备更新流程的创建环节"""

    @allure.title("设备更新冒烟测试 (是否户主: {is_household})")
    @pytest.mark.parametrize("is_household", ["是", "否"])
    def test_smoke_device_update(self, page, ocr_engine, is_household):
        """
        仅验证设备更新申报的创建流程（不含审核和补贴）：
        1. 村级用户登录
        2. 导航到申报管理页
        3. 点击添加 → 选择设备更新
        4. 输入身份证号 → 点击查询
        5. 填写更新表单 → 保存
        6. 用用户编号查询验证草稿保存成功
        """
        login_page = LoginPage(page, ocr_engine)

        # 1. 村级用户登录
        log("冒烟测试", f"========== 设备更新冒烟测试 启动 (是否户主: {is_household}) ==========", "STEP")
        login_page.logout()
        login_page.login("village")

        if Config.needs_portal_navigation():
            home_page = HomePage(page)
            home_page.enter_equipment_update_module()

        log("冒烟测试", "✅ 村级用户登录完成", "OK")

        # 2. 导航到申报管理页
        declaration_page = DeclarationPage(page)
        declaration_page.navigate_to_declaration()

        # 3. 生成设备更新表单数据（由 DataFactory 统一管理）
        update_data = DataFactory.build_device_update_data(is_household=is_household)
        log("冒烟测试", f"测试数据: 是否户主={is_household}, 电话={update_data['applicant_phone']}, 面积={update_data['heating_area']}", "STEP")

        # 4. 创建设备更新申报草稿（仅保存）
        log("冒烟测试", f"使用身份证号: {FIXED_ID_CARD} 创建设备更新草稿(仅保存)", "STEP")
        order_id = declaration_page.create_device_update_record(FIXED_ID_CARD, update_data, submit_action="save")

        # 5. 验证草稿保存及查询功能
        user_number = getattr(declaration_page, 'last_user_number', None)
        assert user_number, f"❌ 未能从设备更新表单中抓取到用户编号。可能身份证 {FIXED_ID_CARD} 查询无结果或前端变化。"

        log("冒烟测试", f"✅ 获取到回显用户编号: {user_number}，正在列表页进行查询验证...", "STEP")

        # 必须先回到列表页的初始状态，确保搜索条件干净
        declaration_page.navigate_to_declaration()

        # 使用用户编号进行精准查询验证
        search_success = declaration_page.search_record_by_user_number(user_number)

        assert search_success, f"❌ 在新增申报管理页使用用户编号 {user_number} 搜索草稿失败"
        log("冒烟测试", f"✅ 成功用用户编号 {user_number} 查出保存的草稿", "OK")
        log("冒烟测试", f"========== 设备更新冒烟测试 通过 (是否户主: {is_household}) ==========", "OK")
