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
from pages.audit_page import AuditPage
from pages.ledger_page import LedgerPage
from datetime import datetime


@pytest.fixture(scope="session")
def audit_p(page):
    """申报审核管理页对象"""
    return AuditPage(page)


@pytest.fixture(scope="session")
def ledger_p(page):
    """设备申报台账管理页对象"""
    return LedgerPage(page)


@pytest.fixture(scope="session")
def declaration_p(page):
    """新增申报信息管理页对象"""
    from pages.declaration_page import DeclarationPage
    return DeclarationPage(page)


@pytest.fixture(scope="session")
def role_manager(page, ocr_engine):
    """角色切换管理器"""
    from utils.role_manager import RoleManager
    return RoleManager(page, ocr_engine)


@pytest.fixture(scope="session")
def subsidy_config_p(page):
    """补贴配置管理页对象"""
    from pages.subsidy_config_page import SubsidyConfigPage
    return SubsidyConfigPage(page)


@pytest.fixture(scope="session")
def history_ledger_p(page):
    """历史台账查询页对象"""
    from pages.history_ledger_page import HistoryLedgerPage
    return HistoryLedgerPage(page)


# ==================== 测试报告定制 ====================

def pytest_configure(config):
    """定制报告顶部的 Environment 栏目"""
    if not hasattr(config, "_metadata"):
        return
    # 移除冗余信息
    config._metadata.pop("JAVA_HOME", None)
    config._metadata.pop("Plugins", None)
    # 添加业务相关信息
    config._metadata["测试项目"] = "清洁取暖设备申报系统 (WARM)"
    config._metadata["运行环境"] = Config.ENV_TYPE.upper()
    config._metadata["测试地址"] = Config.get_base_url()
    config._metadata["执行时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def pytest_html_results_summary(prefix, summary, postfix):
    """注入自定义 CSS 样式，提升报告视觉效果"""
    prefix.extend([
        "<style>",
        "body { font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f9fa; color: #333; }",
        "h1 { color: #0056b3; font-weight: 700; margin-bottom: 20px; border-bottom: 2px solid #0056b3; padding-bottom: 10px; }",
        "#environment { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }",
        "table { border-collapse: separate; border-spacing: 0; width: 100%; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }",
        "thead th { background-color: #0056b3; color: white; padding: 12px; font-weight: 600; text-align: left; border: none; }",
        "tbody tr { transition: background-color 0.2s; }",
        "tbody tr:hover { background-color: #f1f3f5; }",
        "td { padding: 12px; border-bottom: 1px solid #dee2e6; vertical-align: middle; }",
        ".passed { color: #28a745; font-weight: 600; }",
        ".failed { color: #dc3545; font-weight: 600; }",
        ".skipped { color: #6c757d; font-weight: 600; }",
        ".log { font-family: 'Consolas', monospace; font-size: 13px; color: #495057; background: #f8f9fa; padding: 10px; border-radius: 4px; border: 1px solid #e9ecef; }",
        "img { border-radius: 4px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-top: 10px; max-width: 600px !important; cursor: pointer; transition: transform 0.2s; }",
        "img:hover { transform: scale(1.02); }",
        "</style>"
    ])


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

        context = browser.new_context(**context_args, ignore_https_errors=True)
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
    """
    已登录并进入申报页面的 page
    根据 Config.needs_portal_navigation() 判断是否需要门户跳转
    """
    from pages.login_page import LoginPage
    from pages.declaration_page import DeclarationPage
    
    # 1. 登录（LoginPage 内部已自动适配环境）
    login_page = LoginPage(page, ocr_engine)
    login_page.login()
    
    # 2. 仅 test 环境需要门户跳转
    if Config.needs_portal_navigation():
        from pages.home_page import HomePage
        home_page = HomePage(page)
        home_page.enter_equipment_update_module()
    
    # 3. 导航到具体业务页
    declaration_page = DeclarationPage(page)
    declaration_page.navigate_to_declaration()
    return page


@pytest.fixture(scope="session")
def env_config():
    """环境配置"""
    return Config()


# ==================== 测试报告增强钩子 ====================

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    捕捉测试失败情况，为 pytest-html 报告自动截取失败页面截图
    """
    outcome = yield
    report = outcome.get_result()
    extras = getattr(report, "extra", [])

    if report.when == "call" and report.failed:
        # 尝试从该用例的夹具中拿到底层的 page 对象
        page = item.funcargs.get("page", None)
        if not page and "logged_in_page" in item.funcargs:
            page = item.funcargs.get("logged_in_page")

        if page:
            try:
                # 生成唯一截图文件名
                import time
                screenshot_name = f"fail_{item.name}_{int(time.time())}.png"
                screenshot_path = os.path.join(Config.SCREENSHOT_DIR, screenshot_name)
                
                # 执行截图
                page.screenshot(path=screenshot_path)
                log("测试失败", f"[{item.name}] 执行失败，已截图 -> {screenshot_path}", "ERROR")

                # 兼容新版 pytest-html 的附图方式
                import base64
                with open(screenshot_path, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode("utf-8")
                    
                pytest_html = item.config.pluginmanager.getplugin("html")
                if pytest_html is not None:
                    # 使用 image(b64, name) 方式附加
                    extras.append(pytest_html.extras.image(image_b64, "失败截图"))
                    
            except Exception as e:
                log_err("测试失败", "尝试捕捉失败截图时发生异常", e)

    report.extra = extras
