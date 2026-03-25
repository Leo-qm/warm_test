# -*- coding: utf-8 -*-
"""
E2E 全链路业务流程测试
覆盖两阶段完整业务闭环：
  第一阶段：村级用户资格申报 → 镇级用户审核通过 → 数据进入台账
  第二阶段：村级用户补贴申报 → 镇级用户审核补贴
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
    """
    角色切换管理器
    在同一浏览器会话中实现村级/镇级账号之间的无缝切换，
    每次切换会清理登录态并重新走登录+门户流程。
    """

    def __init__(self, page, ocr):
        self.page = page
        self.ocr = ocr
        self.login_page = LoginPage(page, ocr)
        self.current_role = None

    def switch_to(self, role):
        """
        切换到指定角色 (如 'village', 'town')
        如果当前已是该角色则跳过
        """
        if self.current_role == role:
            log("角色切换", f"当前已是 [{role}] 角色，跳过切换", "OK")
            return

        log("角色切换", f"========== 切换到 [{role}] 角色 ==========", "STEP")

        # 1. 登出当前账号
        self.login_page.logout()

        # 2. 以新角色登录
        self.login_page.login(role)

        # 3. 进入门户
        home_page = HomePage(self.page)
        home_page.enter_equipment_update_module()

        self.current_role = role
        log("角色切换", f"✅ 已成功切换到 [{role}] 角色并进入业务系统", "OK")


@pytest.mark.e2e
@allure.feature("全链路业务流程")
@allure.story("资格申报→审核→补贴申报→审核 两阶段完整闭环")
class TestFullBusinessFlow:
    """
    E2E 两阶段全链路测试
    模拟真实业务：
      村级账号填报 → 镇级账号审核 → 村级账号补贴申报 → 镇级账号审核补贴
    参数化：特殊补贴"是/否"分别验证
    """

    @allure.title("两阶段全链路业务闭环测试 (特殊补贴={special_subsidy})")
    @pytest.mark.parametrize("special_subsidy", ["否", "是"])
    def test_full_two_phase_flow(self, page, ocr_engine, special_subsidy):
        """
        完整的两阶段业务闭环:
        第一阶段: 村级申报 → 村级上报 → 镇级审核
        第二阶段: 村级补贴申报 → 镇级审核补贴
        参数化: special_subsidy 控制特殊补贴选择（是=填额外字段，否=跳过）
        """
        # ==================== 初始化 ====================
        role_mgr = RoleManager(page, ocr_engine)
        test_data = DataFactory.build_test_data()
        order_id = None  # 全流程共享的申报编号

        log("E2E", "=" * 60, "STEP")
        log("E2E", "  两阶段全链路业务流程测试 启动", "STEP")
        log("E2E", f"  测试数据: 户主={test_data['household_name']}", "STEP")
        log("E2E", f"  特殊补贴: {special_subsidy}", "STEP")
        log("E2E", "=" * 60, "STEP")

        # ==================== 第一阶段：资格申报与审核 ====================

        with allure.step("第一阶段 - 步骤1: 村级用户创建资格申报"):
            log("E2E", ">>> [阶段1-步骤1] 村级用户：创建资格申报 <<<", "STEP")
            role_mgr.switch_to("village")

            # 导航到申报管理页
            declaration_page = DeclarationPage(page)
            declaration_page.navigate_to_declaration()

            # 创建申报记录
            order_id = declaration_page.create_record(test_data)
            assert order_id, "❌ 新增申报记录失败：未能抓取到系统生成的申报编号"
            log("E2E", f"✅ 资格申报创建成功，申报编号: {order_id}", "OK")

        with allure.step("第一阶段 - 步骤2: 验证申报记录已生成"):
            log("E2E", ">>> [阶段1-步骤2] 验证申报记录存在 <<<", "STEP")
            found = declaration_page.search_record(order_id)
            assert found, f"❌ 申报记录 [{order_id}] 创建后未在列表中找到"
            log("E2E", f"✅ 记录验证通过: {order_id}", "OK")

        with allure.step("第一阶段 - 步骤3: 镇级用户审核资格申报"):
            log("E2E", ">>> [阶段1-步骤3] 镇级用户：审核资格申报 <<<", "STEP")
            role_mgr.switch_to("town")

            # 导航到审核管理页
            audit_page = AuditPage(page)
            audit_page.navigate_to_audit()

            # 执行审核通过
            result = audit_page.perform_approve(order_id, comment="自动化测试：资格审核通过")
            assert result, f"❌ 镇级用户审核记录 [{order_id}] 失败"
            log("E2E", f"✅ 第一阶段完成：资格申报 [{order_id}] 已审核通过，数据进入台账", "OK")

        # ==================== 第二阶段：补贴申报与审核 ====================

        with allure.step(f"第二阶段 - 步骤1: 村级用户发起补贴申报 (特殊补贴={special_subsidy})"):
            log("E2E", ">>> [阶段2-步骤1] 村级用户：发起补贴申报 <<<", "STEP")
            role_mgr.switch_to("village")

            # 导航到台账管理页
            ledger_page = LedgerPage(page)
            ledger_page.navigate_to_ledger()

            # 在台账中找到记录并发起补贴申报
            started = ledger_page.start_subsidy_declaration(order_id)
            assert started, f"❌ 在台账中未能发起 [{order_id}] 的补贴申报"
            log("E2E", f"✅ 已成功进入 [{order_id}] 的补贴申报表单", "OK")

        with allure.step(f"第二阶段 - 步骤2: 填写补贴表单 (特殊补贴={special_subsidy})"):
            log("E2E", f">>> [阶段2-步骤2] 填写补贴申报表单 (特殊补贴={special_subsidy}) <<<", "STEP")

            # 使用 DataFactory 生成的补贴字段填写表单
            subsidy_data = {
                "device_brand": test_data["device_brand"],
                "device_model": test_data["device_model"],
                "purchase_amount": test_data["purchase_amount"],
                "subsidy_amount": test_data["subsidy_amount"],
                "installer_name": test_data["installer_name"],
                "installer_phone": test_data["installer_phone"],
                "invoice_number": test_data["invoice_number"],
                "special_subsidy": special_subsidy,  # 控制是否申报特殊补贴
            }
            submitted = ledger_page.fill_subsidy_declaration(subsidy_data)
            assert submitted, f"❌ 补贴申报表单提交失败"
            log("E2E", f"✅ 补贴申报表单已提交（特殊补贴={special_subsidy}），等待镇级审核", "OK")

        with allure.step("第二阶段 - 步骤3: 镇级用户审核补贴申报"):
            log("E2E", ">>> [阶段2-步骤3] 镇级用户：审核补贴申报 <<<", "STEP")
            role_mgr.switch_to("town")

            # 导航到审核页面 (补贴审核可能在同一页面或不同菜单)
            audit_page = AuditPage(page)
            audit_page.navigate_to_audit()

            # 执行补贴审核通过
            result = audit_page.perform_approve(order_id, comment="自动化测试：补贴审核通过")
            assert result, f"❌ 镇级用户补贴审核 [{order_id}] 失败"
            log("E2E", f"✅ 第二阶段完成：补贴申报 [{order_id}] 已审核通过", "OK")

        # ==================== 流程结束 ====================
        log("E2E", "=" * 60, "OK")
        log("E2E", f"  🎉 两阶段全链路测试通过！申报编号: {order_id}", "OK")
        log("E2E", f"  户主: {test_data['household_name']}", "OK")
        log("E2E", f"  设备: {test_data['device_brand']} {test_data['device_model']}", "OK")
        log("E2E", f"  补贴: ¥{test_data['subsidy_amount']}", "OK")
        log("E2E", f"  特殊补贴: {special_subsidy}", "OK")
        log("E2E", "=" * 60, "OK")
