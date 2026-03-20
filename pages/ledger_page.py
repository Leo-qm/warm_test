# -*- coding: utf-8 -*-
import time
from pages.base_page import BasePage
from utils.config import Config
from utils.logger import log, log_err


class LedgerPage(BasePage):
    """设备申报台账管理页 — 封装台账查询与导出功能"""

    def navigate_to_ledger(self):
        """导航至设备申报台账管理页面"""
        log("业务步骤", "========== 导航至台账管理页面 ==========", "STEP")
        try:
            # 1. 点击顶部“清洁能源”
            top = self.page.locator(".cls-header-menu a:has-text('清洁能源')")
            if top.count() > 0:
                top.first.click(force=True)
                time.sleep(Config.LONG_WAIT)
        except:
            pass

        # 2. 点击左侧菜单
        self.page.click("li.el-submenu:has-text('清洁取暖设备申报管理')")
        time.sleep(Config.MEDIUM_WAIT)
        self.page.click("li.el-menu-item:has-text('设备申报台账管理')")
        
        # 3. 等待列表加载
        self.page.wait_for_selector("table.el-table__body tr", timeout=Config.PAGE_LOAD_TIMEOUT)
        log("导航", "✅ 已进入设备申报台账管理页面", "OK")

    def search_by_order_id(self, order_id):
        """通过申报编号搜索台账记录"""
        if not order_id:
            return False

        log("业务步骤", f"执行 [台账查询] 申报编号: {order_id}", "STEP")
        
        # 点击重置清理状态
        try:
            self.page.click("button:has-text('重置')", timeout=2000)
            time.sleep(Config.SHORT_WAIT)
        except:
            pass

        # 输入并查询
        self.safe_fill("input[placeholder*='申报编号']", order_id, "申报编号")
        self.page.click("button:has-text('搜索')")
        time.sleep(Config.MEDIUM_WAIT)

        # 验证结果
        try:
            row = self.page.locator("table.el-table__body tr").first
            if order_id in row.inner_text():
                log("查询", f"✅ 台账中成功找到记录: {order_id}", "OK")
                return True
        except:
            pass

        log("查询", f"❌ 台账中未找到记录: {order_id}", "ERROR")
        return False

    def export_ledger(self):
        """执行导出台账操作"""
        log("业务步骤", "执行 [导出台账] 操作", "STEP")
        try:
            # 拦截下载事件
            with self.page.expect_download() as download_info:
                self.page.click("button:has-text('导出台账')")
            
            download = download_info.value
            save_path = Config.get_report_path(f"ledger_export_{int(time.time())}.xlsx")
            download.save_as(save_path)
            log("导出", f"✅ 台账导出成功，保存至: {save_path}", "OK")
            return save_path
        except Exception as e:
            log_err("导出", "导出操作失败", e)
            return None

    def start_subsidy_declaration(self, order_id):
        """点击‘补贴申报’按钮"""
        log("业务步骤", f"执行 [发起补贴申报] 流程，编号: {order_id}", "STEP")
        if self.search_by_order_id(order_id):
            try:
                # 定位‘补贴申报’按钮
                btn = self.page.locator("table.el-table__body tr").first.locator("button:has-text('补贴申报')")
                if btn.count() > 0:
                    btn.click()
                    time.sleep(Config.MEDIUM_WAIT)
                    log("补贴申报", f"✅ 已进入 [{order_id}] 的补贴申报表单页面", "OK")
                    return True
                else:
                    log("补贴申报", "❌ 未找到【补贴申报】按钮，可能状态不满足条件", "ERROR")
            except Exception as e:
                log_err("补贴申报", "点击操作异常", e)
        return False

    def fill_subsidy_declaration(self, data):
        """填写补贴申报表单（基于台账页触发后的表单）"""
        log("业务步骤", ">>> 正在填写补贴申报表单内容", "STEP")
        d = data
        try:
            # 根据台账中“补贴申报”弹窗的常见字段进行封装
            # 1. 设备品牌与型号
            self.safe_fill("input[placeholder*='设备品牌']", d.get("device_brand", "格力"), "设备品牌")
            self.safe_fill("input[placeholder*='设备型号']", d.get("device_model", "MOD-X1"), "设备型号")
            
            # 2. 购置金额与补贴金额
            self.safe_fill("input[placeholder*='购置金额']", d.get("purchase_amount", "3000"), "购置金额")
            self.safe_fill("input[placeholder*='补贴金额']", d.get("subsidy_amount", "1000"), "补贴金额")
            
            # 3. 安装人与发票号
            self.safe_fill("input[placeholder*='安装人姓名']", d.get("installer_name", "张师傅"), "安装人姓名")
            self.safe_fill("input[placeholder*='安装人联系电话']", d.get("installer_phone", "13800000000"), "安装人电话")
            self.safe_fill("input[placeholder*='发票号']", d.get("invoice_number", "INV123456"), "发票号")
            
            # 4. 提交
            submit_btn = self.page.locator("button:has-text('提交'), button:has-text('确定'), button:has-text('上 报')").first
            submit_btn.click()
            
            # 等待成功
            self.page.wait_for_selector("text=提交成功, text=上报成功, text=操作成功", timeout=10000)
            log("补贴申报", "✅ 补贴申报表单填写并提交成功", "OK")
            return True
        except Exception as e:
            log_err("补贴申报", "表单填写或提交异常", e)
            return False

    def view_record_detail(self, order_id):
        """查看台账记录详情"""
        log("业务步骤", f"执行 [查看详情] 申报编号: {order_id}", "STEP")
        if self.search_by_order_id(order_id):
            try:
                # 点击第一行的查看按钮
                self.page.locator("table.el-table__body tr").first.locator("button:has-text('查看')").click()
                time.sleep(Config.MEDIUM_WAIT)
                
                # 等待详情弹窗加载
                self.page.wait_for_selector(".el-dialog__title:has-text('详情'), .el-dialog__title:has-text('查看')", timeout=5000)
                log("查看", f"✅ 已打开 [{order_id}] 的详情页面", "OK")
                
                # 关闭弹窗
                self.page.click("button:has-text('关 闭'), .el-dialog__headerbtn")
                time.sleep(Config.SHORT_WAIT)
                return True
            except Exception as e:
                log_err("查看", "查看详情失败", e)
        return False
