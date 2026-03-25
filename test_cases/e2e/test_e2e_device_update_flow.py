# -*- coding: utf-8 -*-
"""
E2E 设备更新全链路业务流程测试
依赖已审核通过的设备新增记录，验证完整的设备更新业务闭环：
  前置：设备新增全流程（资格申报→审核→台账→补贴申报→补贴审核）
  第一阶段：获取原申报人身份证号 → 村级用户设备更新申报 → 镇级审核
  第二阶段：村级用户补贴申报 → 镇级审核补贴
"""
import pytest
import allure
from pages.login_page import LoginPage
from pages.home_page import HomePage
from pages.declaration_page import DeclarationPage
from pages.audit_page import AuditPage
from pages.ledger_page import LedgerPage
from utils.data_factory import DataFactory
from utils.config import Config
from utils.logger import log


class RoleManager:
    """角色切换管理器（与 full_business_flow 相同）"""

    def __init__(self, page, ocr):
        self.page = page
        self.ocr = ocr
        self.login_page = LoginPage(page, ocr)
        self.current_role = None

    def switch_to(self, role):
        if self.current_role == role:
            log("角色切换", f"当前已是 [{role}] 角色，跳过切换", "OK")
            return

        log("角色切换", f"========== 切换到 [{role}] 角色 ==========", "STEP")
        self.login_page.logout()
        self.login_page.login(role)

        if Config.needs_portal_navigation():
            home_page = HomePage(self.page)
            home_page.enter_equipment_update_module()

        self.current_role = role
        log("角色切换", f"✅ 已切换到 [{role}] 角色", "OK")


@allure.feature("E2E 设备更新全链路")
@allure.story("设备新增→审核→设备更新→审核→补贴申报→审核 完整闭环")
class TestDeviceUpdateFlow:
    """
    E2E 设备更新全链路测试
    先执行完整的设备新增流程获取已审核通过的记录，
    再基于该记录的身份证号执行设备更新流程。
    """

    @allure.title("设备更新全链路业务闭环测试")
    def test_device_update_full_flow(self, page, ocr_engine):
        """
        完整流程:
        前置: 设备新增全流程 → 获取 order_id
        步骤0: 从台账获取申报人身份证号
        步骤1: 村级用户设备更新申报
        步骤2: 镇级用户审核设备更新
        步骤3: 村级用户补贴申报
        步骤4: 镇级用户审核补贴
        """
        role_mgr = RoleManager(page, ocr_engine)
        test_data = DataFactory.build_test_data()
        original_order_id = None    # 设备新增的原始申报编号
        update_order_id = None      # 设备更新生成的新申报编号
        applicant_id_card = None    # 原申报人身份证号

        log("E2E", "=" * 60, "STEP")
        log("E2E", "  设备更新全链路业务流程测试 启动", "STEP")
        log("E2E", "=" * 60, "STEP")

        # ==================== 前置：设备新增全流程 ====================

        with allure.step("前置 - 步骤1: 村级用户创建设备新增申报"):
            log("E2E", ">>> [前置-步骤1] 村级用户：创建设备新增申报 <<<", "STEP")
            role_mgr.switch_to("village")

            declaration_page = DeclarationPage(page)
            declaration_page.navigate_to_declaration()

            original_order_id = declaration_page.create_record(test_data)
            assert original_order_id, "❌ 前置条件失败：设备新增申报创建失败"
            log("E2E", f"✅ 设备新增申报创建成功: {original_order_id}", "OK")

        with allure.step("前置 - 步骤2: 镇级用户审核设备新增"):
            log("E2E", ">>> [前置-步骤2] 镇级用户：审核设备新增 <<<", "STEP")
            role_mgr.switch_to("town")

            audit_page = AuditPage(page)
            audit_page.navigate_to_audit()

            result = audit_page.perform_approve(original_order_id, comment="自动化测试：设备新增审核通过")
            assert result, f"❌ 前置条件失败：设备新增 [{original_order_id}] 审核失败"
            log("E2E", f"✅ 设备新增 [{original_order_id}] 审核通过，数据已入台账", "OK")

        # ==================== 步骤0：获取申报人身份证号 ====================

        with allure.step("步骤0: 从台账获取原申报人身份证号"):
            log("E2E", ">>> [步骤0] 从台账获取申报人身份证号 <<<", "STEP")
            # 需先切回村级（台账在村级可见）
            role_mgr.switch_to("village")

            ledger_page = LedgerPage(page)
            ledger_page.navigate_to_ledger()

            applicant_id_card = ledger_page.get_applicant_id_card(original_order_id)
            assert applicant_id_card, f"❌ 未能从台账获取 [{original_order_id}] 的申报人身份证号"
            log("E2E", f"✅ 获取到申报人身份证号: {applicant_id_card}", "OK")

        # ==================== 步骤1：村级用户设备更新申报 ====================

        with allure.step("步骤1: 村级用户创建设备更新申报"):
            log("E2E", f">>> [步骤1] 村级用户：创建设备更新申报 (身份证: {applicant_id_card}) <<<", "STEP")

            # 导航到申报管理页
            declaration_page = DeclarationPage(page)
            declaration_page.navigate_to_declaration()

            # 使用身份证号创建设备更新申报
            update_data = {
                "is_household": test_data.get("is_household", "是"),
                "heating_area": test_data.get("heating_area", "100"),
            }
            update_order_id = declaration_page.create_device_update_record(applicant_id_card, update_data)
            assert update_order_id, "❌ 设备更新申报创建失败"
            log("E2E", f"✅ 设备更新申报创建成功: {update_order_id}", "OK")

        # ==================== 步骤2：镇级用户审核设备更新 ====================

        with allure.step("步骤2: 镇级用户审核设备更新"):
            log("E2E", ">>> [步骤2] 镇级用户：审核设备更新 <<<", "STEP")
            role_mgr.switch_to("town")

            audit_page = AuditPage(page)
            audit_page.navigate_to_audit()

            result = audit_page.perform_approve(update_order_id, comment="自动化测试：设备更新审核通过")
            assert result, f"❌ 镇级用户审核设备更新 [{update_order_id}] 失败"
            log("E2E", f"✅ 设备更新 [{update_order_id}] 审核通过，数据进入台账", "OK")

        # ==================== 步骤3：村级用户补贴申报 ====================

        with allure.step("步骤3: 村级用户发起设备更新补贴申报"):
            log("E2E", ">>> [步骤3] 村级用户：发起补贴申报 <<<", "STEP")
            role_mgr.switch_to("village")

            ledger_page = LedgerPage(page)
            ledger_page.navigate_to_ledger()

            started = ledger_page.start_subsidy_declaration(update_order_id)
            assert started, f"❌ 在台账中未能发起 [{update_order_id}] 的补贴申报"
            log("E2E", f"✅ 已进入 [{update_order_id}] 的补贴申报表单", "OK")

        with allure.step("步骤3: 填写并提交补贴表单"):
            log("E2E", ">>> [步骤3] 填写补贴申报表单 <<<", "STEP")

            subsidy_data = {
                "device_brand": test_data["device_brand"],
                "device_model": test_data["device_model"],
                "purchase_amount": test_data["purchase_amount"],
                "subsidy_amount": test_data["subsidy_amount"],
                "installer_name": test_data["installer_name"],
                "installer_phone": test_data["installer_phone"],
                "invoice_number": test_data["invoice_number"],
                "special_subsidy": "否",
            }
            submitted = ledger_page.fill_subsidy_declaration(subsidy_data)
            assert submitted, "❌ 补贴申报表单提交失败"
            form_result = submitted if isinstance(submitted, dict) else {}
            log("E2E", "✅ 补贴申报表单已提交，等待镇级审核", "OK")

        # ==================== 步骤4：镇级用户审核补贴 ====================

        with allure.step("步骤4: 镇级用户审核设备更新补贴"):
            log("E2E", ">>> [步骤4] 镇级用户：审核补贴申报 <<<", "STEP")
            role_mgr.switch_to("town")

            audit_page = AuditPage(page)
            audit_page.navigate_to_audit()

            result = audit_page.perform_approve(update_order_id, comment="自动化测试：设备更新补贴审核通过")
            assert result, f"❌ 镇级用户补贴审核 [{update_order_id}] 失败"
            log("E2E", f"✅ 设备更新补贴 [{update_order_id}] 已审核通过", "OK")

        # ==================== 流程结束 ====================
        device_info = f"{form_result.get('设备厂家', '-')}-{form_result.get('设备类型', '-')}-{form_result.get('设备型号', '-')}"
        log("E2E", "=" * 60, "OK")
        log("E2E", f"  🎉 设备更新全链路测试通过！", "OK")
        log("E2E", f"  原始设备新增编号: {original_order_id}", "OK")
        log("E2E", f"  设备更新编号: {update_order_id}", "OK")
        log("E2E", f"  申报人身份证号: {applicant_id_card}", "OK")
        log("E2E", f"  户主: {test_data['household_name']}", "OK")
        log("E2E", f"  设备: {device_info}", "OK")
        log("E2E", f"  购置金额: ¥{form_result.get('购置金额', '-')}", "OK")
        log("E2E", f"  预计补贴: ¥{form_result.get('预计补贴', '-')}", "OK")
        log("E2E", "=" * 60, "OK")
