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
        """根据文本选择下拉项，跳过禁用。带重试和等待机制。"""
        try:
            locator = self.page.locator(f"{selector} >> visible=true")
            if locator.count() > 0:
                target = locator.first
                target.scroll_into_view_if_needed()
                if target.is_disabled():
                    if label: log("表单填写", f"⏭️ {label} 已禁用，跳过")
                    return True

                # 最多重试2次（第一次可能下拉面板没弹出）
                for attempt in range(2):
                    target.click()
                    time.sleep(Config.SHORT_WAIT)

                    # 等待下拉面板出现
                    try:
                        self.page.wait_for_selector(
                            ".el-select-dropdown__item >> visible=true",
                            timeout=3000
                        )
                    except:
                        if label: log("表单填写", f"⚠️ {label}: 第{attempt+1}次点击后下拉面板未出现", "WARN")
                        continue

                    opt = self.page.locator(f".el-select-dropdown__item:has-text('{text}') >> visible=true")
                    if opt.count() > 0:
                        opt.first.click()
                        time.sleep(Config.SHORT_WAIT)
                        if label: log("表单填写", f"✅ {label}: {text}")
                        return True
                    else:
                        if label: log("表单填写", f"⚠️ {label}: 未找到 '{text}' 选项（第{attempt+1}次）", "WARN")

                if label: log("表单填写", f"❌ {label}: 重试后仍未选到 '{text}'", "ERROR")
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

    def fill_input_by_label(self, label_text, value, timeout=5000, exact=False):
        """
        通用方法：根据标签文本定位附近的 input 并填充值
        解决搜索栏不使用 .el-form-item 结构时的定位问题，
        并且确保通过 Playwright 原生 fill() 触发 Vue v-model 绑定。

        Args:
            exact: 当为 True 时，使用精确匹配标签文本（避免"安装人员"误匹配"安装人员联系电话"）
        """
        marker = f"auto-fill-{label_text}"

        # 策略1：Playwright 原生定位 + fill（force click 绕过遮挡层）
        try:
            if exact:
                # 精确匹配：找标签精确文本，上溯到 form-item，再定位 input
                label_el = self.page.get_by_text(label_text, exact=True).first
                form_item = label_el.locator("xpath=ancestor::div[contains(@class,'el-form-item')]").first
                loc = form_item.locator("input").first
            else:
                loc = self.page.locator(
                    f".el-form-item:has-text('{label_text}') input"
                ).first
            if loc.is_visible(timeout=2000):
                loc.click(force=True)
                loc.fill(value)
                log("搜索填充", f"✅ [{label_text}] 已填入: {value}")
                return True
        except:
            pass

        # 策略2：JS 定位标签文本附近的 input 并标记
        log("搜索填充", f"策略1未命中，尝试 JS 定位 [{label_text}] 附近的输入框...", "WARN")
        found = self.page.evaluate(f"""() => {{
            // 遍历所有元素，找到包含目标文本的标签
            const allElements = document.querySelectorAll('span, label, div, td, th, p, a');
            for (const el of allElements) {{
                // 精准匹配：直接文本内容包含标签文本
                const directText = Array.from(el.childNodes)
                    .filter(n => n.nodeType === 3)
                    .map(n => n.textContent.trim())
                    .join('');
                if (!directText.includes('{label_text}')) continue;

                // 找到标签了，现在寻找附近的 input
                // 方案A: 同一父容器内的 input
                let input = el.parentElement?.querySelector('input:not([type=hidden])');
                // 方案B: 下一个兄弟元素中的 input
                if (!input) {{
                    let sibling = el.nextElementSibling;
                    for (let i = 0; i < 3 && sibling; i++) {{
                        input = sibling.tagName === 'INPUT' ? sibling : sibling.querySelector('input:not([type=hidden])');
                        if (input) break;
                        sibling = sibling.nextElementSibling;
                    }}
                }}
                // 方案C: 父级的下一个兄弟
                if (!input) {{
                    let parentSibling = el.parentElement?.nextElementSibling;
                    if (parentSibling) {{
                        input = parentSibling.tagName === 'INPUT' ? parentSibling : parentSibling.querySelector('input:not([type=hidden])');
                    }}
                }}
                if (input) {{
                    input.setAttribute('data-auto-marker', '{marker}');
                    return true;
                }}
            }}
            return false;
        }}""")

        if found:
            try:
                target = self.page.locator(f"[data-auto-marker='{marker}']")
                target.click(force=True)
                target.fill(value)
                log("搜索填充", f"✅ [{label_text}] JS 兜底成功，已填入: {value}")
                return True
            except Exception as e:
                log("搜索填充", f"JS 定位到元素但 fill 失败: {e}", "ERROR")
                return False
        else:
            log("搜索填充", f"❌ 未能在页面中找到 [{label_text}] 对应的输入框", "ERROR")
            return False
