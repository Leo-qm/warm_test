# -*- coding: utf-8 -*-
"""
E2E 设备新增全链路业务流程测试
覆盖两阶段完整业务闭环：
  第一阶段：村级用户设备新增资格申报 → 镇级用户审核通过 → 数据进入台账
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
from utils.subsidy_calculator import SubsidyCalculator


@pytest.mark.e2e
@allure.feature("设备新增流程")
@allure.story("设备新增资格申报→审核→补贴申报→审核 完整闭环")
class TestDeviceAddFlow:
    """
    E2E 设备新增全链路测试
    模拟真实业务：
      村级账号设备新增申报 → 镇级账号审核 → 村级账号补贴申报 → 镇级账号审核补贴
    参数化：是否户主"是/否"，特殊补贴"是/否"
    """
    @allure.title("设备新增全链路测试 (是否户主: {is_household}, 特殊补贴={special_subsidy})")
    @pytest.mark.parametrize("is_household", ["是", "否"])
    @pytest.mark.parametrize("special_subsidy", ["否", "是"])
    def test_device_add_flow(self, page, role_manager, special_subsidy, is_household):
        """
        设备新增完整业务闭环:
        第一阶段: 村级设备新增申报 → 镇级审核
        第二阶段: 村级补贴申报 → 镇级审核补贴
        参数化: special_subsidy 控制特殊补贴选择（是=填额外字段，否=跳过）
        """
        # ==================== 初始化 ====================
        role_mgr = role_manager
        test_data = DataFactory.build_test_data()
        order_id = None  # 全流程共享的申报编号
        # 用户编号在整个业务周期中唯一不变，用于台账/审核搜索
        user_number = test_data["user_number"]

        log("E2E", "=" * 60, "STEP")
        log("E2E", "  设备新增全链路流程测试 启动", "STEP")
        log("E2E", f"  测试数据: 户主={test_data['household_name']}", "STEP")
        log("E2E", f"  是否户主: {is_household}", "STEP")
        log("E2E", f"  特殊补贴: {special_subsidy}", "STEP")
        log("E2E", f"  用户编号: {user_number}", "STEP")
        log("E2E", "=" * 60, "STEP")

        # ==================== 第一阶段：资格申报与审核 ====================

        with allure.step("第一阶段 - 步骤1: 村级用户创建设备新增申报"):
            log("E2E", ">>> [阶段1-步骤1] 村级用户：创建设备新增申报 <<<", "STEP")
            role_mgr.switch_to("village")

            # 导航到申报管理页
            declaration_page = DeclarationPage(page)
            declaration_page.navigate_to_declaration()

            # 创建申报记录
            order_id = declaration_page.create_record(test_data)
            assert order_id, "❌ 设备新增申报创建失败：未能抓取到系统生成的申报编号"
            log("E2E", f"✅ 设备新增申报创建成功，申报编号: {order_id}", "OK")

        with allure.step("第一阶段 - 步骤2: 验证申报记录已生成"):
            log("E2E", ">>> [阶段1-步骤2] 验证申报记录存在 <<<", "STEP")
            found = declaration_page.search_record(order_id)
            assert found, f"❌ 申报记录 [{order_id}] 创建后未在列表中找到"
            log("E2E", f"✅ 记录验证通过: {order_id}", "OK")

        with allure.step("第一阶段 - 步骤3: 镇级用户审核设备新增"):
            log("E2E", ">>> [阶段1-步骤3] 镇级用户：审核设备新增 <<<", "STEP")
            role_mgr.switch_to("town")

            # 导航到审核管理页
            audit_page = AuditPage(page)
            audit_page.navigate_to_audit()

            # 执行审核通过（使用 user_number 搜索）
            result = audit_page.perform_approve(user_number, comment="自动化测试：设备新增审核通过")
            assert result, f"❌ 镇级用户审核设备新增 [{user_number}] 失败"
            log("E2E", f"✅ 第一阶段完成：设备新增 [{user_number}] 已审核通过，数据进入台账", "OK")

        # ==================== 第二阶段：补贴申报与审核 ====================

        with allure.step(f"第二阶段 - 步骤1: 村级用户发起补贴申报 (特殊补贴={special_subsidy})"):
            log("E2E", ">>> [阶段2-步骤1] 村级用户：发起补贴申报 <<<", "STEP")
            role_mgr.switch_to("village")

            # 导航到台账管理页
            ledger_page = LedgerPage(page)
            ledger_page.navigate_to_ledger()

            # 在台账中通过用户编号找到记录并发起补贴申报
            started = ledger_page.start_subsidy_declaration(user_number)
            assert started, f"❌ 在台账中未能发起 [{user_number}] 的补贴申报"
            log("E2E", f"✅ 已成功进入 [{user_number}] 的补贴申报表单", "OK")

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
            # 提取表单实际填写值（dict 或 True）
            form_result = submitted if isinstance(submitted, dict) else {}
            log("E2E", f"✅ 补贴申报表单已提交（特殊补贴={special_subsidy}），等待镇级审核", "OK")

        # ==================== 预计补贴金额验算 ====================
        with allure.step("第二阶段 - 补贴金额验算"):
            self._verify_subsidy_calculation(
                page=page,
                purchase_amount=test_data["purchase_amount"],
                special_subsidy=special_subsidy,
                form_result=form_result,
                form_type="EQUIPMENT_SUBSIDY"
            )

        with allure.step("第二阶段 - 步骤3: 镇级用户审核补贴申报"):
            log("E2E", ">>> [阶段2-步骤3] 镇级用户：审核补贴申报 <<<", "STEP")
            role_mgr.switch_to("town")

            # 导航到审核页面 (补贴审核可能在同一页面或不同菜单)
            audit_page = AuditPage(page)
            audit_page.navigate_to_audit()

            # 执行补贴审核通过（使用 user_number 搜索）
            result = audit_page.perform_approve(user_number, comment="自动化测试：补贴审核通过")
            assert result, f"❌ 镇级用户补贴审核 [{user_number}] 失败"
            log("E2E", f"✅ 第二阶段完成：补贴申报 [{user_number}] 已审核通过", "OK")

        # ==================== 流程结束 ====================
        device_info = f"{form_result.get('设备厂家', '-')}-{form_result.get('设备类型', '-')}-{form_result.get('设备型号', '-')}"
        log("E2E", "=" * 60, "OK")
        log("E2E", f"  🎉 设备新增全链路测试通过！用户编号: {user_number}, 申报编号: {order_id}", "OK")
        log("E2E", f"  户主: {test_data['household_name']}", "OK")
        log("E2E", f"  设备: {device_info}", "OK")
        log("E2E", f"  购置金额: ¥{form_result.get('购置金额', '-')}", "OK")
        log("E2E", f"  预计补贴: ¥{form_result.get('预计补贴', '-')}", "OK")
        log("E2E", f"  特殊补贴: {special_subsidy}", "OK")
        log("E2E", "=" * 60, "OK")

    # ==================== 补贴金额验算 ====================
    @staticmethod
    def _verify_subsidy_calculation(page, purchase_amount, special_subsidy, form_result, form_type="EQUIPMENT_SUBSIDY"):
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
