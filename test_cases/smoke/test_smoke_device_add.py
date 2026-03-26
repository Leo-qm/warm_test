# -*- coding: utf-8 -*-
"""
冒烟测试：设备新增申报流程验证
验证设备新增的创建流程：
  村级用户登录 → 点击添加 → 选择基本信息填报 → 保存并上报
"""
import pytest
import allure
from pages.login_page import LoginPage
from pages.home_page import HomePage
from pages.declaration_page import DeclarationPage
from utils.config import Config
from utils.data_factory import DataFactory
from utils.logger import log


@pytest.mark.smoke
@allure.feature("设备新增")
@allure.story("冒烟测试：设备新增申报创建")
class TestSmokeDeviceAdd:
    """冒烟测试：验证设备新增申报流程的创建环节"""

    @allure.title("设备新增冒烟测试 (是否户主: {is_household})")
    @pytest.mark.parametrize("is_household", ["是", "否"])
    def test_smoke_device_add(self, page, ocr_engine, is_household):
        """
        仅验证设备新增申报的创建流程：
        1. 村级用户登录
        2. 导航到申报管理页
        3. 点击添加
        4. 填写新增表单 → 保存并上报
        """
        login_page = LoginPage(page, ocr_engine)

        # 1. 村级用户登录
        log("冒烟测试", "========== 设备新增冒烟测试 启动 ==========", "STEP")
        login_page.logout()
        login_page.login("village")

        if Config.needs_portal_navigation():
            home_page = HomePage(page)
            home_page.enter_equipment_update_module()

        log("冒烟测试", "✅ 村级用户登录完成", "OK")

        # 2. 导航到申报管理页
        declaration_page = DeclarationPage(page)
        declaration_page.navigate_to_declaration()

        # 3. 生成设备新增表单数据（由 DataFactory 统一管理）
        test_data = DataFactory.build_test_data(is_household=is_household)
        log("冒烟测试", f"测试数据: 户主={is_household}, 身份证={test_data['applicant_id_card']}, 姓名={test_data['applicant_name']}", "STEP")

        # 4. 创建设备新增申报
        log("冒烟测试", "创建设备新增申报", "STEP")
        order_id = declaration_page.create_record(test_data)

        # 5. 验证结果
        assert order_id, "❌ 设备新增申报创建失败"
        log("冒烟测试", f"✅ 设备新增申报创建成功，编号: {order_id}", "OK")
        log("冒烟测试", "========== 设备新增冒烟测试 通过 ==========", "OK")
