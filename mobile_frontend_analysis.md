# WARM 移动端代码进阶分析报告 — 全链路自动化测试准备 (加强版)

本报告基于 `warm_mobile` (uni-app) 的深度代码分析，全面梳理了移动端的业务逻辑、组件架构、状态管理、设备权限校验以及核心的表单数据转换，为构建 **“移动端提单 + PC 端审核”全链路 E2E 自动化测试** 提供精准的导航地图。

---

## 1. 架构概览与全局状态管理

### 1.1 技术栈特性
*   **核心框架**：`uni-app (Vue 2)`，兼顾 H5、小程序多端编译。
*   **UI 组件库**：`uView UI 1.8.6`，测试脚本中会大量遇到前缀为 `.u-` 的类名（如 `.u-input`, `.u-picker`）。
*   **网络代理层**：`utils/request.js` 为基座，外加特有的 `api/proxy.js`（`proxyGet`, `proxyPost`），对部分接口增加了 `4201` 等业务状态码的兼容解析。

### 1.2 全局状态 (Vuex Store 与缓存)
移动端的权限验证和用户状态较为分散，测试时若需 Mock 状态或清理缓存，需重点关注：
*   **用户信息存储**：在 `store/modules/user.js` 和缓存中共同维护。`uni.getStorageSync('userInfo')` 和 Vuex 内部均有保存。
*   **角色控制 (Role)**：`roleType`（`village`, `town` 等）控制着页面跳转。例如 `pages/examine/index.vue`（审核容器页）会根据 `roles` 和 `userObj.villageId / townId` 自动重定向至村级 (`village/index.vue`) 或镇级 (`town/index.vue`) 的审核列表。
*   **地理坐标 (Location)**：保存在 Vuex 的 `state.bindList` 和 `state.Area` 中，由逆地理编码解析得出（见后续权限章节）。

---

## 2. 核心业务路由与落地页

| 模块类别 | 页面组件 (`pages.json`) | 核心功能与测试关注点 |
| :--- | :--- | :--- |
| **入口基建** | `pages-home/login/index.vue` | 提供密码、验证码等登录方式。<br>⚠️ **首登弹窗**：带协议同意。 |
| **列表大屏** | `pages/declaration-business/village/index` | 申报清单列表。通过按钮触发弹窗 `DeclarationTypeDialog`，选择新增或更新类型，测试脚本需跨隔离层定位。 |
| **设备新增** | `pages/.../village/subsidy-declaration.vue` | 核心长表单。组件块化布局，依赖视口锚点滚动。 |
| **设备更新** | `pages/.../village/equipment-update-declaration` | 类似于新增，包含针对老设备数据的 `isUpdateMode = true` 逻辑。 |
| **审核列表** | `pages/examine/town/index.vue` 等 | 根据角色分为村镇不同视图。依靠滚动加载(`@scrolltolower`)，测试需模拟页面 `swipe` 实现翻页验证。 |
| **审核详情** | `pages/declaration/equipmentNewAudit.vue`<br>`pages/declaration/equipmentUpdateAudit.vue` | 审核大页。<br>依靠 **`auditPhase`** 参数区分「资格审核阶段(0)」与「补贴审核阶段(1)」，进而控制各块 Tab 及内部组件读写状态。 |

---

## 3. 移动端特有权限拦截 (自动化雷区 ⚠️)

移动端大量调用了原生或 Web 浏览器的设备 API，在 `utils/power.js` 中进行了封装：
*   **定位服务 (`scope.userLocation`)**：`userLocation()` 和 `fnGetlocation()` 。若被调用时未赋权，将阻断页面渲染并弹出需要用户确认的 `showModal`。
*   **摄像头与麦克风 (`scope.camera`, `scope.record`)**：在上传图片组或人脸识别环节被唤醒。

> **自动化解法**：在 Playwright 启动 `BrowserContext` 时，**必须** 显式授予这些权限：
> ```python
> context = browser.new_context(
>     geolocation={"longitude": 116.397128, "latitude": 39.916527},
>     permissions=["geolocation", "camera", "microphone"]
> )
> ```

---

## 4. 表单转换与前后端双向绑定机制 (高故障率区域 ⚠️)

无论是 PC 还是移动端，`utils/formDataConverter.js` 都是最脆弱、最体现领域逻辑的地方，移动端的处理甚至比 PC 更加严格：

### 4.1 字段名的「驼峰 ⇄ 蛇形」互转
历史架构导致应用前端使用了驼峰如 `installationAddress`。但后端一律要求蛇形 `install_address`。
*   **映射常量**：如 `householdHeadName` $\rightarrow$ `household_name`。
*   **同步清洗**：在 `convertToNewFormat()` 时，转换器会强制将旧有属性清除替换；如果是数组类型，还要维护文件的 `uid`、`auditStatus` 和 `auditOpinion` 等元数据（`mergeAuditFromSource`）。

### 4.2 设备更新模式的「前缀隔离」
当执行 `EQUIPMENT_UPDATE` 业务线时，为防止修改操作污染了原设备的初始存证，大量核心字段会被 `isUpdateMode` 判断并打上 `update_` 前缀：
*   原生 `applicant_name` 在更新模式中对应 `update_applicant_name`。
*   原生 `applicant_equipment_photo` 对应 `update_applicant_equipment_photo`。

> **测试数据构造建议**：在编写 `DataFactory` 构造接口模拟或 Payload 比对断言时，若执行「设备更新流」，所有的字段提取需加上 `update_` 判断，否则断言必定失败。

---

## 5. 多阶段审核状态的映射关系

前端 `constants/workflowStatus.js` 定义了与后端的协议对应，这是我们使用接口获取状态、下发断言判定的唯一准则：
*   **资格审核** (0, 14)：村级资格=14，镇级资格=0。
*   **补贴审核** (3, 8)：村级补贴=3，镇级补贴=8。
*   **驳回状态** (15, 1, 4, 11, 6)：分散在不同审查节点。

对应的 `EXAMINE_WORKFLOW_STATUS_LIST` 决定了不同身份角色调用列表接口时（如 `getDeclarationPage`）应当传输的状态筛选集合 (`14,3` 或 `0,8`)。

---

## 6. Playwright E2E 测试扩展策略指南

鉴于 `warm_test` 中已有优秀的基于 POM 模式维护的 PC 自动化测试架构，我们可以沿用其思想：

### 6.1 工程层：Mobile 视图模拟
推荐在现有的 `utils/config.py` 与 `test_cases/` 中引入移动设备能力，创建特定的 Mobile 标识，并在 Setup 时通过 Playwright 的设备描述符：
```python
from playwright.sync_api import sync_playwright

def test_mobile_declaration(playwright):
    iphone_12 = playwright.devices['iPhone 12']
    browser = playwright.chromium.launch()
    # 挂载设备信息和免弹窗权限
    context = browser.new_context(**iphone_12, permissions=["geolocation"])
    page = context.new_page()
    # 后续走移动端的 POM
```

### 6.2 业务层：Mobile - PC 协同交互长流程剧本
最体现移动端自动化价值的用例，莫过于模拟现场干部的办公长流转：
1.  **[Device: Phone] 村干部入户**：用带 H5 Emulation 的 `page` 登录 `village`，生成一条 "新增设备"，进入 `subsidy-declaration` 填单并 "提交"。
2.  **[Device: Desktop] 镇审核员批复**：用常规 PC 屏幕的 `page` 登录 `town`，打开审核后台，对刚才产生的数据（按 `orderId` 查询）进行 "驳回"。
3.  **[Device: Phone] 再次确认回退状态**：手机端执行下拉刷新，验证台账卡片上出现 "资格审核驳回" 的红字，且点开后能看到 `auditOpinion`。

通过这份深化分析，您的自动化团队现已完全掌握该体系移动端的内部黑盒运作逻辑。后续可基于此直接向 `warm_test` 添加各类移动端 E2E 脚本。
