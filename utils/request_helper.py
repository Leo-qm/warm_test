import requests
from loguru import logger

class RequestHelper:
    @staticmethod
    def request(method, url, **kwargs):
        logger.info(f"发送请求: {method} {url} 参数: {kwargs}")
        response = requests.request(method, url, **kwargs)
        logger.info(f"收到响应: {response.status_code} {response.text}")
        return response
