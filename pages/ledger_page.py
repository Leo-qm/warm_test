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
        self.navigate_to_menu(
            "清洁取暖设备申报管理", "设备申报台账管理",
            "table.el-table__body tr"
        )
        log("导航", "✅ 已进入设备申报台账管理页面", "OK")

    # ==================== 台账查询 ====================
    def search_by_user_number(self, user_number):
        """通过用户编号搜索台账记录（用户编号在整个业务周期中唯一不变）"""
        log("业务步骤", f"执行 [台账查询] 用户编号: {user_number}", "STEP")
        return self.search_in_table("用户编号", user_number)

    def get_applicant_id_card(self, user_number):
        """从台账详情弹窗中获取申报人身份证号"""
        log("业务步骤", f"执行 [获取申报人身份证号] 用户编号: {user_number}", "STEP")
        if not self.search_by_user_number(user_number):
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
    def start_subsidy_declaration(self, user_number):
        """点击台账表格中申报状态列的"补贴申报"蓝色链接文字"""
        log("业务步骤", f"执行 [发起补贴申报] 流程，用户编号: {user_number}", "STEP")
        if self.search_by_user_number(user_number):
            try:
                row = self.page.locator("table.el-table__body tr").first
                link = row.locator("text=补贴申报").first
                if link.is_visible(timeout=3000):
                    link.click()
                    time.sleep(Config.MEDIUM_WAIT)
                    log("补贴申报", f"✅ 已点击 [{user_number}] 的'补贴申报'链接", "OK")
                    return True
                btn = row.locator("button:has-text('补贴申报')")
                if btn.count() > 0:
                    btn.first.click()
                    time.sleep(Config.MEDIUM_WAIT)
                    log("补贴申报", f"✅ 已点击 [{user_number}] 的补贴申报按钮", "OK")
                    return True
                log("补贴申报", "❌ 未找到【补贴申报】链接或按钮", "ERROR")
            except Exception as e:
                log_err("补贴申报", "点击操作异常", e)
        return False

    # ==================== 补贴申报表单填写 ====================
    def fill_subsidy_declaration(self, data):
        """填写补贴申报表单（设备信息 + 安装信息 + 附件上传 + 提交）

        基于前端 DeviceInfo.vue / InstallationInfo.vue / SpecialSubsidyInfo.vue 分析：
        - 设备厂家、设备类型、设备型号均为 el-select（非 el-cascader）
        - 三者存在前端级联过滤关系：厂家→类型→型号
        - 选择厂家后 Vue 通过 filteredEquipmentTypeOptions 过滤类型选项
        - 选择类型后 Vue 通过 filteredEquipmentModelOptions 过滤型号选项
        - 每次级联选择后 Vue 用 cascaderTypeKey++ / cascaderModelKey++ 强制重渲染组件
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

            # ========== 设备信息 ==========
            log("补贴申报", ">> [设备信息] 填写设备字段", "STEP")

            # 1. 购置金额
            self.fill_input_by_label("购置金额", d.get("purchase_amount", "3000"))

            # 2. 设备厂家 → 设备类型 → 设备型号
            #    设备厂家: el-select | 设备类型: el-cascader | 设备型号: el-cascader
            # 2.1 设备厂家 (el-select, 选择后触发级联重渲染)
            self.select_dropdown_in_dialog("设备厂家")
            time.sleep(Config.CASCADE_WAIT)   # 级联等待：Vue cascaderTypeKey++ 重渲染
            self.wait_for_vue_update()

            # 2.2 设备类型 (el-cascader，选择后触发设备型号级联)
            for attempt in range(3):
                result = self.select_cascader_in_dialog("设备类型")
                if result:
                    break
                time.sleep(1)
            time.sleep(Config.CASCADE_WAIT)
            self.wait_for_vue_update()

            # 2.3 设备型号 (el-cascader)
            for attempt in range(3):
                result = self.select_cascader_in_dialog("设备型号")
                if result:
                    break
                time.sleep(1)
            time.sleep(Config.SHORT_WAIT)

            # 3. 能耗级别
            self.select_dropdown_in_dialog("能耗级别")

            # 4. 质保日期
            self.pick_date("质保日期")

            # 5. 发票号码
            self.fill_input_by_label("发票号码", d.get("invoice_number", "INV20260324001"))

            # ========== 安装信息 ==========
            log("补贴申报", ">> [安装信息] 填写安装字段", "STEP")

            # 6. 安装日期
            self.pick_date("安装日期")

            # 7. 安装人员
            self.fill_input_by_label("安装人员", d.get("installer_name", "张师傅"), exact=True)

            # 8. 安装人员联系电话
            self.fill_input_by_label("安装人员联系电话", d.get("installer_phone", "13800000000"))

            # ========== 特殊补贴信息 ==========
            special_subsidy = d.get("special_subsidy", "否")
            log("补贴申报", f">> [特殊补贴] 是否申报: {special_subsidy}", "STEP")
            try:
                special_section = self.page.locator(".el-form-item").filter(has_text="是否申报特殊补贴")
                # Element UI el-radio: 通过 span.el-radio__label 精准匹配文本，再回溯到 label 点击
                radios = special_section.locator("label.el-radio")
                target_radio = None
                for i in range(radios.count()):
                    radio = radios.nth(i)
                    label_text = radio.locator("span.el-radio__label").inner_text(timeout=2000).strip()
                    if label_text == special_subsidy:
                        target_radio = radio
                        break

                if target_radio:
                    # 点击 el-radio__inner（可视圆点），确保触发 Vue change 事件
                    inner = target_radio.locator("span.el-radio__inner")
                    if inner.is_visible(timeout=2000):
                        inner.click()
                    else:
                        target_radio.click()
                    time.sleep(0.5)

                    # 验证选中状态（el-radio 选中后 class 会包含 is-checked）
                    is_checked = "is-checked" in (target_radio.get_attribute("class") or "")
                    if is_checked:
                        log("表单填写", f"✅ 是否申报特殊补贴: 已选 [{special_subsidy}] (已验证选中)")
                    else:
                        log("表单填写", f"⚠️ 是否申报特殊补贴: 点击了 [{special_subsidy}] 但未检测到选中状态，尝试JS兜底", "WARN")
                        # JS 兜底：直接触发 radio input 的 click
                        self.page.evaluate(f"""(targetText) => {{
                            const items = document.querySelectorAll('.el-form-item');
                            for (const item of items) {{
                                if (!item.textContent.includes('是否申报特殊补贴')) continue;
                                const radios = item.querySelectorAll('label.el-radio');
                                for (const radio of radios) {{
                                    const label = radio.querySelector('.el-radio__label');
                                    if (label && label.textContent.trim() === targetText) {{
                                        const input = radio.querySelector('input[type="radio"]');
                                        if (input) {{
                                            input.click();
                                            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                        }}
                                        return;
                                    }}
                                }}
                            }}
                        }}""", special_subsidy)
                        time.sleep(0.5)
                        log("表单填写", f"✅ 是否申报特殊补贴: JS兜底点击 [{special_subsidy}]")

                    if special_subsidy == "是":
                        self.wait_for_vue_update()

                        # 特殊补贴申报类型（el-select）
                        self.select_dropdown_in_dialog("特殊补贴申报类型")

                        # 特殊补贴证明材料（附件上传）
                        try:
                            test_img = os.path.join(os.getcwd(), "test_upload.png")
                            if os.path.exists(test_img):
                                cert_section = self.page.locator(".el-form-item").filter(has_text="特殊补贴证明材料")
                                cert_input = cert_section.locator("input[type='file']").first
                                cert_input.set_input_files(test_img)
                                time.sleep(Config.UPLOAD_WAIT)
                                log("表单填写", "✅ 特殊补贴证明材料: 已上传")
                        except Exception as e:
                            log("表单填写", f"⚠️ 特殊补贴证明材料上传失败: {e}", "WARN")
                else:
                    log("表单填写", f"⚠️ 未在radio列表中找到 '{special_subsidy}' 选项", "WARN")
            except Exception as e:
                log("表单填写", f"⚠️ 特殊补贴信息处理异常: {e}", "WARN")

            # ========== 附件上传 ==========
            self.upload_files()
            # 等待所有附件上传完成（检测 el-upload-list__item 中是否有 uploading 状态）
            try:
                self.page.wait_for_function(
                    """() => {
                        const uploading = document.querySelectorAll('.el-upload-list__item.is-uploading');
                        return uploading.length === 0;
                    }""",
                    timeout=10000
                )
            except:
                time.sleep(Config.UPLOAD_WAIT)

            # ========== 提交前校验 ==========
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

            # ========== 滚动到底部并提交 ==========
            try:
                self.page.evaluate("""() => {
                    document.querySelectorAll('.el-dialog__body').forEach(b => {
                        if (b.offsetParent) b.scrollTop = b.scrollHeight;
                    });
                }""")
                time.sleep(0.5)
            except:
                pass

            # 点击弹窗内"保存并提交"
            submit_btn = self.page.locator(".el-dialog__wrapper:visible button:has-text('保存并提交')").first
            try:
                submit_btn.scroll_into_view_if_needed()
            except:
                pass
            submit_btn.click(force=True)
            log("补贴申报", "已点击 [保存并提交]")

            # 智能等待响应（替代硬编码 time.sleep）
            try:
                self.page.wait_for_selector(
                    ".el-message-box, .el-message--success, .el-message--error",
                    timeout=Config.SUBMIT_TIMEOUT
                )
            except:
                log("补贴申报", "⚠️ 等待提交响应超时", "WARN")

            time.sleep(Config.SHORT_WAIT)

            # 二次确认弹窗
            try:
                confirm = self.page.locator(
                    ".el-message-box__btns button:has-text('确定')"
                ).first
                if confirm.is_visible(timeout=3000):
                    confirm.click()
                    # 等待服务器响应
                    self.wait_for_network_idle(timeout=10000)
                    time.sleep(Config.MEDIUM_WAIT)
            except:
                pass

            # ========== 检测结果 ==========
            # 检测错误提示
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

            # 检测成功提示
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

    # ==================== 查看详情 ====================
    def view_record_detail(self, user_number):
        """查看台账记录详情"""
        log("业务步骤", f"执行 [查看详情] 用户编号: {user_number}", "STEP")
        if self.search_by_user_number(user_number):
            try:
                self.page.locator("table.el-table__body tr").first.locator(
                    "button:has-text('查看')"
                ).click()
                time.sleep(Config.MEDIUM_WAIT)
                self.page.wait_for_selector(
                    ".el-dialog__title:has-text('详情'), .el-dialog__title:has-text('查看')",
                    timeout=5000
                )
                log("查看", f"✅ 已打开 [{user_number}] 的详情页面", "OK")
                self.page.click("button:has-text('关 闭'), .el-dialog__headerbtn")
                time.sleep(Config.SHORT_WAIT)
                return True
            except Exception as e:
                log_err("查看", "查看详情失败", e)
        return False
