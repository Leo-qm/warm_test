# -*- coding: utf-8 -*-
import time
from utils.logger import log, log_err
from utils.config import Config


class BasePage:
    """基础页面类 — 封装 Playwright 页面原子操作（通用等待、截图、表单填写）"""

    def __init__(self, page):
        self.page = page

    # ==================== 导航 ====================
    def navigate(self, url: str):
        log("页面", f"跳转至: {url}")
        self.page.goto(url)

    # ==================== 截图 ====================
    def take_screenshot(self, name: str):
        path = f"{Config.SCREENSHOT_DIR}/{name}.png"
        self.page.screenshot(path=path)
        log("截图", f"已保存: {path}")

    # ==================== 表单原子操作 ====================
    def safe_fill(self, selector: str, value: str, label: str = "") -> bool:
        """安全填写，自动跳过禁用字段"""
        try:
            locator = self.page.locator(f"{selector} >> visible=true")
            if locator.count() > 0:
                target = locator.first
                target.scroll_into_view_if_needed()

                if target.is_disabled():
                    if label: log("表单填写", f"⏭️ {label} 已禁用，跳过")
                    return True

                target.click()
                target.fill(value)
                if label: log("表单填写", f"✅ {label}: {value}")
                return True
        except Exception as e:
            if label: log_err("表单填写", f"{label} 填写失败", e)
        return False

    def safe_select_first(self, selector: str, label: str = "") -> bool:
        """下拉选择第一项，跳过禁用"""
        try:
            locator = self.page.locator(f"{selector} >> visible=true")
            if locator.count() > 0:
                target = locator.first
                target.scroll_into_view_if_needed()
                if target.is_disabled():
                    if label: log("表单填写", f"⏭️ {label} 已禁用，跳过")
                    return True

                target.click()
                time.sleep(Config.SHORT_WAIT)
                item = self.page.locator(".el-select-dropdown__item >> visible=true")
                if item.count() > 0:
                    item.nth(0).click()
                    if label: log("表单填写", f"✅ {label}: 已选第一项")
                    return True
        except Exception as e:
            if label: log_err("表单填写", f"{label} 选择失败", e)
        return False

    def safe_select_by_text(self, selector: str, text: str, label: str = "") -> bool:
        """根据文本选择下拉项，跳过禁用"""
        try:
            locator = self.page.locator(f"{selector} >> visible=true")
            if locator.count() > 0:
                target = locator.first
                target.scroll_into_view_if_needed()
                if target.is_disabled():
                    if label: log("表单填写", f"⏭️ {label} 已禁用，跳过")
                    return True

                target.click()
                time.sleep(Config.SHORT_WAIT)
                opt = self.page.locator(f".el-select-dropdown__item:has-text('{text}') >> visible=true")
                if opt.count() > 0:
                    opt.first.click()
                    if label: log("表单填写", f"✅ {label}: {text}")
                    return True
        except Exception as e:
            if label: log_err("表单填写", f"{label} 选择失败", e)
        return False

    def safe_pick_today(self, selector: str, label: str = "") -> bool:
        """选择今天日期，跳过禁用"""
        try:
            locator = self.page.locator(f"{selector} >> visible=true")
            if locator.count() > 0:
                target = locator.first
                target.scroll_into_view_if_needed()
                if target.is_disabled():
                    if label: log("表单填写", f"⏭️ {label} 已禁用，跳过")
                    return True

                target.click()
                time.sleep(Config.SHORT_WAIT)
                today = self.page.locator("td.available.today >> visible=true")
                if today.count() > 0:
                    today.first.click()
                    if label: log("表单填写", f"✅ {label}: 今天")
                    return True
        except Exception as e:
            if label: log_err("表单填写", f"{label} 日期选择失败", e)
        return False

    def get_dialog_body(self):
        """获取可见对话框内容区"""
        return self.page.locator(".el-dialog__body >> visible=true").first
