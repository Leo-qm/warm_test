# -*- coding: utf-8 -*-
import time
from utils.logger import log, log_err
from utils.config import Config


class BasePage:
    """基础页面类 — 封装 Playwright 页面原子操作（通用等待、截图、表单填写）"""

    def __init__(self, page):
        self.page = page

    # ==================== Vue / 网络同步工具 ====================
    def wait_for_vue_update(self, timeout=None):
        """等待 Vue $nextTick 完成 + DOM 稳定。
        
        通过在页面中执行 Vue.nextTick() 并等待 DOM MutationObserver 静默，
        确保 Vue 响应式更新（如级联选择器的选项过滤、key++ 强制重渲染等）已完成。
        """
        timeout = timeout or Config.VUE_TICK_TIMEOUT
        try:
            self.page.evaluate("""() => new Promise(resolve => {
                // 等待 Vue.nextTick
                if (window.Vue && window.Vue.nextTick) {
                    window.Vue.nextTick(() => setTimeout(resolve, 100));
                } else {
                    // 兜底：使用 MutationObserver 检测 DOM 变化停止
                    let timer;
                    const observer = new MutationObserver(() => {
                        clearTimeout(timer);
                        timer = setTimeout(() => { observer.disconnect(); resolve(); }, 200);
                    });
                    observer.observe(document.body, { childList: true, subtree: true, attributes: true });
                    // 超时兜底
                    setTimeout(() => { observer.disconnect(); resolve(); }, 1500);
                }
            })""")
        except:
            time.sleep(0.3)

    def wait_for_network_idle(self, timeout=5000):
        """安全地等待网络空闲，替代硬编码 time.sleep()"""
        try:
            self.page.wait_for_load_state("networkidle", timeout=timeout)
        except:
            time.sleep(1)

    def select_dropdown_in_dialog(self, label_text, option_text=None, dialog_title=None):
        """弹窗内精准下拉选择 — 限定在可见弹窗范围内操作 el-select。

        解决多弹窗场景下 select_dropdown() 全局定位误命中背景页元素的问题。
        如果 option_text 为空则选择第一个可用选项。

        Args:
            label_text: 表单标签文本，如 "设备厂家"
            option_text: 指定选项文本，None 则选第一个可用项
            dialog_title: 可选，限定弹窗标题
        """
        log("弹窗下拉", f">> 选择 [{label_text}]" + (f" -> [{option_text}]" if option_text else ""), "STEP")

        # 通过 JS 在可见弹窗中精确定位 el-select 并点击展开
        clicked = self.page.evaluate(f"""() => {{
            const wrappers = document.querySelectorAll('.el-dialog__wrapper');
            for (const wrapper of wrappers) {{
                // el-dialog__wrapper 是 position:fixed，offsetParent 永远为 null
                // 必须用 getComputedStyle 检查 display 属性
                const wStyle = getComputedStyle(wrapper);
                if (wStyle.display === 'none' || wStyle.visibility === 'hidden') continue;
                {f"const header = wrapper.querySelector('.el-dialog__header'); if (!header || !header.textContent.includes('{dialog_title}')) continue;" if dialog_title else ""}
                const body = wrapper.querySelector('.el-dialog__body');
                if (!body) continue;
                const formItems = body.querySelectorAll('.el-form-item');
                for (const fi of formItems) {{
                    if (fi.offsetHeight === 0) continue;
                    const label = fi.querySelector('.el-form-item__label');
                    if (!label || !label.textContent.includes('{label_text}')) continue;
                    const inp = fi.querySelector('.el-select .el-input__inner');
                    if (inp && !inp.disabled) {{
                        inp.click();
                        return true;
                    }}
                }}
            }}
            return false;
        }}""")

        if not clicked:
            log("弹窗下拉", f"⚠️ [{label_text}]: 未在弹窗内找到可用的 el-select", "WARN")
            # 降级到通用 select_dropdown
            return self.select_dropdown(label_text)

        time.sleep(Config.SHORT_WAIT)

        # 等待下拉面板弹出
        try:
            self.page.wait_for_selector(
                ".el-select-dropdown__item >> visible=true", timeout=3000
            )
        except:
            log("弹窗下拉", f"⚠️ [{label_text}]: 下拉面板未弹出", "WARN")
            self.page.keyboard.press("Escape")
            return False

        # 选择目标选项
        if option_text:
            opt = self.page.locator(
                f".el-select-dropdown__item:has-text('{option_text}') >> visible=true"
            )
            if opt.count() > 0:
                opt.first.click()
                time.sleep(Config.SHORT_WAIT)
                log("弹窗下拉", f"✅ [{label_text}]: 已选 [{option_text}]")
                return True
            log("弹窗下拉", f"⚠️ [{label_text}]: 未找到 '{option_text}' 选项", "WARN")
            self.page.keyboard.press("Escape")
            return False
        else:
            # 选择第一个可用选项
            items = self.page.locator(".el-select-dropdown__item >> visible=true")
            for i in range(items.count()):
                item = items.nth(i)
                classes = item.get_attribute("class") or ""
                text = item.inner_text().strip()
                if "is-disabled" in classes or text in ("", "请选择"):
                    continue
                item.click()
                time.sleep(Config.SHORT_WAIT)
                log("弹窗下拉", f"✅ [{label_text}]: 已选 [{text}]")
                return True

        log("弹窗下拉", f"⚠️ [{label_text}]: 无可选项", "WARN")
        self.page.keyboard.press("Escape")
        return False

    def select_cascader_in_dialog(self, label_text, dialog_title=None):
        """在弹窗内选择 el-cascader 组件（设备类型、设备型号）。

        el-cascader 的 DOM 结构：
          .el-cascader > .el-input > .el-input__inner  (点击打开面板)
          .el-cascader-panel > .el-cascader-menu > .el-cascader-node (面板选项)

        与 el-select 不同，el-cascader 是多级面板，需要逐级点击直到叶子节点。
        设备类型/型号使用 :props="{ emitPath: false }" 配置，只返回最终值。

        Args:
            label_text: 表单标签文本
            dialog_title: 可选，限定弹窗标题
        """
        log("弹窗级联", f">> 选择 [{label_text}]", "STEP")

        # 1. 在弹窗中找到 el-cascader 并点击打开面板
        clicked = self.page.evaluate(f"""() => {{
            const wrappers = document.querySelectorAll('.el-dialog__wrapper');
            for (const wrapper of wrappers) {{
                const wStyle = getComputedStyle(wrapper);
                if (wStyle.display === 'none' || wStyle.visibility === 'hidden') continue;
                {"const header = wrapper.querySelector('.el-dialog__header'); if (!header || !header.textContent.includes('" + (dialog_title or '') + "')) continue;" if dialog_title else ""}
                const body = wrapper.querySelector('.el-dialog__body');
                if (!body) continue;
                const formItems = body.querySelectorAll('.el-form-item');
                for (const fi of formItems) {{
                    if (fi.offsetHeight === 0) continue;
                    const label = fi.querySelector('.el-form-item__label');
                    if (!label || !label.textContent.includes('{label_text}')) continue;
                    // el-cascader 的 input
                    const inp = fi.querySelector('.el-cascader .el-input__inner');
                    if (inp && !inp.disabled) {{
                        inp.click();
                        return true;
                    }}
                    // 兜底：检查是否 disabled
                    const cascader = fi.querySelector('.el-cascader');
                    if (cascader) {{
                        const isDisabled = cascader.classList.contains('is-disabled');
                        return {{ found: true, disabled: isDisabled }};
                    }}
                    return {{ found: false, label: label.textContent.trim() }};
                }}
            }}
            return false;
        }}""")

        if not clicked:
            log("弹窗级联", f"⚠️ [{label_text}]: 未在弹窗内找到 el-cascader", "WARN")
            return False
        if isinstance(clicked, dict):
            if clicked.get('disabled'):
                log("弹窗级联", f"⚠️ [{label_text}]: el-cascader 处于禁用状态", "WARN")
                return False
            if not clicked.get('found', True):
                log("弹窗级联", f"⚠️ [{label_text}]: form-item 内无 el-cascader", "WARN")
                return False

        time.sleep(Config.SHORT_WAIT)

        # 2. 等待级联面板出现
        try:
            self.page.wait_for_selector(
                ".el-cascader-panel >> visible=true", timeout=3000
            )
        except:
            log("弹窗级联", f"⚠️ [{label_text}]: 级联面板未弹出", "WARN")
            self.page.keyboard.press("Escape")
            return False

        time.sleep(0.3)

        # 3. 逐级选择第一个可用选项（最多5级深度）
        for level in range(5):
            # 找到当前级别面板中的第一个可选节点
            result = self.page.evaluate(f"""() => {{
                const panels = document.querySelectorAll('.el-cascader-panel');
                // 取最后一个可见的 panel（避免命中隐藏面板）
                let panel = null;
                for (let i = panels.length - 1; i >= 0; i--) {{
                    if (panels[i].offsetHeight > 0) {{ panel = panels[i]; break; }}
                }}
                if (!panel) return {{ error: 'no_panel' }};

                // 获取所有级别的菜单
                const menus = panel.querySelectorAll('.el-cascader-menu');
                // 取最后一个菜单（最深层级）
                const lastMenu = menus[menus.length - 1];
                if (!lastMenu) return {{ error: 'no_menu' }};

                // 找第一个非禁用节点
                const nodes = lastMenu.querySelectorAll('.el-cascader-node');
                for (const node of nodes) {{
                    if (node.classList.contains('is-disabled')) continue;
                    if (node.offsetHeight === 0) continue;
                    const label = node.querySelector('.el-cascader-node__label');
                    const text = label ? label.textContent.trim() : '';
                    // 点击该节点
                    node.click();
                    // 检查是否是叶子节点（没有展开箭头）
                    const hasArrow = node.querySelector('.el-icon-arrow-right') !== null;
                    return {{ action: hasArrow ? 'expanded' : 'selected', label: text, level: menus.length }};
                }}
                return {{ error: 'no_selectable_nodes', menuCount: menus.length }};
            }}""")

            if not result or 'error' in result:
                log("弹窗级联", f"⚠️ [{label_text}] 调试: {result}", "WARN")
                break

            if result.get('action') == 'selected':
                time.sleep(Config.SHORT_WAIT)
                log("弹窗级联", f"✅ [{label_text}]: 已选 [{result.get('label', '')}]")
                return True
            elif result.get('action') == 'expanded':
                time.sleep(0.5)  # 等待下一级菜单加载
                continue

        log("弹窗级联", f"⚠️ [{label_text}]: 未能完成级联选择", "WARN")
        self.page.keyboard.press("Escape")
        return False


    # ==================== 通用菜单导航 ====================
    def navigate_to_menu(self, submenu_text, menu_item_text, wait_selector,
                         wait_timeout=None, top_menu_text="清洁能源"):
        """通用侧边菜单导航 — 点击顶部菜单 → 展开子菜单 → 点击目标菜单项 → 等待加载。

        所有业务页面（申报、审核、台账、历史台账、补贴配置）共享同一导航模式，
        此方法将其抽象为一个可复用的入口。

        Args:
            submenu_text: 子菜单文本，如 "清洁取暖设备申报管理"
            menu_item_text: 菜单项文本，如 "新增申报信息管理"
            wait_selector: 页面加载完成的标志选择器
            wait_timeout: 等待超时（毫秒），默认使用 Config.PAGE_LOAD_TIMEOUT
            top_menu_text: 顶部菜单文本，默认 "清洁能源"
        """
        timeout = wait_timeout or Config.PAGE_LOAD_TIMEOUT

        # 0. 关闭可能遮挡菜单的弹窗/遮罩层（防止 view-detail-dialog 等阻塞交互）
        try:
            self.page.evaluate("""() => {
                // 关闭所有可见弹窗
                document.querySelectorAll('.el-dialog__wrapper').forEach(w => {
                    if (w.style.display !== 'none' && w.offsetParent !== null) {
                        // 尝试点击关闭按钮
                        const closeBtn = w.querySelector('.el-dialog__headerbtn');
                        if (closeBtn) closeBtn.click();
                    }
                });
                // 移除遮罩层
                document.querySelectorAll('.v-modal, .el-loading-mask').forEach(m => {
                    m.style.display = 'none';
                });
            }""")
            time.sleep(0.5)
        except:
            pass

        # 1. 点击顶部菜单（可能已在目标菜单区域内，点击失败也不影响）
        try:
            top = self.page.locator(f".cls-header-menu a:has-text('{top_menu_text}')")
            if top.count() > 0:
                top.first.click(force=True)
                time.sleep(Config.LONG_WAIT)
        except:
            pass

        # 2. 展开子菜单
        self.page.click(f"li.el-submenu:has-text('{submenu_text}')")
        time.sleep(Config.MEDIUM_WAIT)

        # 3. 点击目标菜单项
        self.page.click(f"li.el-menu-item:has-text('{menu_item_text}')")

        # 4. 等待页面加载标志
        self.page.wait_for_selector(wait_selector, timeout=timeout)

    # ==================== 通用表格搜索 ====================
    def search_in_table(self, search_label, keyword, verify_keyword=None):
        """通用表格搜索 — 重置筛选 → 填充关键词 → 点击搜索 → 验证结果行。

        适用于所有使用 Element UI 表格 + 搜索栏的页面（台账、审核、申报等）。

        Args:
            search_label: 搜索字段标签文本，如 "用户编号"、"申报编号"
            keyword: 搜索关键词
            verify_keyword: 验证时在结果行中查找的文本，默认与 keyword 相同
        Returns:
            bool: 是否找到匹配记录
        """
        if not keyword:
            log("查询", f"❌ 错误: {search_label} 为空，无法查询", "ERROR")
            return False

        verify = verify_keyword or keyword

        # 1. 重置筛选条件
        try:
            reset_btn = self.page.locator("button:has-text('重置')").first
            if reset_btn.is_visible(timeout=2000):
                reset_btn.click()
                time.sleep(Config.SHORT_WAIT)
        except:
            pass

        # 2. 填充搜索关键词
        self.fill_input_by_label(search_label, keyword)
        time.sleep(0.5)

        # 3. 点击搜索
        self.page.click("button:has-text('搜索')")
        time.sleep(Config.LONG_WAIT)

        # 4. 验证结果
        try:
            row = self.page.locator("table.el-table__body tr").first
            row.wait_for(state="visible", timeout=5000)
            if verify in row.inner_text():
                log("查询", f"✅ 成功找到记录: {keyword}", "OK")
                return True
        except:
            pass

        log("查询", f"❌ 未找到匹配记录: {keyword}", "ERROR")
        return False

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

    # ==================== 通用下拉选择 ====================
    def select_dropdown(self, label_text, option_text=None):
        """通用下拉选择器 — 根据标签文本定位 el-select 并选择指定文本或第一个可用选项。

        兼容两种 DOM 结构：
        1. 标准 .el-form-item 内嵌 .el-select
        2. 弹窗内非标准布局（JS 兜底定位）

        Args:
            label_text: 表单标签文本，如 "能源类型"、"设备厂家"
            option_text: 可选，指定要选择的选项内容（支持包含匹配）。若为空则选第一个。
        """
        log("下拉选择", f">> 选择 [{label_text}]", "STEP")

        # 策略1：Playwright 原生定位 — 找到 form-item 内的 el-select input 并点击
        try:
            form_item = self.page.locator(
                f".el-form-item:has-text('{label_text}')"
            ).first
            select_input = form_item.locator(".el-select .el-input__inner").first

            if select_input.is_visible(timeout=3000):
                # 如果已禁用则跳过
                if select_input.is_disabled():
                    log("下拉选择", f"⏭️ [{label_text}] 已禁用，跳过")
                    return True

                select_input.click(force=True)
                time.sleep(Config.SHORT_WAIT)

                # 等待下拉面板弹出
                try:
                    self.page.wait_for_selector(
                        ".el-select-dropdown__item >> visible=true",
                        timeout=3000
                    )
                except:
                    # 重试一次点击
                    select_input.click(force=True)
                    time.sleep(Config.SHORT_WAIT)

                # 选择匹配要求可见且非禁用的选项
                items = self.page.locator(".el-select-dropdown__item >> visible=true")
                for i in range(items.count()):
                    item = items.nth(i)
                    # 跳过禁用项和「请选择」占位项
                    classes = item.get_attribute("class") or ""
                    text = item.inner_text().strip()
                    if "is-disabled" in classes or text in ("", "请选择"):
                        continue
                    if option_text and option_text not in text:
                        continue
                    item.click()
                    time.sleep(Config.SHORT_WAIT)
                    log("下拉选择", f"✅ [{label_text}]: 已选 [{text}]")
                    return True

                log("下拉选择", f"⚠️ [{label_text}]: 下拉面板无满足条件的选项", "WARN")
                # 点击空白处关闭面板
                self.page.keyboard.press("Escape")
                return False
        except Exception as e:
            log("下拉选择", f"策略1未命中 [{label_text}]: {e}", "WARN")

        # 策略2：JS 兜底 — 在可见弹窗中通过标签文字找到 el-select 并点击
        try:
            clicked = self.page.evaluate(f"""() => {{
                const formItems = document.querySelectorAll('.el-form-item');
                for (const fi of formItems) {{
                    if (!fi.offsetParent) continue;
                    const label = fi.querySelector('.el-form-item__label');
                    if (!label || !label.textContent.includes('{label_text}')) continue;
                    const inp = fi.querySelector('.el-select .el-input__inner');
                    if (inp && !inp.disabled) {{
                        inp.click();
                        return true;
                    }}
                }}
                return false;
            }}""")

            if clicked:
                time.sleep(Config.SHORT_WAIT)
                self.page.wait_for_selector(".el-select-dropdown__item >> visible=true", timeout=3000)
                items = self.page.locator(".el-select-dropdown__item >> visible=true")
                for i in range(items.count()):
                    item = items.nth(i)
                    if item.is_visible(timeout=3000):
                        classes = item.get_attribute("class") or ""
                        text = item.inner_text().strip()
                        if "is-disabled" in classes or text in ("", "请选择"):
                            continue
                        if option_text and option_text not in text:
                            continue
                        item.click()
                        time.sleep(Config.SHORT_WAIT)
                        log("下拉选择", f"✅ [{label_text}]: JS兜底已选 [{text}]")
                        return True

            log("下拉选择", f"❌ [{label_text}]: 未能完成下拉选择", "ERROR")
        except Exception as e:
            log_err("下拉选择", f"[{label_text}] 选择失败", e)
        return False

    # ==================== 级联选择器 ====================
    def select_cascader(self, label_text):
        """通用级联选择器 — 根据标签文本定位 el-cascader 并选择第一个可用选项。

        与 el-select 不同，el-cascader 使用 .el-cascader-panel 下拉面板，
        选项定位器为 .el-cascader-node 而非 .el-select-dropdown__item。

        Args:
            label_text: 表单标签文本，如 "设备类型"、"设备型号"
        """
        log("级联选择", f">> 选择 [{label_text}]", "STEP")

        # 策略1：Playwright 原生定位 — 找到 form-item 内的 el-cascader input 并点击
        try:
            form_item = self.page.locator(
                f".el-form-item:has-text('{label_text}')"
            ).first
            # el-cascader 的 input 在 .el-cascader 容器内
            cascader_input = form_item.locator(
                ".el-cascader .el-input__inner, .el-cascader input"
            ).first

            if cascader_input.is_visible(timeout=3000):
                # 如果已禁用则跳过
                if cascader_input.is_disabled():
                    log("级联选择", f"⏭️ [{label_text}] 已禁用，跳过")
                    return True

                cascader_input.click(force=True)
                time.sleep(Config.SHORT_WAIT)

                # 等待级联面板弹出
                try:
                    self.page.wait_for_selector(
                        ".el-cascader-panel .el-cascader-node >> visible=true",
                        timeout=5000
                    )
                except:
                    # 重试一次点击
                    cascader_input.click(force=True)
                    time.sleep(Config.MEDIUM_WAIT)
                    try:
                        self.page.wait_for_selector(
                            ".el-cascader-panel .el-cascader-node >> visible=true",
                            timeout=5000
                        )
                    except:
                        log("级联选择", f"⚠️ [{label_text}]: 级联面板未弹出", "WARN")
                        self.page.keyboard.press("Escape")
                        return False

                # 选择第一个可见且非禁用的选项
                nodes = self.page.locator(
                    ".el-cascader-panel .el-cascader-node >> visible=true"
                )
                for i in range(nodes.count()):
                    node = nodes.nth(i)
                    classes = node.get_attribute("class") or ""
                    # 跳过禁用项
                    if "is-disabled" in classes:
                        continue
                    # 获取选项文本（el-cascader-node 内的 label）
                    label_el = node.locator(".el-cascader-node__label, span")
                    text = label_el.first.inner_text().strip() if label_el.count() > 0 else ""
                    if not text or text in ("请选择",):
                        continue
                    node.click()
                    time.sleep(Config.SHORT_WAIT)
                    # 点击后关闭面板（级联选择器可能仍处于展开状态）
                    try:
                        self.page.keyboard.press("Escape")
                        time.sleep(0.3)
                    except:
                        pass
                    log("级联选择", f"✅ [{label_text}]: 已选 [{text}]")
                    return True

                log("级联选择", f"⚠️ [{label_text}]: 级联面板无可选项", "WARN")
                self.page.keyboard.press("Escape")
                return False
        except Exception as e:
            log("级联选择", f"策略1未命中 [{label_text}]: {e}", "WARN")

        # 策略2：JS 兜底 — 在可见弹窗中通过标签文字找到 el-cascader 并点击
        try:
            clicked = self.page.evaluate(f"""() => {{
                const formItems = document.querySelectorAll('.el-form-item');
                for (const fi of formItems) {{
                    if (!fi.offsetParent) continue;
                    const label = fi.querySelector('.el-form-item__label');
                    if (!label || !label.textContent.includes('{label_text}')) continue;
                    const inp = fi.querySelector('.el-cascader .el-input__inner, .el-cascader input');
                    if (inp && !inp.disabled) {{
                        inp.click();
                        return true;
                    }}
                }}
                return false;
            }}""")

            if clicked:
                time.sleep(Config.MEDIUM_WAIT)
                node = self.page.locator(
                    ".el-cascader-panel .el-cascader-node >> visible=true"
                ).first
                if node.is_visible(timeout=5000):
                    label_el = node.locator(".el-cascader-node__label, span")
                    text = label_el.first.inner_text().strip() if label_el.count() > 0 else ""
                    node.click()
                    time.sleep(Config.SHORT_WAIT)
                    try:
                        self.page.keyboard.press("Escape")
                        time.sleep(0.3)
                    except:
                        pass
                    log("级联选择", f"✅ [{label_text}]: JS兜底已选 [{text}]")
                    return True

            log("级联选择", f"❌ [{label_text}]: 未能完成级联选择", "ERROR")
        except Exception as e:
            log_err("级联选择", f"[{label_text}] 选择失败", e)
        return False

    # ==================== 日期选择 ====================
    def pick_date(self, label_text):
        """通用日期选择器 — 根据标签文本定位 el-date-editor 并选择今天。

        策略：
        1. Playwright 定位 form-item 内的日期输入框并点击
        2. 在弹出的日期面板中点击 "今天" 或当前高亮日期
        3. JS 兜底直接写入今天的日期字符串

        Args:
            label_text: 表单标签文本，如 "安装日期"、"质保日期"
        """
        log("日期选择", f">> 选择 [{label_text}]", "STEP")
        from datetime import datetime
        today_str = datetime.now().strftime("%Y-%m-%d")

        # 策略1：Playwright 点击日期输入框 → 选择今天
        try:
            form_item = self.page.locator(
                f".el-form-item:has-text('{label_text}')"
            ).first
            date_input = form_item.locator(
                ".el-date-editor input, .el-input__inner"
            ).first

            if date_input.is_visible(timeout=3000):
                if date_input.is_disabled():
                    log("日期选择", f"⏭️ [{label_text}] 已禁用，跳过")
                    return True

                date_input.click(force=True)
                time.sleep(Config.SHORT_WAIT)

                # 尝试点击日期面板中的 "今天" 按钮
                today_btn = self.page.locator(
                    ".el-picker-panel__footer button:has-text('今天'), "
                    ".el-picker-panel__footer a:has-text('此刻')"
                )
                if today_btn.count() > 0 and today_btn.first.is_visible(timeout=2000):
                    today_btn.first.click()
                    time.sleep(Config.SHORT_WAIT)
                    log("日期选择", f"✅ [{label_text}]: 已选今天 ({today_str})")
                    return True

                # "今天"按钮不存在时，直接点击日历中的 today 单元格
                today_cell = self.page.locator("td.available.today >> visible=true")
                if today_cell.count() > 0:
                    today_cell.first.click()
                    time.sleep(Config.SHORT_WAIT)
                    log("日期选择", f"✅ [{label_text}]: 已选今天单元格 ({today_str})")
                    return True

                # 面板打开了但没找到今天，点击任意可用日期
                any_cell = self.page.locator("td.available:not(.disabled) >> visible=true")
                if any_cell.count() > 0:
                    any_cell.first.click()
                    time.sleep(Config.SHORT_WAIT)
                    log("日期选择", f"✅ [{label_text}]: 已选第一个可用日期")
                    return True

        except Exception as e:
            log("日期选择", f"策略1未命中 [{label_text}]: {e}", "WARN")

        # 策略2：JS 兜底 — 直接往 input 写入日期字符串并触发 Vue 响应
        try:
            success = self.page.evaluate(f"""() => {{
                const formItems = document.querySelectorAll('.el-form-item');
                for (const fi of formItems) {{
                    if (!fi.offsetParent) continue;
                    const label = fi.querySelector('.el-form-item__label');
                    if (!label || !label.textContent.includes('{label_text}')) continue;
                    const inp = fi.querySelector('.el-date-editor input, .el-input__inner');
                    if (inp && !inp.disabled) {{
                        // 通过 Vue 的 __vue__ 实例写入
                        const wrapper = fi.querySelector('.el-date-editor');
                        if (wrapper && wrapper.__vue__) {{
                            wrapper.__vue__.$emit('input', '{today_str}');
                            wrapper.__vue__.emitInput('{today_str}');
                        }}
                        // 直接赋值并触发事件
                        const nativeSet = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value').set;
                        nativeSet.call(inp, '{today_str}');
                        inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return true;
                    }}
                }}
                return false;
            }}""")

            if success:
                # 关闭可能还开着的日期面板
                self.page.keyboard.press("Escape")
                time.sleep(Config.SHORT_WAIT)
                log("日期选择", f"✅ [{label_text}]: JS兜底写入 {today_str}")
                return True
        except Exception as e:
            log_err("日期选择", f"[{label_text}] JS兜底失败", e)

        log("日期选择", f"❌ [{label_text}]: 未能完成日期选择", "ERROR")
        return False

    # ==================== 批量附件上传 ====================
    def upload_files(self):
        """批量附件上传 — 自动识别可见弹窗内所有上传入口并填入测试图片。

        使用 DOM 指纹打标策略 (`uploaded-done`)，避免重复上传同一个入口。
        自动在可见弹窗内寻找所有 input[type=file] 并逐一上传 test_upload.png。
        """
        import os
        log("附件上传", ">> 开始批量上传附件", "STEP")

        test_img = os.path.join(os.getcwd(), "test_upload.png")
        if not os.path.exists(test_img):
            log("附件上传", f"⚠️ 测试图片不存在: {test_img}", "WARN")
            return False

        uploaded_count = 0

        # 在可见弹窗中找到所有未标记的 file input 并标记
        try:
            total = self.page.evaluate("""() => {
                let count = 0;
                // 在所有可见的对话框中查找
                const wrappers = document.querySelectorAll('.el-dialog__wrapper');
                for (const wrapper of wrappers) {
                    if (wrapper.style.display === 'none') continue;
                    const body = wrapper.querySelector('.el-dialog__body');
                    if (!body) continue;
                    const fileInputs = body.querySelectorAll("input[type='file']");
                    fileInputs.forEach((inp, idx) => {
                        if (!inp.getAttribute('data-uploaded-done')) {
                            inp.setAttribute('data-upload-index', String(count));
                            count++;
                        }
                    });
                }
                // 兜底：页面级别的上传入口（非弹窗场景）
                if (count === 0) {
                    const fileInputs = document.querySelectorAll("input[type='file']");
                    fileInputs.forEach((inp, idx) => {
                        if (!inp.getAttribute('data-uploaded-done')) {
                            inp.setAttribute('data-upload-index', String(count));
                            count++;
                        }
                    });
                }
                return count;
            }""")

            if total == 0:
                log("附件上传", "⚠️ 未找到任何未上传的文件入口", "WARN")
                return True  # 没有上传入口不算失败

            log("附件上传", f"发现 {total} 个上传入口")

            for i in range(total):
                try:
                    file_input = self.page.locator(
                        f"input[type='file'][data-upload-index='{i}']"
                    ).first
                    file_input.set_input_files(test_img)
                    time.sleep(1)  # 等待上传完成
                    # 标记为已上传
                    self.page.evaluate(f"""() => {{
                        const inp = document.querySelector(
                            "input[type='file'][data-upload-index='{i}']"
                        );
                        if (inp) {{
                            inp.setAttribute('data-uploaded-done', 'true');
                            inp.removeAttribute('data-upload-index');
                        }}
                    }}""")
                    uploaded_count += 1
                except Exception as e:
                    log("附件上传", f"⚠️ 第 {i+1} 个上传入口失败: {e}", "WARN")

        except Exception as e:
            log_err("附件上传", "批量上传异常", e)
            return False

        if uploaded_count > 0:
            log("附件上传", f"✅ 已完成 {uploaded_count}/{total} 个附件上传")
        else:
            log("附件上传", "⚠️ 没有成功上传任何附件", "WARN")
        return uploaded_count > 0

    # ==================== 表单完整性校验 ====================
    def validate_form_completeness(self):
        """表单完整性校验 — 遍历可见弹窗内 .is-required 表单项，检查是否存在空值。

        使用 Element UI 的 .is-required 类标记检测必填项，
        读取每个必填项内的 input/textarea 值，汇报空缺字段。
        """
        log("表单校验", ">> 开始校验必填字段完整性", "STEP")

        try:
            result = self.page.evaluate("""() => {
                const empty = [];
                const filled = [];
                // 在可见弹窗中查找必填字段
                const wrappers = document.querySelectorAll('.el-dialog__wrapper');
                let formItems = [];
                for (const wrapper of wrappers) {
                    if (wrapper.style.display === 'none') continue;
                    const body = wrapper.querySelector('.el-dialog__body');
                    if (!body) continue;
                    formItems = body.querySelectorAll('.el-form-item.is-required');
                    if (formItems.length > 0) break;
                }
                // 兜底：页面级别的必填项
                if (formItems.length === 0) {
                    formItems = document.querySelectorAll('.el-form-item.is-required');
                }

                formItems.forEach(fi => {
                    if (!fi.offsetParent) return; // 跳过不可见项

                    const labelEl = fi.querySelector('.el-form-item__label');
                    const label = labelEl ? labelEl.textContent.trim() : '未知字段';

                    // 检查 input
                    const inp = fi.querySelector('.el-input__inner, textarea');
                    if (inp) {
                        const val = inp.value || '';
                        if (val.trim() === '') {
                            empty.push(label);
                        } else {
                            filled.push(label);
                        }
                        return;
                    }

                    // 检查上传组件（有已上传的文件列表则视为已填）
                    const uploadList = fi.querySelector('.el-upload-list__item');
                    if (uploadList) {
                        filled.push(label + '(附件)');
                        return;
                    }

                    // 没有 input 也没有上传（如纯文本展示），跳过
                });

                return { empty, filled, total: formItems.length };
            }""")

            if result["empty"]:
                log("表单校验",
                    f"⚠️ 以下 {len(result['empty'])} 个必填字段为空: "
                    f"{', '.join(result['empty'])}", "WARN")
            else:
                log("表单校验",
                    f"✅ 所有 {result['total']} 个必填字段已填写 "
                    f"({len(result['filled'])} 项有值)")

            return result
        except Exception as e:
            log_err("表单校验", "校验过程异常", e)
            return None

    # ==================== 弹窗按钮点击 ====================
    def click_button_in_dialog(self, button_text):
        """在可见弹窗中点击包含指定文本的按钮。

        优先在弹窗 footer 区域查找，兜底在整个弹窗范围内查找。

        Args:
            button_text: 按钮文本，如 "关闭"、"取消"、"确定"
        """
        log("弹窗操作", f">> 点击弹窗按钮 [{button_text}]", "STEP")

        # 尝试多种文本变体（Element UI 按钮文字有时带空格，如 "关 闭"）
        spaced_text = " ".join(button_text)  # "关闭" → "关 闭"
        variants = [button_text, spaced_text] if len(button_text) == 2 else [button_text]

        for text in variants:
            try:
                btn = self.page.locator(
                    f".el-dialog__wrapper:visible button:has-text('{text}')"
                ).first
                if btn.is_visible(timeout=2000):
                    btn.click(force=True)
                    time.sleep(Config.SHORT_WAIT)
                    log("弹窗操作", f"✅ 已点击 [{button_text}]")
                    return True
            except:
                continue

        # 兜底：JS 点击
        try:
            clicked = self.page.evaluate(f"""() => {{
                const wrappers = document.querySelectorAll('.el-dialog__wrapper');
                for (const wrapper of wrappers) {{
                    if (wrapper.style.display === 'none') continue;
                    const btns = wrapper.querySelectorAll('button');
                    for (const btn of btns) {{
                        const txt = btn.textContent.trim().replace(/\\s/g, '');
                        if (txt.includes('{button_text}')) {{
                            btn.click();
                            return true;
                        }}
                    }}
                }}
                return false;
            }}""")
            if clicked:
                time.sleep(Config.SHORT_WAIT)
                log("弹窗操作", f"✅ JS兜底已点击 [{button_text}]")
                return True
        except Exception as e:
            log_err("弹窗操作", f"点击 [{button_text}] 失败", e)

        log("弹窗操作", f"❌ 未在弹窗中找到 [{button_text}] 按钮", "ERROR")
        # 最后一招：按 Escape 关闭弹窗
        self.page.keyboard.press("Escape")
        return False
