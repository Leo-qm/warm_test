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
        self.navigate_to_menu(
            "清洁取暖设备申报管理", "新增申报信息管理",
            "button:has-text('添加')"
        )
        log("导航", "✅ 已进入新增申报管理页面", "OK")

    def create_record(self, data):
        """[Create] 点击添加并填写全表单（设备新增）"""
        log("业务步骤", "执行 [新增] 记录流程", "STEP")
        self.page.click("button:has-text('添加')")
        self.page.click(".declaration-type-dialog .type-button:has-text('设备新增')")
        self.page.locator(".section-title:has-text('户主信息')").first.wait_for(state="visible", timeout=Config.PAGE_LOAD_TIMEOUT)
        self._fill_form_content(data)
        return self._save_form()

    def create_device_update_record(self, id_card, data=None, submit_action="submit"):
        """
        [Create] 设备更新：输入身份证号查询已有设备 → 填写更新表单
        
        :param id_card: 已审核通过的设备新增记录的申报人身份证号
        :param data: 可选的额外表单数据（如需覆盖预填值）
        :param submit_action: "save" (仅保存为草稿) 或 "submit" (保存并提交)
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

            # 抓取自动带出的用户编号，存入对象以便后续查询验证
            self.last_user_number = self.page.evaluate("""() => {
                const wrappers = document.querySelectorAll('.el-dialog__wrapper');
                for (const wrapper of wrappers) {
                    if (wrapper.style.display === 'none') continue;
                    const labels = wrapper.querySelectorAll('.el-form-item__label');
                    for (const label of labels) {
                        if (label.textContent.includes('用户编号')) {
                            const input = label.parentElement.querySelector('input');
                            if (input && input.value) return input.value;
                        }
                    }
                }
                return null;
            }""")
            if self.last_user_number:
                log("设备更新", f"✅ 成功抓取回显用户编号: {self.last_user_number}")
        except Exception as e:
            log_err("设备更新", "点击查询按钮或抓取异常", e)
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
        
        is_household = data.get("is_household", "是")
        # 是否户主下拉在弹窗内，必须用弹窗内精准定位
        self.select_dropdown_in_dialog("是否户主", is_household)
        # 选择后等待 Vue 响应式更新（联动控制申报人字段的显示/可编辑状态）
        time.sleep(1)
        self.wait_for_vue_update()
        
        if is_household != "是":
            # 非户主时，申报人信息不会从原台账自动带入，三个字段必须手动填写
            log("设备更新", f"  当前[是否户主]为'{is_household}'，需手动填写申报人信息", "STEP")
            fill_in_dialog("申报人姓名", data.get("applicant_name", ""), "申报人姓名")
            fill_in_dialog("申报人身份证", data.get("applicant_id_card", ""), "申报人身份证号")
            fill_in_dialog("申报人联系电话", data.get("applicant_phone", ""), "申报人联系电话")
            
            # 户籍信息（树形下拉，需逐级展开到村级）
            self._select_huji_to_village()
        else:
            log("设备更新", "  当前选择[是否户主]为“是”，跳过申报人名称/电话/户籍信息的填写 (原台账已带入)", "OK")

        if data.get("heating_area"):
            fill_in_dialog("采暖面积", str(data["heating_area"]), "采暖面积")
        
        # 6.2 申报类型区块 — 能源类型
        log("设备更新", ">> [申报类型] 选择能源类型", "STEP")
        self.select_dropdown("能源类型")

        # 6.3 基本信息区块（门牌号、银行卡号、开户人姓名）
        log("设备更新", ">> [基本信息] 填写空字段", "STEP")
        if body:
            body.evaluate("el => el.scrollTop += 600")
            time.sleep(0.5)
        
        # 不要查填【用户编号】，在设备更新查询后其原台账会在头部信息展示且不可编辑。


        if data.get("bank_account"):
            fill_in_dialog("银行卡", data["bank_account"], "银行卡/折账号")
        if data.get("account_holder_name"):
            fill_in_dialog("开户人", data["account_holder_name"], "开户人姓名")
        
        # 6.4 统一上传附件（证明材料）
        log("设备更新", ">> [附件] 上传证明材料", "STEP")
        if body:
            body.evaluate("el => el.scrollTop = 0")
            time.sleep(0.5)
        self.upload_files()
        
        # 7. 提交前校验所有必填字段
        self.validate_form_completeness()
        
        # 8. 滚动到底部并点击「保存并提交」
        log("设备更新", ">> 点击保存并提交", "STEP")
        if body:
            body.evaluate("el => el.scrollTop = el.scrollHeight")
            time.sleep(0.5)
        try:
            clicked = self.page.evaluate(f"""(action) => {{
                const wrappers = document.querySelectorAll('.el-dialog__wrapper');
                for (const wrapper of wrappers) {{
                    if (wrapper.style.display === 'none') continue;
                    const header = wrapper.querySelector('.el-dialog__header');
                    if (!header || !header.textContent.includes('设备更新')) continue;
                    const footer = wrapper.querySelector('.el-dialog__footer') || wrapper.querySelector('.dialog-footer') || wrapper;
                    const btns = footer.querySelectorAll('button');
                    
                    if (action === 'submit') {{
                        for (const btn of btns) {{
                            if (btn.textContent.trim().includes('保存并提交')) {{
                                btn.click();
                                return 'submit';
                            }}
                        }}
                    }}
                    
                    // 退化到仅保存，或指定 action === 'save'
                    for (const btn of btns) {{
                        const txt = btn.textContent.trim();
                        if (txt.includes('保存') && !txt.includes('取消') && (!txt.includes('提交') || action === 'submit')) {{
                            btn.click();
                            return 'save';
                        }}
                    }}
                }}
                return null;
            }}""", submit_action)
            if clicked:
                log("设备更新", f"✅ 已点击按钮: {clicked}")
            else:
                log("设备更新", "❌ 未在弹窗内找到保存按钮", "ERROR")
                return None
        except Exception as e:
            log("设备更新", f"❌ 点击保存按钮异常: {e}", "ERROR")
            return None

        # 9. 等待保存成功并抓取编号（复用通用逻辑）
        return self._wait_save_and_capture_order_id("设备更新")

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

    def search_record_by_user_number(self, user_number):
        """[Read] 在列表页通过"用户编号"精准搜索记录"""
        if not user_number:
            log("查询", "❌ 错误: 用户编号为空，无法查询", "ERROR")
            return False

        log("业务步骤", f"执行 [查询-用户编号] 用户编号: {user_number}", "STEP")
        time.sleep(1.5)
        # 1. 点击重置
        try:
            reset_btn = self.page.locator("button:has-text('重置')").first
            if reset_btn.is_visible():
                reset_btn.click()
                time.sleep(Config.SHORT_WAIT)
        except:
            pass

        # 2. 填充系统/用户编号（通常前端系统会自动匹配）
        log("查询", f"填充用户编号: {user_number}")
        # 这里尝试填入用户编号输入框，如果没有对应的精确label则用模糊匹配
        try:
            self.fill_input_by_label("用户编号", user_number)
        except:
            # 兼容如果前端叫“系统/用户编号”
            self.fill_input_by_label("系统/用户编号", user_number)

        # 3. 点击搜索
        log("查询", "点击搜索按钮")
        self.page.click("button:has-text('搜索')")
        time.sleep(Config.LONG_WAIT)

        # 4. 验证结果
        try:
            row = self.page.locator("table.el-table__body tr").first
            row.wait_for(state="visible", timeout=5000)
            text = row.inner_text()
            if user_number in text:
                log("查询", f"✅ 成功找到记录: {user_number}", "OK")
                return True
        except:
            pass

        log("查询", f"❌ 未找到匹配记录: {user_number}", "ERROR")
        return False

    def update_record(self, user_number, new_area):
        """[Update] 编辑现有记录(通过用户编号定位)"""
        log("业务步骤", f"执行 [更新] 申报对应用户编号: {user_number} -> 新面积: {new_area}", "STEP")
        if not self.search_record_by_user_number(user_number):
            return False

        try:
            edit_btn = self.page.locator("table.el-table__body tr").first.locator("button:has-text('编辑'), button:has-text('修改')").first
            edit_btn.click()
            time.sleep(Config.LONG_WAIT)
            
            # 定位对应的弹窗内部
            self.safe_fill("input[placeholder*='采暖面积']", str(new_area), "采暖面积")
            self._save_form()  # 里面会点击保存
            self.wait_for_vue_update()
            self.wait_for_network_idle()
            return True
        except Exception as e:
            log("更新", f"❌ 编辑报错: {e}", "ERROR")
            return False

    def report_record(self, user_number):
        """[Report] 上报状态为草稿的记录"""
        log("业务步骤", f"执行 [上报] 用户编号: {user_number}", "STEP")
        if not self.search_record_by_user_number(user_number):
            return False
            
        try:
            report_btn = self.page.locator("table.el-table__body tr").first.locator("button:has-text('上报')")
            if report_btn.is_visible():
                report_btn.click()
                time.sleep(1.5)
                # 确认上报
                confirm_btn = self.page.locator(
                    ".el-message-box__btns button:has-text('确定')"
                ).last
                if confirm_btn.is_visible():
                    confirm_btn.click()
                    time.sleep(Config.LONG_WAIT)
                    log("上报", f"✅ 用户编号 [{user_number}] 上报成功", "OK")
                    return True
                else:
                    log("上报", "❌ 未找到上报确认按钮", "ERROR")
            else:
                log("上报", "❌ 列表中未找到【上报】按钮", "ERROR")
            return False
        except Exception as e:
            log("上报", f"❌ 上报异常: {e}", "ERROR")
            return False

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
        """填写设备新增的4个区块表单字段

        基于前端组件分析：
        - HouseholdInfo.vue: 户主姓名/身份证号/联系电话(el-input)，安装地址(Treeselect)，门牌号/客户编号(el-input)
        - ApplicantInfo.vue: 是否户主(el-select)，申报人姓名/身份证号/联系电话(el-input)，户籍信息(Treeselect)，采暖面积(el-input)
        - DeclarationType.vue: 能源类型(el-select)
        - BasicInfoUpload.vue: 用户编号/银行卡号/开户人姓名(el-input)，附件上传(file-upload)
        """
        d = data

        # 区块 1: 户主信息
        log("表单", ">>> [Section 1] 户主信息", "STEP")
        self.safe_fill("input[placeholder='请输入户主姓名']", d["household_name"], "户主姓名")
        self.safe_fill("input[placeholder='请输入身份证号']", d["id_card"], "身份证号")
        self.safe_fill("input[placeholder='请输入联系电话']", d["phone"], "联系电话")

        # 安装地址 — 前端使用 Treeselect 组件（不是普通 input），需通过 Vue 实例赋值
        self._select_treeselect_first_leaf("安装地址")

        self.safe_fill("input[placeholder='请输入门牌号']", d["door_number"], "门牌号")
        self.safe_fill("input[placeholder='请输入客户编号']", d["customer_id"], "客户编号")

        # 区块 2: 申报人信息
        log("表单", ">>> [Section 2] 申报人信息 (处理禁用联动)", "STEP")

        # 是否户主 — 前端 ApplicantInfo.vue 使用 el-select（不是基于 placeholder 的 input）
        self.select_dropdown("是否户主")
        self.wait_for_vue_update()  # 选择后可能触发申报人字段的禁用/启用联动

        self.safe_fill("input[placeholder='请输入申报人姓名']", d["applicant_name"], "申报人姓名")
        self.safe_fill("input[placeholder='请输入申报人身份证号']", d["applicant_id_card"], "申报人身份证号")
        self.safe_fill("input[placeholder='请输入申报人联系电话']", d["applicant_phone"], "申报人联系电话")

        # 户籍信息（Treeselect 组件，通过 Vue 实例直接设值）
        self._select_huji_to_village()

        self.safe_fill("input[placeholder*='采暖面积']", d["heating_area"], "采暖面积")

        # 区块 3: 能源类型 — 前端 DeclarationType.vue 使用 el-select
        log("表单", ">>> [Section 3] 能源类型", "STEP")
        body = self.get_dialog_body()
        self.select_dropdown("能源类型")

        # 区块 4: 基础信息
        log("表单", ">>> [Section 4] 基础信息", "STEP")

        if body:
            body.evaluate("el => el.scrollTop += 600")
            time.sleep(0.3)
        self.safe_fill("input[placeholder*='用户编号']", d["user_number"], "用户编号")
        self.safe_fill("input[placeholder*='银行卡号']", d["bank_account"], "银行卡号")
        self.safe_fill("input[placeholder*='开户人姓名']", d["account_holder_name"], "开户人姓名")

        # 统一上传附件
        if body:
            body.evaluate("el => el.scrollTop = 0")
            time.sleep(0.3)
        self.upload_files()
        # 等待所有附件上传完成
        try:
            self.page.wait_for_function(
                """() => {
                    const uploading = document.querySelectorAll('.el-upload-list__item.is-uploading');
                    return uploading.length === 0;
                }""",
                timeout=10000
            )
        except:
            time.sleep(Config.UPLOAD_WAIT)


    def _save_form(self):
        """保存表单并捕获新生成的申报编号"""
        log("新增", "点击【保存】（生成系统编号）", "STEP")
        try:
            btn = self.page.locator("button:has-text('保 存') >> visible=true").first
            btn.click()
            log("新增", "等待系统响应...")
            return self._wait_save_and_capture_order_id("新增")
        except Exception as e:
            log("新增", f"❌ 保存或编号抓取失败: {e}", "ERROR")
            return None

    def _wait_save_and_capture_order_id(self, tag="保存", timeout=15000):
        """等待保存成功提示并从列表首行抓取 SB 格式的系统申报编号。

        此方法是 _save_form() 和 create_device_update_record() 共享的核心逻辑，
        避免在两处重复实现相同的等待和抓取流程。

        Args:
            tag: 日志标签，用于区分调用来源
            timeout: 等待保存成功提示的超时时间（毫秒）
        Returns:
            str: 抓取到的申报编号，失败返回 None
        """
        try:
            self.page.wait_for_selector("text=保存成功", timeout=timeout)
            log(tag, "✅ 保存成功提示已出现")
            time.sleep(Config.SHORT_WAIT)

            # 等待弹窗关闭
            try:
                self.page.wait_for_selector(".el-dialog__wrapper", state="hidden", timeout=5000)
            except:
                pass

            # 从列表首行抓取 SB 编号（最多重试 3 次）
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
                        log(tag, f"✅ 成功抓取系统申报编号: {txt}", "OK")
                        return txt
                log(tag, f"第 {attempt+1} 次抓取未成功，重试中...", "WARN")

            log(tag, "⚠️ 多次重试未发现 SB 编号", "WARN")
            return None
        except Exception as e:
            log(tag, f"❌ 保存响应异常: {e}", "ERROR")
            return None




    def _select_treeselect_first_leaf(self, label_text):
        """选择 Treeselect 组件的第一个叶子节点 — 通过 form-item label 精确定位 + 计算属性 setter 赋值。

        前端 HouseholdInfo.vue 中安装地址使用 @riophae/vue-treeselect 组件：
          <Treeselect v-model="installAddressForTreeselect"
                      :options="filteredDistrictTreeOptions" />
        计算属性 setter 会调用 $set(saveFormData, fieldCode, String(val))

        Args:
            label_text: 表单标签文本，如 "安装地址"
        """
        log("表单填写", f">> [{label_text}] 选择 Treeselect 叶子节点", "STEP")
        try:
            result = self.page.evaluate(f"""() => {{
                const wrappers = document.querySelectorAll('.el-dialog__wrapper');
                for (const wrapper of wrappers) {{
                    if (wrapper.style.display === 'none') continue;
                    const body = wrapper.querySelector('.el-dialog__body');
                    if (!body) continue;

                    // === 精确定位：通过 form-item label 找到目标 Treeselect ===
                    const formItems = body.querySelectorAll('.el-form-item');
                    let targetTsEl = null;
                    for (const fi of formItems) {{
                        const labelEl = fi.querySelector('.el-form-item__label');
                        if (!labelEl || !labelEl.textContent.includes('{label_text}')) continue;
                        targetTsEl = fi.querySelector('.vue-treeselect');
                        break;
                    }}
                    if (!targetTsEl) continue;

                    // === 回溯到拥有 tree options 的父组件 ===
                    let vm = targetTsEl.__vue__;
                    while (vm && !vm.filteredDistrictTreeOptions && !vm.districtTreeOptions && vm.$parent) {{
                        vm = vm.$parent;
                    }}
                    const options = vm.filteredDistrictTreeOptions || vm.districtTreeOptions;
                    if (!options || options.length === 0) continue;

                    // === 递归找第一个叶子节点 ===
                    function findLeaf(nodes) {{
                        for (const n of nodes) {{
                            if (!n.children || n.children.length === 0) return n;
                            const r = findLeaf(n.children);
                            if (r) return r;
                        }}
                        return null;
                    }}
                    const leaf = findLeaf(options);
                    if (!leaf) continue;

                    // === 通过计算属性 setter 赋值（触发 Vue 响应式 + Treeselect UI 更新）===
                    if ('installAddressForTreeselect' in vm) {{
                        vm.installAddressForTreeselect = Number(leaf.id);
                    }} else {{
                        // 兜底: 直接 $set
                        const fieldCode = vm.fieldCodeInstallAddress || 'install_address';
                        if (vm.saveFormData) {{
                            vm.$set(vm.saveFormData, fieldCode, String(leaf.id));
                        }}
                    }}

                    // 强制 Treeselect 组件刷新 UI
                    const tsVue = targetTsEl.__vue__;
                    if (tsVue) {{
                        if (tsVue.$forceUpdate) tsVue.$forceUpdate();
                        if (tsVue.$parent && tsVue.$parent.$forceUpdate) tsVue.$parent.$forceUpdate();
                    }}

                    return leaf.name || String(leaf.id);
                }}
                return null;
            }}""")

            if result:
                time.sleep(Config.SHORT_WAIT)
                log("表单填写", f"✅ [{label_text}]: 已选 [{result}]")
            else:
                log("表单填写", f"⚠️ [{label_text}]: 未能通过 Vue 实例设值", "WARN")
        except Exception as e:
            log("表单填写", f"⚠️ [{label_text}] Treeselect 选择异常: {e}", "WARN")

    def _select_huji_to_village(self):
        """通过 JS + UI 交互选择户籍信息 — 逐级展开 Treeselect 至叶子节点。

        vue-treeselect 监听 mousedown 事件打开菜单（不是 click 事件），
        所以必须用 Playwright 原生 click（会触发完整 mousedown→mouseup→click 序列）
        来打开下拉面板。
        """
        log("表单填写", ">> [户籍信息] 选择到村级", "STEP")
        try:
            # 1. 用 Playwright 定位并点击户籍信息的 Treeselect 控件
            #    （Playwright click 会触发 mousedown 事件，JS click() 不会）
            dialog = self.page.locator('.el-dialog__wrapper:visible')
            huji_fi = dialog.locator('.el-form-item').filter(has_text='户籍信息')
            ts_control = huji_fi.locator('.vue-treeselect__control').first
            ts_control.click()
            time.sleep(1)  # 等待 menu 渲染（append-to-body 到 body 级别）

            # 2. 逐级展开分支并选择叶子节点（纯 JS 交互）
            for depth in range(10):
                result = self.page.evaluate("""() => {
                    // 找到当前可见的 vue-treeselect menu
                    const menus = document.querySelectorAll('.vue-treeselect__menu');
                    let menu = null;
                    for (let i = menus.length - 1; i >= 0; i--) {
                        const m = menus[i];
                        if (m.offsetHeight > 0 && m.offsetWidth > 0) {
                            menu = m;
                            break;
                        }
                    }
                    if (!menu) return { error: 'no_visible_menu', total: menus.length };

                    // 遍历所有 option
                    const options = menu.querySelectorAll('.vue-treeselect__option');
                    let visibleCount = 0;
                    for (const opt of options) {
                        // 跳过隐藏的 option（被折叠的子级）
                        if (opt.offsetHeight === 0) continue;
                        // 跳过有 --hide 类的
                        if (opt.classList.contains('vue-treeselect__option--hide')) continue;
                        visibleCount++;

                        const arrowContainer = opt.querySelector('.vue-treeselect__option-arrow-container');

                        if (arrowContainer) {
                            // === 分支节点 ===
                            const arrowEl = arrowContainer.querySelector('.vue-treeselect__option-arrow');
                            const isExpanded = arrowEl && arrowEl.classList.contains('vue-treeselect__option-arrow--rotated');
                            if (isExpanded) {
                                continue; // 已展开，继续查找子级
                            }
                            // 未展开 → 点击箭头展开
                            arrowContainer.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                            return { action: 'expanded' };
                        } else {
                            // === 叶子节点 === → 点击选择
                            const labelEl = opt.querySelector('.vue-treeselect__label');
                            const text = labelEl ? labelEl.textContent.trim() : '';
                            // vue-treeselect 用 mousedown 事件触发选择
                            opt.querySelector('.vue-treeselect__label-container').dispatchEvent(
                                new MouseEvent('mousedown', { bubbles: true })
                            );
                            return { action: 'selected', label: text };
                        }
                    }
                    return { error: 'no_actionable_options', visible: visibleCount, total: options.length };
                }""")

                if not result or 'error' in result:
                    log("表单填写", f"⚠️ 户籍信息调试: {result}", "WARN")
                    break

                if result.get('action') == 'selected':
                    time.sleep(Config.SHORT_WAIT)
                    log("表单填写", f"✅ 户籍信息: 已选 [{result.get('label', '')}]")
                    return True
                elif result.get('action') == 'expanded':
                    time.sleep(0.5)
                    continue

            # 关闭可能残留的下拉面板，避免遮挡后续操作
            self.page.keyboard.press("Escape")
            time.sleep(0.3)
            log("表单填写", "⚠️ 户籍信息: 未能完成选择", "WARN")
            return False

        except Exception as e:
            log("表单填写", f"⚠️ 户籍信息选择异常: {e}", "WARN")
            try:
                self.page.keyboard.press("Escape")
                time.sleep(0.3)
            except:
                pass
            return False



