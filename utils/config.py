# -*- coding: utf-8 -*-
import os

# [DEBUG] 打印加载路径，确保用户修改的是同一个文件
print(f"[CONFIG] 配置文件加载路径: {os.path.abspath(__file__)}")

class Config:
    """自动化测试全局配置"""
    # 获取项目根目录 (c:/.../warm_test)
    _ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # ================= 配置开关 (一键切换) =================
    # 环境切换：可选 "local", "test"
    ENV_TYPE = "local" 
    
    # 角色切换：可选 "admin", "city", "district", "town", "village"
    USER_ROLE = "village"
    # =================================================

    # 环境字典：聚合地址与账号
    ENV_MAP = {
        "local": {
            "url": "http://localhost:8888/",
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
                "admin":    {"username": "gly1",    "password": "Pass@000000"},
                "city":     {"username": "shiji1",  "password": "Pass@000000"},
                "district": {"username": "quji1",   "password": "Pass@000000"},
                "town":     {"username": "zhenji1", "password": "Pass@000000"},
                "village":  {"username": "cunji1",  "password": "Pass@000000"},
            }
        }
    }

    @classmethod
    def _get_env_config(cls):
        """内部方法：确保获取当前 ENV_TYPE 对应的配置"""
        config = cls.ENV_MAP.get(cls.ENV_TYPE)
        if not config:
            return cls.ENV_MAP["test"]
        return config

    # --- 动态获取方法 ---
    @classmethod
    def get_base_url(cls):
        url = cls._get_env_config()["url"]
        print(f"[CONFIG] 运行时获取 URL: {url} (当前 ENV_TYPE: {cls.ENV_TYPE})")
        return url

    @classmethod
    def get_username(cls):
        accounts = cls._get_env_config()["accounts"]
        return accounts.get(cls.USER_ROLE, accounts["village"])["username"]

    @classmethod
    def get_password(cls):
        accounts = cls._get_env_config()["accounts"]
        return accounts.get(cls.USER_ROLE, accounts["village"])["password"]

    # 浏览器设置
    HEADLESS = False
    SLOW_MO = 500
    WINDOW_MAXIMIZED = False
    VIEWPORT_W = 1920
    VIEWPORT_H = 1080

    # 超时时间 (ms)
    PAGE_LOAD_TIMEOUT = 10_000
    ELEMENT_TIMEOUT = 5_000
    
    # 等待时间 (s)
    SHORT_WAIT = 0.5
    MEDIUM_WAIT = 1.0
    LONG_WAIT = 2.0

    # 路径配置 (使用绝对路径)
    SCREENSHOT_DIR = os.path.join(_ROOT_DIR, "screenshots")
    LOG_FILE = os.path.join(_ROOT_DIR, "logs", "test_playwright.log")
    
    # 登录重试
    MAX_LOGIN_RETRIES = 10
