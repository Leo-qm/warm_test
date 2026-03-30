# -*- coding: utf-8 -*-
from pages.login_page import LoginPage
from pages.home_page import HomePage
from utils.logger import log
from utils.config import Config

class RoleManager:
    """
    角色切换管理器
    在同一浏览器会话中实现各级账号之间的无缝切换，
    每次切换会清理登录态并重新走登录+门户流程。
    """

    def __init__(self, page, ocr):
        self.page = page
        self.ocr = ocr
        self.login_page = LoginPage(page, ocr)
        self.current_role = None

    def switch_to(self, role):
        """
        切换到指定角色 (如 'village', 'town')
        """
        if self.current_role == role:
            log("角色切换", f"当前已是 [{role}] 角色，跳过切换", "OK")
            return

        log("角色切换", f"========== 切换到 [{role}] 角色 ==========", "STEP")

        # 1. 登出当前账号
        self.login_page.logout()

        # 2. 以新角色登录
        self.login_page.login(role)

        # 3. 进入门户
        if Config.needs_portal_navigation():
            home_page = HomePage(self.page)
            home_page.enter_equipment_update_module()

        self.current_role = role
        log("角色切换", f"✅ 已成功切换到 [{role}] 角色并进入业务系统", "OK")
