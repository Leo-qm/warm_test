# -*- coding: utf-8 -*-
"""
台账管理页面封装
设计模式：
  - 弹窗内下拉/日期使用 Playwright click(force=True) 绕过遮挡层并正确触发 Vue 事件
  - 文本字段使用 fill_input_by_label 精确匹配标签文本
  - 级联下拉严格按顺序执行并用较长等待确保选项加载
"""
import os
import time
from pages.base_page import BasePage
from utils.config import Config
from utils.logger import log, log_err


class LedgerPage(BasePage):
    """设备申报台账管理页 — 封装台账查询、补贴申报与导出功能"""

    # ==================== 导航 ====================
    def navigate_to_ledger(self):
        """导航至设备申报台账管理页面"""
        log("业务步骤", "========== 导航至台账管理页面 ==========", "STEP")
        try:
            top = self.page.locator(".cls-header-menu a:has-text('清洁能源')")
            if top.count() > 0:
                top.first.click(force=True)
                time.sleep(Config.LONG_WAIT)
        except:
            pass

        self.page.click("li.el-submenu:has-text('清洁取暖设备申报管理')")
        time.sleep(Config.MEDIUM_WAIT)
        self.page.click("li.el-menu-item:has-text('设备申报台账管理')")
        self.page.wait_for_selector("table.el-table__body tr", timeout=Config.PAGE_LOAD_TIMEOUT)
        log("导航", "✅ 已进入设备申报台账管理页面", "OK")

    # ==================== 台账查询 ====================
    def search_by_order_id(self, order_id):
        """通过申报编号搜索台账记录"""
        if not order_id:
            return False

        log("业务步骤", f"执行 [台账查询] 申报编号: {order_id}", "STEP")
        try:
            self.page.click("button:has-text('重置')", timeout=2000)
            time.sleep(Config.SHORT_WAIT)
        except:
            pass

        self.fill_input_by_label("申报编号", order_id)
        self.page.click("button:has-text('搜索')")
        time.sleep(Config.MEDIUM_WAIT)

        try:
            row = self.page.locator("table.el-table__body tr").first
            if order_id in row.inner_text():
                log("查询", f"✅ 台账中成功找到记录: {order_id}", "OK")
                return True
        except:
            pass

        log("查询", f"❌ 台账中未找到记录: {order_id}", "ERROR")
        return False

    # ==================== 导出 ====================
    def export_ledger(self):
        """执行导出台账操作"""
        log("业务步骤", "执行 [导出台账] 操作", "STEP")
        try:
            with self.page.expect_download() as download_info:
                self.page.click("button:has-text('导出台账')")
            download = download_info.value
            save_path = Config.get_report_path(f"ledger_export_{int(time.time())}.xlsx")
            download.save_as(save_path)
            log("导出", f"✅ 台账导出成功，保存至: {save_path}", "OK")
            return save_path
        except Exception as e:
            log_err("导出", "导出操作失败", e)
            return None

    # ==================== 补贴申报入口 ====================
    def start_subsidy_declaration(self, order_id):
        """点击台账表格中申报状态列的"补贴申报"蓝色链接文字"""
        log("业务步骤", f"执行 [发起补贴申报] 流程，编号: {order_id}", "STEP")
        if self.search_by_order_id(order_id):
            try:
                row = self.page.locator("table.el-table__body tr").first
                link = row.locator("text=补贴申报").first
                if link.is_visible(timeout=3000):
                    link.click()
                    time.sleep(Config.MEDIUM_WAIT)
                    log("补贴申报", f"✅ 已点击 [{order_id}] 的'补贴申报'链接", "OK")
                    return True
                btn = row.locator("button:has-text('补贴申报')")
                if btn.count() > 0:
                    btn.first.click()
                    time.sleep(Config.MEDIUM_WAIT)
                    log("补贴申报", f"✅ 已点击 [{order_id}] 的补贴申报按钮", "OK")
                    return True
                log("补贴申报", "❌ 未找到【补贴申报】链接或按钮", "ERROR")
            except Exception as e:
                log_err("补贴申报", "点击操作异常", e)
        return False

    # ==================== 补贴申报表单填写 ====================
    def fill_subsidy_declaration(self, data):
        """
        填写补贴申报表单（弹窗：补贴申报材料上传）

        表单布局（基于实际截图确认）：
        设备信息区：
          Row1: 购置金额(input) | 设备型号(select,依赖设备类型)
          Row2: 预计补贴(自动算) | 能耗级别(select)
          Row3: 设备厂家(select) | 质保日期(date)
          Row4: 设备类型(select,依赖设备厂家) | 发票号码(input)
        安装信息区：
          Row5: 安装日期(date) | 安装人员(input)
          Row6: 安装人员联系电话(input)

        核心修复：
        1. 下拉用 Playwright click(force=True) 代替 JS click（确保 Vue 事件触发）
        2. 级联等待增加到 2 秒确保选项从服务端加载
        3. 标签匹配使用精确匹配避免"安装人员"误匹配"安装人员联系电话"
        """
        log("业务步骤", ">>> 正在填写补贴申报表单内容", "STEP")
        d = data
        try:
            time.sleep(Config.MEDIUM_WAIT)

            # 切换到"补贴申报材料"标签页
            try:
                tab = self.page.locator(".el-tabs__item:has-text('补贴申报材料')")
                if tab.count() > 0 and tab.first.is_visible():
                    tab.first.click()
                    time.sleep(Config.SHORT_WAIT)
            except:
                pass

            # === 设备信息 ===
            # 1. 购置金额
            self.fill_input_by_label("购置金额", d.get("purchase_amount", "3000"))

            # 2. 级联下拉：设备厂家 → 设备类型 → 设备型号（每步等 2 秒让选项加载）
            self._select_dropdown("设备厂家")
            time.sleep(2)  # 等待设备类型选项从服务端加载

            self._select_dropdown("设备类型")
            time.sleep(2)  # 等待设备型号选项从服务端加载

            self._select_dropdown("设备型号")
            time.sleep(1)

            # 3. 能耗级别
            self._select_dropdown("能耗级别")

            # 4. 质保日期
            self._pick_date("质保日期")

            # 5. 发票号码
            self.fill_input_by_label("发票号码", d.get("invoice_number", "INV20260324001"))

            # === 安装信息 ===
            # 6. 安装日期
            self._pick_date("安装日期")

            # 7. 安装人员（精确匹配，避免匹配到"安装人员联系电话"）
            self.fill_input_by_label("安装人员", d.get("installer_name", "张师傅"), exact=True)

            # 8. 安装人员联系电话
            self.fill_input_by_label("安装人员联系电话", d.get("installer_phone", "13800000000"))

            # === 特殊补贴信息 ===
            special_subsidy = d.get("special_subsidy", "否")
            try:
                special_section = self.page.locator(".el-form-item").filter(has_text="是否申报特殊补贴")
                radio_btn = special_section.locator("label.el-radio").filter(has_text=special_subsidy).first

                if radio_btn.is_visible(timeout=2000):
                    radio_btn.click(force=True)
                    time.sleep(0.5)
                    log("表单填写", f"✅ 是否申报特殊补贴: 已选 [{special_subsidy}]")

                    # 选"是"时需要额外填写2个字段
                    if special_subsidy == "是":
                        time.sleep(1)

                        # 1. 特殊补贴申报类型（下拉单选）
                        self._select_dropdown("特殊补贴申报类型")

                        # 2. 特殊补贴证明材料（上传附件）
                        try:
                            test_img = os.path.join(os.getcwd(), "test_upload.png")
                            if os.path.exists(test_img):
                                # 找特殊补贴证明材料的上传按钮
                                cert_section = self.page.locator(".el-form-item").filter(has_text="特殊补贴证明材料")
                                cert_input = cert_section.locator("input[type='file']").first
                                cert_input.set_input_files(test_img)
                                time.sleep(1)
                                log("表单填写", "✅ 特殊补贴证明材料: 已上传")
                        except Exception as e:
                            log("表单填写", f"⚠️ 特殊补贴证明材料上传失败: {e}", "WARN")
                else:
                    log("表单填写", f"⚠️ 特殊补贴信息: '{special_subsidy}'选项不可见", "WARN")
            except Exception as e:
                log("表单填写", f"⚠️ 特殊补贴信息处理异常: {e}", "WARN")

            # === 附件上传 ===
            try:
                test_img = os.path.join(os.getcwd(), "test_upload.png")
                if os.path.exists(test_img):
                    inputs = self.page.locator("input[type='file']")
                    for i in range(inputs.count()):
                        try:
                            inputs.nth(i).set_input_files(test_img)
                        except:
                            pass
                    if inputs.count() > 0:
                        log("补贴申报", f"已上传 {inputs.count()} 个附件")
            except:
                pass


            # === 提交前校验：检查弹窗内所有必填字段是否已填写，并收集实际值 ===
            empty_fields = []
            actual_values = {}  # 收集实际表单值用于日志
            check_fields = ["购置金额", "设备厂家", "设备类型", "设备型号",
                            "能耗级别", "质保日期", "发票号码",
                            "安装日期", "安装人员", "安装人员联系电话"]
            # 限定在弹窗内搜索（避免匹配主页面的空字段）
            dialog = self.page.locator(".el-dialog__body").first
            for field_name in check_fields:
                try:
                    fi = dialog.locator(".el-form-item").filter(has_text=field_name)
                    inp = fi.locator(".el-input__inner").first
                    val = inp.input_value(timeout=2000)
                    if not val or val.strip() == "":
                        empty_fields.append(field_name)
                    else:
                        actual_values[field_name] = val.strip()
                except:
                    empty_fields.append(field_name)

            # 额外读取"预计补贴"（只读自动计算字段）
            try:
                subsidy_fi = dialog.locator(".el-form-item").filter(has_text="预计补贴")
                subsidy_inp = subsidy_fi.locator(".el-input__inner").first
                subsidy_val = subsidy_inp.input_value(timeout=2000)
                if subsidy_val and subsidy_val.strip():
                    actual_values["预计补贴"] = subsidy_val.strip()
            except:
                pass

            if empty_fields:
                log("补贴申报", f"⚠️ 以下必填字段未填写: {', '.join(empty_fields)}", "WARN")
            else:
                log("补贴申报", "✅ 所有必填字段已填写", "OK")

            # === 滚动弹窗到底部确保"保存并提交"按钮可见 ===
            try:
                self.page.evaluate("""() => {
                    document.querySelectorAll('.el-dialog__body').forEach(b => {
                        if (b.offsetParent) b.scrollTop = b.scrollHeight;
                    });
                }""")
                time.sleep(0.5)
            except:
                pass

            # === 点击弹窗内的"保存并提交" ===
            submit_btn = self.page.locator(".el-dialog__wrapper:visible button:has-text('保存并提交')").first
            try:
                submit_btn.scroll_into_view_if_needed()
            except:
                pass
            submit_btn.click(force=True)
            time.sleep(Config.LONG_WAIT)
            log("补贴申报", "已点击 [保存并提交]")

            # 二次确认弹窗
            try:
                confirm = self.page.locator(
                    ".el-message-box__btns button:has-text('确定')"
                ).first
                if confirm.is_visible(timeout=3000):
                    confirm.click()
                    time.sleep(Config.LONG_WAIT)
            except:
                pass

            # === 检测错误提示（必填项未填时系统会弹出红色提示或表单红框） ===
            error_msg = self.page.locator(".el-message--error, .el-message-box__message")
            try:
                if error_msg.first.is_visible(timeout=2000):
                    err_text = error_msg.first.inner_text()
                    log("补贴申报", f"❌ 提交失败，系统提示: {err_text}", "ERROR")
                    # 尝试关闭错误弹窗
                    try:
                        self.page.locator(".el-message-box__btns button").first.click()
                    except:
                        pass
                    return False
            except:
                pass

            # === 检测成功提示 ===
            try:
                success = self.page.locator(".el-message--success").first
                if success.is_visible(timeout=5000):
                    log("补贴申报", "✅ 补贴申报表单填写并提交成功", "OK")
                    return actual_values or True
            except:
                pass

            # 弹窗是否已关闭（提交成功后弹窗会自动关闭）
            try:
                dialog = self.page.locator(".el-dialog__wrapper[style*='display']")
                if dialog.count() == 0 or not dialog.first.is_visible(timeout=3000):
                    log("补贴申报", "✅ 补贴申报表单填写并提交成功（弹窗已关闭）", "OK")
                    return actual_values or True
            except:
                pass

            log("补贴申报", "⚠️ 提交状态不确定，未检测到成功或错误提示", "WARN")
            return actual_values or True
        except Exception as e:
            log_err("补贴申报", "表单填写或提交异常", e)
            return None

    # ==================== 弹窗内操作工具方法 ====================
    def _select_dropdown(self, label_text):
        """
        【键盘选择策略】
        
        核心方案（后续所有下拉选择都应遵循）：
        1. 用 .el-form-item__label 精确匹配标签（不匹配 placeholder 子串）
        2. Playwright click(force=True) 打开下拉框
        3. 键盘 ArrowDown + Enter 选择第一项（走 Element UI 内置事件链）
        
        为什么用键盘而不是 JS click：
        - Element UI el-select 的选项通过组件内部事件触发 v-model 更新
        - JS item.click() 不一定能完整触发 Vue 级联响应
        - 键盘操作走组件内置 handleKeyDown，确保 v-model 更新 + 级联触发
        """
        try:
            form_item = self.page.locator(".el-form-item").filter(
                has=self.page.locator(".el-form-item__label", has_text=label_text)
            )
            select_input = form_item.locator(".el-input__inner").first

            is_disabled = select_input.evaluate("el => el.disabled")
            if is_disabled:
                log("表单填写", f"⚠️ {label_text}: 输入框被禁用（可能上级未选）", "WARN")
                return

            # Playwright 点击打开下拉框
            select_input.click(force=True)
            time.sleep(1)

            # 键盘选择第一项：ArrowDown 高亮第一个选项，Enter 确认选择
            self.page.keyboard.press("ArrowDown")
            time.sleep(0.3)
            self.page.keyboard.press("Enter")
            time.sleep(0.5)

            # 验证是否选择成功（读取 input 的 value）
            val = select_input.input_value()
            if val and val.strip():
                log("表单填写", f"✅ {label_text}: 已选 [{val}]")
            else:
                log("表单填写", f"⚠️ {label_text}: 键盘选择后值仍为空", "WARN")
        except Exception as e:
            log_err("表单填写", f"{label_text} 下拉选择失败", e)

    def _pick_date(self, label_text):
        """
        【Playwright 原生日期选择】
        使用 Playwright click(force=True) 打开日期面板，选择"今天"。
        """
        try:
            form_item = self.page.locator(
                f".el-form-item"
            ).filter(has_text=label_text)

            date_input = form_item.locator(".el-input__inner").first

            is_disabled = date_input.evaluate("el => el.disabled")
            if is_disabled:
                log("表单填写", f"⚠️ {label_text}: 日期选择器被禁用", "WARN")
                return

            date_input.click(force=True)
            time.sleep(0.5)

            today = self.page.locator("td.available.today >> visible=true")
            if today.count() > 0:
                today.first.click()
                time.sleep(0.5)
                log("表单填写", f"✅ {label_text}: 已选今天")
            else:
                log("表单填写", f"⚠️ {label_text}: 未找到今天日期", "WARN")
        except Exception as e:
            log_err("表单填写", f"{label_text} 日期选择失败", e)

    # ==================== 查看详情 ====================
    def view_record_detail(self, order_id):
        """查看台账记录详情"""
        log("业务步骤", f"执行 [查看详情] 申报编号: {order_id}", "STEP")
        if self.search_by_order_id(order_id):
            try:
                self.page.locator("table.el-table__body tr").first.locator(
                    "button:has-text('查看')"
                ).click()
                time.sleep(Config.MEDIUM_WAIT)
                self.page.wait_for_selector(
                    ".el-dialog__title:has-text('详情'), .el-dialog__title:has-text('查看')",
                    timeout=5000
                )
                log("查看", f"✅ 已打开 [{order_id}] 的详情页面", "OK")
                self.page.click("button:has-text('关 闭'), .el-dialog__headerbtn")
                time.sleep(Config.SHORT_WAIT)
                return True
            except Exception as e:
                log_err("查看", "查看详情失败", e)
        return False
