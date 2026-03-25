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
        """[Create] 点击添加并填写全表单"""
        log("业务步骤", "执行 [新增] 记录流程", "STEP")
        self.page.click("button:has-text('添加')")
        self.page.click(".declaration-type-dialog .type-button:has-text('设备新增')")
        self.page.locator(".section-title:has-text('户主信息')").first.wait_for(state="visible", timeout=Config.PAGE_LOAD_TIMEOUT)
        self._fill_form_content(data)
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
