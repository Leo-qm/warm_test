# -*- coding: utf-8 -*-
import pytest
from pages.login_page import LoginPage
from utils.logger import log


@pytest.mark.smoke
def test_smoke_login(page, ocr_engine):
    """冒烟测试：验证登录流程"""
    login_page = LoginPage(page, ocr_engine)
    login_page.login()
    # 断言：成功进入首页
    assert page.locator(".cls-title").count() > 0
    log("冒烟测试", "✅ 登录冒烟测试通过", "OK")
