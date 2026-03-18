# -*- coding: utf-8 -*-
import os
import traceback
from datetime import datetime
from .config import Config

class Logger:
    """格式化日志输出并写入文件"""
    
    SYMBOLS = {
        "INFO": "[INFO]",
        "WARN": "[WARN]",
        "ERROR": "[FAIL]",
        "STEP": "[STEP]",
        "OK": "[ OK ]",
    }

    @staticmethod
    def log(tag: str, msg: str, level: str = "INFO"):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        sym = Logger.SYMBOLS.get(level, "[INFO]")
        line = f"[{ts}] {sym} [{tag}] {msg}"
        print(line)
        try:
            # 确保日志目录存在
            log_dir = os.path.dirname(Config.LOG_FILE)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            with open(Config.LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    @staticmethod
    def error_with_tb(tag: str, msg: str, exc: Exception):
        """记录错误并输出完整 traceback"""
        Logger.log(tag, f"{msg}: {exc}", "ERROR")
        tb_str = traceback.format_exc()
        for tb_line in tb_str.strip().splitlines():
            Logger.log(tag, f"  {tb_line}", "ERROR")

# 便捷映射
log = Logger.log
log_err = Logger.error_with_tb
