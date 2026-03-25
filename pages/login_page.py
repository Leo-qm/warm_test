# -*- coding: utf-8 -*-
"""
登录页面封装模块
自动根据 Config.ENV_TYPE 区分 local / test 环境的登录差异：
- local: 验证码 5 位，Base64 图片，登录后直达清洁能源系统，登录按钮 class=lgoinBtn
- test:  验证码 4 位，URL 图片，登录后进入门户首页，登录按钮为 el-button--primary

验证码重试策略优化：
- 策略1（点击换一个文字）/ 策略2（点击验证码图片）：只需重新识别验证码，不需重输账号密码
- 策略3（物理刷新页面）：需要重新输入账号、密码、验证码
"""
import time
from pages.base_page import BasePage
import allure
from utils.config import Config
from utils.logger import log, log_err


class LoginPage(BasePage):
    """登录页 — 封装登录流程与菜单导航（自动适配 local/test 环境）"""

    def __init__(self, page, ocr):
        super().__init__(page)
        self.ocr = ocr

    def _get_captcha_img_locator(self):
        """
        获取验证码图片定位器（兼容两种环境的 src 格式）
        - test 环境: img[src*='captcha']  (URL 中含 captcha)
        - local 环境: img[src^='data:image'] (Base64 编码图片)
        """
        if Config.ENV_TYPE == "local":
            return self.page.locator("img[src^='data:image']").first
        else:
            return self.page.locator("img[src*='captcha']").first

    @allure.step("登录系统 (角色: {role})")
    def login(self, role="village"):
        """
        执行完整登录流程（含验证码识别与重试），可通过 role 参数切换登录角色。
        
        优化要点：
        - 首次进入及策略3（页面物理刷新）后才重新输入用户名和密码
        - 策略1/2（刷新验证码图片）只需重新识别并输入验证码
        """
        env = Config.ENV_TYPE
        captcha_len = Config.get_captcha_length()
        log("业务步骤", f"========== 执行登录流程 (角色: {role}, 环境: {env}, 验证码: {captcha_len}位) ==========", "STEP")

        base_url = Config.get_base_url()
        log("登录", f"正在打开测试地址: {base_url}", "INFO")
        self.page.goto(base_url)
        try:
            self.page.wait_for_load_state("networkidle", timeout=10000)
        except:
            pass
        time.sleep(1)

        # 标记是否需要重新填写账号密码（首次必须填写）
        need_fill_credentials = True

        for i in range(1, Config.MAX_LOGIN_RETRIES + 1):
            try:
                # 检查是否已经登录成功
                if self._is_logged_in():
                    log("登录", "已处于登录状态", "OK")
                    return

                if i > 1:
                    log("登录", f"正在执行第 {i} 次登录尝试...", "INFO")
                    # 策略3（物理刷新）每 3 次触发一次，此时需要重填账号密码
                    use_force_reload = (i % 3 == 0)
                    self._trigger_captcha_refresh(force_reload=use_force_reload)
                    need_fill_credentials = use_force_reload

                # ========== 等待登录表单就绪 ==========
                self.page.wait_for_selector("input[placeholder*='用户名']", timeout=10000)

                # ========== 填写用户名和密码（仅首次或物理刷新后） ==========
                if need_fill_credentials:
                    user_input = self.page.locator("input[placeholder*='用户名']").first
                    user_input.focus()
                    user_input.click()
                    time.sleep(0.5)
                    user_input.fill("")
                    user_input.fill(Config.get_username(role))

                    pwd_input = self.page.locator("input[placeholder*='密码']").first
                    pwd_input.focus()
                    pwd_input.click()
                    time.sleep(0.5)
                    pwd_input.fill("")
                    pwd_input.fill(Config.get_password(role))

                # ========== 识别并填写验证码 ==========
                captcha_img = self._get_captcha_img_locator()
                captcha_img.wait_for(state="visible", timeout=8000)
                captcha_bytes = captcha_img.screenshot()
                code = self.ocr.classify(captcha_bytes)

                # 根据环境校验验证码位数
                if not code or len(code) != captcha_len:
                    actual_len = len(code) if code else 0
                    log("登录", f"验证码识别位数不符 (预期 {captcha_len} 位，实际 {actual_len} 位: {code})，正在主动刷新...", "WARN")
                    self._trigger_captcha_refresh()
                    # 策略1/2刷新验证码不需要重填账号密码
                    need_fill_credentials = False
                    continue

                code_input = self.page.locator("input[placeholder*='验证码']").first
                code_input.focus()
                code_input.click()
                code_input.fill("")
                code_input.fill(code)
                log("登录", f"正在输入验证码: {code}")

                # ========== 点击登录 ==========
                login_btn = self.page.locator("#btnSubmit, .lgoinBtn, #loginBtn, .el-button--primary").first
                login_btn.click()

                # ========== 兜底：处理安全风险弹窗 (仅 test 环境 HTTPS) ==========
                if env == "test":
                    try:
                        adv_btn = self.page.locator("#details-button, text=高级, text=Advanced")
                        if adv_btn.is_visible(timeout=1500):
                            adv_btn.click()
                            proceed_link = self.page.locator("#proceed-link, text=继续访问, text=Proceed")
                            if proceed_link.is_visible(timeout=1500):
                                proceed_link.click()
                    except:
                        pass

                # ========== 检查业务报错 ==========
                try:
                    error_msg_loc = self.page.locator(".el-message--error, .error, .el-form-item__error").first
                    if error_msg_loc.is_visible(timeout=2000):
                        txt = error_msg_loc.inner_text().strip()
                        log("登录", f"业务报错: {txt}", "WARN")
                        if "验证码" in txt or "错误" in txt:
                            self._trigger_captcha_refresh()
                            # 验证码错误只需重新输入验证码
                            need_fill_credentials = False
                        continue
                except:
                    pass

                # ========== 等待登录成功标志 ==========
                self._wait_for_login_success()
                return

            except Exception as e:
                if i == Config.MAX_LOGIN_RETRIES:
                    raise e
                log("登录", f"正在捕获异常并继续重试: {e}", "WARN")

        raise Exception("登录失败：已达到最大重试次数")

    def _is_logged_in(self):
        """判断是否已处于登录状态"""
        return (
            self.page.locator(".cls-title").count() > 0
            or self.page.get_by_text("设备更新(新增)补贴管理").count() > 0
        )

    def _wait_for_login_success(self):
        """等待登录成功的标志元素"""
        self.page.wait_for_selector("text=设备更新(新增)补贴管理", timeout=15000)
        log("登录", "✅ 登录成功，已到达门户首页面！", "OK")

    def _trigger_captcha_refresh(self, force_reload=False):
        """
        触发验证码刷新动作的兜底策略：
        1. 优先点击验证码图片本身（最快，local 环境主要方式）
        2. 其次点击"换一个"等文字（test 环境）
        3. 如果上述均失效或指定 force_reload，则刷新浏览器页面
        
        注意：只有策略3会导致账号密码清空，策略1/2不会
        """
        if force_reload:
            log("登录", "触发 [物理刷新浏览器] 策略...", "WARN")
            self.page.reload()
            time.sleep(2.5)
            try:
                self.page.wait_for_load_state("networkidle", timeout=5000)
            except:
                pass
            return

        try:
            # 策略 1: 点击"换一个"等文字 (test 环境专属/优先)
            refresh_text = self.page.locator("text=换一个, text=看不清, text=刷新, .captcha-refresh").first
            if refresh_text.is_visible(timeout=1000):
                log("登录", "尝试通过点击 [换一个] 文字刷新...", "INFO")
                refresh_text.click()
                time.sleep(1.5)
                return

            # 策略 2: 点击验证码图片（local 环境常用）
            captcha_img = self._get_captcha_img_locator()
            if captcha_img.is_visible(timeout=1500):
                log("登录", "尝试通过 [点击验证码图片] 刷新...", "INFO")
                captcha_img.click()
                time.sleep(1.5)
                return

            # 策略 3: 页面物理刷新（兜底）
            log("登录", "刷新交互未响应，执行 [页面重载] 兜底...", "WARN")
            self.page.reload()
            time.sleep(2.5)
        except Exception as e:
            log("登录", f"刷新过程异常，直接执行页面重载: {e}", "WARN")
            self.page.reload()
            time.sleep(2)

    @allure.step("强制登出清理全量缓存")
    def logout(self):
        """强制登出：清理会话状态并刷新页面"""
        log("登录", "清理登录状态，准备重新登录...", "INFO")
        try:
            self.page.context.clear_cookies()
            self.page.evaluate("() => { window.localStorage.clear(); window.sessionStorage.clear(); }")
            self.page.goto(Config.get_base_url())
            self.page.wait_for_selector("input[placeholder*='用户名']", timeout=10000)
        except Exception as e:
            log("登录", f"强制登出发生异常 (可能已是登录页): {e}", "WARN")
