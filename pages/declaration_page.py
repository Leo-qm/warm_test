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
            """在弹窗内通过 placeholder 定位 input 并填值（JS标记 + Playwright原生fill）"""
            marker = f"device-update-{placeholder_keyword}"
            found = self.page.evaluate("""(args) => {
                const [keyword, marker] = args;
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
                            inp.setAttribute('data-auto-marker', marker);
                            return true;
                        }
                    }
                    return false;
                }
                return false;
            }""", [placeholder_keyword, marker])
            if found:
                try:
                    target = self.page.locator(f"[data-auto-marker='{marker}']").first
                    target.click(force=True)
                    target.fill(value)
                    log("设备更新", f"  ✅ {label}: {value}")
                    return True
                except Exception as e:
                    log("设备更新", f"  ❌ {label}: 填写失败: {e}", "ERROR")
                    return False
            else:
                log("设备更新", f"  ❌ {label}: 未在弹窗内找到 '{placeholder_keyword}' 输入框", "ERROR")
            return False
        
        # 6.1 申请人信息区块
        log("设备更新", ">> [申请人信息] 填写空字段", "STEP")
        if data.get("applicant_phone"):
            fill_in_dialog("申报人联系电话", data["applicant_phone"], "申报人联系电话")
        if data.get("heating_area"):
            fill_in_dialog("采暖面积", str(data["heating_area"]), "采暖面积")
        
        # 6.2 申报类型区块 — 能源类型（下拉，JS标记+Playwright点击）
        log("设备更新", ">> [申报类型] 选择能源类型", "STEP")
        if body:
            body.evaluate("el => el.scrollTop += 400")
            time.sleep(0.5)
        try:
            marked = self.page.evaluate("""() => {
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
                            inp.setAttribute('data-auto-marker', 'energy-type-select');
                            return true;
                        }
                    }
                }
                return false;
            }""")
            if marked:
                target = self.page.locator("[data-auto-marker='energy-type-select']").first
                target.click(force=True)
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

        if data.get("bank_account"):
            fill_in_dialog("银行卡", data["bank_account"], "银行卡/折账号")
        if data.get("account_holder_name"):
            fill_in_dialog("开户人", data["account_holder_name"], "开户人姓名")
        
        # 6.4 统一上传附件（证明材料）
        log("设备更新", ">> [附件] 上传证明材料", "STEP")
        self._upload(body)
        
        # 7. 提交前校验所有必填字段
        self._validate_form_completeness()
        
        # 8. 滚动到底部并点击「保存并提交」
        log("设备更新", ">> 点击保存并提交", "STEP")
        if body:
            body.evaluate("el => el.scrollTop = el.scrollHeight")
            time.sleep(0.5)
        try:
            clicked = self.page.evaluate("""() => {
                const wrappers = document.querySelectorAll('.el-dialog__wrapper');
                for (const wrapper of wrappers) {
                    if (wrapper.style.display === 'none') continue;
                    const header = wrapper.querySelector('.el-dialog__header');
                    if (!header || !header.textContent.includes('设备更新')) continue;
                    const footer = wrapper.querySelector('.el-dialog__footer') || wrapper.querySelector('.dialog-footer') || wrapper;
                    const btns = footer.querySelectorAll('button');
                    for (const btn of btns) {
                        if (btn.textContent.trim().includes('保存并提交')) {
                            btn.click();
                            return 'submit';
                        }
                    }
                    for (const btn of btns) {
                        const txt = btn.textContent.trim();
                        if (txt.includes('保存') && !txt.includes('取消')) {
                            btn.click();
                            return 'save';
                        }
                    }
                }
                return null;
            }""")
            if clicked:
                log("设备更新", f"✅ 已点击按钮: {clicked}")
            else:
                log("设备更新", "❌ 未在弹窗内找到保存按钮", "ERROR")
                return None
        except Exception as e:
            log("设备更新", f"❌ 点击保存按钮异常: {e}", "ERROR")
            return None

        # 9. 等待保存成功并抓取编号
        try:
            self.page.wait_for_selector("text=保存成功", timeout=15000)
            log("设备更新", "✅ 保存成功提示已出现")
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
                        log("设备更新", f"✅ 成功抓取系统申报编号: {txt}", "OK")
                        return txt
                log("设备更新", f"第 {attempt+1} 次抓取未成功，重试中...", "WARN")
            
            log("设备更新", "⚠️ 多次重试未发现 SB 编号", "WARN")
            return None
        except Exception as e:
            log("设备更新", f"❌ 保存响应异常: {e}", "ERROR")
            return None

    def search_record(self, order_id):
        """[Read] 在列表页通过"申报编号"精准搜索记录"""
        if not order_id:
            log("查询", "❌ 错误: 申报编号为空，无法查询", "ERROR")
            return False

        log("业务步骤", f"执行 [查询] 申报编号: {order_id}", "STEP")

        # 清除遮挡层
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

        # 3. 填充申报编号
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
        """填写设备新增的4个区块表单字段"""
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
        # 户籍信息使用 .el-form-item filter

        try:
            fi = self.page.locator(".el-form-item").filter(has_text="户籍信息")
            inp = fi.locator(".el-input__inner").first
            if inp.is_visible() and not inp.is_disabled():
                inp.click()
                time.sleep(Config.SHORT_WAIT)
                item = self.page.locator(".el-select-dropdown__item >> visible=true")
                if item.count() > 0:
                    item.nth(0).click()
                    log("表单填写", "✅ 户籍信息: 已选第一项")
                else:
                    log("表单填写", "⚠️ 户籍信息: 下拉面板无选项", "WARN")

        except Exception as e:

            log("表单填写", f"⚠️ 户籍信息选择异常: {e}", "WARN")

        self.safe_fill("input[placeholder*='采暖面积']", d["heating_area"], "采暖面积")

        # 区块 3: 能源类型

        log("表单", ">>> [Section 3] 能源类型", "STEP")
        body = self.get_dialog_body()
        if body:
            body.evaluate("el => el.scrollTop += 600")
        try:
            fi = self.page.locator(".el-form-item").filter(has_text="能源类型")
            inp = fi.locator(".el-input__inner").first
            if inp.is_visible() and not inp.is_disabled():
                inp.click()
                time.sleep(Config.SHORT_WAIT)
                item = self.page.locator(".el-select-dropdown__item >> visible=true")
                if item.count() > 0:
                    item.nth(0).click()
                    log("表单填写", "✅ 能源类型: 已选第一项")
                else:
                    log("表单填写", "⚠️ 能源类型: 下拉面板无选项", "WARN")
        except Exception as e:
            log("表单填写", f"⚠️ 能源类型选择异常: {e}", "WARN")



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
        寻找当前弹窗内可见的“点击上传”按钮，依次点击并利用事件拦截器填入附件。
        """
        log("上传", ">>> 执行文件上传策略（点击按钮法）", "STEP")
        test_img = os.path.join(os.getcwd(), "test_upload.png")
        if not os.path.exists(test_img):
            self.page.screenshot(path=test_img)

        # 回到顶部确保基础视图
        if body:
            body.evaluate("el => el.scrollTop = 0")
            time.sleep(0.5)

        try:
            uploaded_count = 0
            for attempt in range(25):  # 限制最大打捞次数防止死循环
                # 重新定位尚未被处理过的第一个可见且包含“点击上传”文本的按钮
                btn_locator = self.page.locator(".el-dialog__wrapper:not([style*='display: none']) .el-dialog__body button:has-text('点击上传'):not(.uploaded-done)")
                if btn_locator.count() == 0:
                    break
                
                btn = btn_locator.first
                btn.scroll_into_view_if_needed()
                time.sleep(0.5)
                
                try:
                    with self.page.expect_file_chooser(timeout=3000) as fc_info:
                        btn.click()
                    fc_info.value.set_files(test_img)
                    uploaded_count += 1
                    log("上传", f"✅ 成功填入第 {uploaded_count} 个附件")
                    time.sleep(1.5)  # 等待组件响应与界面重排
                except Exception as e:
                    log("上传", f"⚠️ 附件交互异常，跳过该节点: {e}", "WARN")
                finally:
                    # 无论成败，在 DOM 上注上标记，下次查询 locator 将自动将其剔除
                    try:
                        btn.evaluate("node => node.classList.add('uploaded-done')")
                    except:
                        pass
                        
            log("上传", f"✅ 共成功处理了 {uploaded_count} 个附件上传入口", "OK")
        except Exception as e:
            log("上传", f"❌ 执行集中上传策略失败: {e}", "ERROR")

    def _validate_form_completeness(self):
        """提交前校验：遍历弹窗内所有必填字段，检查空值和未上传附件"""
        log("表单", ">>> 提交前置校验：正在核实所有必填字段完整性...", "STEP")
        missing_msg = self.page.evaluate("""() => {
            const wrappers = document.querySelectorAll('.el-dialog__wrapper');
            for (const wrapper of wrappers) {
                if (wrapper.style.display === 'none') continue;
                const items = wrapper.querySelectorAll('.el-form-item.is-required');
                for (const item of items) {
                    const label = (item.querySelector('.el-form-item__label') || {innerText: '未知字段'}).innerText.trim();
                    const uploadBtn = item.querySelector('button');
                    if (uploadBtn && uploadBtn.innerText.includes('点击上传') && !uploadBtn.classList.contains('uploaded-done')) {
                        return '附件缺失 (' + label + ')';
                    }
                    const uploadContainer = item.querySelector('.el-upload');
                    if (uploadContainer) {
                        const fileList = item.querySelectorAll('.el-upload-list__item, img');
                        if (fileList.length === 0) {
                            return '附件缺失 (' + label + ')';
                        }
                    }
                    const inp = item.querySelector('input');
                    if (inp && !inp.readOnly && !inp.disabled) {
                        if (inp.type === 'radio' || inp.type === 'checkbox') {
                        } else if (!inp.value.trim()) {
                            return '文本缺失 (' + label + ')';
                        }
                    }
                }
            }
            return null;
        }""")

        if missing_msg:
            log("表单", f"⚠️ 前置校验发现问题: {missing_msg}", "WARN")
        else:
            log("表单", "✅ 前置校验通过，所有的必填字段目前皆已覆盖妥当", "OK")
