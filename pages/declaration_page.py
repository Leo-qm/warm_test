# -*- coding: utf-8 -*-
import os
import time
from pages.base_page import BasePage
from utils.config import Config
from utils.logger import log, log_err


class DeclarationPage(BasePage):
    """申报管理页 — 封装 CRUD 全部操作（7 大区块表单填写）"""

    def navigate_to_declaration(self):
        """导航至清洁取暖申报管理页面"""
        log("业务步骤", "========== 导航至申报页面 ==========", "STEP")
        try:
            top = self.page.locator(".cls-header-menu a:has-text('清洁能源')")
            if top.count() > 0:
                top.first.click(force=True)
                time.sleep(Config.LONG_WAIT)
        except:
            pass

        self.page.click("li.el-submenu:has-text('清洁取暖设备申报管理')")
        time.sleep(Config.MEDIUM_WAIT)
        self.page.click("li.el-menu-item:has-text('新增申报信息管理')")
        self.page.wait_for_selector("button:has-text('添加')", timeout=Config.PAGE_LOAD_TIMEOUT)
        log("导航", "✅ 已进入新增申报管理页面", "OK")

    def create_record(self, data):
        """[Create] 点击添加并填写全表单（设备新增）"""
        log("业务步骤", "执行 [新增] 记录流程", "STEP")
        self.page.click("button:has-text('添加')")
        self.page.click(".declaration-type-dialog .type-button:has-text('设备新增')")
        self.page.locator(".section-title:has-text('户主信息')").first.wait_for(state="visible", timeout=Config.PAGE_LOAD_TIMEOUT)
        self._fill_form_content(data)
        return self._save_form()

    def create_device_update_record(self, id_card, data=None):
        """
        [Create] 设备更新：输入身份证号查询已有设备 → 填写更新表单 → 保存并上报
        
        :param id_card: 已审核通过的设备新增记录的申报人身份证号
        :param data: 可选的额外表单数据（如需覆盖预填值）
        :return: 系统生成的申报编号，失败返回 None
        """
        log("业务步骤", f"执行 [设备更新] 记录流程 (身份证: {id_card})", "STEP")
        
        # 1. 点击添加 → 选择设备更新
        self.page.click("button:has-text('添加')")
        time.sleep(Config.SHORT_WAIT)
        self.page.click(".declaration-type-dialog .type-button:has-text('设备更新')")
        time.sleep(Config.LONG_WAIT)  # 等待设备更新弹窗加载
        log("设备更新", "✅ 已选择 [设备更新] 类型")
        
        # 2. 用JS轮询等待"设备更新申报"弹窗可见
        #    截图DOM: 弹窗标题"设备更新申报" → 申报资格查询区域:
        #    所属区 所属镇 所属村 查询[下拉:身份证号] [请输入 input] [查询按钮]
        try:
            for attempt in range(10):
                visible = self.page.evaluate("""() => {
                    const dialogs = document.querySelectorAll('.el-dialog__wrapper');
                    for (const wrapper of dialogs) {
                        if (wrapper.style.display === 'none') continue;
                        const header = wrapper.querySelector('.el-dialog__header');
                        if (header && header.textContent.includes('设备更新')) {
                            return true;
                        }
                    }
                    return false;
                }""")
                if visible:
                    log("设备更新", "✅ 设备更新弹窗已加载（JS轮询确认）")
                    break
                time.sleep(1)
            else:
                log("设备更新", "❌ 等待设备更新弹窗超时", "ERROR")
                return None
        except Exception as e:
            log_err("设备更新", "等待弹窗异常", e)
            return None
        
        time.sleep(Config.MEDIUM_WAIT)

        # 辅助函数：定位可见的设备更新弹窗
        FIND_VISIBLE_DIALOG_JS = """
            const dialogs = document.querySelectorAll('.el-dialog__wrapper');
            for (const wrapper of dialogs) {
                if (wrapper.style.display === 'none') continue;
                const header = wrapper.querySelector('.el-dialog__header');
                if (header && header.textContent.includes('设备更新')) {
                    return wrapper.querySelector('.el-dialog');
                }
            }
            return null;
        """

        # 3. 选择查询类型下拉为"身份证号"
        try:
            self.page.evaluate("""() => {
                const dialogs = document.querySelectorAll('.el-dialog__wrapper');
                for (const wrapper of dialogs) {
                    if (wrapper.style.display === 'none') continue;
                    const header = wrapper.querySelector('.el-dialog__header');
                    if (header && header.textContent.includes('设备更新')) {
                        const dlg = wrapper.querySelector('.el-dialog');
                        const selects = dlg.querySelectorAll('.el-select .el-input__inner');
                        // 最后一个 select 就是查询类型下拉（前面是区/镇/村）
                        const querySelect = selects[selects.length - 1];
                        if (querySelect) querySelect.click();
                        return;
                    }
                }
            }""")
            time.sleep(Config.SHORT_WAIT)
            # 在下拉面板中选择"身份证号"
            try:
                option = self.page.locator(".el-select-dropdown__item:has-text('身份证')").last
                if option.is_visible(timeout=3000):
                    option.click()
                    time.sleep(Config.SHORT_WAIT)
                    log("设备更新", "✅ 查询类型下拉已选择 [身份证号]")
                else:
                    log("设备更新", "⚠️ 下拉面板未出现'身份证'选项，可能已默认选中")
            except:
                log("设备更新", "⚠️ 未找到身份证下拉选项，继续使用默认值")
        except Exception as e:
            log("设备更新", f"⚠️ 操作查询类型下拉异常: {e}，继续尝试", "WARN")

        # 4. 定位并填写身份证号输入框
        try:
            id_input_index = self.page.evaluate("""() => {
                const dialogs = document.querySelectorAll('.el-dialog__wrapper');
                for (const wrapper of dialogs) {
                    if (wrapper.style.display === 'none') continue;
                    const header = wrapper.querySelector('.el-dialog__header');
                    if (header && header.textContent.includes('设备更新')) {
                        const body = wrapper.querySelector('.el-dialog__body');
                        if (!body) continue;
                        const allInputs = document.querySelectorAll('input.el-input__inner');
                        for (let i = 0; i < allInputs.length; i++) {
                            const inp = allInputs[i];
                            if (!body.contains(inp)) continue;
                            if (!inp.offsetParent || inp.readOnly || inp.disabled) continue;
                            const ph = inp.placeholder || '';
                            if (ph.includes('请输入') || ph === '') {
                                const selectParent = inp.closest('.el-select');
                                if (!selectParent) {
                                    return i;
                                }
                            }
                        }
                    }
                }
                return -1;
            }""")
            
            if id_input_index >= 0:
                id_input = self.page.locator("input.el-input__inner").nth(id_input_index)
                id_input.click()
                id_input.fill("")
                id_input.type(id_card, delay=50)
                time.sleep(Config.SHORT_WAIT)
                log("设备更新", f"✅ 已填入身份证号: {id_card}")
            else:
                log("设备更新", "❌ JS未能定位到身份证号输入框", "ERROR")
                return None
        except Exception as e:
            log_err("设备更新", "填写身份证号失败", e)
            return None
        
        # 5. 点击蓝色查询按钮
        try:
            self.page.evaluate("""() => {
                const dialogs = document.querySelectorAll('.el-dialog__wrapper');
                for (const wrapper of dialogs) {
                    if (wrapper.style.display === 'none') continue;
                    const header = wrapper.querySelector('.el-dialog__header');
                    if (header && header.textContent.includes('设备更新')) {
                        const dlg = wrapper.querySelector('.el-dialog');
                        const btns = dlg.querySelectorAll('button');
                        for (const btn of btns) {
                            const txt = btn.textContent.trim();
                            if (txt === '查询' || txt.includes('查询')) {
                                btn.click();
                                return;
                            }
                        }
                    }
                }
            }""")
            time.sleep(Config.LONG_WAIT)
            log("设备更新", "✅ 已点击查询按钮")
        except Exception as e:
            log_err("设备更新", "点击查询按钮失败", e)
            return None
        
        # 6. 填写必填字段（data 由 DataFactory.build_device_update_data() 提供）
        #    关键：所有填写操作必须限定在可见弹窗 DOM 内，不能用全局选择器
        log("设备更新", ">>> 开始填写设备更新表单必填字段 <<<", "STEP")
        
        if not data:
            data = {}
            log("设备更新", "⚠️ 未传入 data，空字段将无法填写", "WARN")
        
        body = self.get_dialog_body()
        
        # 定义弹窗内精确填写方法（避免全局选择器匹配到背景页元素）
        def fill_in_dialog(placeholder_keyword, value, label):
            """在可见的设备更新弹窗内，通过 placeholder 定位 input 并填值"""
            filled = self.page.evaluate("""(args) => {
                const [keyword, val] = args;
                const wrappers = document.querySelectorAll('.el-dialog__wrapper');
                for (const wrapper of wrappers) {
                    if (wrapper.style.display === 'none') continue;
                    const header = wrapper.querySelector('.el-dialog__header');
                    if (!header || !header.textContent.includes('设备更新')) continue;
                    const body = wrapper.querySelector('.el-dialog__body');
                    if (!body) continue;
                    const inputs = body.querySelectorAll('input');
                    for (const inp of inputs) {
                        if (inp.readOnly || inp.disabled) continue;
                        const ph = inp.placeholder || '';
                        if (ph.includes(keyword)) {
                            // 先聚焦，再设值，最后触发 input 事件让 Vue 识别
                            inp.focus();
                            inp.value = val;
                            inp.dispatchEvent(new Event('input', {bubbles: true}));
                            inp.dispatchEvent(new Event('change', {bubbles: true}));
                            return true;
                        }
                    }
                    return false;  // 弹窗找到了但没匹配到字段
                }
                return false;
            }""", [placeholder_keyword, value])
            if filled:
                log("设备更新", f"  ✅ {label}: {value}")
            else:
                log("设备更新", f"  ❌ {label}: 未在弹窗内找到 '{placeholder_keyword}' 输入框", "ERROR")
            return filled
        
        # 6.1 申请人信息区块
        log("设备更新", ">> [申请人信息] 填写空字段", "STEP")
        if data.get("applicant_phone"):
            fill_in_dialog("申报人联系电话", data["applicant_phone"], "申报人联系电话")
        if data.get("heating_area"):
            fill_in_dialog("采暖面积", str(data["heating_area"]), "采暖面积")
        
        # 6.2 申报类型区块 — 能源类型（下拉）
        log("设备更新", ">> [申报类型] 选择能源类型", "STEP")
        if body:
            body.evaluate("el => el.scrollTop += 400")
            time.sleep(0.5)
        try:
            # 能源类型是下拉选择，需要用 Playwright 点击交互
            # 但要用 JS 先定位弹窗内的那个 select input
            clicked = self.page.evaluate("""() => {
                const wrappers = document.querySelectorAll('.el-dialog__wrapper');
                for (const wrapper of wrappers) {
                    if (wrapper.style.display === 'none') continue;
                    const header = wrapper.querySelector('.el-dialog__header');
                    if (!header || !header.textContent.includes('设备更新')) continue;
                    const body = wrapper.querySelector('.el-dialog__body');
                    if (!body) continue;
                    const inputs = body.querySelectorAll('input');
                    for (const inp of inputs) {
                        const ph = inp.placeholder || '';
                        if (ph.includes('能源类型')) {
                            inp.click();
                            return true;
                        }
                    }
                }
                return false;
            }""")
            if clicked:
                time.sleep(Config.SHORT_WAIT)
                item = self.page.locator(".el-select-dropdown__item >> visible=true")
                if item.count() > 0:
                    item.nth(0).click()
                    time.sleep(Config.SHORT_WAIT)
                    log("设备更新", "  ✅ 能源类型: 已选第一项")
                else:
                    log("设备更新", "  ⚠️ 能源类型下拉面板无选项")
            else:
                log("设备更新", "  ⚠️ 未在弹窗内找到能源类型输入框")
        except Exception as e:
            log("设备更新", f"  ⚠️ 能源类型选择异常: {e}")
        
        # 6.3 基本信息区块（用户编号、门牌号、银行卡号、开户人姓名）
        log("设备更新", ">> [基本信息] 填写空字段", "STEP")
        if body:
            body.evaluate("el => el.scrollTop += 600")
            time.sleep(0.5)
        
        if data.get("user_number"):
            fill_in_dialog("用户编号", data["user_number"], "用户编号")
        if data.get("door_number"):
            fill_in_dialog("门牌", data["door_number"], "门牌号")
        if data.get("bank_account"):
            fill_in_dialog("银行卡", data["bank_account"], "银行卡/折账号")
        if data.get("account_holder_name"):
            fill_in_dialog("开户人", data["account_holder_name"], "开户人姓名")
        
        # 6.4 统一上传附件（证明材料）
        log("设备更新", ">> [附件] 上传证明材料", "STEP")
        self._upload(body)
        
        # 7. 保存并上报
        return self._save_form()

    def search_record(self, order_id):
        """[Read] 在列表页通过"申报编号"精准搜索记录"""
        if not order_id:
            log("查询", "❌ 错误: 申报编号为空，无法查询", "ERROR")
            return False

        log("业务步骤", f"执行 [查询] 申报编号: {order_id}", "STEP")

        # 1. 强力刷新：确保列表态可用
        time.sleep(1.5)
        try:
            masks = [".el-loading-mask", ".v-modal", ".el-dialog__wrapper"]
            for mask in masks:
                loc = self.page.locator(mask)
                if loc.count() > 0:
                    loc.first.wait_for(state="hidden", timeout=5000)
        except:
            pass

        # 2. 点击重置
        try:
            reset_btn = self.page.locator("button:has-text('重置')").first
            if reset_btn.is_visible():
                reset_btn.click()
                time.sleep(Config.SHORT_WAIT)
        except:
            pass

        # 3. 填充申报编号（使用通用方法，自动适配不同 DOM 结构）
        log("查询", f"填充申报编号: {order_id}")
        self.fill_input_by_label("申报编号", order_id)

        # 4. 点击搜索
        log("查询", "点击搜索按钮")
        self.page.click("button:has-text('搜索')")
        time.sleep(Config.LONG_WAIT)

        # 5. 验证结果
        try:
            row = self.page.locator("table.el-table__body tr").first
            row.wait_for(state="visible", timeout=5000)
            text = row.inner_text()
            if order_id in text:
                log("查询", f"✅ 成功找到记录: {order_id}", "OK")
                return True
        except:
            pass

        log("查询", f"❌ 未找到匹配记录: {order_id}", "ERROR")
        return False

    def view_record(self, order_id):
        """[Read] 查看详细信息"""
        log("业务步骤", f"执行 [查看] 申报编号: {order_id}", "STEP")
        if not self.search_record(order_id):
            return

        try:
            view_btn = self.page.locator("button:has-text('查看')").first
            if view_btn.is_visible():
                view_btn.click()
                time.sleep(Config.LONG_WAIT)
                log("查看", f"✅ 已打开申报编号 [{order_id}] 的查看弹窗", "OK")

                close_btn = self.page.locator(
                    "button:has-text('关 闭'), button:has-text('取 消'), "
                    "button:has-text('取消'), button:has-text('关闭')"
                ).first
                if close_btn.is_visible():
                    close_btn.click()
                else:
                    self.page.keyboard.press("Escape")

                time.sleep(Config.MEDIUM_WAIT)
                log("查看", "✅ 弹窗已关闭", "OK")
            else:
                log("查看", "❌ 未找到【查看】按钮", "ERROR")
        except Exception as e:
            log_err("查看", "查看操作异常", e)

    def update_record(self, order_id, new_area):
        """[Update] 编辑现有记录"""
        log("业务步骤", f"执行 [更新] 申报编号: {order_id} -> 新面积: {new_area}", "STEP")
        if not self.search_record(order_id):
            return

        self.page.locator("table.el-table__body tr").first.locator("button:has-text('编辑')").click()
        time.sleep(Config.LONG_WAIT)

        self.safe_fill("input[placeholder*='采暖面积']", str(new_area), "采暖面积")
        self._save_form()

    def delete_record(self, order_id):
        """[Delete] 删除现有记录"""
        log("业务步骤", f"执行 [删除] 申报编号: {order_id}", "STEP")
        if not self.search_record(order_id):
            return

        try:
            self.page.wait_for_selector(".el-dialog__wrapper", state="hidden", timeout=5000)

            delete_btn = self.page.locator("button:has-text('删除')").first
            if delete_btn.is_visible():
                try:
                    delete_btn.click(timeout=3000)
                except:
                    delete_btn.click(force=True)

                time.sleep(1.5)
                confirm_btn = self.page.locator(
                    ".el-message-box__btns button:has-text('确定'), "
                    ".el-message-box__btns button:has-text('删除')"
                ).last

                if confirm_btn.is_visible():
                    confirm_btn.click()
                    time.sleep(Config.LONG_WAIT)
                    log("删除", f"✅ 申报编号 [{order_id}] 删除成功", "OK")
                else:
                    log("删除", "❌ 未找到删除确认按钮", "ERROR")
            else:
                log("删除", "❌ 未找到【删除】按钮", "ERROR")
        except Exception as e:
            log_err("删除", "删除操作异常", e)

    # ==================== 内部方法 ====================

    def _fill_form_content(self, data):
        """内部方法：仅负责表单字段填写（不含点击添加和保存）"""
        d = data

        # 区块 1: 户主信息
        log("表单", ">>> [Section 1] 户主信息", "STEP")
        self.safe_fill("input[placeholder='请输入户主姓名']", d["household_name"], "户主姓名")
        self.safe_fill("input[placeholder='请输入身份证号']", d["id_card"], "身份证号")
        self.safe_fill("input[placeholder='请输入联系电话']", d["phone"], "联系电话")
        self.safe_fill("input[placeholder='请输入安装地址']", d["address"], "安装地址")
        self.safe_fill("input[placeholder='请输入门牌号']", d["door_number"], "门牌号")
        self.safe_fill("input[placeholder='请输入客户编号']", d["customer_id"], "客户编号")

        # 区块 2: 申报人信息
        log("表单", ">>> [Section 2] 申报人信息 (处理禁用联动)", "STEP")
        self.safe_select_by_text("input[placeholder='请选择是否户主']", d["is_household"], "是否户主")
        self.safe_fill("input[placeholder='请输入申报人姓名']", d["applicant_name"], "申报人姓名")
        self.safe_fill("input[placeholder='请输入申报人身份证号']", d["applicant_id_card"], "申报人身份证号")
        self.safe_fill("input[placeholder='请输入申报人联系电话']", d["applicant_phone"], "申报人联系电话")
        self.safe_select_first("input[placeholder='请输入户籍信息']", "户籍信息")
        self.safe_fill("input[placeholder*='采暖面积']", d["heating_area"], "采暖面积")

        # 区块 3: 能源类型
        log("表单", ">>> [Section 3] 能源类型", "STEP")
        body = self.get_dialog_body()
        if body:
            body.evaluate("el => el.scrollTop += 600")
        self.safe_select_first("label:has-text('能源类型') + div input", "能源类型")

        # 区块 4: 基础信息
        log("表单", ">>> [Section 4] 基础信息", "STEP")
        if body:
            body.evaluate("el => el.scrollTop += 600")
        self.safe_fill("input[placeholder*='用户编号']", d["user_number"], "用户编号")
        self.safe_fill("input[placeholder*='银行卡号']", d["bank_account"], "银行卡号")
        self.safe_fill("input[placeholder*='开户人姓名']", d["account_holder_name"], "开户人姓名")

        # 统一上传附件
        self._upload(body)

    def _save_form(self):
        """保存表单并捕获新生成的申报编号"""
        log("新增", "点击【保存】（生成系统编号）", "STEP")
        try:
            btn = self.page.locator("button:has-text('保 存') >> visible=true").first
            btn.click()

            log("新增", "等待系统响应...")
            self.page.wait_for_selector("text=保存成功", timeout=10000)
            time.sleep(Config.SHORT_WAIT)

            try:
                self.page.wait_for_selector(".el-dialog__wrapper", state="hidden", timeout=5000)
            except:
                pass

            for attempt in range(3):
                time.sleep(Config.MEDIUM_WAIT)
                row = self.page.locator("table.el-table__body tr").first
                if row.count() == 0:
                    continue

                cells = row.locator("td")
                count = cells.count()
                for i in range(count):
                    txt = cells.nth(i).inner_text().strip()
                    if txt.startswith("SB20"):
                        log("新增", f"✅ 成功抓取系统申报编号: {txt}", "OK")
                        return txt
                log("新增", f"第 {attempt+1} 次抓取未成功，重试中...", "WARN")

            log("新增", "⚠️ 警告: 经多次重试未在列表首行发现 SB 格式的编号", "WARN")
            return None
        except Exception as e:
            log("新增", f"❌ 保存或编号抓取失败: {e}", "ERROR")
            return None

    def _upload(self, body):
        """
        统一上传附件
        滚动整个表单区域，发现所有 file input 并逐一上传
        """
        log("上传", ">>> 执行文件上传策略", "STEP")
        test_img = os.path.join(os.getcwd(), "test_upload.png")
        if not os.path.exists(test_img):
            self.page.screenshot(path=test_img)

        # 回到顶部
        if body:
            body.evaluate("el => el.scrollTop = 0")
        
        uploaded = set()
        prev_count = 0  # 上一轮上传数量，用于检测是否有新增
        no_new_rounds = 0  # 连续无新增上传的轮次

        # 恢复完整滚动范围，确保覆盖所有附件区域
        for pos in range(0, 3001, 400):
            if body:
                body.evaluate(f"el => el.scrollTop = {pos}")
            time.sleep(0.3)
            
            inputs = self.page.locator("input[type='file']")
            total = inputs.count()
            for i in range(total):
                if i not in uploaded:
                    try:
                        inputs.nth(i).set_input_files(test_img)
                        uploaded.add(i)
                    except:
                        pass
            
            # 检查是否有新增上传
            if len(uploaded) == prev_count:
                no_new_rounds += 1
            else:
                no_new_rounds = 0
                prev_count = len(uploaded)
            
            # 连续 3 轮无新增 且 已有上传 → 提前退出
            if no_new_rounds >= 3 and len(uploaded) > 0:
                break

        # 二次验证：回到顶部再扫一次，确保不遗漏
        if body:
            body.evaluate("el => el.scrollTop = 0")
            time.sleep(0.3)
        remaining = self.page.locator("input[type='file']")
        for i in range(remaining.count()):
            if i not in uploaded:
                try:
                    remaining.nth(i).set_input_files(test_img)
                    uploaded.add(i)
                except:
                    pass

        log("上传", f"✅ 已上传 {len(uploaded)} 个文件", "OK")
