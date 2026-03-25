# -*- coding: utf-8 -*-
"""
申报审核管理页封装
镇级用户操作：搜索待审核记录并执行审核通过/驳回
支持按申报状态筛选（如"资格审核"、"补贴审核"）
"""
import time
from pages.base_page import BasePage
from utils.config import Config
from utils.logger import log, log_err


class AuditPage(BasePage):
    """申报审核管理页 — 封装审核流程（镇级用户操作）"""

    def navigate_to_audit(self):
        """导航至申报审核管理页面，确保数据加载完成（含刷新重试）"""
        log("业务步骤", "========== 导航至申报审核页面 ==========", "STEP")
        try:
            top = self.page.locator(".cls-header-menu a:has-text('清洁能源')")
            if top.count() > 0:
                top.first.click(force=True)
                time.sleep(Config.LONG_WAIT)
        except:
            pass

        self.page.click("li.el-submenu:has-text('清洁取暖设备申报管理')")
        time.sleep(Config.MEDIUM_WAIT)
        self.page.click("li.el-menu-item:has-text('申报审核管理')")
        self.page.wait_for_selector("button:has-text('搜索')", timeout=Config.PAGE_LOAD_TIMEOUT)

        # 点击重置按钮清除可能残留的筛选条件
        try:
            reset_btn = self.page.locator("button:has-text('重置')").first
            if reset_btn.is_visible(timeout=2000):
                reset_btn.click()
                time.sleep(Config.MEDIUM_WAIT)
        except:
            pass

        # 等待表格数据加载（含刷新重试，最多 3 次）
        for attempt in range(1, 4):
            try:
                self.page.wait_for_selector(
                    "table.el-table__body tr", timeout=Config.PAGE_LOAD_TIMEOUT
                )
                log("导航", "✅ 已进入申报审核管理页面", "OK")
                return
            except:
                if attempt < 3:
                    log("导航", f"表格数据未加载，正在刷新页面 (第 {attempt} 次)...", "WARN")
                    self.page.reload()
                    time.sleep(Config.LONG_WAIT)
                    try:
                        self.page.wait_for_load_state("networkidle", timeout=8000)
                    except:
                        pass

        log("导航", "⚠️ 多次刷新后表格仍无数据", "WARN")

    def _set_status_filter(self, status_text):
        """
        设置"申报状态"筛选条件（如"补贴审核"、"资格审核"）
        通过 JS 在弹窗/页面中定位"申报状态"下拉框并选择指定选项
        """
        try:
            log("筛选", f"设置申报状态筛选: {status_text}")
            # JS 点击"申报状态"下拉框
            self.page.evaluate("""() => {
                const labels = document.querySelectorAll('.el-form-item__label, span, label');
                for (const label of labels) {
                    const text = label.textContent.trim();
                    if (text.includes('申报状态')) {
                        const formItem = label.closest('.el-form-item') || label.parentElement;
                        if (formItem) {
                            const input = formItem.querySelector('.el-input__inner');
                            if (input) input.click();
                        }
                        break;
                    }
                }
            }""")
            time.sleep(Config.SHORT_WAIT)

            # 选择目标选项
            option = self.page.locator(
                f".el-select-dropdown__item:has-text('{status_text}') >> visible=true"
            )
            if option.count() > 0:
                option.first.click()
                time.sleep(Config.SHORT_WAIT)
                log("筛选", f"✅ 申报状态已选择: {status_text}")
                return True
            else:
                log("筛选", f"⚠️ 未找到 '{status_text}' 选项", "WARN")
        except Exception as e:
            log_err("筛选", f"设置申报状态筛选失败", e)
        return False

    def search_by_order_id(self, order_id, status_filter=None):
        """
        通过申报编号搜索记录
        
        Args:
            order_id: 申报编号
            status_filter: 可选，设置申报状态筛选（如 "补贴审核"）
        """
        if not order_id:
            log("查询", "❌ 错误: 申报编号为空", "ERROR")
            return False

        log("业务步骤", f"执行 [查询] 申报审核列表，编号: {order_id}", "STEP")

        # 点击重置
        try:
            reset_btn = self.page.locator("button:has-text('重置')").first
            if reset_btn.is_visible():
                reset_btn.click()
                time.sleep(Config.SHORT_WAIT)
        except:
            pass

        # 设置申报状态筛选（如果指定）
        if status_filter:
            self._set_status_filter(status_filter)

        # 通过通用方法填充申报编号
        self.fill_input_by_label("申报编号", order_id)
        time.sleep(0.5)

        # 搜索并重试（如果列表为空，刷新页面重新搜索，最多 3 次）
        for attempt in range(1, 4):
            self.page.click("button:has-text('搜索')")
            time.sleep(Config.LONG_WAIT)

            try:
                row = self.page.locator("table.el-table__body tr").first
                if order_id in row.inner_text():
                    log("查询", f"✅ 成功定位到待审核记录: {order_id}", "OK")
                    return True
            except:
                pass

            if attempt < 3:
                log("查询", f"未找到 {order_id}，刷新页面重试 (第 {attempt} 次)...", "WARN")
                self.page.reload()
                time.sleep(Config.LONG_WAIT)
                try:
                    self.page.wait_for_load_state("networkidle", timeout=8000)
                except:
                    pass
                # 重新填写搜索条件
                self.fill_input_by_label("申报编号", order_id)
                time.sleep(0.5)

        log("查询", f"❌ 多次刷新后仍未找到待审核记录: {order_id}", "ERROR")
        return False

    def click_audit_button(self, order_id, status_filter=None):
        """点击指定行的"审核"按钮"""
        if self.search_by_order_id(order_id, status_filter=status_filter):
            log("审核", f"点击 [{order_id}] 的审核按钮")
            audit_btn = self.page.locator(
                "table.el-table__body tr"
            ).first.locator("button:has-text('审核')")
            if audit_btn.count() > 0:
                audit_btn.click()
                time.sleep(Config.MEDIUM_WAIT)
                return True
        return False

    def perform_approve(self, order_id, comment="测试通过", status_filter=None):
        """
        执行审核通过操作
        
        Args:
            order_id: 申报编号
            comment: 审核意见
            status_filter: 可选，申报状态筛选（第二阶段传 "补贴审核"）
        
        审核弹窗操作路径：
        点击"全部置为通过状态" → 点击"保存并提交"
        """
        log("业务步骤", f"执行 [审核通过] 流程，编号: {order_id}", "STEP")
        if not self.click_audit_button(order_id, status_filter=status_filter):
            return False

        try:
            # 等待审核弹窗加载
            visible_dialog = self.page.locator(".el-dialog__wrapper:visible")
            visible_dialog.first.wait_for(state="visible", timeout=10000)
            time.sleep(Config.MEDIUM_WAIT)
            dialog = visible_dialog.first

            # 滚动弹窗 body 确保底部按钮可见
            try:
                dialog.locator(".el-dialog__body").first.evaluate(
                    "el => el.scrollTop = el.scrollHeight"
                )
                time.sleep(0.5)
            except:
                pass

            # 1. 点击"全部置为通过状态"
            approve_all_btn = dialog.locator(
                "button:has-text('全部置为通过状态')"
            ).first
            try:
                approve_all_btn.scroll_into_view_if_needed()
            except:
                pass
            approve_all_btn.click(force=True)
            time.sleep(Config.SHORT_WAIT)
            log("审核", "已点击 [全部置为通过状态]")

            # 2. 点击"保存并提交"
            submit_btn = dialog.locator("button:has-text('保存并提交')").first
            try:
                submit_btn.scroll_into_view_if_needed()
            except:
                pass
            submit_btn.click(force=True)
            time.sleep(Config.MEDIUM_WAIT)
            log("审核", "已点击 [保存并提交]")

            # 3. 二次确认
            try:
                confirm_btn = self.page.locator(
                    ".el-message-box__btns button:has-text('确定')"
                ).first
                if confirm_btn.is_visible(timeout=3000):
                    confirm_btn.click()
                    time.sleep(Config.MEDIUM_WAIT)
            except:
                pass

            # 等待成功提示
            try:
                self.page.wait_for_selector(
                    ".el-message--success, text=操作成功, text=提交成功",
                    timeout=5000
                )
            except:
                pass

            log("审核", f"✅ 记录 [{order_id}] 审核通过完成", "OK")
            return True
        except Exception as e:
            log_err("审核", f"审核通过操作异常: {order_id}", e)
            return False
