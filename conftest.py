# -*- coding: utf-8 -*-
import os
import sys
import pytest
import ddddocr
from playwright.sync_api import sync_playwright

# 确保项目根目录在 Python 搜索路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.config import Config
from utils.logger import log, log_err
from utils.ocr_helper import OCRHelper
from pages.login_page import LoginPage


# ==================== 环境自检 ====================
def _ensure_env():
    """确保截图和日志目录存在"""
    for d in [Config.SCREENSHOT_DIR, os.path.dirname(Config.LOG_FILE)]:
        if not os.path.exists(d):
            os.makedirs(d)
            log("环境自检", f"已创建目录: {d}")


# ==================== Pytest Fixtures ====================

@pytest.fixture(scope="session")
def ocr_engine():
    """OCR 识别引擎（整个测试会话复用）"""
    return OCRHelper()


@pytest.fixture(scope="session")
def browser_context():
    """浏览器上下文（代替旧 runner.py 的浏览器管理逻辑）"""
    _ensure_env()

    log("运行器", "=" * 50)
    log("运行器", "  WARM 自动化测试项目启动")
    log("运行器", "=" * 50)

    launch_args = ["--start-maximized"] if Config.WINDOW_MAXIMIZED else []

    with sync_playwright() as p:
        log("浏览器", "正在启动 Chromium...")
        browser = p.chromium.launch(
            headless=Config.HEADLESS,
            slow_mo=Config.SLOW_MO,
            args=launch_args
        )

        context_args = {"no_viewport": True} if Config.WINDOW_MAXIMIZED else {
            "viewport": {"width": Config.VIEWPORT_W, "height": Config.VIEWPORT_H}
        }

        context = browser.new_context(**context_args)
        yield context
        browser.close()
        log("运行器", "测试周期结束，浏览器已关闭")


@pytest.fixture(scope="session")
def page(browser_context):
    """持久化页面（整个测试会话复用同一个 page，保持登录态）"""
    pg = browser_context.new_page()
    yield pg
    pg.close()


@pytest.fixture(scope="session")
def logged_in_page(page, ocr_engine):
    """已登录并导航到申报页面的 page（会话级别，仅执行一次登录）"""
    login_page = LoginPage(page, ocr_engine)
    login_page.login()
    
    from pages.declaration_page import DeclarationPage
    declaration_page = DeclarationPage(page)
    declaration_page.navigate_to_declaration()
    return page


@pytest.fixture(scope="session")
def env_config():
    """环境配置"""
    return Config()
