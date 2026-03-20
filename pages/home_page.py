# -*- coding: utf-8 -*-
import allure
from pages.base_page import BasePage
from utils.logger import log

class HomePage(BasePage):
    """首页门户页面封装"""

    def __init__(self, page):
        super().__init__(page)
        # 定位器定义
        self.portal_container = page.locator(".el-main, .home-container") # 首页主容器
        self.equipment_update_card = page.locator("text=设备更新(新增)补贴管理")
        self.system_title = page.locator(".cls-title") # 业务系统的标题标志

    @allure.step("从首页门户进入‘设备更新(新增)补贴管理’模块")
    def enter_equipment_update_module(self):
        """点击卡片进入业务模块"""
        log("首页", "正在点击‘设备更新(新增)补贴管理’模块...")
        
        # 等待卡片可见并点击
        self.equipment_update_card.wait_for(state="visible", timeout=10000)
        self.equipment_update_card.click()
        
        # 等待页面跳转并出现业务标志
        self.system_title.wait_for(state="visible", timeout=15000)
        log("首页", "✅ 已成功进入业务系统")
