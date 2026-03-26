# -*- coding: utf-8 -*-
"""
验证码识别助手模块
封装了 ddddocr 库，用于自动化处理 Web 登录界面中的图形验证码。
"""

import ddddocr
from utils.logger import log

class OCRHelper:
    """
    OCR 识别工具类
    基于 ddddocr 提供通用的图形验证码识别功能。
    """

    def __init__(self):
        """
        初始化 OCR 引擎
        关闭 ddddocr 的广告输出，保持控制台整洁。
        """
        self.ocr = ddddocr.DdddOcr(show_ad=False, beta=True)

    def classify(self, image_bytes: bytes) -> str:
        """
        根据图片字节流识别字符
        :param image_bytes: 图片的二进制数据 (bytes)
        :return: 识别出的验证码文本内容 (str)
        """
        code = self.ocr.classification(image_bytes).lower()
        log("OCR", f"识别结果: {code}")
        return code

    def classify_from_file(self, image_path: str) -> str:
        """
        从本地文件读取并识别验证码
        :param image_path: 图片文件的绝对路径
        :return: 识别出的验证码文本内容
        """
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        return self.classify(image_bytes)
