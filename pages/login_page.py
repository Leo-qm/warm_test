# -*- coding: utf-8 -*-
import time
from pages.base_page import BasePage
from utils.config import Config
from utils.logger import log, log_err


class LoginPage(BasePage):
    """登录页 — 封装登录流程与菜单导航"""

    def __init__(self, page, ocr):
        super().__init__(page)
        self.ocr = ocr

    def login(self):
        """执行完整登录流程（含验证码识别与重试）"""
        log("业务步骤", "========== 执行登录流程 ==========", "STEP")
        base_url = Config.get_base_url()
        log("登录", f"正在打开测试地址: {base_url}", "INFO")
        self.page.goto(base_url)
        time.sleep(1)

        for i in range(1, Config.MAX_LOGIN_RETRIES + 1):
            try:
                # 检查是否已经在首页
                if self.page.locator(".cls-title").count() > 0:
                    log("登录", "已处于登录状态", "OK")
                    return

                if i > 1:
                    log("登录", f"正在执行第 {i} 次登录尝试...", "INFO")
                    self.page.locator("img.login-code-img").click()
                    time.sleep(2)

                # 显式清除之前的输入
                self.page.locator("input[placeholder='请输入用户名']").fill("")
                self.page.fill("input[placeholder='请输入用户名']", Config.get_username())

                self.page.locator("input[placeholder='请输入密码']").fill("")
                self.page.fill("input[placeholder='请输入密码']", Config.get_password())

                captcha_img = self.page.locator("img.login-code-img")
                captcha_img.wait_for(state="visible", timeout=Config.ELEMENT_TIMEOUT)
                captcha_bytes = captcha_img.screenshot()

                code = self.ocr.classify(captcha_bytes)
                if not code or len(code) < 2:
                    log("登录", "验证码识别失败，跳过本次尝试", "WARN")
                    continue

                self.page.locator("input[placeholder='验证码']").fill("")
                self.page.fill("input[placeholder='验证码']", code)
                self.page.click("button:has-text('登录')")

                # 快速检查报错
                try:
                    error_msg = self.page.wait_for_selector(".el-message--error", timeout=1500)
                    if error_msg:
                        log("登录", f"重试：{error_msg.inner_text()}", "WARN")
                        continue
                except:
                    pass

                # 等待首页标志
                self.page.wait_for_selector(".cls-title", timeout=8000)
                log("登录", "✅ 登录成功！", "OK")
                return
            except Exception as e:
                log("登录", f"未进入首页，重试... {e}", "WARN")
        raise Exception("登录失败")

