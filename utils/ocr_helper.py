# -*- coding: utf-8 -*-
import ddddocr
from utils.logger import log

class OCRHelper:
    """验证码识别（封装 ddddocr）"""

    def __init__(self):
        self.ocr = ddddocr.DdddOcr(show_ad=False)

    def classify(self, image_bytes: bytes) -> str:
        """识别验证码图片字节流"""
        code = self.ocr.classification(image_bytes)
        log("OCR", f"识别结果: {code}")
        return code

    def classify_from_file(self, image_path: str) -> str:
        """识别验证码图片文件"""
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        return self.classify(image_bytes)
