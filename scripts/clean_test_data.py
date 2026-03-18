import os
from loguru import logger

def clean_logs():
    if os.path.exists("logs/test.log"):
        os.remove("logs/test.log")
        logger.info("已清理日志文件")

def clean_reports():
    # 清理报告逻辑
    pass

if __name__ == "__main__":
    clean_logs()
