# -*- coding: utf-8 -*-
"""台账管理页面封装 — 台账查询、补贴申报与导出功能"""
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

    def get_applicant_id_card(self, order_id):
        """从台账详情弹窗中获取申报人身份证号"""
        log("业务步骤", f"执行 [获取申报人身份证号] 编号: {order_id}", "STEP")
        if not self.search_by_order_id(order_id):
            return None

        try:
            # 点击查看按钮打开详情弹窗
            row = self.page.locator("table.el-table__body tr").first
            view_btn = row.locator("button:has-text('查看')")
            if view_btn.count() > 0:
                view_btn.first.click()
            else:
                # 也可能是蓝色链接"查看"
                row.locator("text=查看").first.click()
            time.sleep(Config.LONG_WAIT)

            # 从详情弹窗中读取"申报人身份证号"
            id_card = None
            dialog = self.page.locator(".el-dialog__body").first
            try:
                # 尝试精确查找"申报人身份证号"字段
                fi = dialog.locator(".el-form-item").filter(has_text="申报人身份证号")
                inp = fi.locator(".el-input__inner").first
                id_card = inp.input_value(timeout=3000)
            except:
                pass

            # 兜底：读取"身份证号"字段（可能标签不同）
            if not id_card:
                try:
                    fi = dialog.locator(".el-form-item").filter(has_text="身份证号")
                    inp = fi.locator(".el-input__inner").first
                    id_card = inp.input_value(timeout=3000)
                except:
                    pass

            # 关闭详情弹窗
            try:
                close_btn = self.page.locator(
                    "button:has-text('关 闭'), button:has-text('关闭'), "
                    "button:has-text('取 消'), button:has-text('取消')"
                ).first
                if close_btn.is_visible(timeout=2000):
                    close_btn.click()
                else:
                    self.page.keyboard.press("Escape")
            except:
                self.page.keyboard.press("Escape")
            time.sleep(Config.MEDIUM_WAIT)

            if id_card and id_card.strip():
                log("台账详情", f"✅ 获取到申报人身份证号: {id_card.strip()}", "OK")
                return id_card.strip()
            else:
                log("台账详情", "❌ 未能读取到申报人身份证号", "ERROR")
                return None
        except Exception as e:
            log_err("台账详情", "获取身份证号异常", e)
            return None

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
        """填写补贴申报表单（设备信息 + 安装信息 + 附件上传 + 提交）"""
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

            # 2. 级联下拉：设备厂家 → 设备类型 → 设备型号
            self._select_dropdown("设备厂家")
            time.sleep(2)

            self._select_dropdown("设备类型")
            time.sleep(2)

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

            # 7. 安装人员
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

            # === 附件上传（打标法） ===
            try:
                test_img = os.path.join(os.getcwd(), "test_upload.png")
                if not os.path.exists(test_img):
                    self.page.screenshot(path=test_img)
                
                uploaded_count = 0
                for attempt in range(25):
                    btn_locator = self.page.locator(".el-dialog__wrapper:not([style*='display: none']) .el-dialog__body button:has-text('点击上传'):not(.uploaded-done)")
                    if btn_locator.count() == 0:
                        break
                    btn = btn_locator.first
                    btn.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    try:
                        with self.page.expect_file_chooser(timeout=3000) as fc_info:
                            btn.click()
                        fc_info.value.set_files(test_img)
                        uploaded_count += 1
                        log("补贴申报", f"✅ 成功填入第 {uploaded_count} 个附件")
                        time.sleep(1.5)
                    except Exception as e:
                        log("补贴申报", f"⚠️ 附件交互异常: {e}", "WARN")
                    finally:
                        try:
                            btn.evaluate("node => node.classList.add('uploaded-done')")
                        except:
                            pass
                log("补贴申报", f"✅ 共成功处理了 {uploaded_count} 个附件上传入口", "OK")
            except Exception as e:
                log("补贴申报", f"⚠️ 附件上传异常: {e}", "WARN")


            # === 提交前校验 ===
            empty_fields = []
            actual_values = {}
            check_fields = ["购置金额", "设备厂家", "设备类型", "设备型号",
                            "能耗级别", "质保日期", "发票号码",
                            "安装日期", "安装人员", "安装人员联系电话"]
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

            # 读取"预计补贴"
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

            # === 滚动弹窗到底部 ===
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

            # === 检测错误提示 ===
            error_msg = self.page.locator(".el-message--error, .el-message-box__message")
            try:
                if error_msg.first.is_visible(timeout=2000):
                    err_text = error_msg.first.inner_text()
                    log("补贴申报", f"❌ 提交失败，系统提示: {err_text}", "ERROR")
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

            # 弹窗是否已关闭
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
        """通过键盘 ArrowDown+Enter 选择下拉第一项（确保触发 Vue 级联）"""
        try:
            form_item = self.page.locator(".el-form-item").filter(
                has=self.page.locator(".el-form-item__label", has_text=label_text)
            )
            select_input = form_item.locator(".el-input__inner").first

            is_disabled = select_input.evaluate("el => el.disabled")
            if is_disabled:
                log("表单填写", f"⚠️ {label_text}: 输入框被禁用（可能上级未选）", "WARN")
                return

            select_input.click(force=True)
            time.sleep(1)

            self.page.keyboard.press("ArrowDown")
            time.sleep(0.3)
            self.page.keyboard.press("Enter")
            time.sleep(0.5)

            val = select_input.input_value()
            if val and val.strip():
                log("表单填写", f"✅ {label_text}: 已选 [{val}]")
            else:
                log("表单填写", f"⚠️ {label_text}: 键盘选择后值仍为空", "WARN")
        except Exception as e:
            log_err("表单填写", f"{label_text} 下拉选择失败", e)

    def _pick_date(self, label_text):
        """打开日期面板并选择今天"""
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
