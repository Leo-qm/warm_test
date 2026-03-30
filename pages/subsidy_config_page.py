# -*- coding: utf-8 -*-
import time
from pages.base_page import BasePage
from utils.config import Config
from utils.logger import log, log_err

class SubsidyConfigPage(BasePage):
    """补贴配置管理页封装"""

    def navigate_to_config(self):
        """导航至补贴配置管理页面"""
        log("业务步骤", "========== 导航至补贴配置管理页面 ==========", "STEP")
        self.navigate_to_menu(
            "清洁取暖设备申报管理", "补贴配置管理",
            "table.el-table__body tr"
        )
        log("导航", "✅ 已进入补贴配置管理页面", "OK")

    def search_config(self, keyword):
        """搜索配置"""
        log("查询", f"搜索补贴配置: {keyword}")
        return self.search_in_table("能源类型", keyword)

    def view_config(self):
        """查看配置"""
        try:
            btn = self.page.locator("table.el-table__body tr").first.locator("button:has-text('查看')")
            if btn.count() > 0:
                btn.click()
                time.sleep(Config.MEDIUM_WAIT)
                self.click_button_in_dialog("关闭")
                return True
        except Exception as e:
            log_err("查看", "查看配置失败", e)
        return False
