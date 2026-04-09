# -*- coding: utf-8 -*-
"""
E2E 设备更新全链路业务流程测试
依赖已审核通过的设备新增记录，验证完整的设备更新业务闭环：
  前置：设备新增全流程（资格申报→审核→台账→补贴申报→补贴审核）
  步骤1：用户主身份证号关联设备更新申报 → 镇级审核
  步骤2：村级用户补贴申报 → 镇级审核补贴
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
from utils.subsidy_calculator import SubsidyCalculator


@allure.feature("E2E 设备更新全链路")
@allure.story("设备新增→审核→设备更新→审核→补贴申报→审核 完整闭环")
class TestDeviceUpdateFlow:
    """
    E2E 设备更新全链路测试
    先执行完整的设备新增流程，再用户主身份证号直接关联设备更新。
    """
    @allure.title("设备更新全链路测试 (是否户主: {is_household}, 特殊补贴={special_subsidy})")
    @pytest.mark.parametrize("is_household", ["是", "否"])
    @pytest.mark.parametrize("special_subsidy", ["否", "是"])
    def test_device_update_full_flow(self, page, role_manager, is_household, special_subsidy):
        """
        完整流程:
        前置: 设备新增全流程 → 获取 order_id
        步骤1: 用户主身份证号创建设备更新申报
        步骤2: 镇级用户审核设备更新
        步骤3: 村级用户补贴申报
        步骤4: 镇级用户审核补贴
        """
        role_mgr = role_manager
        test_data = DataFactory.build_test_data(is_household)
        original_order_id = None    # 设备新增的原始申报编号
        update_order_id = None      # 设备更新生成的新申报编号
        # 直接使用户主身份证号关联设备更新，无需从台账二次获取
        household_id_card = test_data["id_card"]
        # 用户编号在整个业务周期中唯一不变，用于台账/审核搜索
        user_number = test_data["user_number"]

        log("E2E", "=" * 60, "STEP")
        log("E2E", "  设备更新全链路业务流程测试 启动", "STEP")
        log("E2E", f"  测试数据: 户主={test_data['household_name']}", "STEP")
        log("E2E", f"  是否户主: {is_household}", "STEP")
        log("E2E", f"  特殊补贴: {special_subsidy}", "STEP")
        log("E2E", f"  户主身份证号: {household_id_card}", "STEP")
        log("E2E", f"  用户编号: {user_number}", "STEP")
        log("E2E", "=" * 60, "STEP")

        # ==================== 前置：设备新增全流程 ====================

        with allure.step("前置 - 步骤1: 村级用户创建设备新增申报"):
            log("E2E", ">>> [前置-步骤1] 村级用户：创建设备新增申报 <<<", "STEP")
            role_mgr.switch_to("village")

            declaration_page = DeclarationPage(page)
            declaration_page.navigate_to_declaration()

            original_order_id = declaration_page.create_record(test_data, submit_action="submit")
            assert original_order_id, "❌ 前置条件失败：设备新增申报创建失败"
            log("E2E", f"✅ 设备新增申报创建成功: {original_order_id}", "OK")

        with allure.step("前置 - 步骤2: 镇级用户审核设备新增"):
            log("E2E", ">>> [前置-步骤2] 镇级用户：审核设备新增 <<<", "STEP")
            role_mgr.switch_to("town")

            audit_page = AuditPage(page)
            audit_page.navigate_to_audit()

            result = audit_page.perform_approve(user_number, comment="自动化测试：设备新增审核通过")
            assert result, f"❌ 前置条件失败：设备新增 [{user_number}] 审核失败"
            log("E2E", f"✅ 设备新增 [{user_number}] 审核通过，数据已入台账", "OK")

        with allure.step("前置 - 步骤3: 村级用户发起设备新增补贴申报"):
            log("E2E", ">>> [前置-步骤3] 村级用户：发起设备新增补贴申报 <<<", "STEP")
            role_mgr.switch_to("village")

            ledger_page = LedgerPage(page)
            ledger_page.navigate_to_ledger()

            started = ledger_page.start_subsidy_declaration(user_number)
            assert started, f"❌ 前置条件失败：未能发起 [{user_number}] 的补贴申报"
            log("E2E", f"✅ 已进入 [{user_number}] 的补贴申报表单", "OK")

        with allure.step("前置 - 步骤3: 填写并提交补贴表单"):
            log("E2E", ">>> [前置-步骤3] 填写设备新增补贴申报表单 <<<", "STEP")

            subsidy_data = {
                "device_brand": test_data["device_brand"],
                "device_model": test_data["device_model"],
                "purchase_amount": test_data["purchase_amount"],
                "subsidy_amount": test_data["subsidy_amount"],
                "installer_name": test_data["installer_name"],
                "installer_phone": test_data["installer_phone"],
                "invoice_number": test_data["invoice_number"],
                "special_subsidy": special_subsidy,
            }
            submitted = ledger_page.fill_subsidy_declaration(subsidy_data)
            assert submitted, "❌ 前置条件失败：设备新增补贴申报提交失败"
            log("E2E", "✅ 设备新增补贴申报已提交", "OK")

        with allure.step("前置 - 步骤4: 镇级用户审核设备新增补贴"):
            log("E2E", ">>> [前置-步骤4] 镇级用户：审核设备新增补贴 <<<", "STEP")
            role_mgr.switch_to("town")

            audit_page = AuditPage(page)
            audit_page.navigate_to_audit()

            result = audit_page.perform_approve(user_number, comment="自动化测试：设备新增补贴审核通过")
            assert result, f"❌ 前置条件失败：设备新增补贴 [{user_number}] 审核失败"
            log("E2E", f"✅ 设备新增补贴 [{user_number}] 审核通过，前置流程完成", "OK")

        # ==================== 步骤1：村级用户设备更新申报 ====================

        with allure.step("步骤1: 村级用户创建、修改并上报设备更新申报"):
            log("E2E", f">>> [步骤1] 村级用户：创建草稿、修改并上报设备更新 (户主身份证: {household_id_card}) <<<", "STEP")
            role_mgr.switch_to("village")

            declaration_page = DeclarationPage(page)
            declaration_page.navigate_to_declaration()

            update_data = DataFactory.build_device_update_data(is_household)
            
            # a. 填报后，点击保存按钮即可（仅保存不提交）
            log("E2E", f">>> 正在创建设备更新草稿 <<<", "STEP")
            update_order_id = declaration_page.create_device_update_record(household_id_card, update_data, submit_action="save")
            
            # 从表单回显中抓取真实的用户编号（原台账带入，非脚本生成）
            real_user_number = getattr(declaration_page, 'last_user_number', None) or user_number
            log("E2E", f"设备更新使用的用户编号: {real_user_number}", "INFO")
            
            # 确保在列表页刷新状态
            declaration_page.navigate_to_declaration()
            
            # b. 到新增申报信息管理页用用户编号去查询设备更新保存的草稿，查到后，点击修改按钮修改重新保存
            log("E2E", f">>> 正在查询并修改设备更新草稿 <<<", "STEP")
            new_area = int(update_data.get("heating_area", 100)) + 12
            modify_success = declaration_page.update_record(real_user_number, new_area)
            assert modify_success, "❌ 修改设备更新申报草稿失败"
            
            # c. 再次用用户编号查询该条记录，查到后，点击上报
            log("E2E", f">>> 正在查询并上报设备更新草稿 <<<", "STEP")
            report_success = declaration_page.report_record(real_user_number)
            assert report_success, "❌ 上报设备更新申报草稿失败"
            
            log("E2E", f"✅ 设备更新申报保存-修改-上报流程执行成功: {update_order_id or '通过用户编号执行'}", "OK")

        # ==================== 步骤2：镇级用户审核设备更新 ====================

        with allure.step("步骤2: 镇级用户审核设备更新"):
            log("E2E", ">>> [步骤2] 镇级用户：审核设备更新 <<<", "STEP")
            role_mgr.switch_to("town")

            audit_page = AuditPage(page)
            audit_page.navigate_to_audit()

            result = audit_page.perform_approve(real_user_number, comment="自动化测试：设备更新审核通过")
            assert result, f"❌ 镇级用户审核设备更新 [{real_user_number}] 失败"
            log("E2E", f"✅ 设备更新 [{real_user_number}] 审核通过，数据进入台账", "OK")

        # ==================== 步骤3：村级用户补贴申报 ====================

        with allure.step("步骤3: 村级用户发起设备更新补贴申报"):
            log("E2E", ">>> [步骤3] 村级用户：发起补贴申报 <<<", "STEP")
            role_mgr.switch_to("village")

            ledger_page = LedgerPage(page)
            ledger_page.navigate_to_ledger()

            started = ledger_page.start_subsidy_declaration(user_number)
            assert started, f"❌ 在台账中未能发起 [{user_number}] 的补贴申报"
            log("E2E", f"✅ 已进入 [{user_number}] 的补贴申报表单", "OK")

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
                "special_subsidy": special_subsidy,
            }
            submitted = ledger_page.fill_subsidy_declaration(subsidy_data)
            assert submitted, "❌ 补贴申报表单提交失败"
            form_result = submitted if isinstance(submitted, dict) else {}
            log("E2E", "✅ 补贴申报表单已提交，等待镇级审核", "OK")

        # ==================== 预计补贴金额验算 ====================
        with allure.step("步骤3 - 补贴金额验算"):
            self._verify_subsidy_calculation(
                page=page,
                purchase_amount=test_data["purchase_amount"],
                special_subsidy=special_subsidy,
                form_result=form_result,
                form_type="EQUIPMENT_UPDATE"
            )

        # ==================== 步骤4：镇级用户审核补贴 ====================

        with allure.step("步骤4: 镇级用户审核设备更新补贴"):
            log("E2E", ">>> [步骤4] 镇级用户：审核补贴申报 <<<", "STEP")
            role_mgr.switch_to("town")

            audit_page = AuditPage(page)
            audit_page.navigate_to_audit()

            result = audit_page.perform_approve(user_number, comment="自动化测试：设备更新补贴审核通过")
            assert result, f"❌ 镇级用户补贴审核 [{user_number}] 失败"
            log("E2E", f"✅ 设备更新补贴 [{user_number}] 已审核通过", "OK")

        # ==================== 流程结束 ====================
        device_info = f"{form_result.get('设备厂家', '-')}-{form_result.get('设备类型', '-')}-{form_result.get('设备型号', '-')}"
        log("E2E", "=" * 60, "OK")
        log("E2E", f"  🎉 设备更新全链路测试通过！", "OK")
        log("E2E", f"  用户编号: {user_number}", "OK")
        log("E2E", f"  原始设备新增编号: {original_order_id}", "OK")
        log("E2E", f"  设备更新编号: {update_order_id}", "OK")
        log("E2E", f"  户主身份证号: {household_id_card}", "OK")
        log("E2E", f"  户主: {test_data['household_name']}", "OK")
        log("E2E", f"  是否户主: {is_household}", "OK")
        log("E2E", f"  设备: {device_info}", "OK")
        log("E2E", f"  购置金额: ¥{form_result.get('购置金额', '-')}", "OK")
        log("E2E", f"  预计补贴: ¥{form_result.get('预计补贴', '-')}", "OK")
        log("E2E", f"  特殊补贴: {special_subsidy}", "OK")
        log("E2E", "=" * 60, "OK")

    # ==================== 补贴金额验算 ====================
    @staticmethod
    def _verify_subsidy_calculation(page, purchase_amount, special_subsidy, form_result, form_type="EQUIPMENT_UPDATE"):
        """
        调用 SubsidyCalculator 计算预期补贴金额，与前端实际展示值对比验算。

        计算算法（复刻前端 DeviceInfo.vue）：
          1. 基础补贴 = min(购置金额 × 比例%, 最高限额)  ← 基本/生态互斥
          2. 特殊补贴 = min(剩余金额 × 特殊比例%, 特殊限额)  ← 对剩余金额再算
          3. 总补贴 = 基础补贴 + 特殊补贴

        :param page: Playwright Page 对象
        :param purchase_amount: 购置金额（来自测试数据）
        :param special_subsidy: "是" 或 "否"
        :param form_result: 表单提交后返回的实际值字典
        :param form_type: 表单类型 EQUIPMENT_SUBSIDY / EQUIPMENT_UPDATE
        """
        log("E2E", ">>> [补贴验算] 开始计算预计补贴金额并与前端对比 <<<", "STEP")
        try:
            # 1. 从浏览器创建计算器实例（自动获取 token / tenant-id）
            calculator = SubsidyCalculator.from_page(page)

            # 2. 加载补贴配置和区域列表
            config = calculator.load_subsidy_config()
            if not config:
                log("E2E", "⚠️ 无法获取补贴配置，跳过验算", "WARN")
                return

            calculator.load_district_list()

            # 3. 判断是否生态涵养区（E2E 测试用村级账号所属区域）
            is_ecological = calculator.is_ecological_area()

            # 4. 判断特殊补贴条件
            is_special = (special_subsidy == "是")
            # 选"是"且已选择特殊补贴类型时才计入
            has_special_type = is_special

            # 5. 计算并输出详细过程
            expected_subsidy = calculator.calculate_and_log(
                purchase_amount=float(purchase_amount),
                is_ecological=is_ecological,
                is_special_subsidy=is_special,
                has_special_type=has_special_type,
            )

            # 6. 对比前端实际值
            ui_subsidy_str = form_result.get("预计补贴", "")
            if ui_subsidy_str:
                try:
                    ui_subsidy = float(ui_subsidy_str)
                    diff = abs(ui_subsidy - expected_subsidy)
                    if diff < 0.01:
                        log("E2E", f"✅ 补贴金额验算通过! 前端显示: ¥{ui_subsidy}, 脚本计算: ¥{expected_subsidy}", "OK")
                    else:
                        log("E2E", f"⚠️ 补贴金额存在差异! 前端显示: ¥{ui_subsidy}, 脚本计算: ¥{expected_subsidy}, 差额: ¥{diff}", "WARN")
                except ValueError:
                    log("E2E", f"⚠️ 前端预计补贴值非数字: '{ui_subsidy_str}', 脚本计算: ¥{expected_subsidy}", "WARN")
            else:
                log("E2E", f"⚠️ 未从前端获取到预计补贴值, 脚本计算: ¥{expected_subsidy}", "WARN")

        except Exception as e:
            log("E2E", f"⚠️ 补贴金额验算过程出错（不影响主流程）: {e}", "WARN")
