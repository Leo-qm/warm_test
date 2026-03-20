# -*- coding: utf-8 -*-
import pytest
import allure
from pages.login_page import LoginPage
from pages.home_page import HomePage
from utils.logger import log


@pytest.mark.smoke
@allure.feature("登录模块")
@allure.story("多角色登录冒烟测试")
@allure.title("验证角色: {role} 的登录流程")
# @pytest.mark.parametrize("role", ["village", "town", "district", "city", "admin"])
@pytest.mark.parametrize("role", ["admin"])
def test_smoke_login(page, ocr_engine, role):
    """冒烟测试：验证动态角色切换的登录流程"""
    login_page = LoginPage(page, ocr_engine)
    
    # 强制清理：以防共享 session 层 page 留存了上一个用例或 fixture 的 Cookie
    login_page.logout()
    
    # 1. 根据指定的业务角色登入 (到达门户)
    login_page.login(role)
    
    # 2. 从门户进入具体业务模块
    home_page = HomePage(page)
    home_page.enter_equipment_update_module()

    # 3. 验证最终是否到达业务系统 (检查 .cls-title)
    assert page.locator(".cls-title").count() > 0
    log("冒烟测试", f"✅ 角色: {role} 完整登录并进入模块流程测试通过", "OK")
