# -*- coding: utf-8 -*-
"""
日志管理模块
提供统一的格式化控制台输出和文件持久化记录功能。
支持根据业务场景（INFO, WARN, ERROR, STEP, OK）使用不同的状态标识。
"""

import os
import traceback
from datetime import datetime
from .config import Config

class Logger:
    """
    轻量级日志类
    封装了 Python 原生 print 和文件写入逻辑，支持带标签 (Tag) 的格式化输出。
    """
    
    # 日志状态标识符字典
    SYMBOLS = {
        "INFO": "[INFO]",  # 普通信息
        "WARN": "[WARN]",  # 警告信息
        "ERROR": "[FAIL]", # 失败/错误信息
        "STEP": "[STEP]",  # 业务步骤
        "OK": "[ OK ]",    # 成功断言
    }

    @staticmethod
    def log(tag: str, msg: str, level: str = "INFO"):
        """
        核心日志输出方法
        将日志同时输出到控制台并追加到 Config.LOG_FILE 指定的文件中。
        
        :param tag: 业务模块标签 (如 "登录", "OCR", "运行器")
        :param msg: 日志正文内容
        :param level: 日志级别，对应 SYMBOLS 中的键
        """
        # 生成当前时间戳，精确到毫秒
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        # 获取对应的状态标识
        sym = Logger.SYMBOLS.get(level, "[INFO]")
        # 组装格式化行
        line = f"[{ts}] {sym} [{tag}] {msg}"
        
        # 1. 输出到控制台
        print(line)
        
        # 2. 持久化到文件
        try:
            # 确保日志存储目录存在
            log_dir = os.path.dirname(Config.LOG_FILE)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            # 以追加模式写入，指定 utf-8 编码
            with open(Config.LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            # 即使磁盘写入失败（如权限问题），也不应中断测试脚本执行
            pass

    @staticmethod
    def error_with_tb(tag: str, msg: str, exc: Exception):
        """
        记录错误并输出完整的堆栈轨迹 (Traceback)
        常用于捕获异常后的详细排查日志。
        
        :param tag: 业务模块标签
        :param msg: 自定义错误描述
        :param exc: 捕获到的异常对象
        """
        # 首先记录简要的错误摘要
        Logger.log(tag, f"{msg}: {exc}", "ERROR")
        # 获取完整的堆栈字符串
        tb_str = traceback.format_exc()
        # 逐行输出堆栈，保持日志整齐
        for tb_line in tb_str.strip().splitlines():
            Logger.log(tag, f"  {tb_line}", "ERROR")

# --- 便捷映射 (可以在外部直接调用 log(...) 而不需要 Logger.log(...)) ---
log = Logger.log
log_err = Logger.error_with_tb
