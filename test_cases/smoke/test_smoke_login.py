# -*- coding: utf-8 -*-
import pytest
import allure
from pages.login_page import LoginPage
from utils.logger import log


@pytest.mark.smoke
@allure.feature("登录模块")
@allure.story("多角色登录冒烟测试")
@allure.title("验证角色: {role} 的登录流程")
# @pytest.mark.parametrize("role", ["village", "town", "district", "city", "admin"])
@pytest.mark.parametrize("role", ["village"])
def test_smoke_login(page, ocr_engine, role):
    """冒烟测试：验证动态角色切换的登录流程"""
    login_page = LoginPage(page, ocr_engine)
    
    # 强制清理：以防共享 session 层 page 留存了上一个用例或 fixture 的 Cookie
    login_page.logout()
    
    # 根据指定的业务角色登入
    login_page.login(role)
    
    # 断言：成功进入首页
    assert page.locator(".cls-title").count() > 0
    log("冒烟测试", f"✅ 登录冒烟测试通过 (角色: {role})", "OK")
