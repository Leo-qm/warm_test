# -*- coding: utf-8 -*-
"""
补贴金额计算器模块
复刻前端 DeviceInfo.vue 中的补贴金额计算算法，用于 E2E 测试验证。

计算规则：
  1. 基本补贴 和 生态涵养区补贴 互斥（由区域决定）
  2. 特殊补贴 可叠加在基础补贴之上（对"剩余金额"再按比例计算）
  3. 结果保留两位小数（与前端 Math.round(x*100)/100 一致）
"""

import math
import requests
from utils.logger import log
from utils.config import Config


class SubsidyCalculator:
    """
    补贴金额计算器
    通过 API 获取补贴配置和区域信息，按前端算法计算预计补贴金额。
    """

    @classmethod
    def from_page(cls, page):
        """
        从 Playwright page 对象创建计算器实例
        自动从浏览器 localStorage 提取 ACCESS_TOKEN 和 TENANT_ID

        :param page: Playwright Page 对象（已登录状态）
        :return: SubsidyCalculator 实例
        """
        api_base = Config.get_api_base_url()
        token = None
        tenant_id = None
        try:
            token = page.evaluate("() => localStorage.getItem('ACCESS_TOKEN')")
            tenant_id = page.evaluate("() => localStorage.getItem('TENANT_ID')")
            log("补贴计算", f"从浏览器获取鉴权信息: token={'✓' if token else '✗'}, tenant-id={tenant_id or '✗'}", "INFO")
        except Exception as e:
            log("补贴计算", f"从浏览器获取鉴权信息失败: {e}", "WARN")
        return cls(api_base_url=api_base, token=token, tenant_id=tenant_id)

    def __init__(self, api_base_url: str, token: str = None, tenant_id: str = None):
        """
        初始化计算器

        :param api_base_url: 后端 API 基础地址，如 https://rural.touchit.com.cn/agri-api
        :param token: 登录 Token（Bearer 鉴权）
        :param tenant_id: 租户 ID
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.headers = {
            "Content-Type": "application/json",
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        if tenant_id:
            self.headers["tenant-id"] = str(tenant_id)

        # 补贴配置（延迟加载）
        self._config = None
        # 区域列表（延迟加载）
        self._district_list = None

    # ==================== API 数据获取 ====================

    def load_subsidy_config(self) -> dict:
        """
        从后端 API 加载补贴配置
        接口：GET /system/subsidy-ratio/get-all
        返回示例：{ basicRatio, basicMaxAmount, ecologicalRatio, ecologicalMaxAmount, specialRatio, specialMaxAmount }
        """
        url = f"{self.api_base_url}/system/subsidy-ratio/get-all"
        log("补贴计算", f"正在加载补贴配置: {url}", "INFO")

        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            result = resp.json()
            if result.get("code") == 0 and result.get("data"):
                data = result["data"]
                self._config = {
                    "basicRatio": self._parse_num(data.get("basicRatio")),
                    "basicMaxAmount": self._parse_num(data.get("basicMaxAmount")),
                    "ecologicalRatio": self._parse_num(data.get("ecologicalRatio")),
                    "ecologicalMaxAmount": self._parse_num(data.get("ecologicalMaxAmount")),
                    "specialRatio": self._parse_num(data.get("specialRatio")),
                    "specialMaxAmount": self._parse_num(data.get("specialMaxAmount")),
                }
                log("补贴计算", f"补贴配置加载成功: {self._config}", "OK")
                return self._config
            else:
                log("补贴计算", f"补贴配置加载失败: {result}", "ERROR")
                return {}
        except Exception as e:
            log("补贴计算", f"补贴配置加载异常: {e}", "ERROR")
            return {}

    def load_district_list(self) -> list:
        """
        从后端 API 加载区域列表（含生态涵养区标识）
        接口：GET /system/area/district-list
        """
        url = f"{self.api_base_url}/system/area/district-list"
        log("补贴计算", f"正在加载区域列表: {url}", "INFO")

        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            result = resp.json()
            if result.get("code") == 0 and isinstance(result.get("data"), list):
                self._district_list = result["data"]
                eco_count = sum(1 for d in self._district_list if d.get("isEcological") == 1)
                log("补贴计算", f"区域列表加载成功: 共 {len(self._district_list)} 条, 生态涵养区 {eco_count} 个", "OK")
                return self._district_list
            else:
                log("补贴计算", f"区域列表加载失败: {result}", "ERROR")
                return []
        except Exception as e:
            log("补贴计算", f"区域列表加载异常: {e}", "ERROR")
            return []

    def is_ecological_area(self, district_id=None, town_id=None) -> bool:
        """
        判断给定区域是否为生态涵养区

        :param district_id: 区级行政区 ID
        :param town_id: 镇级行政区 ID
        :return: 是否为生态涵养区
        """
        if not self._district_list:
            self.load_district_list()

        if not self._district_list:
            return False

        candidate_ids = []
        if town_id:
            candidate_ids.append(str(town_id))
        if district_id:
            candidate_ids.append(str(district_id))

        if not candidate_ids:
            return False

        for item in self._district_list:
            if str(item.get("id")) in candidate_ids and item.get("isEcological") == 1:
                return True
        return False

    # ==================== 核心计算方法 ====================

    def calculate(
        self,
        purchase_amount: float,
        is_ecological: bool = False,
        is_special_subsidy: bool = False,
        has_special_type: bool = False,
        config: dict = None
    ) -> dict:
        """
        计算预计补贴金额（核心方法）

        复刻前端 DeviceInfo.vue 的 calculateEstimatedSubsidy() 算法：
          1. 基础补贴 = min(购置金额 × 比例%, 最高限额)
          2. 特殊补贴 = min(剩余金额 × 特殊比例%, 特殊限额)
          3. 总补贴 = 基础补贴 + 特殊补贴

        :param purchase_amount: 设备购置总金额（元）
        :param is_ecological: 是否生态涵养区
        :param is_special_subsidy: 是否申请特殊补贴
        :param has_special_type: 是否已选择特殊补贴类型
        :param config: 补贴配置（不传则使用已加载的配置）
        :return: 计算结果字典，包含中间过程和最终金额
        """
        cfg = config or self._config
        if not cfg:
            cfg = self.load_subsidy_config()

        if not cfg:
            log("补贴计算", "无法获取补贴配置，跳过计算", "WARN")
            return {"estimated_subsidy": 0, "error": "无补贴配置"}

        purchase_amount = self._parse_num(purchase_amount)

        # 构建详细的计算过程记录
        process = {
            "purchase_amount": purchase_amount,
            "is_ecological": is_ecological,
            "is_special_subsidy": is_special_subsidy,
            "has_special_type": has_special_type,
        }

        # 购置金额为 0 或负数
        if purchase_amount <= 0:
            process["result"] = 0
            process["reason"] = "购置金额 ≤ 0，预计补贴为 0"
            return self._build_result(process, cfg)

        # ======== 第一步：确定基础补贴比例和上限 ========
        if is_ecological:
            ratio = cfg["ecologicalRatio"]
            max_amount = cfg["ecologicalMaxAmount"]
            ratio_type = "生态涵养区补贴"
        else:
            ratio = cfg["basicRatio"]
            max_amount = cfg["basicMaxAmount"]
            ratio_type = "基本补贴"

        process["ratio_type"] = ratio_type
        process["ratio"] = ratio
        process["max_amount"] = max_amount

        # ======== 第二步：计算基础补贴金额 ========
        raw_base_subsidy = purchase_amount * (ratio / 100)
        base_subsidy = min(raw_base_subsidy, max_amount)
        hit_base_cap = raw_base_subsidy > max_amount

        process["raw_base_subsidy"] = round(raw_base_subsidy, 4)
        process["base_subsidy"] = base_subsidy
        process["hit_base_cap"] = hit_base_cap

        total_subsidy = base_subsidy

        # ======== 第三步：特殊补贴叠加 ========
        if is_special_subsidy and has_special_type:
            remaining = max(0, purchase_amount - base_subsidy)
            raw_special = remaining * (cfg["specialRatio"] / 100)
            special_subsidy = min(raw_special, cfg["specialMaxAmount"])
            hit_special_cap = raw_special > cfg["specialMaxAmount"]

            total_subsidy = base_subsidy + special_subsidy

            process["remaining_amount"] = remaining
            process["special_ratio"] = cfg["specialRatio"]
            process["special_max_amount"] = cfg["specialMaxAmount"]
            process["raw_special_subsidy"] = round(raw_special, 4)
            process["special_subsidy"] = special_subsidy
            process["hit_special_cap"] = hit_special_cap
        else:
            process["special_subsidy"] = 0
            process["special_note"] = "未申请特殊补贴" if not is_special_subsidy else "未选择特殊补贴类型"

        # ======== 第四步：四舍五入保留两位小数 ========
        # 与 JS Math.round(x*100)/100 保持一致
        final_amount = math.floor(total_subsidy * 100 + 0.5) / 100
        process["result"] = final_amount

        return self._build_result(process, cfg)

    # ==================== 日志输出 ====================

    def log_calculation(self, result: dict):
        """
        将计算过程以格式化日志输出

        :param result: calculate() 返回的结果字典
        """
        p = result.get("process", {})
        cfg = result.get("config", {})

        log("补贴计算", "=" * 50, "STEP")
        log("补贴计算", "📊 预计补贴金额计算过程", "STEP")
        log("补贴计算", "-" * 50, "STEP")

        # 输入参数
        log("补贴计算", f"  购置金额: ¥{p.get('purchase_amount', '-')}", "INFO")
        log("补贴计算", f"  是否生态涵养区: {'是 ✓' if p.get('is_ecological') else '否'}", "INFO")
        log("补贴计算", f"  是否申请特殊补贴: {'是 ✓' if p.get('is_special_subsidy') else '否'}", "INFO")
        if p.get("is_special_subsidy"):
            log("补贴计算", f"  是否已选特殊类型: {'是 ✓' if p.get('has_special_type') else '否 ✗'}", "INFO")

        # 配置参数
        log("补贴计算", "-" * 50, "STEP")
        log("补贴计算", f"  当前补贴配置:", "INFO")
        log("补贴计算", f"    基本补贴: {cfg.get('basicRatio', '-')}%, 上限 ¥{cfg.get('basicMaxAmount', '-')}", "INFO")
        log("补贴计算", f"    生态涵养区: {cfg.get('ecologicalRatio', '-')}%, 上限 ¥{cfg.get('ecologicalMaxAmount', '-')}", "INFO")
        log("补贴计算", f"    特殊补贴: {cfg.get('specialRatio', '-')}%, 上限 ¥{cfg.get('specialMaxAmount', '-')}", "INFO")

        # 计算过程
        purchase = p.get("purchase_amount", 0)
        if purchase <= 0:
            log("补贴计算", "-" * 50, "STEP")
            log("补贴计算", f"  ⚠️ {p.get('reason', '购置金额无效')}", "WARN")
            log("补贴计算", f"  🏷️ 预计补贴金额: ¥0", "OK")
        else:
            log("补贴计算", "-" * 50, "STEP")
            log("补贴计算", f"  🔹 第1步 - 基础补贴 ({p.get('ratio_type', '-')}):", "INFO")
            log("补贴计算", f"    公式: ¥{purchase} × {p.get('ratio', '-')}% = ¥{p.get('raw_base_subsidy', '-')}", "INFO")

            if p.get("hit_base_cap"):
                log("补贴计算", f"    ⚡ 触发上限! min(¥{p.get('raw_base_subsidy', '-')}, ¥{p.get('max_amount', '-')}) = ¥{p.get('base_subsidy', '-')}", "WARN")
            else:
                log("补贴计算", f"    基础补贴 = ¥{p.get('base_subsidy', '-')} (未触发上限 ¥{p.get('max_amount', '-')})", "INFO")

            # 特殊补贴
            if p.get("is_special_subsidy") and p.get("has_special_type"):
                log("补贴计算", f"  🔹 第2步 - 特殊补贴叠加:", "INFO")
                log("补贴计算", f"    剩余金额: max(0, ¥{purchase} - ¥{p.get('base_subsidy', '-')}) = ¥{p.get('remaining_amount', '-')}", "INFO")
                log("补贴计算", f"    公式: ¥{p.get('remaining_amount', '-')} × {p.get('special_ratio', '-')}% = ¥{p.get('raw_special_subsidy', '-')}", "INFO")

                if p.get("hit_special_cap"):
                    log("补贴计算", f"    ⚡ 触发上限! min(¥{p.get('raw_special_subsidy', '-')}, ¥{p.get('special_max_amount', '-')}) = ¥{p.get('special_subsidy', '-')}", "WARN")
                else:
                    log("补贴计算", f"    特殊补贴 = ¥{p.get('special_subsidy', '-')} (未触发上限 ¥{p.get('special_max_amount', '-')})", "INFO")

                log("补贴计算", f"  🔹 第3步 - 汇总:", "INFO")
                log("补贴计算", f"    总补贴 = ¥{p.get('base_subsidy', '-')} + ¥{p.get('special_subsidy', '-')} = ¥{p.get('result', '-')}", "INFO")
            else:
                note = p.get("special_note", "")
                if note:
                    log("补贴计算", f"  🔹 第2步 - 特殊补贴: 跳过 ({note})", "INFO")

            log("补贴计算", "-" * 50, "STEP")
            log("补贴计算", f"  🏷️ 预计补贴金额: ¥{p.get('result', '-')}", "OK")

        log("补贴计算", "=" * 50, "STEP")

        return p.get("result", 0)

    # ==================== 便捷方法 ====================

    def calculate_and_log(
        self,
        purchase_amount: float,
        is_ecological: bool = False,
        is_special_subsidy: bool = False,
        has_special_type: bool = False,
    ) -> float:
        """
        一步完成计算 + 日志输出，返回最终金额

        :return: 预计补贴金额 (float)
        """
        result = self.calculate(
            purchase_amount=purchase_amount,
            is_ecological=is_ecological,
            is_special_subsidy=is_special_subsidy,
            has_special_type=has_special_type,
        )
        return self.log_calculation(result)

    # ==================== 私有工具方法 ====================

    @staticmethod
    def _parse_num(val) -> float:
        """解析数字（兼容字符串和 None）"""
        if val is None or val == "":
            return 0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _build_result(process: dict, config: dict) -> dict:
        """构建标准返回字典"""
        return {
            "estimated_subsidy": process.get("result", 0),
            "process": process,
            "config": config,
        }
