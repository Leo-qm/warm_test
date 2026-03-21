# -*- coding: utf-8 -*-
"""
项目全局配置模块
用于管理自动化测试的环境切换、多角色账号信息、浏览器驱动设置及全局路径。
"""

import os
import sys

# 【防玄学神器】禁止 Python 缓存当前模块的 .pyc 文件
# 以后你每次只管直接改这篇代码，改完 Ctrl+S，环境立刻无缝切换，绝不需要清理缓存！
sys.dont_write_bytecode = True

# [DEBUG] 打印加载路径，确保用户修改的是同一个文件
print(f"[CONFIG] 配置文件加载路径: {os.path.abspath(__file__)}")

class Config:
    """
    自动化测试全局配置类
    采用类属性方式存储静态配置，并通过类方法实现动态环境切换。
    """
    
    # 获取项目根目录 (c:/.../warm_test)
    _ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # ================= 配置开关 (一键切换) =================
    # 环境切换：可选 "local" (本地开发环境), "test" (联调/测试环境)
    ENV_TYPE = "test" 
    
    # =================================================

    # 环境字典：聚合不同环境下的基础地址与业务账号
    ENV_MAP = {
        "local": {
            "url": "http://localhost:8889/#/admin/",
            "accounts": {
                "admin":    {"username": "gly1",    "password": "Pass@000000"},
                "city":     {"username": "shiji1",  "password": "Pass@000000"},
                "district": {"username": "quji1",   "password": "Pass@000000"},
                "town":     {"username": "zhenji1", "password": "Pass@000000"},
                "village":  {"username": "cunji1",  "password": "Pass@000000"},
            }
        },
        "test": {
            "url": "https://rural.touchit.com.cn/agri/#/admin?redirect=%2FcleanEnergy",
            "accounts": {
                "admin":    {"username": "18800000060",    "password": "Pass@000000"},
                "city":     {"username": "qingjieshi",     "password": "Pass@000000"},
                "district": {"username": "qingjiequ",      "password": "Pass@000000"},
                "town":     {"username": "qingjiezhen",    "password": "Pass@000000"},
                "village":  {"username": "qingjiecun",     "password": "Pass@000000"},
            }
        }
    }

    @classmethod
    def _get_env_config(cls):
        """
        内部方法：根据当前 ENV_TYPE 获取对应的配置字典
        :return: 包含 url 和 accounts 的配置字典，若 ENV_TYPE 无效则默认返回 test 配置
        """
        config = cls.ENV_MAP.get(cls.ENV_TYPE)
        if not config:
            return cls.ENV_MAP["test"]
        return config

    # --- 动态获取方法 ---
    @classmethod
    def get_base_url(cls):
        """
        获取当前环境的网站入口地址
        :return: 完整的 URL 字符串
        """
        url = cls._get_env_config()["url"]
        return url

    @classmethod
    def get_username(cls, role="village"):
        """
        根据业务角色获取登录用户名
        :param role: 业务角色标签 ("admin", "city", "district", "town", "village")
        :return: 用户名字符串
        """
        accounts = cls._get_env_config()["accounts"]
        return accounts.get(role, accounts["village"])["username"]

    @classmethod
    def get_password(cls, role="village"):
        """
        根据业务角色获取登录密码
        :param role: 业务角色标签
        :return: 密码字符串
        """
        accounts = cls._get_env_config()["accounts"]
        return accounts.get(role, accounts["village"])["password"]

    # --- 浏览器运行设置 ---
    HEADLESS = False           # 是否开启无头模式 (True 则不显示 UI 界面)
    SLOW_MO = 500              # 演示模式：每个操作强制等待的毫秒数 (有助于观察 UI 动作)
    WINDOW_MAXIMIZED = False   # 是否启动时最大化窗口
    VIEWPORT_W = 1920          # 默认浏览器宽度
    VIEWPORT_H = 1080          # 默认浏览器高度

    # --- 隐式与显式超时 (ms) ---
    PAGE_LOAD_TIMEOUT = 10_000 # 页面加载等待上限
    ELEMENT_TIMEOUT = 5_000    # 元素查找/可操作等待上限
    
    # --- 逻辑等待预设 (s) ---
    SHORT_WAIT = 0.5           # 短等待
    MEDIUM_WAIT = 1.0          # 中等待
    LONG_WAIT = 2.0            # 长等待

    # --- 路径配置 (使用绝对路径，避免由于执行目录不同导致的找不到文件) ---
    SCREENSHOT_DIR = os.path.join(_ROOT_DIR, "screenshots") # 截图存放目录
    LOG_FILE = os.path.join(_ROOT_DIR, "logs", "test_playwright.log") # 日志文件全路径
    
    # --- 登录业务特有配置 ---
    MAX_LOGIN_RETRIES = 10     # 验证码识别错误时的自动重试最大次数
