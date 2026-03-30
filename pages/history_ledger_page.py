# -*- coding: utf-8 -*-
import time
from pages.base_page import BasePage
from utils.config import Config
from utils.logger import log, log_err

class HistoryLedgerPage(BasePage):
    """历史台账查询页封装"""

    def navigate_to_history(self):
        """导航至历史台账查询页面"""
        log("业务步骤", "========== 导航至历史台账查询页面 ==========", "STEP")
        self.navigate_to_menu(
            "清洁取暖设备申报管理", "历史台账查询",
            "table.el-table__body tr"
        )
        log("导航", "✅ 已进入历史台账查询页面", "OK")

    def search_by_user_number(self, user_number):
        """按用户编号搜索历史记录"""
        log("业务步骤", f"执行 [历史台账查询] 用户编号: {user_number}", "STEP")
        return self.search_in_table("用户编号", user_number)

    def view_history_record(self):
        """查看历史台账记录"""
        try:
            btn = self.page.locator("table.el-table__body tr").first.locator("button:has-text('查看')")
            if btn.count() > 0:
                btn.first.click()
                time.sleep(Config.MEDIUM_WAIT)
                self.click_button_in_dialog("关闭")
                return True
        except Exception as e:
            log_err("查看", "查看历史记录失败", e)
        return False
