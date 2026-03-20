# -*- coding: utf-8 -*-
import time
from pages.base_page import BasePage
import allure
from utils.config import Config
from utils.logger import log, log_err


class LoginPage(BasePage):
    """登录页 — 封装登录流程与菜单导航"""

    def __init__(self, page, ocr):
        super().__init__(page)
        self.ocr = ocr

    @allure.step("登录系统 (角色: {role})")
    def login(self, role="village"):
        """执行完整登录流程（含验证码识别与重试），可通过 role 参数切换登录角色"""
        log("业务步骤", f"========== 执行登录流程 (角色: {role}) ==========", "STEP")
        base_url = Config.get_base_url()
        log("登录", f"正在打开测试地址: {base_url}", "INFO")
        self.page.goto(base_url)
        # 增加等待以确保 SSO 重定向完成
        self.page.wait_for_load_state("networkidle")
        time.sleep(1)

        for i in range(1, Config.MAX_LOGIN_RETRIES + 1):
            try:
                # 检查是否已经在首页
                if self.page.locator(".cls-title").count() > 0:
                    log("登录", "已处于登录状态", "OK")
                    return

                if i > 1:
                    log("登录", f"正在执行第 {i} 次登录尝试...", "INFO")
                    # 优先点击“换一个”文字，其次是验证码图片
                    refresh_text = self.page.locator("text=换一个, text=看不清, text=刷新").first
                    captcha_img_loc = self.page.locator("img[src*='captcha']").first
                    
                    if refresh_text.is_visible(timeout=2000):
                        log("登录", "正在点击“换一个”刷新验证码图...", "INFO")
                        refresh_text.click()
                    elif captcha_img_loc.is_visible(timeout=2000):
                        log("登录", "正在点击验证码图片以刷新...", "INFO")
                        captcha_img_loc.click()
                    else:
                        log("登录", "未找到刷新按钮或验证码图，尝试直接刷新页面...", "WARN")
                        self.page.reload()
                    time.sleep(2)

                # 显式清除之前的输入 (使用 placeholder* 模糊搜索)
                user_input = self.page.locator("input[placeholder*='用户名']").first
                user_input.focus()   # 触发 onfocus
                user_input.click()   # 双重保障
                time.sleep(0.5)      # 等待脚本移除 readonly
                user_input.fill("")
                user_input.fill(Config.get_username(role))

                pwd_input = self.page.locator("input[placeholder*='密码']").first
                pwd_input.focus()
                pwd_input.click()
                time.sleep(0.5)
                pwd_input.fill("")
                pwd_input.fill(Config.get_password(role))

                # 获取验证码图片 (使用 .first)
                captcha_img = self.page.locator("img[src*='captcha']").first
                captcha_img.wait_for(state="visible", timeout=Config.ELEMENT_TIMEOUT)
                captcha_bytes = captcha_img.screenshot()
                code = self.ocr.classify(captcha_bytes)
                # 根据用户最新反馈：验证码始终为 4 位
                if not code or len(code) != 4:
                    log("登录", f"验证码识别位数不符 (预期 4 位，识别到 {len(code)} 位: {code})，正在进行刷新重试...", "WARN")
                    continue

                code_input = self.page.locator("input[placeholder*='验证码']").first
                code_input.focus()
                code_input.click()
                code_input.fill("")
                code_input.fill(code)
                
                # 点击登录按钮
                login_btn = self.page.locator("#btnSubmit, #loginBtn, .el-button--primary").first
                if login_btn.is_visible(timeout=2000):
                    login_btn.click()
                else:
                    self.page.click("button:has-text('登录'), a:has-text('登录')", timeout=2000)

                # --- 兜底逻辑：处理测试环境可能出现的“安全风险”弹窗 ---
                try:
                    # 检查浏览器原生的 SSL 警告页面 (Chrome/Edge 常见文本)
                    adv_btn = self.page.locator("#details-button, text=高级, text=Advanced")
                    if adv_btn.is_visible(timeout=2000):
                        log("登录", "检测到安全风险提示，正在点击‘高级’并继续访问...", "WARN")
                        adv_btn.click()
                        # 点击“继续访问”
                        proceed_link = self.page.locator("#proceed-link, text=继续访问, text=Proceed")
                        if proceed_link.is_visible(timeout=2000):
                            proceed_link.click()
                except:
                    pass

                # 快速检查业务逻辑层面的报错
                try:
                    error_msg = self.page.wait_for_selector(".el-message--error, .error, #error-msg", timeout=1500)
                    if error_msg:
                        log("登录", f"重试：{error_msg.inner_text()}", "WARN")
                        continue
                except:
                    pass

                # 等待门户首页标志 (等卡片出现)
                self.page.wait_for_selector("text=设备更新(新增)补贴管理", timeout=12000)
                log("登录", "✅ 登录成功，已到达门户首页面！", "OK")
                return
            except Exception as e:
                # 处理 SecurityError 或者是不可编辑等异常
                if "SecurityError" in str(e) or "not editable" in str(e):
                    log("登录", f"环境检测到限制，正在尝试通过强制交互处理... {i}", "WARN")
                
                if i == Config.MAX_LOGIN_RETRIES:
                    raise e
                log("登录", f"尝试进行中，当前报错: {e}", "WARN")
        raise Exception("登录失败")

    @allure.step("强制登出清理全量缓存")
    def logout(self):
        """强制登出：清理会话状态并刷新页面，以便进行单次浏览器内账号切换"""
        log("登录", "清理登录状态，准备重新登录...", "INFO")
        try:
            # 1. 清理 Cookie
            self.page.context.clear_cookies()
            # 2. 清理 Local Storage 和 Session Storage (解决 token 残留导致自动跳回首页)
            self.page.evaluate("() => { window.localStorage.clear(); window.sessionStorage.clear(); }")
            
            # 3. 拦截等待重定向回登录页
            self.page.goto(Config.get_base_url())
            self.page.wait_for_selector("input[placeholder*='用户名']", timeout=5000)
        except Exception as e:
            log("登录", f"强制登出发生异常 (可能已是登录页): {e}", "WARN")
