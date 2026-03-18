# WARM 自动化测试项目 (warm_test)

本项目是基于 `Pytest` + `Playwright` + `POM (Page Object Model)` 设计模式构建的 Web UI 自动化测试框架。专门用于“清洁取暖设备申报管理”等业务系统的核心功能自动化验证。

## 技术栈

*   **测试框架**: [Pytest](https://docs.pytest.org/) (用于测试用例组织、夹具注入及执行)
*   **Web 自动化工具**: [Playwright](https://playwright.dev/python/) (用于浏览器驱动、无头浏览器测试)
*   **OCR 识别**: [ddddocr](https://github.com/sml2h3/ddddocr) (用于本地化图片验证码识别)
*   **设计模式**: POM (Page Object Model)，将页面元素和操作行为分离，提升代码复用性和可维护性。

## 项目目录结构

```text
warm_test/
├── api/                       # 接口测试层 (预留，处理需绕过 UI 的数据准备等)
├── data/                      # 静态测试数据 (如 account_data.csv)
├── logs/                      # 自动生成的运行日志
├── pages/                     # POM 页面操作对象层
│   ├── base_page.py           # 基础页面封装 (点击、输入、下拉选择等原子防错容错操作)
│   ├── login_page.py          # 登录相关业务
│   └── declaration_page.py    # 申报系统核心填报及管理业务
├── scripts/                   # 运维或执行辅助脚本
├── test_cases/                # 自动化测试用例集
│   ├── e2e/                   # 端到端闭环测试用例
│   ├── regression/            # 回归测试目录
│   └── smoke/                 # 冒烟测试目录
├── utils/                     # 核心工具层
│   ├── config.py              # 全局核心配置 (环境变量、浏览器、超时、账号等)
│   ├── data_factory.py        # 随机业务测试数据生成工厂
│   ├── logger.py              # 自定义日志记录器
│   ├── ocr_helper.py          # 验证码识别集成
│   └── request_helper.py      # HTTP 请求辅助库
├── conftest.py                # Pytest 核心配置文件 (提供浏览器上下文、登录页面等 Fixture)
├── pytest.ini                 # Pytest 运行定制配置
└── requirements.txt           # Python 依赖清单
```

## 环境准备与安装

1.  **安装 Python** (推荐 Python 3.8+)
2.  **安装 Python 依赖库**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **安装 Playwright 浏览器驱动** (运行一次即可):
    ```bash
    playwright install chromium
    ```

## 配置说明 (`utils/config.py`)

所有关键设置统一存放在 `utils/config.py` 中，支持通过修改此处来切换不同环境：

*   **环境切换**: `ENV_TYPE = 'test'` (默认指向测试平台) 或 `'local'` (指向本地联调环境)。
*   **浏览器模式**: `HEADLESS = False` (建议调试时设为False，持续集成时设为True)。
*   **登录配置**: `MAX_LOGIN_RETRIES` (登录重试次数，应对 OCR 精度问题)。
*   **默认账号**: `USER_ROLE` (可配置为 `city`、`district` 等不同角色使用的基准账号)。

## 测试用例执行

项目配置了完整的 `pytest` 标记 (markers: `smoke`, `e2e`, `regression`)。可通过不同的标签灵活运行不同粒度的测试。

### 1. 运行所有用例 (不推荐，耗时较长)
```bash
pytest -vs
```

### 2. 执行冒烟测试 (验证多角色和登录可用)
验证主流程（如多角色的账号验证码登录）是否顺畅：
```bash
pytest -m smoke -vs
```
*注：可通过在用例中使用 `@pytest.mark.parametrize("role", ["village", "town"])` 并配合 `login_page.logout()` 与 `login_page.login(role)` 来动态实现多角色测试。*

### 3. 执行端到端 (E2E) 闭环测试
执行完整复杂的业务链路（例如清洗取暖设备的“新增-查询-查看-修改-删除”闭环）：
```bash
pytest -m e2e -vs
```
*注：该用例内含参数化（parametrize），会自动分别以“户主”和“非户主”两种表单分支执行全流程。*

## 如何编写新用例

1.  在 `test_cases/` 对应子目录（如 `regression/`）中新建以 `test_` 开头的文件。
2.  测试类以 `Test` 开头，测试方法以 `test_` 开头。
3.  直接在方法参数中请求 `conftest.py` 提供的 `fixture`（夹具），例如：
    *   `page`: 提供一个纯净的基础浏览器页面对象。
    *   `logged_in_page`: **推荐使用**，自动为您完成【环境检测 -> 浏览器开启 -> OCR验证码识别登录 -> 导航至首页】的一条龙前置准备。

**示例代码**：
```python
import pytest
from pages.declaration_page import DeclarationPage

@pytest.mark.regression
def test_some_new_feature(logged_in_page):
    # 1. 声明你想操作的 POM 页面，传入具备登录态的 page
    declaration_page = DeclarationPage(logged_in_page)
    
    # 2. 导航与执行动作
    declaration_page.navigate_to_declaration()
    assert declaration_page.search_record("SB20268899") == True
```

## 附件与日志
*   每次运行自动产生的 `test_playwright.log` 存放于 `logs/` 目录中。
*   如遇错误，截图将会自动存储在 `screenshots/` 中（如有开启截图配置）。
