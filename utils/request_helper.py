# -*- coding: utf-8 -*-
"""
HTTP 请求助手模块
封装了 requests 库，提供统一的请求记录与响应调试输出。
"""

import requests
from utils.logger import log

class RequestHelper:
    """
    网络请求工具类
    拦截并记录所有发送的请求及返回的响应，便于接口层自动化调试。
    """
    
    @staticmethod
    def request(method: str, url: str, **kwargs) -> requests.Response:
        """
        发送通用 HTTP 请求
        :param method: 请求方法 (GET, POST, PUT, DELETE 等)
        :param url: 请求完整的 URL 地址
        :param kwargs: 传递给 requests 的额外参数 (json, data, headers, cookies 等)
        :return: requests.Response 对象
        """
        log("INTER", f"发送请求: {method} {url} 参数: {kwargs}")
        # 执行物理请求
        response = requests.request(method, url, **kwargs)
        # 记录关键响应结果
        log("INTER", f"收到响应: {response.status_code} {response.text[:200]}...") # 截断过长输出
        return response
