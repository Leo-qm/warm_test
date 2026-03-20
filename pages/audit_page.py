# -*- coding: utf-8 -*-
import time
from pages.base_page import BasePage
from utils.config import Config
from utils.logger import log, log_err


class AuditPage(BasePage):
    """申报审核管理页 — 封装审核流程（镇级用户操作）"""

    def navigate_to_audit(self):
        """导航至申报审核管理页面"""
        log("业务步骤", "========== 导航至申报审核页面 ==========", "STEP")
        try:
            # 1. 点击顶部“清洁能源”
            top = self.page.locator(".cls-header-menu a:has-text('清洁能源')")
            if top.count() > 0:
                top.first.click(force=True)
                time.sleep(Config.LONG_WAIT)
        except:
            pass

        # 2. 点击左侧菜单
        self.page.click("li.el-submenu:has-text('清洁取暖设备申报管理')")
        time.sleep(Config.MEDIUM_WAIT)
        self.page.click("li.el-menu-item:has-text('申报审核管理')")
        
        # 3. 等待列表加载
        self.page.wait_for_selector("table.el-table__body tr", timeout=Config.PAGE_LOAD_TIMEOUT)
        log("导航", "✅ 已进入申报审核管理页面", "OK")

    def search_by_order_id(self, order_id):
        """通过申报编号搜索记录"""
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

        # 输入编号并搜索
        input_sel = "input[placeholder*='申报编号']"
        self.safe_fill(input_sel, order_id, "申报编号")
        self.page.click("button:has-text('查询')")
        time.sleep(Config.MEDIUM_WAIT)

        # 检查第一行是否匹配
        try:
            row = self.page.locator("table.el-table__body tr").first
            if order_id in row.inner_text():
                log("查询", f"✅ 成功定位到待审核记录: {order_id}", "OK")
                return True
        except:
            pass

        log("查询", f"❌ 未找到待审核记录: {order_id}", "ERROR")
        return False

    def click_audit_button(self, order_id):
        """点击指定行的“审核”按钮"""
        if self.search_by_order_id(order_id):
            log("审核", f"点击 [{order_id}] 的审核按钮")
            # 定位表格行中的审核按钮
            audit_btn = self.page.locator("table.el-table__body tr").first.locator("button:has-text('审核')")
            if audit_btn.count() > 0:
                audit_btn.click()
                time.sleep(Config.MEDIUM_WAIT)
                return True
        return False

    def perform_approve(self, order_id, comment="测试通过"):
        """执行审核通过操作"""
        log("业务步骤", f"执行 [审核通过] 流程，编号: {order_id}", "STEP")
        if not self.click_audit_button(order_id):
            return False

        try:
            # 典型的审核弹窗操作：填写意见并点击通过/确定
            # 由于没有截图详细内容，暂按常见 UI 设计封装
            self.safe_fill("textarea[placeholder*='意见'], .audit-comment textarea", comment, "审核意见")
            
            # 点击“通过”或“审核通过”按钮
            pass_btn = self.page.locator("button:has-text('通过'), button:has-text('审核通过'), button:has-text('确 定')").first
            pass_btn.click()
            
            # 等待成功提示
            self.page.wait_for_selector("text=操作成功, text=已通过", timeout=5000)
            log("审核", f"✅ 记录 [{order_id}] 审核通过完成", "OK")
            return True
        except Exception as e:
            log_err("审核", f"审核通过操作异常: {order_id}", e)
            return False
