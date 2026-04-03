# WARM 移动端代码分析报告 — 全链路自动化测试准备

本报告基于 `warm_mobile` (uni-app) 的代码分析，旨在梳理移动端的页面结构、组件特征以及表单数据逻辑，为接下来的“移动端 + PC 端”全链路自动化测试打下基础。

## 1. 技术栈与测试选型概览

| 分类 | 技术/工具 | 说明 |
|------|-----------|------|
| 框架核心 | uni-app (Vue 2) | 编译到H5、小程序或APP跨端框架 |
| UI 库 | uView UI 1.8.6 | 核心组件库，类名多包含 `u-` |
| 状态管理 | Vuex | 管理坐标、用户信息等全局状态 |
| 网络请求 | 内部封装 `utils/request.js` | 统一处理 Token 拦截、刷新、租户隔离 |
| **测试建议选型** | **Playwright (Mobile Emulation)** | 若可编译为 H5 运行，使用 Playwright 的设备模拟（如 `devices['iPhone 12']`）是投入产出比最高的方案，可与目前 PC 测试框架无缝集成。 |
| **替代选型** | **Minium / Airtest** | 若必须在真实的微信小程序或 App 环境运行，则需引入相关自动化方案。 |

---

## 2. 核心业务页面路由地图

进入移动端页面配置在 `pages.json`，核心模块如下：

| 模块 | 页面文件 | 路由路径 | 功能说明及测试关注点 |
|------|----------|----------|----------------------|
| **登录模块** | `pages-home/login/index.vue` | `/pages-home/login/index` | 移动端测试入口。支持验证码、获取短信等。包含首登强制引导协议弹窗。 |
| **工作台** | `pages/declaration-business/index.vue`| `/pages/declaration-business/index` | 申报业务入口。 |
| **申报列表** | `pages/declaration-business/village/index.vue` | `/pages/declaration-business/village/index` | 申报清单列表。注意：点击新增有弹窗选择“设备新增”或“设备更新”。 |
| **设备新增** | `pages/.../village/subsidy-declaration.vue` | `/pages/declaration-business/village/subsidy-declaration` | **核心长表单页**。通过锚点滚动(`pageScrollTo`)实现视口内定位。 |
| **设备更新** | `pages/.../village/equipment-update-declaration.vue`| `/pages/declaration-business/village/equipment-update-declaration`| **设备更新表单**。类似于新增，但带有前置的身份检索逻辑。 |
| **审核列表** | `pages/examine/index.vue` | `/pages/examine/index` | 根据角色(village_manager等)自动重定向到村/镇级审核页。 |
| **审核详情** | `pages/declaration/equipmentNewAudit.vue` | `/pages/declaration/equipmentNewAudit` | 审核设备新增数据的落地页。 |
| **申报台账** | `pages/ledger/index.vue` | `/pages/ledger/index` | 台账列表，包含上传补贴材料入口。 |
| **补贴上传** | `pages/ledger/subsidy-materials-upload.vue`| `/pages/ledger/subsidy-materials-upload` | 用户上传发票、现场比对图片等的核心业务页。 |

---

## 3. DOM 结构与自动化测试选择器策略

由于 uni-app 最终编译的特殊性，测试时需要注意元素定位和操作方式：

### 3.1 输入与表单组件
- **输入框**：使用底层的 `<input class="uni-input">` 或 uView 的组件。
  - 定位策略建议：使用文本关联或 `placeholder` 定位，例如 `page.locator("input[placeholder*='手机号码']")`。
- **选择器 (Picker)**：一般为底部划出的选择面板 (`u-picker` 或原生的 `picker`)。
  - 测试注意：选中选项后，需要显式点击“确定”才能完成值绑定。
- **长表单视口与滚动**：
  - 各个表单区块用 `<view id="sec-household" class="form-sec">` 划分。如果 Playwright 无法自动滚动到元素，可能需要调用原生滑动逻辑或在元素上触发点击前使用 `.scrollIntoViewIfNeeded()`。

### 3.2 弹窗与确认框
- **权限与协议同意弹窗** (Login页)：
  登录页有强制引导弹窗：`.popup-box-chat`。首次登录必须点击 `.guide-button-wrapper .confirm-btn`。
- **类型选择弹窗** (申报列表页)：
  点击新增会触发弹窗 `DeclarationTypeDialog`，需要从弹窗内点击对应类型才能跳转到填表页。

### 3.3 列表与无限滚动
- 移动端列表多使用 `<scroll-view>` 以及基于 `@scrolltolower` (下拉触底) 进行分页加载。
- **测试难点**：自动化验证分页加载时，需要模拟容器内的高频 Swipe 向下滚动事件或直接注入触底事件。
- 行内操作：通过定位卡片 `.card` 并查找内部按钮如 `.action-submit`（提交）、`.action-edit`（编辑）。针对“更多操作”如果是在滑动滑块内，则需先模拟左滑。

---

## 4. 数据字典与前后端桥接逻辑 (核心大坑预警 ⚠️)

移动端 `utils/formDataConverter.js` 是全链路中极易引发数据断层的地方，必须重点测试：

### 4.1 核心职能
因为移动端继承了部分前端组件的驼峰命名(`camelCase`)习惯或老版数据协议，在保存往后端发请求前，会通过 `convertToNewFormat()` 强制洗为 `snake_case`；反之列表或详情回显时，由 `convertToOldFormat()` 洗回来。同时还要处理文件数组中携带的 `uid` 以及关联审核记录的状态(`auditOpinion`, `auditStatus`)。

**关键字段转换映射 (ARCHIVE_INFO_FIELD_MAP):**
* `householdHeadName` $\rightarrow$ `household_name`
* `idCard` $\rightarrow$ `household_id_card`
* `customerNumber` $\rightarrow$ `customer_number`
* `installationAddress` $\rightarrow$ `install_address`
* `houseNumber` $\rightarrow$ `house_number`

### 4.2 设备更新隔离字段 (Update vs Applicant)
在设备更新模式下 (`isUpdateMode === true`)，为了防范更新申报数据污染或覆盖掉“初次安装时（资格申报）”的历史快照，引入了强隔离机制：
* 原有字段 `applicant_name` 在更新阶段必须从 `update_applicant_name` 中读写。
* 证书附件等也从 `applicant_equipment_photo` 变成了 `update_applicant_equipment_photo`。

> **自动化测试建议** $\rightarrow$ 服务端接口或端到端验证时，如果涉及设备更新流，断言及Mock时极度容易用错键名，请务必核对 `update_` 前缀及其在转换器内的转换映射规则。

---

## 5. 多端全链路测试（Mobile + PC）规划建议

考虑到我们已有的 `warm_test` 仓库使用 Playwright-Python 框架，可通过在运行时启动 Mobile Emulation，做到在单个 Test Case 中跑通从移动端上报到 PC 端审核的完整闭环。

### 5.1 流程剧本：基础设备新增全链路
1. **[步骤一：移动端申报]**
    - 创建一个带 Mobile 视窗（如 `viewport={'width': 375, 'height': 812}`、及相应 user-agent）的 Context。
    - **[角色: 农户/网格员]** 登录移动端，勾选协议，进入主页和申报业务。
    - 填写并上报“设备新增”表单。上传身份正反面和基本资料。验证移动端台账列表页面状态切换为“待审批”。
2. **[步骤二：PC端初审驳回测试]**
    - 另开一个大屏 Context。
    - **[角色: 村级管理员]** 登录 PC 审核大厅，定位该移动端发起的表单，并在任一组件块加上驳回意见后驳回。
3. **[步骤三：移动端申诉与修正]**
    - 回到移动端 Context，刷新台账列表。检查是否出现“资格审核驳回”状态 (`isAppealMode` 展现红字驳回意见)。
    - **[角色: 农户/网格员]** 进入编辑并重提。
4. **[步骤四：PC端闭环]**
    - **[角色: 镇级管理员]** PC 端接手完成资格审批，移动端再提交补贴材料，PC端完成补贴终审。记录台账和归档完成。

### 5.2 现有框架调整点 (Action Items)

- **PO 模型补齐**：需在 `warm_test/pages` 目录下新增移动端专属 Page Object（如 `MobileLoginPage`、`MobileDeclarationPage`），继承 `BasePage` 但选择器适配 H5 类名或 `placeholder`。
- **环境隔离配置**：需要查明或配置当前 uni-app H5 模式下的入口地址（一般类似于 `http://localhost:8080/` 或者测试环境的 `/h5/` 网关），并在 `utils/config.py` 中补充 `MOBILE_URL` 常量。
- **权限跳过与Mock**：移动端代码中包含了如获取经纬度、拍照授权、录音授权等(`userLocation`, `getSysCamera`, `getSysRecord`) 逻辑。在 Playwright 配置中需提前注入 Browser Context 的 `geolocation` 权限并授权：`context.grant_permissions(['geolocation'])`，免于被运行时出现的白屏拦截死锁。
