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
        
        # 2. 等待"设备更新申报"弹窗出现，并定位身份证号输入框
        #    截图DOM结构：弹窗标题"设备更新申报" → 查询区域: [身份证号下拉] [请输入 input] [查询按钮]
        try:
            # 等待设备更新弹窗标题出现（区分类型选择弹窗）
            self.page.locator(".el-dialog__header:has-text('设备更新')").first.wait_for(
                state="visible", timeout=Config.PAGE_LOAD_TIMEOUT
            )
            time.sleep(Config.SHORT_WAIT)
            log("设备更新", "✅ 设备更新弹窗已加载")
            
            # 定位正确的弹窗（含"设备更新"标题的那个 dialog）
            dialog = self.page.locator(".el-dialog:has(.el-dialog__header:has-text('设备更新')) .el-dialog__body").first
            id_input = None
            
            # 策略1：找蓝色查询按钮同级的输入框
            try:
                query_btn = dialog.locator("button:has-text('查询')").first
                if query_btn.is_visible(timeout=2000):
                    # 查询按钮的父容器内的文本输入框
                    parent = query_btn.locator("..")  # 按钮的父元素
                    inp = parent.locator(".. >> input.el-input__inner").first
                    if not inp.is_visible(timeout=1000):
                        inp = None
                    else:
                        id_input = inp
                        log("设备更新", "✅ 策略1命中：查询按钮同行输入框")
            except:
                pass
            
            # 策略2：通过 placeholder "请输入" 在弹窗内精确查找
            if not id_input:
                try:
                    candidates = dialog.locator("input.el-input__inner[placeholder*='请输入']")
                    cnt = candidates.count()
                    log("设备更新", f"策略2：找到 {cnt} 个 placeholder 含'请输入'的 input")
                    for i in range(cnt):
                        inp = candidates.nth(i)
                        if inp.is_visible(timeout=1000) and inp.is_enabled(timeout=1000):
                            # 排除下拉选择框内的 input（readonly 或 aria-role=combobox）
                            readonly = inp.get_attribute("readonly")
                            if readonly is None:
                                id_input = inp
                                log("设备更新", f"✅ 策略2命中：第{i+1}个可编辑input")
                                break
                except:
                    pass
            
            # 策略3：JS 兜底 — 在所有弹窗内找身份证号查询区域的输入框
            if not id_input:
                try:
                    js_result = self.page.evaluate("""() => {
                        const dialogs = document.querySelectorAll('.el-dialog__body');
                        for (const d of dialogs) {
                            if (!d.offsetParent) continue;  // 跳过隐藏的
                            const inputs = d.querySelectorAll('input.el-input__inner');
                            for (const inp of inputs) {
                                if (inp.offsetParent && !inp.readOnly && !inp.disabled) {
                                    const ph = inp.placeholder || '';
                                    if (ph.includes('请输入') || ph.includes('输入')) {
                                        return true;
                                    }
                                }
                            }
                        }
                        return false;
                    }""")
                    if js_result:
                        id_input = self.page.locator(".el-dialog__body >> input.el-input__inner[placeholder*='请输入']:not([readonly])").first
                        if id_input.is_visible(timeout=2000):
                            log("设备更新", "✅ 策略3命中：JS兜底定位")
                        else:
                            id_input = None
                except:
                    pass
            
            if not id_input:
                log("设备更新", "❌ 所有策略均未找到身份证号输入框", "ERROR")
                return None

            id_input.click()
            id_input.fill(id_card)
            time.sleep(Config.SHORT_WAIT)
            log("设备更新", f"✅ 已填入身份证号: {id_card}")
        except Exception as e:
            log_err("设备更新", "填写身份证号失败", e)
            return None
        
        # 3. 点击查询按钮
        try:
            query_btn = dialog.locator("button:has-text('查询'), button:has-text('搜索')").first
            query_btn.click()
            time.sleep(Config.LONG_WAIT)
            log("设备更新", "✅ 已点击查询按钮")
        except Exception as e:
            log_err("设备更新", "点击查询按钮失败", e)
            return None
        
        # 4. 等待查询结果（表单出现，应显示关联的原有设备信息）
        try:
            self.page.locator(".section-title:has-text('原有设备信息'), .section-title:has-text('户主信息'), .section-title:has-text('申报类型')").first.wait_for(
                state="visible", timeout=Config.PAGE_LOAD_TIMEOUT
            )
            log("设备更新", "✅ 查询成功，设备更新表单已加载")
        except:
            log("设备更新", "❌ 查询身份证号后未能加载表单", "ERROR")
            return None
        
        # 5. 填写需要补充的字段（申报人信息区块）
        if data:
            try:
                # 是否户主
                if data.get("is_household"):
                    self.safe_select_by_text("input[placeholder='请选择是否户主']", data["is_household"], "是否户主")
                # 采暖面积
                if data.get("heating_area"):
                    self.safe_fill("input[placeholder*='采暖面积']", str(data["heating_area"]), "采暖面积")
                # 户籍信息
                self.safe_select_first("input[placeholder='请输入户籍信息']", "户籍信息")
            except Exception as e:
                log("设备更新", f"⚠️ 表单补充填写异常: {e}", "WARN")
        
        # 6. 保存并上报
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
