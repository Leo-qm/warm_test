from utils.request_helper import RequestHelper
from utils.config import Config

def test_api_login():
    config = Config()
    url = f"{config.api_url}/login"
    payload = {"username": "admin", "password": "123"}
    response = RequestHelper.request("POST", url, json=payload)
    assert response.status_code == 200
