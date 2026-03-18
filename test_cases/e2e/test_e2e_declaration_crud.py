# -*- coding: utf-8 -*-
import pytest
from pages.declaration_page import DeclarationPage
from utils.data_factory import DataFactory
from utils.logger import log


@pytest.mark.e2e
class TestDeclarationCRUD:
    """清洁取暖设备申报 — CRUD 端到端闭环测试"""

    @pytest.mark.parametrize("is_household", ["是", "否"])
    def test_crud_loop(self, logged_in_page, is_household):
        """完整 CRUD 闭环: 新增 -> 查询 -> 查看 -> 修改 -> 删除"""
        page = logged_in_page
        declaration = DeclarationPage(page)

        log("测试用例", f">>> 开始执行: [CRUD 闭环测试 (户主={is_household})] <<<")

        # 1. [Create] 新增记录
        log("测试用例", "--- 阶段 1: 新增记录 ---", "STEP")
        test_data = DataFactory.build_test_data(is_household=is_household)
        order_id = declaration.create_record(test_data)
        assert order_id, "新增记录后未能抓取到申报编号，无法执行后续 CRUD 闭环"

        # 2. [Read] 查询与查看验证
        log("测试用例", "--- 阶段 2: 查询与查看验证 ---", "STEP")
        assert declaration.search_record(order_id), f"新增后查询失败，申报编号 [{order_id}] 未找到"
        declaration.view_record(order_id)

        # 3. [Update] 修改记录
        log("测试用例", "--- 阶段 3: 修改记录 ---", "STEP")
        new_area = 200.5
        declaration.update_record(order_id, new_area)
        declaration.search_record(order_id)

        # 4. [Delete] 删除记录
        log("测试用例", "--- 阶段 4: 删除记录 ---", "STEP")
        declaration.delete_record(order_id)

        # 最终验证：确认已删除
        log("测试用例", "--- 最终验证: 确认已删除 ---", "STEP")
        assert not declaration.search_record(order_id), \
            f"删除后查询依然存在，申报编号 [{order_id}] 删除失败"

        log("测试用例", ">>> CRUD 闭环执行成功! <<<", "OK")
